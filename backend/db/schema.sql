-- Supervisor Templates
CREATE TABLE supervisors (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    base_instruction TEXT NOT NULL,
    available_actions JSONB,
    wake_aggressiveness VARCHAR,
    model_config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Represents a single order supervisor run
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    supervisor_id UUID REFERENCES supervisors(id),
    order_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL, -- running, paused, completed
    order_context JSONB,     -- Persist initial order details
    memory_summary TEXT,
    wake_guidance TEXT,      -- Persist wake guidance between runs
    next_wake_up_at TIMESTAMP,
    instructions JSONB DEFAULT '[]', -- Run-specific instructions
    -- End-of-run outputs explicitly separated
    final_summary TEXT,
    important_actions_taken TEXT,
    key_learnings TEXT,
    feedback_recommendations TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- A unified table for all events, tool executions, and agent thoughts
CREATE TABLE activities (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES runs(id),
    -- Must support at least these categories:
    -- 'incoming_event', 'agent_action', 'wake_decision', 'sleep_decision', 'manual_instruction', 'final_output', 'control_action'
    activity_type VARCHAR NOT NULL, 
    name VARCHAR NOT NULL, 
    payload JSONB, -- The raw data
    timestamp TIMESTAMP DEFAULT NOW()
);
