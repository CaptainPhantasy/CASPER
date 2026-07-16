-- CASPER Prime Database Initialization Script
-- This script sets up the initial database schema for CASPER Prime

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS casper;
CREATE SCHEMA IF NOT EXISTS monitoring;

-- Set default schema
SET search_path TO casper, public;

-- Users and Authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent Sessions
CREATE TABLE IF NOT EXISTS agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    agent_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Terminal Sessions
CREATE TABLE IF NOT EXISTS terminal_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_name VARCHAR(255),
    working_directory VARCHAR(500),
    environment_variables JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Command History
CREATE TABLE IF NOT EXISTS command_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    terminal_session_id UUID NOT NULL REFERENCES terminal_sessions(id) ON DELETE CASCADE,
    command TEXT NOT NULL,
    exit_code INTEGER,
    output TEXT,
    execution_time_ms INTEGER,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task Execution
CREATE TABLE IF NOT EXISTS task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_description TEXT NOT NULL,
    agent_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- File Operations Log
CREATE TABLE IF NOT EXISTS file_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL, -- create, update, delete, move
    file_path VARCHAR(1000) NOT NULL,
    old_content TEXT,
    new_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System Metrics (for monitoring)
CREATE TABLE IF NOT EXISTS monitoring.system_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC NOT NULL,
    labels JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Metrics
CREATE TABLE IF NOT EXISTS monitoring.performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    response_time_ms INTEGER NOT NULL,
    status_code INTEGER NOT NULL,
    user_id UUID REFERENCES users(id),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Terminal Metrics
CREATE TABLE IF NOT EXISTS monitoring.terminal_metrics (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES terminal_sessions(id) ON DELETE CASCADE,
    command_count INTEGER DEFAULT 0,
    session_duration_ms BIGINT,
    memory_usage_mb NUMERIC,
    cpu_usage_percent NUMERIC,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_project ON agent_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_terminal_sessions_project ON terminal_sessions(project_id);
CREATE INDEX IF NOT EXISTS idx_terminal_sessions_user ON terminal_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_command_history_session ON command_history(terminal_session_id);
CREATE INDEX IF NOT EXISTS idx_command_history_executed_at ON command_history(executed_at);
CREATE INDEX IF NOT EXISTS idx_task_executions_project ON task_executions(project_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_user ON task_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON task_executions(status);
CREATE INDEX IF NOT EXISTS idx_file_operations_project ON file_operations(project_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_timestamp ON monitoring.system_metrics(metric_name, timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_endpoint ON monitoring.performance_metrics(endpoint);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_timestamp ON monitoring.performance_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_terminal_metrics_session ON monitoring.terminal_metrics(session_id);
CREATE INDEX IF NOT EXISTS idx_terminal_metrics_timestamp ON monitoring.terminal_metrics(timestamp);

-- Create update triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_sessions_updated_at BEFORE UPDATE ON agent_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_terminal_sessions_updated_at BEFORE UPDATE ON terminal_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create default admin user (password: admin123)
INSERT INTO users (email, username, password_hash, is_active, is_verified)
VALUES (
    'admin@casper-prime.ai',
    'admin',
    crypt('admin123', gen_salt('bf')),
    true,
    true
) ON CONFLICT (email) DO NOTHING;

-- Create sample project
INSERT INTO projects (name, description, owner_id, settings)
SELECT
    'Sample Project',
    'A sample project for testing CASPER Prime functionality',
    u.id,
    '{
        "terminal_enabled": true,
        "auto_approval": false,
        "preferred_agents": ["backend-prime", "frontend-prime"]
    }'::jsonb
FROM users u
WHERE u.username = 'admin'
ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA casper TO casper;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA casper TO casper;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO casper;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO casper;

-- Create monitoring views
CREATE OR REPLACE VIEW monitoring.terminal_session_stats AS
SELECT
    ts.id as session_id,
    ts.project_id,
    ts.user_id,
    COUNT(ch.id) as command_count,
    AVG(ch.execution_time_ms) as avg_execution_time,
    EXTRACT(epoch FROM (NOW() - ts.created_at))::integer as session_age_seconds
FROM terminal_sessions ts
LEFT JOIN command_history ch ON ts.id = ch.terminal_session_id
WHERE ts.status = 'active'
GROUP BY ts.id, ts.project_id, ts.user_id, ts.created_at;

CREATE OR REPLACE VIEW monitoring.system_health AS
SELECT
    'active_sessions' as metric,
    COUNT(*)::numeric as value,
    NOW() as timestamp
FROM terminal_sessions
WHERE status = 'active'
UNION ALL
SELECT
    'total_commands_today' as metric,
    COUNT(*)::numeric as value,
    NOW() as timestamp
FROM command_history
WHERE executed_at >= CURRENT_DATE
UNION ALL
SELECT
    'active_tasks' as metric,
    COUNT(*)::numeric as value,
    NOW() as timestamp
FROM task_executions
WHERE status IN ('pending', 'running');

-- Insert initial monitoring data
INSERT INTO monitoring.system_metrics (metric_name, metric_value, labels)
VALUES ('database_initialized', 1, '{"version": "1.0.0", "timestamp": "' || NOW()::text || '"}');

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'CASPER Prime database initialized successfully!';
    RAISE NOTICE 'Default admin user created: admin@casper-prime.ai / admin123';
    RAISE NOTICE 'Sample project created for testing';
END $$;