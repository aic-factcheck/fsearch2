import logging

from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from claim_extractor.nodes import (
    decomposition_node,
    disambiguation_node,
    selection_node,
    sentence_splitter_node,
    validation_node,
)
from claim_extractor.schemas import State

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph() -> CompiledStateGraph:
    """Set up the claim extraction workflow graph.

    The pipeline follows these steps:
    1. Split text into contextual sentences
    2. Filter for sentences with factual content
    3. Resolve ambiguities like pronouns
    4. Extract specific atomic claims
    5. Validate claims are properly formed
    """
    workflow = StateGraph(State)

    # Add nodes
    workflow.add_node("sentence_splitter", sentence_splitter_node)
    workflow.add_node("selection", selection_node)
    workflow.add_node("disambiguation", disambiguation_node)
    workflow.add_node("decomposition", decomposition_node)
    workflow.add_node("validation", validation_node)

    # Set entry point
    workflow.set_entry_point("sentence_splitter")

    # Connect the nodes in sequence
    workflow.add_edge("sentence_splitter", "selection")
    workflow.add_edge("selection", "disambiguation")
    workflow.add_edge("disambiguation", "decomposition")
    workflow.add_edge("decomposition", "validation")

    # Set finish point
    workflow.set_finish_point("validation")

    return workflow.compile()


graph = create_graph()
