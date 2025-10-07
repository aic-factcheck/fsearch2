# 🧠 FactSearch2 — Backend

> **Automated Fact-Checking Pipeline**  
> Retrieval → Analysis → Verdict Generation 🕵️‍♀️  

---

## ⚙️ Overview

**FactSearch2** is the backend component of an automated fact-checking system.  
It retrieves evidence from the open web and generates structured verdicts based on optimized prompts and hierarchical document analysis.

🔗 For the frontend implementation, see: [FactSearch2 Frontend](https://github.com/aic-factcheck/fsearch2-front)

---

## 🔍 Evidence Retrieval

- 🌐 **Open-world search** powered by the *Google Search API* via [**Serper**](https://serper.dev)
- 🧩 Based on [ClaimeAI](https://github.com/aic-factcheck/ClaimeAI)
- 📝 Enhanced with **Markdown conversion** for structured text analysis

---

## 🧾 Verdict Generation

- 🧠 **Prompt optimization** trained on real-world fact-checking data from [Demagog.cz](https://demagog.cz) *(integration link coming soon!)*
- 🧰 Uses [PromptOpt](https://github.com/aic-factcheck/prompt_opt) for fine-tuning model prompts  
- 📜 Default verdict-generation prompt: [`generate_verdict_instructions_v2.txt`](./data/templates/generate_verdict_instructions_v2.txt)
- 🧱 **Hierarchical representation** of Markdown documents with structure-aware chunking for contextual reasoning
- 🔗 **Each generated verdict includes explicit references** to the evidence documents used to justify the claim assessment

---

## 🛠️ Installation & Configuration

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate   # on macOS / Linux
# or
.venv\Scripts\activate      # on Windows
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the project root:

```bash
# ⚠️ Keep your API keys private. Never commit them to GitHub!

OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=your_serper_key_here
```

---

## 💾 FastText Vectors

Semantical Markdown chunking requires **FastText word embeddings**.
You need to place the model files in:

```
data/fasttext/vectors
```

### For English vectors:

```bash
wget https://dl.fbaipublicfiles.com/fasttext/vectors-crawl/cc.en.300.bin.gz
gunzip -d cc.en.300.bin.gz
```

After extraction, you should have:

```
data/fasttext/vectors/cc.en.300.bin
```

> 📘 You can use other FastText languages by placing their corresponding `.bin` files in the same directory and fix configuration [here](./fsearch2/fact_search/config/nodes.py) and [here](./fsearch2/claim_verifier/config/nodes.py).

---

## 👥 User Management

To add new users:

```bash
python fsearch2/create_user.py <user_name>
```

* New users are stored in `users.json`
* Ensure `users.json` is writable by the backend service

---

## 🧩 Project Structure

```
fsearch2/
├── claim_verifier/
│   └── config/               # Retrieval node configuration files
├── fact_search/
│   ├── agent.py              # LangGraph pipeline definition
│   └── config/               # Verdict generation node configuration files
├── ws_server.py              # WebSocket server entry point
├── create_user.py            # CLI script for user management
└── ...
```

---

## 🚀 Running the Server

Make sure your `PYTHONPATH` includes the project root:

```bash
export PYTHONPATH=.:fsearch2:$PYTHONPATH
uvicorn fsearch2.ws_server:app --reload --port 8413
```

---

## 📜 License

This project is licensed under the **MIT License** — see [`LICENSE`](./LICENSE) for details.

---

## 💡 Acknowledgements
* 🌐 [CEDMO](https://cedmohub.eu) — Central European Digital Media Observatory supporting research & infrastructure for open knowledge, media analysis, and fact-checking
* 🧠 [Demagog.cz](https://demagog.cz) for real-world fact-checking data
