import json
import uuid
from typing import Dict, Any, Literal
from temporalio import activity
from datetime import datetime, timezone

from agent.graph import app as agent_graph
from db.client import get_supabase_client

@activity.defn
async def run_agent_cognitive_loop(
    run_id: str, 
    trigger_type: Literal["start", "scheduled", "signal", "interrupt", "instruction", "resume"], 
    incoming_event: Dict[str, Any]
) -> Dict[str, Any]:
    
    print(f"[{run_id}] Running cognitive loop. Trigger: {trigger_type}")
    
    # 1. Fetch current run state from DB
    sb = get_supabase_client()
    res = sb.table("runs").select("*, supervisors(base_instruction, available_actions, wake_aggressiveness, model_config)").eq("id", run_id).execute()
    
    if not res.data:
        raise ValueError(f"Run {run_id} not found in DB")
        
    run_record = res.data[0]
    supervisor = run_record["supervisors"]
    
    # 2. Build Agent State
    initial_state = {
        "run_id": run_id,
        "trigger_type": trigger_type,
        "incoming_event": incoming_event,
        "base_instruction": supervisor["base_instruction"],
        "order_context": run_record["order_context"],
        "wake_aggressiveness": supervisor["wake_aggressiveness"],
        "model_config": supervisor["model_config"],
        "available_actions": supervisor["available_actions"],
        "memory_summary": run_record.get("memory_summary", "No prior memory."),
        "run_instructions": run_record.get("instructions", []),
        "wake_guidance": run_record.get("wake_guidance")
    }
    
    # 3. Invoke LangGraph
    final_state = agent_graph.invoke(initial_state)
    
    # 4. Save updated state back to DB (memory, wake_guidance, etc.)
    update_payload = {}
    if "new_memory_summary" in final_state:
        update_payload["memory_summary"] = final_state["new_memory_summary"]
    if "new_wake_guidance" in final_state:
        update_payload["wake_guidance"] = final_state["new_wake_guidance"]
        
    if update_payload:
        sb.table("runs").update(update_payload).eq("id", run_id).execute()
        
    next_wake_up_at = final_state.get("next_wake_up_at")
    
    return {
        "new_memory": final_state.get("new_memory_summary"),
        "next_sleep": next_wake_up_at.isoformat() if next_wake_up_at else None,
        "recommend_close": final_state.get("recommend_close", False)
    }

@activity.defn
async def run_final_summary_activity(run_id: str) -> Dict[str, Any]:
    print(f"[{run_id}] Running final summary activity...")
    
    sb = get_supabase_client()
    res = sb.table("runs").select("*, supervisors(base_instruction)").eq("id", run_id).execute()
    if not res.data:
        return {}
        
    run_record = res.data[0]
    
    # Fetch all activities for this run
    act_res = sb.table("activities").select("*").eq("run_id", run_id).order("timestamp", desc=False).execute()
    timeline = act_res.data
    
    # Use LLM to generate final outputs
    from langchain_groq import ChatGroq
    from pydantic import BaseModel, Field
    from langchain_core.messages import SystemMessage
    
    class FinalSummaryOutput(BaseModel):
        final_summary: str = Field(description="Narrative summary of the entire order lifecycle.")
        important_actions_taken: str = Field(description="Bullet points of key actions taken.")
        key_learnings: str = Field(description="Any patterns or anomalies noticed.")
        feedback_recommendations: str = Field(description="Process improvements recommended.")
        
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2).with_structured_output(FinalSummaryOutput)
    
    prompt = f"""
    You are finalizing an order supervisor run.
    Order ID: {run_record['order_id']}
    Order Context: {json.dumps(run_record['order_context'])}
    Base Instruction: {run_record['supervisors']['base_instruction']}
    
    Full Timeline:
    {json.dumps(timeline, default=str)}
    
    Generate the final outputs.
    """
    
    result = llm.invoke([SystemMessage(content=prompt)])
    
    # Save to DB
    sb.table("runs").update({
        "status": "completed",
        "final_summary": result.final_summary,
        "important_actions_taken": result.important_actions_taken,
        "key_learnings": result.key_learnings,
        "feedback_recommendations": result.feedback_recommendations,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", run_id).execute()
    
    # Log the final output activity
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "final_output",
        "name": "Final Summary Generated",
        "payload": result.model_dump()
    }).execute()
    
    return result.model_dump()
