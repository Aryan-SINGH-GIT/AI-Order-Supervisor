import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from dotenv import load_dotenv

from temporal.workflows import OrderSupervisorWorkflow
from temporal.activities import run_agent_cognitive_loop, run_final_summary_activity

load_dotenv()

async def main():
    print("Starting Temporal Worker...")
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="order-supervisor-queue",
        workflows=[OrderSupervisorWorkflow],
        activities=[run_agent_cognitive_loop, run_final_summary_activity],
    )
    
    print("Worker is ready and listening on 'order-supervisor-queue'...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
