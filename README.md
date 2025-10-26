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
   - JSONB for flexible attribute storage
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
- OpenAPI documentation: http://localhost:8000/docs
- ReDoc alternative: http://localhost:8000/redoc

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
