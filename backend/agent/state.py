from typing import TypedDict, List, Optional, Any, Dict
from datetime import datetime

class AgentState(TypedDict):
    # Inputs:
    run_id: str
    trigger_type: str
    incoming_event: Optional[Dict[str, Any]]
    base_instruction: str  
    order_context: Dict[str, Any]
    wake_aggressiveness: str # Configured aggressiveness for the classifier
    model_config: Dict[str, Any] # Model overrides for the main agent
    available_actions: List[str] # List of tool names to bind to the agent
    memory_summary: str
    run_instructions: List[Dict[str, Any]]
    wake_guidance: Optional[str] 
    
    # Outputs:
    is_important: bool
    reasoning_rationale: str 
    escalation_flagged: bool 
    recommend_close: bool
    next_wake_up_at: Optional[datetime]
    new_memory_summary: str
    new_wake_guidance: Optional[str]
    _llm_response: Any
