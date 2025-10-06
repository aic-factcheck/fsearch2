import logging

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from claim_verifier.nodes import (
    evaluate_evidence_node,
    generate_search_query_node,
    retrieve_evidence_node,
    search_decision_node,
)
from claim_verifier.schemas import ClaimVerifierState

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph() -> CompiledStateGraph:
    """Set up the iterative claim verification workflow.

    The pipeline follows these steps:
    1. Generate search query for a claim
    2. Retrieve evidence from web search
    3. Decide whether to continue searching or evaluate
    4. Either generate new query or make final evaluation
    """
    workflow = StateGraph(ClaimVerifierState)

    workflow.add_node("generate_search_query", generate_search_query_node)
    workflow.add_node("retrieve_evidence", retrieve_evidence_node)
    workflow.add_node("search_decision", search_decision_node)
    workflow.add_node("evaluate_evidence", evaluate_evidence_node)

    workflow.set_entry_point("generate_search_query")

    workflow.add_edge("generate_search_query", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "search_decision")
    # search_decision node returns Command objects, so no conditional edge needed
    workflow.add_edge("evaluate_evidence", END)

    return workflow.compile()


graph = create_graph()
