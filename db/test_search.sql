-- Set context for first organization (copy ID from seed_data.sql comments)
SET app.current_org_id = '<first-org-uuid-from-seed>';

-- Test basic queries
SELECT 
    id,
    status,
    location,
    position,
    data->>'full_name' as name,
    data->>'email' as email
FROM employees 
LIMIT 5;

-- Test search functionality
SELECT 
    data->>'full_name' as name,
    position,
    location
FROM employees 
WHERE search_vector @@ to_tsquery('english', 'engineer');

-- Test organization isolation
SELECT COUNT(*) FROM employees;  -- Shows only current org's employees
