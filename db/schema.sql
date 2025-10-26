-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum for employee status
CREATE TYPE employee_status AS ENUM ('active', 'inactive', 'terminated');

-- Create employees table
CREATE TABLE IF NOT EXISTS employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company VARCHAR(100) NOT NULL,  -- New field
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(50),
    department VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    status employee_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('english', first_name), 'A') ||
        setweight(to_tsvector('english', last_name), 'A') ||
        setweight(to_tsvector('english', company), 'A') ||    -- Add company to search vector
        setweight(to_tsvector('english', department), 'B') ||
        setweight(to_tsvector('english', position), 'B') ||
        setweight(to_tsvector('english', location), 'B')
    ) STORED
);

-- Create indexes for common search patterns
CREATE INDEX IF NOT EXISTS idx_employees_search_vector ON employees USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_employees_department ON employees (department);
CREATE INDEX IF NOT EXISTS idx_employees_location ON employees (location);
CREATE INDEX IF NOT EXISTS idx_employees_status ON employees (status);
CREATE INDEX IF NOT EXISTS idx_employees_email ON employees (email);
-- Add index for company lookups
CREATE INDEX IF NOT EXISTS idx_employees_company ON employees (company);

-- Enable Row Level Security
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;

-- Create policy for company-based access
CREATE POLICY company_isolation ON employees
    FOR ALL
    TO authenticated_user
    USING (
        company = current_setting('app.current_company')::VARCHAR
        OR current_setting('app.is_master_admin')::BOOLEAN = true
    );

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_employees_updated_at
    BEFORE UPDATE ON employees
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
