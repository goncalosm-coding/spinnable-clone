from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import TypedDict, Annotated, Sequence
import operator

from app.tools import all_tools
from app.tools.read_latest_email import AGENT_CONTEXT
from app.core.config import settings

# State definition — what the agent carries between steps
class AgentState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    worker_name: str
    worker_role: str
    business_context: str
    tenant_id: str
    worker_id: str
    user_id: str

# Initialize LLM with tools bound
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=settings.OPENAI_API_KEY
)


def resolve_skills_for_role(worker_role: str) -> dict[str, bool]:
    """Return default permissions based on worker role/title."""
    role = (worker_role or "").lower()

    base = {
        "gmail_read": False,
        "gmail_send": False,
        "calendar_read": False,
        "calendar_write": False,
        "web_research": True,
        "notes_write": True,
    }

    if any(k in role for k in ["assistant", "executive", "operations", "support"]):
        base["gmail_read"] = True
        base["gmail_send"] = True
        base["calendar_read"] = True
        base["calendar_write"] = True
    elif any(k in role for k in ["sales", "account manager", "customer success"]):
        base["gmail_read"] = True
        base["gmail_send"] = True
    elif any(k in role for k in ["research", "analyst"]):
        base["web_research"] = True
        base["notes_write"] = True

    return base


def tools_for_skills(skills: dict[str, bool]):
    """Enable only tools permitted by role-based skills."""
    tool_by_name = {tool.name: tool for tool in all_tools}
    enabled_tools = []

    if skills.get("web_research") and "web_search" in tool_by_name:
        enabled_tools.append(tool_by_name["web_search"])
    if skills.get("notes_write") and "take_note" in tool_by_name:
        enabled_tools.append(tool_by_name["take_note"])
    if skills.get("gmail_send") and "send_email" in tool_by_name:
        enabled_tools.append(tool_by_name["send_email"])
    if skills.get("gmail_read") and "read_latest_email" in tool_by_name:
        enabled_tools.append(tool_by_name["read_latest_email"])

    return enabled_tools

def build_system_prompt(state: AgentState) -> str:
    skills = resolve_skills_for_role(state["worker_role"])
    granted = [name for name, allowed in skills.items() if allowed]
    denied = [name for name, allowed in skills.items() if not allowed]

    return f"""You are {state['worker_name']}, an AI worker with the role of {state['worker_role']}.

Business context:
{state['business_context']}

Granted skills/permissions:
{", ".join(granted) if granted else "none"}

Restricted skills/permissions:
{", ".join(denied) if denied else "none"}

When a user asks for an action that needs a restricted skill (example: read/send Gmail),
do not pretend it is done. Ask for explicit permission and explain exactly what access is needed.
Only use tools that map to granted permissions.

You are helpful, proactive, and professional.
Always respond concisely and actionably."""

def agent_node(state: AgentState):
    """Main reasoning step — LLM decides what to do next."""
    system_prompt = build_system_prompt(state)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    role_skills = resolve_skills_for_role(state["worker_role"])
    role_tools = tools_for_skills(role_skills)
    llm_with_role_tools = llm.bind_tools(role_tools)
    response = llm_with_role_tools.invoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Route: if the last message has tool calls, go to tools. Otherwise end."""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

# Build the graph
tool_node = ToolNode(all_tools)

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
graph.add_edge("tools", "agent")

worker_graph = graph.compile()


async def run_agent(
    user_message: str,
    conversation_history: list,
    worker_name: str,
    worker_role: str,
    business_context: str,
    tenant_id: str,
    worker_id: str,
    user_id: str,
) -> str:
    """Run the agent and return its final text response."""
    history_messages = []
    for msg in conversation_history:
        if msg["role"] == "user":
            history_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history_messages.append(AIMessage(content=msg["content"]))

    history_messages.append(HumanMessage(content=user_message))

    context_token = AGENT_CONTEXT.set({"tenant_id": tenant_id, "user_id": user_id})
    try:
        result = await worker_graph.ainvoke({
            "messages": history_messages,
            "worker_name": worker_name,
            "worker_role": worker_role,
            "business_context": business_context,
            "tenant_id": tenant_id,
            "worker_id": worker_id,
            "user_id": user_id,
        })
    finally:
        AGENT_CONTEXT.reset(context_token)

    return result["messages"][-1].content