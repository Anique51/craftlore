from langgraph.graph import END, StateGraph

from app.graph import nodes
from app.graph.state import CraftState


def build_graph():
    g = StateGraph(CraftState)
    g.add_node("router", nodes.router)
    g.add_node("rag", nodes.rag)
    g.add_node("mechanics", nodes.mechanics)
    g.add_node("answer", nodes.answer)
    g.add_node("verify", nodes.verify)

    g.set_entry_point("router")
    g.add_conditional_edges("router", lambda s: s["route"],
                            {"lore": "rag", "mechanics": "mechanics"})
    g.add_edge("rag", "answer")
    g.add_edge("mechanics", "answer")
    g.add_edge("answer", "verify")
    g.add_conditional_edges("verify", nodes.after_verify,
                            {"end": END, "answer": "answer"})
    return g.compile()
