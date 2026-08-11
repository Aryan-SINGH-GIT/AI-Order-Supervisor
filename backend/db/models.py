from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class SupervisorTemplate(BaseModel):
    id: str
    name: str
    base_instruction: str
    available_actions: List[str]
    wake_aggressiveness: str = "medium"
    model_config: Dict[str, Any] = {}
    created_at: Optional[datetime] = None

class SupervisorTemplateCreate(BaseModel):
    name: str
    base_instruction: str
    available_actions: List[str]
    wake_aggressiveness: Optional[str] = "medium"
    model_config: Optional[Dict[str, Any]] = {}

class RunCreate(BaseModel):
    supervisor_id: str
    order_id: str
    order_context: Dict[str, Any]

class RunResponse(BaseModel):
    id: str
    supervisor_id: str
    order_id: str
    status: str
    order_context: Optional[Dict[str, Any]] = None
    memory_summary: Optional[str] = None
    wake_guidance: Optional[str] = None
    next_wake_up_at: Optional[datetime] = None
    instructions: List[Dict[str, Any]] = []
    final_summary: Optional[str] = None
    important_actions_taken: Optional[str] = None
    key_learnings: Optional[str] = None
    feedback_recommendations: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class EventSignal(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    
class InstructionSignal(BaseModel):
    instruction: str
