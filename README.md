# SagePilot - AI Order Supervisor

SagePilot is a proof-of-concept for a long-running, event-driven AI supervisor built to oversee order lifecycles from creation until completion. 

The system uses **Temporal** for durable orchestration (the "body"), ensuring the workflow stays alive for days or weeks without losing state. It uses **LangGraph** (the "brain") to handle cognitive reasoning, waking up only when necessary to process events, execute tools, and compact its memory.

## Tech Stack

*   **Frontend**: Next.js (App Router), Tailwind CSS v4, Axios
*   **Backend**: Python, FastAPI
*   **Orchestration**: Temporal Python SDK
*   **Agent Runtime**: LangGraph, LangChain, Groq (`llama-3.3-70b-versatile`)
*   **Persistence**: PostgreSQL (Supabase)

## Prerequisites

Before running the project, you must have the following installed:
*   [Node.js](https://nodejs.org/en)
*   [Python 3.10+](https://www.python.org/)
*   [Temporal CLI](https://docs.temporal.io/cli) (or Docker to run the Temporal server)
*   A [Supabase](https://supabase.com/) project (with the tables created via `backend/db/schema.sql`)
*   A [Groq](https://console.groq.com/keys) API Key

## Environment Setup

1. **Backend Configuration:**
   Create a `.env` file in the `backend/` directory:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   GROQ_API_KEY=your_groq_api_key
   ```

2. **Database Setup:**
   Run the SQL script located in `backend/db/schema.sql` in your Supabase SQL editor to create the necessary tables (`supervisors`, `runs`, `activities`). Make sure to reload your schema cache if required.

3. **Install Dependencies:**
   ```bash
   # Frontend
   cd frontend
   npm install
   
   # Backend
   cd backend
   python -m venv venv
   source venv/bin/activate  # (or .\venv\Scripts\Activate.ps1 on Windows)
   pip install -r requirements.txt
   ```

## Running the Application

You need to run 4 separate processes to power the full system:

**1. Temporal Server:**
```bash
temporal server start-dev
```

**2. FastAPI Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload
```

**3. Temporal Python Worker:**
```bash
cd backend
source venv/bin/activate
python -m temporal.worker
```

**4. Next.js Frontend:**
```bash
cd frontend
npm run dev
```

Once everything is running, open `http://localhost:3000` in your browser to access the Dashboard.

## Features

*   **Supervisor Templates:** Define baseline instructions and allowed tools for different types of agents (e.g., "Strict Logistics" vs. "Customer Support").
*   **Durable Workflows:** Each order runs as a distinct Temporal workflow that can pause, sleep, and resume without losing context.
*   **Cognitive Loop:** The agent uses a lightweight classifier to decide whether an incoming event is important enough to wake up the main reasoning engine.
*   **Memory Compaction:** The agent summarizes its own history over time to maintain a compact context window.
*   **Event Simulator:** Inject real-time events or manual instructions into a live workflow directly from the UI.
