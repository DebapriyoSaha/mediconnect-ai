from typing import Annotated, List, Optional, Union

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    next: str
    patient_id: Optional[str]
    appointment_details: Optional[dict]
