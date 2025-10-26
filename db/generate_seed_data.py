from faker import Faker
import random
import uuid
import json

fake = Faker()

# Constants for realistic data
ORGANIZATIONS = [
    str(uuid.uuid4()) for _ in range(5)  # Generate 5 different organizations
]

LOCATIONS = ['New York', 'San Francisco', 'Chicago', 'Austin', 'Seattle', 'Boston', 'London', 'Singapore']
POSITIONS = ['Software Engineer', 'Product Manager', 'HR Specialist', 'Sales Representative', 
            'Marketing Manager', 'Data Analyst', 'DevOps Engineer', 'Financial Analyst']
STATUSES = ['active', 'inactive', 'terminated']

def generate_employee_data():
    """Generate JSONB data field"""
    first_name = fake.first_name()
    last_name = fake.last_name()
    return {
        'full_name': f"{first_name} {last_name}",
        'email': fake.email(),
        'phone': fake.phone_number(),
        'department': fake.random_element(['Engineering', 'Product', 'HR', 'Sales', 'Marketing', 'Finance']),
        'hire_date': fake.date().format(),
        'salary': round(random.uniform(50000, 150000), 2),
        'skills': random.sample(['Python', 'SQL', 'Java', 'JavaScript', 'Leadership', 'Communication'], 
                              random.randint(2, 4))
    }

def generate_insert_statements(num_records=1000):
    statements = []
    for _ in range(num_records):
        org_id = random.choice(ORGANIZATIONS)
        status = random.choice(STATUSES)
        location = random.choice(LOCATIONS)
        position = random.choice(POSITIONS)
        data = generate_employee_data()
        
        stmt = f"""INSERT INTO employees (
    organization_id, 
    status,
    location,
    position,
    data
) VALUES (
    '{org_id}',
    '{status}',
    '{location}',
    '{position}',
    '{json.dumps(data)}'::jsonb
);"""
        statements.append(stmt)
    return statements

if __name__ == "__main__":
    # Create seed_data.sql
    with open('db/seed_data.sql', 'w') as f:
        f.write("-- Test data generated for HRM API\n\n")
        # Store organization IDs for reference
        f.write("-- Organizations created:\n")
        for org in ORGANIZATIONS:
            f.write(f"-- {org}\n")
        f.write("\n")
        # Write INSERT statements
        for stmt in generate_insert_statements(1000):
            f.write(stmt + "\n")
