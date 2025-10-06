import logging
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from claim_verifier.nodes import (
    generate_search_query_node,
    retrieve_evidence_node,
    search_decision_node,
)
from fact_search.nodes import evaluate_evidence_node, mock_retrieve_evidence_node

from claim_verifier.schemas import ClaimVerifierState

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def create_graph() -> CompiledStateGraph:
    """Set up the iterative claim verification workflow with caching per claim."""
    workflow = StateGraph(ClaimVerifierState)
    
    # DEBUGGING VERDICT GENERATION
    # workflow.add_node("mock_retrieve_evidence", mock_retrieve_evidence_node)
    # workflow.add_node("evaluate_evidence", evaluate_evidence_node)
    # workflow.set_entry_point("mock_retrieve_evidence")
    # workflow.add_edge("mock_retrieve_evidence", "evaluate_evidence")
    
    workflow.add_node("generate_search_query",  generate_search_query_node)
    workflow.add_node("retrieve_evidence", retrieve_evidence_node)
    workflow.add_node("search_decision", search_decision_node)
    workflow.add_node("evaluate_evidence", evaluate_evidence_node, context={"text_reducer": "TBD"})
    workflow.set_entry_point("generate_search_query")
    workflow.add_edge("generate_search_query", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "search_decision")
    
    workflow.add_edge("evaluate_evidence", END)

    return workflow.compile()
