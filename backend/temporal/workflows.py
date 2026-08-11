from datetime import timedelta
import asyncio
from typing import Dict, Any, Optional
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from temporal.activities import run_agent_cognitive_loop, run_final_summary_activity

@workflow.defn
class OrderSupervisorWorkflow:
    def __init__(self) -> None:
        self.is_paused = False
        self.terminate_received = False
        self.recommend_close = False
        
        self.signal_queue = []
        self.signal_event = asyncio.Event()

    @workflow.signal
    async def process_signal(self, payload: Dict[str, Any]) -> None:
        signal_type = payload.get("type")
        
        if signal_type == "pause":
            self.is_paused = True
        elif signal_type == "resume":
            self.is_paused = False
            self.signal_queue.append({"trigger_type": "resume", "event": {}})
            self.signal_event.set()
        elif signal_type == "terminate":
            self.terminate_received = True
            self.signal_event.set()
        elif signal_type == "interrupt":
            self.signal_queue.append({"trigger_type": "interrupt", "event": payload.get("event", {})})
            self.signal_event.set()
        elif signal_type == "instruction":
            self.signal_queue.append({"trigger_type": "instruction", "event": {}})
            # Instructions queue silently if paused
            if not self.is_paused:
                self.signal_event.set()
        elif signal_type == "event":
            self.signal_queue.append({"trigger_type": "signal", "event": payload.get("event", {})})
            if not self.is_paused:
                self.signal_event.set()

    @workflow.run
    async def run(self, run_id: str) -> None:
        workflow.logger.info(f"Starting workflow for run: {run_id}")
        
        # Initial trigger
        current_trigger = "start"
        current_event = {}
        
        while not self.terminate_received and not self.recommend_close:
            
            # Execute Cognitive Loop
            result = await workflow.execute_activity(
                run_agent_cognitive_loop,
                args=[run_id, current_trigger, current_event],
                start_to_close_timeout=timedelta(minutes=5),
            )
            
            self.recommend_close = result.get("recommend_close", False)
            next_sleep_iso = result.get("next_sleep")
            
            if self.recommend_close or self.terminate_received:
                break
                
            # Clear event flag before waiting
            self.signal_event.clear()
            
            # Determine timeout
            timeout_seconds = None
            if next_sleep_iso:
                try:
                    from datetime import datetime
                    next_sleep = datetime.fromisoformat(next_sleep_iso.replace('Z', '+00:00'))
                    now = datetime.now(next_sleep.tzinfo)
                    timeout_seconds = max(0.0, (next_sleep - now).total_seconds())
                except Exception:
                    pass
            
            # Wait for signal or timeout
            try:
                await workflow.wait_condition(
                    lambda: (not self.is_paused and self.signal_event.is_set()) or self.terminate_received,
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                # Timer expired
                if self.is_paused:
                    # Timer expired while paused, suppress wake-up and wait indefinitely
                    await workflow.wait_condition(
                        lambda: (not self.is_paused and self.signal_event.is_set()) or self.terminate_received
                    )
                else:
                    # Woke up naturally via timer
                    current_trigger = "scheduled"
                    current_event = {}
                    continue
            
            # Woke up via signal
            if self.terminate_received:
                break
                
            if self.signal_queue:
                sig = self.signal_queue.pop(0)
                current_trigger = sig["trigger_type"]
                current_event = sig["event"]
                # If there are more signals, re-set the event so we process them on the next loop iteration
                if self.signal_queue:
                    self.signal_event.set()
            else:
                # Should not happen if signal_event was set, but fallback
                current_trigger = "scheduled"
                current_event = {}

        # Completion Phase
        await workflow.execute_activity(
            run_final_summary_activity,
            args=[run_id],
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        workflow.logger.info(f"Workflow {run_id} completed.")
