from langgraph_swarm import create_swarm
from agents.definitions import agents
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()

# Build the Swarm Graph
graph = create_swarm(agents, default_active_agent="Triage").compile(checkpointer=checkpointer)
