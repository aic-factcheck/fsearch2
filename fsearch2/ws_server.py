import json
import secrets
import asyncio
import logging
from datetime import datetime, timedelta
import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Query,
    Request,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from passlib.context import CryptContext

from claim_verifier.schemas import ClaimVerifierState, LoginRequest, ValidatedClaim
from fact_search.agent import create_graph
from aic_nlp_utils.json import write_json

from fsearch2.fact_search.config.nodes import TEXT_REDUCER_CONFIG
from fsearch2.utils.text_reducer import TextReducer

# -------------------------------------------------
load_dotenv()

text_reducer = TextReducer(vectors=TEXT_REDUCER_CONFIG["vectors"])
logger = logging.getLogger("fsearch2")
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# CORS (development: vite dev server on 5174). Update for production.
ALLOWED_ORIGINS = ["http://localhost:5174", "http://localhost:4173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Users file (admin script writes this)
USERS_FILE = Path("users.json")
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Cookie/session configuration
COOKIE_NAME = "fs2_session"
SESSION_TTL_HOURS = 8
COOKIE_SAMESITE = "lax"  # 'none' for cross-site prod
COOKIE_SECURE = False     # True for HTTPS prod

# In-memory auth sessions (token -> {username, expires})
AUTH_SESSIONS: Dict[str, Dict[str, Any]] = {}
claim_sessions: Dict[str, Dict[str, Any]] = {}


# ---------- helpers ----------
def load_users() -> Dict[str, Any]:
    if not USERS_FILE.exists():
        return {}
    try:
        return json.loads(USERS_FILE.read_text())
    except Exception:
        logger.exception("Failed to load users.json")
        return {}


def verify_user_password(username: str, password: str) -> bool:
    users = load_users()
    user = users.get(username)
    if not user:
        return False
    pw_hash = user.get("password_hash")
    if not pw_hash:
        return False
    try:
        return pwd_context.verify(password, pw_hash)
    except Exception:
        logger.exception("Error verifying password for %s", username)
        return False


def create_auth_session(username: str, ttl_hours: int = SESSION_TTL_HOURS) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=ttl_hours)
    AUTH_SESSIONS[token] = {"username": username, "expires": expires.isoformat()}
    logger.info("Created session for %s, token=%s (expires=%s)", username, token, expires)
    return token


def get_username_from_session(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    session = AUTH_SESSIONS.get(token)
    if not session:
        return None
    try:
        expires = datetime.fromisoformat(session["expires"])
    except Exception:
        AUTH_SESSIONS.pop(token, None)
        return None
    if expires < datetime.utcnow():
        AUTH_SESSIONS.pop(token, None)
        return None
    return session["username"]


def destroy_session(token: Optional[str]):
    if token:
        AUTH_SESSIONS.pop(token, None)


async def _cleanup_sessions_loop():
    while True:
        try:
            now = datetime.utcnow()
            expired = [t for t, s in AUTH_SESSIONS.items()
                       if datetime.fromisoformat(s["expires"]) < now]
            for t in expired:
                AUTH_SESSIONS.pop(t, None)
            await asyncio.sleep(60 * 5)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Session cleanup error")


@app.on_event("startup")
async def startup_tasks():
    asyncio.create_task(_cleanup_sessions_loop())


# ---------- auth endpoints ----------
@app.post("/api/login")
async def login(req: LoginRequest):
    if not verify_user_password(req.username, req.password):
        return JSONResponse(status_code=401, content={"detail": "Invalid username or password"})
    token = create_auth_session(req.username)
    resp = JSONResponse({"ok": True, "username": req.username})
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=SESSION_TTL_HOURS * 3600,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )
    return resp


@app.post("/api/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    destroy_session(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


@app.get("/api/me")
async def me(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    username = get_username_from_session(token)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": username}


# ---------- WebSocket ----------
@app.websocket("/ws/claims/{claim_id}")
async def ws_claim(websocket: WebSocket, claim_id: str, last_seq: int = Query(default=0)):
    await websocket.accept()
    token = websocket.cookies.get(COOKIE_NAME)
    username = get_username_from_session(token)

    if not username:
        try:
            await websocket.send_json({
                "type": "error",
                "error": "Unauthorized: please login first",
                "message": "Unauthorized: please login first",
                "seq": 0,
                "claim_id": claim_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass
        await websocket.close(code=4001)
        logger.info("Unauthorized websocket connection attempt to claim %s", claim_id)
        return

    logger.info("New WS connection user=%s claim_id=%s", username, claim_id)

    session = claim_sessions.get(claim_id)
    if session:
        missed = [u for u in session["updates"] if u.get("seq", -1) > last_seq]
        for msg in missed:
            try:
                await websocket.send_json(msg)
            except Exception:
                logger.exception("Failed to send missed msg to %s", claim_id)
        if session.get("done"):
            await websocket.send_json({
                "type": "graph_complete",
                "claim_id": claim_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
    else:
        # Expect initial claim_text
        try:
            init_msg = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "error": "No claim_text provided within 10s",
                "message": "No claim_text provided within 10s",
                "seq": 0,
                "claim_id": claim_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            await websocket.close(code=4002)
            return

        claim_text = init_msg.get("claim_text", "").strip()
        if not claim_text:
            await websocket.send_json({
                "type": "error",
                "error": "Empty claim_text",
                "message": "Empty claim_text",
                "seq": 0,
                "claim_id": claim_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            await websocket.close(code=4003)
            return

        state = ClaimVerifierState(claim=ValidatedClaim(claim_text=claim_text))
        graph = create_graph()

        claim_sessions[claim_id] = {
            "graph": graph,
            "state": state,
            "seq": 0,
            "updates": [],
            "username": username,
        }

        task = asyncio.create_task(run_graph_and_stream(claim_id, websocket))
        claim_sessions[claim_id]["task"] = task

        def _task_done(t: asyncio.Task):
            try:
                exc = t.exception()
                if exc:
                    logger.exception("Background task for claim_id=%s raised exception", claim_id)
            except asyncio.CancelledError:
                logger.info("Background task for claim_id=%s was cancelled", claim_id)

        task.add_done_callback(_task_done)

    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS disconnected for claim_id=%s (user=%s)", claim_id, username)
        sess = claim_sessions.get(claim_id)
        if sess:
            task = sess.get("task")
            if task and not task.done():
                task.cancel()


# ---------- graph runner ----------
async def run_graph_and_stream(claim_id: str, websocket: WebSocket):
    session = claim_sessions[claim_id]
    graph = session["graph"]
    state = session["state"]

    base_dir = Path("run")
    base_dir.mkdir(exist_ok=True)
    run_dir = base_dir / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir.mkdir()

    try:
        async for chunk in graph.astream(
            state, stream_mode=["debug", "updates"], context={"text_reducer": text_reducer}
        ):
            stream_mode, data = chunk

            if stream_mode == "debug":
                if data.get("type") == "task" and data.get("step") is not None:
                    payload = data["payload"]
                    node_name = payload.get("name", "unknown")
                    session["seq"] += 1
                    input_ = payload.get("input", {})
                    msg = {
                        "type": "node_start",
                        "claim_id": claim_id,
                        "node": node_name,
                        "seq": session["seq"],
                        "status": "started",
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": getattr(input_, "model_dump", lambda: input_)(),
                    }
                    session["updates"].append(msg)
                    try:
                        await websocket.send_json(msg)
                    except Exception:
                        logger.exception("Send failed for claim %s (debug)", claim_id)

            elif stream_mode == "updates":
                for node_name, result in data.items():
                    session["seq"] += 1
                    msg = {
                        "type": "node_update",
                        "claim_id": claim_id,
                        "node": node_name,
                        "seq": session["seq"],
                        "status": "completed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": result,
                    }
                    write_json(run_dir / f"server_{session['seq']:02d}_{node_name}.json", result)
                    if node_name == "evaluate_evidence":
                        session["done"] = True
                    session["updates"].append(msg)
                    try:
                        await websocket.send_json(msg)
                    except Exception:
                        logger.exception("Send failed for claim %s (updates)", claim_id)

    except Exception as e:
        logger.exception("Error while running graph for claim %s", claim_id)
        session["seq"] += 1
        err_msg = {
            "type": "error",
            "claim_id": claim_id,
            "seq": session["seq"],
            "error": str(e),
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
        session["updates"].append(err_msg)
        try:
            await websocket.send_json(err_msg)
        except Exception:
            logger.debug("Failed to send error msg to client %s (socket may be closed)", claim_id)
        session["done"] = True
