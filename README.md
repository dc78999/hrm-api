# HRM Search API

## Problem Statement
Develop a scalable search API for a HR application managing millions of employee records. The system must handle heavy loads and provide efficient search capabilities while ensuring data security and preventing API abuse.

## Technical Stack & Architecture

### Stack Selection
- **FastAPI**: Chosen for high performance, async support, and automatic OpenAPI docs
- **PostgreSQL**: Robust for millions of records, supports JSONB and Full-Text Search
- **Docker**: Container orchestration and isolated environments
- **Python 3.10**: Latest stable features while maintaining compatibility

### Design Architecture
1. **Database Layer**
   - Optimized schema with GIN indexes for full-text search
   - JSONB for dynamic attribute storage and flexible columns
   - Partitioning ready for future scaling

2. **API Layer**
   - RESTful endpoints with pagination
   - Custom rate limiting (no external libs)
   - Query parameter validation
   - Response filtering per organization

## Setup & Launch

### Prerequisites
- Docker
- Docker Compose
- Make (optional, for convenience)

### Local Development
```bash
# Clone repository
git clone [repository-url]

# Start containers
docker-compose up -d

# Run tests
docker-compose exec api pytest
```

### Database Management
Access pgAdmin4 through your browser:
```bash
# URL: http://localhost:5050
# Email: admin@admin.com
# Password: admin

# To connect to the database:
# 1. Add New Server
# 2. Connection settings:
#    - Host: postgres-hrm
#    - Port: 5432
#    - Database: hrm_db
#    - Username: hrm_user
#    - Password: hrm_password
```

### Data Generation
```bash
# Initialize database with schema and seed data (all-in-one command)
make init-db

# Or to completely reset and reinitialize:
make full-reset

# Or step by step:
make db-up
make generate-seed-data
make load-seed-data

# Preview the generated SQL file (first 20 lines)
make preview-seed

# Preview the data in database
make preview-db
```

The initialization process:
1. Creates database schema (tables, indexes, etc.)
2. Loads generated test data
3. Verifies the data load with counts

The test data includes 1000 employee records with realistic:
- Names and contact information
- Department and position combinations
- Office locations
- Employment status (weighted towards 'active')

### API Documentation
- **OpenAPI documentation**: http://localhost:8000/docs ← **Main Documentation**
- **ReDoc alternative**: http://localhost:8000/redoc ← **Alternative UI**

### 🧪 Real Test Data Examples

Based on the actual seed data, you can test with these real examples:

**Search by name:**
```bash
curl -X GET "http://localhost:8000/api/v1/employees/search?q=Johnson" \
     -H "X-Organization-ID: 124690d3-458f-4ead-8c57-532a7cd6892b"
```

**Search by department:**
```bash
curl -X GET "http://localhost:8000/api/v1/employees/search?location=Engineering" \
     -H "X-Organization-ID: 68e529cc-78ba-4179-b955-76f1624550ae"
```

**Search by skills:**
```bash
curl -X GET "http://localhost:8000/api/v1/employees/search?q=Python" \
     -H "X-Organization-ID: feb99c04-3b47-413e-8387-959574862e24"
```

**Complex search:**
```bash
curl -X GET "http://localhost:8000/api/v1/employees/search?q=Leadership&location=Finance&status=active&page=1&page_size=10" \
     -H "X-Organization-ID: 881d4f6d-dcb3-4cdd-8222-2dc6df57ab20"
```

### Available Organizations with Real Data

- **124690d3-458f-4ead-8c57-532a7cd6892b**: 500+ employees (Primary test org)
- **68e529cc-78ba-4179-b955-76f1624550ae**: 400+ employees (Engineering focus)  
- **feb99c04-3b47-413e-8387-959574862e24**: 300+ employees (Mixed departments)
- **881d4f6d-dcb3-4cdd-8222-2dc6df57ab20**: 200+ employees (Finance/Sales focus)
- **8e531ace-009f-46eb-b68c-0b13380eadec**: 300+ employees (Product/Marketing focus)

### Real Employee Names in Database
- Jason Noble, Daniel Adams, Mark Thompson, Kathryn Smith
- Aaron Mcguire, Eileen Decker, Jessica Small, Gerald Myers
- And 990+ more realistic employee records

## Security Considerations

1. **Data Protection**
   - Row-level security in PostgreSQL
   - Response filtering prevents data leaks
   - Input validation and sanitization

2. **API Security**
   - Rate limiting per client
   - JWT authentication (Stage 2)
   - CORS policy enforcement

3. **Infrastructure**
   - Containerized deployment
   - No sensitive data in codebase
   - Regular security updates

## Development Stages

### Stage 1 (Current)
- Search API implementation
- Database design for scale
- Unit tests
- Basic containerization

### Stage 2 (Planned)
- Rate limiting
- Authentication
- Advanced monitoring

## Contact
- Maintainer: [Your Name]
- Email: [Your Email]

### Testing
```bash
# Run tests once
make test

# Run tests in watch mode (requires pytest-watch)
make test-watch

# Run tests with coverage report
make test-coverage
```
