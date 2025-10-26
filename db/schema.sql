-- Enable necessary extension for UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum for employee status
CREATE TYPE employee_status AS ENUM ('active', 'inactive', 'terminated'); -- Using your previous assignment terms

-- ----------------------------------------------------------------------
-- TABLE DEFINITION
-- ----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- CORE SECURITY & FILTER COLUMNS (Must be dedicated columns)
    organization_id UUID NOT NULL, -- CRUCIAL: Use UUID for secure RLS anchor
    status employee_status NOT NULL DEFAULT 'active',
    location VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,

    -- DYNAMIC ATTRIBUTES (Mandatory for the assignment's dynamic column requirement)
    data JSONB NOT NULL, -- Stores all flexible fields (names, email, phone, custom properties)

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- FTS VECTOR (GENERATED ALWAYS): Includes all filterable text for comprehensive search
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', status::text), 'A') || 
        setweight(to_tsvector('english', location), 'A') || 
        setweight(to_tsvector('english', position), 'A') ||
        -- Pull searchable text from JSONB (e.g., name, email, phone)
        setweight(to_tsvector('english', coalesce(data ->> 'full_name', '')), 'B') ||
        setweight(to_tsvector('english', coalesce(data ->> 'email', '')), 'C') ||
        setweight(to_tsvector('english', coalesce(data ->> 'phone', '')), 'C')
    ) STORED
);

-- ----------------------------------------------------------------------
-- INDEXING STRATEGY (B-Tree for Filters, GIN for Search/JSONB)
-- ----------------------------------------------------------------------

-- 1. GIN Index for FTS (Crucial for search performance)
CREATE INDEX IF NOT EXISTS idx_employees_search_vector ON employees USING GIN (search_vector);

-- 2. GIN Index for JSONB (Crucial for querying dynamic fields)
CREATE INDEX IF NOT EXISTS idx_employees_data_gin ON employees USING GIN (data);

-- 3. B-Tree Indexes for Filter Columns (Mandatory for fast WHERE/ORDER BY)
CREATE INDEX IF NOT EXISTS idx_employees_org_id ON employees (organization_id);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees (status);
CREATE INDEX IF NOT EXISTS idx_employees_location ON employees (location);
CREATE INDEX IF NOT EXISTS idx_employees_position ON employees (position);

-- ----------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) - SECURE ACCESS CONTROL
-- ----------------------------------------------------------------------

-- Enable RLS
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;

-- Policy based on a unique Organization ID, not a business name
CREATE POLICY org_isolation_policy ON employees
    FOR ALL
    TO public -- Applies to all users/roles accessing the table
    USING (
        -- The employee's organization ID MUST match the ID set in the session context
        organization_id = current_setting('app.current_org_id', true)::UUID
        -- OR, allow access if the session user is a master admin
        OR current_setting('app.is_master_admin', true)::BOOLEAN = true
    );

-- ----------------------------------------------------------------------
-- MAINTENANCE TRIGGER
-- ----------------------------------------------------------------------
-- Update updated_at column on every row modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
