from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from typing import TypedDict, Annotated, Sequence
import operator

from app.tools import all_tools
from app.core.config import settings

# State definition — what the agent carries between steps
class AgentState(TypedDict):
    messages: Annotated[Sequence, operator.add]
    worker_name: str
    worker_role: str
    business_context: str
    tenant_id: str
    worker_id: str

# Initialize LLM with tools bound
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=settings.OPENAI_API_KEY
)
llm_with_tools = llm.bind_tools(all_tools)

def build_system_prompt(state: AgentState) -> str:
    return f"""You are {state['worker_name']}, an AI worker with the role of {state['worker_role']}.

Business context:
{state['business_context']}

You are helpful, proactive, and professional. You have access to tools to search the web, 
send emails, and save notes. Use them when needed to complete tasks.
Always respond concisely and actionably."""

def agent_node(state: AgentState):
    """Main reasoning step — LLM decides what to do next."""
    system_prompt = build_system_prompt(state)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
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
) -> str:
    """Run the agent and return its final text response."""
    history_messages = []
    for msg in conversation_history:
        if msg["role"] == "user":
            history_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            history_messages.append(AIMessage(content=msg["content"]))

    history_messages.append(HumanMessage(content=user_message))

    result = await worker_graph.ainvoke({
        "messages": history_messages,
        "worker_name": worker_name,
        "worker_role": worker_role,
        "business_context": business_context,
        "tenant_id": tenant_id,
        "worker_id": worker_id,
    })

    return result["messages"][-1].content