import uuid
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from temporalio.client import Client
from typing import List, Dict, Any
from datetime import datetime, timezone

from db.client import get_supabase_client
from db.models import (
    SupervisorTemplateCreate, SupervisorTemplate, 
    RunCreate, RunResponse, EventSignal, InstructionSignal
)
from temporal.workflows import OrderSupervisorWorkflow
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Order Supervisor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



async def get_temporal_client() -> Client:
    return await Client.connect("localhost:7233")

# --- Supervisor Endpoints ---

@app.post("/api/supervisors", response_model=SupervisorTemplate)
async def create_supervisor(template: SupervisorTemplateCreate):
    sb = get_supabase_client()
    new_id = str(uuid.uuid4())
    payload = {
        "id": new_id,
        "name": template.name,
        "base_instruction": template.base_instruction,
        "available_actions": template.available_actions,
        "wake_aggressiveness": template.wake_aggressiveness,
        "model_config": template.model_config,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    try:
        res = sb.table("supervisors").insert(payload).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/supervisors", response_model=List[SupervisorTemplate])
async def list_supervisors():
    sb = get_supabase_client()
    try:
        res = sb.table("supervisors").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/supervisors/{id}", response_model=SupervisorTemplate)
async def get_supervisor(id: str):
    sb = get_supabase_client()
    res = sb.table("supervisors").select("*").eq("id", id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return res.data[0]

# --- Run Endpoints ---

@app.post("/api/runs")
async def start_run(run: RunCreate):
    sb = get_supabase_client()
    # Check supervisor exists
    res = sb.table("supervisors").select("id").eq("id", run.supervisor_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Supervisor not found")
        
    run_id = str(uuid.uuid4())
    payload = {
        "id": run_id,
        "supervisor_id": run.supervisor_id,
        "order_id": run.order_id,
        "status": "running",
        "order_context": run.order_context,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Save to DB
    sb.table("runs").insert(payload).execute()
    
    # Start Temporal Workflow
    client = await get_temporal_client()
    await client.start_workflow(
        OrderSupervisorWorkflow.run,
        run_id,
        id=f"order-workflow-{run_id}",
        task_queue="order-supervisor-queue",
    )
    
    return {"run_id": run_id, "message": "Run started successfully"}

@app.get("/api/runs", response_model=List[RunResponse])
async def list_runs():
    sb = get_supabase_client()
    res = sb.table("runs").select("*").order("created_at", desc=True).execute()
    return res.data

@app.get("/api/runs/{id}")
async def get_run(id: str):
    sb = get_supabase_client()
    res = sb.table("runs").select("*").eq("id", id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Run not found")
    run_data = res.data[0]
    
    # Also fetch activities
    act_res = sb.table("activities").select("*").eq("run_id", id).order("timestamp", desc=True).execute()
    run_data["activities"] = act_res.data
    return run_data

# --- Temporal Signals ---

async def send_temporal_signal(run_id: str, payload: Dict[str, Any]):
    client = await get_temporal_client()
    workflow_id = f"order-workflow-{run_id}"
    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(OrderSupervisorWorkflow.process_signal, payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send signal: {e}")

@app.post("/api/runs/{run_id}/events")
async def inject_event(run_id: str, event: EventSignal):
    # Log event to DB
    sb = get_supabase_client()
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "incoming_event",
        "name": event.event_type,
        "payload": event.payload
    }).execute()
    
    # Send signal to Temporal
    await send_temporal_signal(run_id, {"type": "event", "event": {"event_type": event.event_type, "payload": event.payload}})
    return {"message": "Event injected"}

@app.post("/api/runs/{run_id}/instructions")
async def add_instruction(run_id: str, instr: InstructionSignal):
    sb = get_supabase_client()
    # Fetch current instructions
    res = sb.table("runs").select("instructions").eq("id", run_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Run not found")
        
    current_instr = res.data[0].get("instructions") or []
    current_instr.append({"instruction": instr.instruction, "timestamp": datetime.now(timezone.utc).isoformat()})
    
    # Update DB
    sb.table("runs").update({"instructions": current_instr}).eq("id", run_id).execute()
    
    # Log instruction
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "manual_instruction",
        "name": "New Instruction",
        "payload": {"instruction": instr.instruction}
    }).execute()
    
    # Send signal
    await send_temporal_signal(run_id, {"type": "instruction"})
    return {"message": "Instruction added"}

@app.post("/api/runs/{run_id}/pause")
async def pause_run(run_id: str):
    sb = get_supabase_client()
    sb.table("runs").update({"status": "paused"}).eq("id", run_id).execute()
    
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "control_action",
        "name": "Pause",
        "payload": {}
    }).execute()
    
    await send_temporal_signal(run_id, {"type": "pause"})
    return {"message": "Run paused"}

@app.post("/api/runs/{run_id}/resume")
async def resume_run(run_id: str):
    sb = get_supabase_client()
    sb.table("runs").update({"status": "running"}).eq("id", run_id).execute()
    
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "control_action",
        "name": "Resume",
        "payload": {}
    }).execute()
    
    await send_temporal_signal(run_id, {"type": "resume"})
    return {"message": "Run resumed"}

@app.post("/api/runs/{run_id}/interrupt")
async def interrupt_run(run_id: str):
    sb = get_supabase_client()
    
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "control_action",
        "name": "Interrupt",
        "payload": {}
    }).execute()
    
    await send_temporal_signal(run_id, {"type": "interrupt"})
    return {"message": "Run interrupted"}

@app.post("/api/runs/{run_id}/terminate")
async def terminate_run(run_id: str):
    sb = get_supabase_client()
    
    sb.table("activities").insert({
        "id": str(uuid.uuid4()),
        "run_id": run_id,
        "activity_type": "control_action",
        "name": "Terminate",
        "payload": {}
    }).execute()
    
    await send_temporal_signal(run_id, {"type": "terminate"})
    return {"message": "Run termination signal sent"}
