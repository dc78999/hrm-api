from faker import Faker
import random

fake = Faker()

# Constants for realistic data
DEPARTMENTS = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations', 'Legal', 'Product']
POSITIONS = {
    'Engineering': ['Software Engineer', 'DevOps Engineer', 'QA Engineer', 'Tech Lead', 'Engineering Manager'],
    'Sales': ['Sales Representative', 'Account Executive', 'Sales Manager', 'Sales Director'],
    'Marketing': ['Marketing Specialist', 'Content Writer', 'SEO Specialist', 'Marketing Manager'],
    'HR': ['HR Specialist', 'Recruiter', 'HR Manager', 'HR Director'],
    'Finance': ['Accountant', 'Financial Analyst', 'Controller', 'Finance Manager'],
    'Operations': ['Operations Analyst', 'Project Manager', 'Operations Manager'],
    'Legal': ['Legal Counsel', 'Paralegal', 'Legal Assistant'],
    'Product': ['Product Manager', 'Product Owner', 'Product Analyst']
}
LOCATIONS = ['New York', 'San Francisco', 'Chicago', 'Austin', 'Seattle', 'Boston', 'London', 'Singapore']
STATUSES = ['active', 'inactive', 'terminated']  # weighted towards active

# Add companies
COMPANIES = ['TechCorp', 'FinanceInc', 'HealthCare Ltd', 'RetailCo']

def generate_insert_statements(num_records=1000):
    statements = []
    for _ in range(num_records):
        department = random.choice(DEPARTMENTS)
        position = random.choice(POSITIONS[department])
        location = random.choice(LOCATIONS)
        status = random.choice(STATUSES)
        company = random.choice(COMPANIES)
        
        stmt = f"""INSERT INTO employees (
    company, first_name, last_name, email, phone, department, position, location, status
) VALUES (
    '{company}',
    '{fake.first_name().replace("'", "''")}',
    '{fake.last_name().replace("'", "''")}',
    '{fake.email()}',
    '{fake.phone_number()}',
    '{department}',
    '{position}',
    '{location}',
    '{status}'
);"""
        statements.append(stmt)
    return statements

if __name__ == "__main__":
    with open('seed_data.sql', 'w') as f:
        f.write("-- Test data generated for HRM API\n\n")
        for stmt in generate_insert_statements(1000):
            f.write(stmt + "\n")
