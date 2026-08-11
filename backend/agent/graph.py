import json
import uuid
from typing import Dict, Any, List
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from agent.state import AgentState
from agent.tools import AVAILABLE_TOOLS
from db.client import get_supabase_client

# -- Pydantic Schemas for Structured Outputs --

class ClassifierOutput(BaseModel):
    is_important: bool = Field(description="True if the event warrants waking the main agent, False otherwise.")
    reasoning: str = Field(description="Why this decision was made.")
    escalation_flagged: bool = Field(description="True if the event is highly anomalous or unrecognizable.")

class AgentReasoningOutput(BaseModel):
    reasoning_rationale: str = Field(description="Step-by-step reasoning on what to do next.")
    recommend_close: bool = Field(description="Set to true if the workflow is complete and can be closed.")
    next_wake_up_at: str = Field(description="ISO 8601 timestamp for when to wake up next if not closed. Return an empty string if no timer is needed.")
    wake_guidance: str = Field(description="Guidance for the classifier for the next wake cycle.")

class MemoryCompactionOutput(BaseModel):
    new_memory_summary: str = Field(description="The updated compressed memory summary.")

# -- Node 1: Classifier --
def classify_event(state: AgentState) -> Dict[str, Any]:
    print("[Node 1] Classifying event...")
    if state["trigger_type"] != "signal":
        # Bypass classifier for non-signals
        return {"is_important": True, "reasoning_rationale": "Bypassed classifier due to trigger_type", "escalation_flagged": False}
    
    event = state.get("incoming_event", {})
    if not event:
        return {"is_important": True, "reasoning_rationale": "No event provided, defaulting to wake", "escalation_flagged": False}

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(ClassifierOutput)
    
    prompt = f"""
    You are an event classifier for an order supervisor agent.
    Order Context: {json.dumps(state['order_context'])}
    Current Memory: {state['memory_summary']}
    Wake Guidance from last run: {state.get('wake_guidance', 'None')}
    Aggressiveness: {state.get('wake_aggressiveness', 'medium')}

    Incoming Event: {json.dumps(event)}

    Decide if this event is important enough to wake the main agent. 
    If the event is unrecognizable or highly anomalous, set escalation_flagged to true and is_important to true.
    """
    
    result = structured_llm.invoke([SystemMessage(content=prompt)])
    
    # Log the wake decision to DB
    try:
        sb = get_supabase_client()
        sb.table("activities").insert({
            "id": str(uuid.uuid4()),
            "run_id": state["run_id"],
            "activity_type": "wake_decision",
            "name": "Classifier Decision",
            "payload": result.model_dump()
        }).execute()
    except Exception as e:
        print(f"Error logging classifier decision: {e}")

    return {
        "is_important": result.is_important,
        "reasoning_rationale": result.reasoning,
        "escalation_flagged": result.escalation_flagged
    }

# -- Node 2: Main Agent Reasoning --
def main_agent_reasoning(state: AgentState) -> Dict[str, Any]:
    print("[Node 2] Main Agent Reasoning...")
    model_name = state.get("model_config", {}).get("model", "llama-3.3-70b-versatile")
    llm = ChatGroq(model=model_name, temperature=0.2)
    
    # Bind available tools dynamically
    available_tool_names = state.get("available_actions", [])
    tools_to_bind = [AVAILABLE_TOOLS[name] for name in available_tool_names if name in AVAILABLE_TOOLS]
    
    llm_with_tools = llm.bind_tools(tools_to_bind)
    
    prompt = f"""
    You are the core reasoning engine for an order supervisor.
    Base Instruction: {state['base_instruction']}
    Order Context: {json.dumps(state['order_context'])}
    Memory: {state['memory_summary']}
    Incoming Event: {json.dumps(state.get('incoming_event', {}))}
    Manual Instructions: {json.dumps(state.get('run_instructions', []))}
    Escalation Flagged: {state.get('escalation_flagged', False)}

    Analyze the situation and decide on the next actions. Use tools if necessary.
    """
    
    # We call the LLM once to get tool calls, then we call it again with structured output to get the final state updates.
    # A cleaner approach for LangGraph is to let the LLM return tool calls, and use a separate structured parser for state, 
    # but for simplicity, we can ask it for structured output OR tool calls.
    # Let's use a two-step approach or a single unified schema if we wrap tools.
    # Actually, standard LangChain tool calling handles this by returning a message with tool_calls.
    
    response = llm_with_tools.invoke([SystemMessage(content=prompt)])
    
    # Save tool calls to state so Node 3 can execute them
    # We will pass the response message forward
    return {"_llm_response": response} # Using a temporary key

# -- Node 3: Execute Required Actions --
def execute_actions(state: AgentState) -> Dict[str, Any]:
    print("[Node 3] Executing Actions...")
    response = state.get("_llm_response")
    tool_calls = response.tool_calls if response and hasattr(response, "tool_calls") else []
    
    actions_taken = []
    sb = get_supabase_client()
    
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        if tool_name in AVAILABLE_TOOLS:
            tool_func = AVAILABLE_TOOLS[tool_name]
            try:
                result = tool_func.invoke(tool_args)
                actions_taken.append({"tool": tool_name, "args": tool_args, "result": result})
                
                # Log to DB
                sb.table("activities").insert({
                    "id": str(uuid.uuid4()),
                    "run_id": state["run_id"],
                    "activity_type": "agent_action",
                    "name": tool_name,
                    "payload": {"args": tool_args, "result": result}
                }).execute()
            except Exception as e:
                actions_taken.append({"tool": tool_name, "error": str(e)})
    
    # Now that tools are executed, determine the final state updates (recommend_close, next_wake, etc.)
    model_name = state.get("model_config", {}).get("model", "llama-3.3-70b-versatile")
    llm = ChatGroq(model=model_name, temperature=0).with_structured_output(AgentReasoningOutput)
    
    summary_prompt = f"""
    You just processed an event for order {state['order_context'].get('id', 'unknown')}.
    Actions just taken: {json.dumps(actions_taken)}
    
    Provide your reasoning rationale, whether the workflow should close (recommend_close), 
    and when you need to wake up next (next_wake_up_at in ISO format, or empty string).
    Also provide wake_guidance for the classifier for next time.
    """
    
    result = llm.invoke([SystemMessage(content=summary_prompt)])
    
    # Parse next_wake_up_at
    next_wake = None
    if result.next_wake_up_at:
        try:
            next_wake = datetime.fromisoformat(result.next_wake_up_at.replace('Z', '+00:00'))
        except:
            pass
            
    # Log sleep decision
    try:
        sb.table("activities").insert({
            "id": str(uuid.uuid4()),
            "run_id": state["run_id"],
            "activity_type": "sleep_decision",
            "name": "Sleep Decision",
            "payload": result.model_dump()
        }).execute()
    except Exception as e:
        print(f"Error logging sleep decision: {e}")

    return {
        "reasoning_rationale": result.reasoning_rationale,
        "recommend_close": result.recommend_close,
        "next_wake_up_at": next_wake,
        "new_wake_guidance": result.wake_guidance
    }

# -- Node 4: Compact Memory --
def compact_memory(state: AgentState) -> Dict[str, Any]:
    print("[Node 4] Compacting Memory...")
    # Dynamically triggered based on recent activity count.
    # For POC, we'll fetch recent activities from DB and compact if > N.
    sb = get_supabase_client()
    try:
        res = sb.table("activities").select("*").eq("run_id", state["run_id"]).order("timestamp", desc=True).limit(20).execute()
        recent_activities = res.data
    except Exception as e:
        print(f"Error fetching activities for memory compaction: {e}")
        recent_activities = []
        
    # Simple compaction rule: just summarize the recent activities + old memory
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0).with_structured_output(MemoryCompactionOutput)
    prompt = f"""
    Current Memory: {state['memory_summary']}
    Recent Activities: {json.dumps(recent_activities)}
    
    Write a new, concise memory summary that incorporates the recent activities.
    Keep it strictly factual and under 500 words.
    """
    
    result = llm.invoke([SystemMessage(content=prompt)])
    return {"new_memory_summary": result.new_memory_summary}

# -- Build Graph --
def should_continue(state: AgentState) -> str:
    if state.get("is_important"):
        return "main_agent_reasoning"
    return END

workflow = StateGraph(AgentState)

workflow.add_node("classify_event", classify_event)
workflow.add_node("main_agent_reasoning", main_agent_reasoning)
workflow.add_node("execute_actions", execute_actions)
workflow.add_node("compact_memory", compact_memory)

workflow.set_entry_point("classify_event")

workflow.add_conditional_edges(
    "classify_event",
    should_continue,
    {
        "main_agent_reasoning": "main_agent_reasoning",
        END: END
    }
)

workflow.add_edge("main_agent_reasoning", "execute_actions")
workflow.add_edge("execute_actions", "compact_memory")
workflow.add_edge("compact_memory", END)

app = workflow.compile()
