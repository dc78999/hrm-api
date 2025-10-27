import pytest
import uuid
from datetime import datetime

@pytest.fixture
def test_org_id():
    return str(uuid.uuid4())

@pytest.fixture
def sample_employee():
    return {
        "id": str(uuid.uuid4()),
        "organization_id": str(uuid.uuid4()),
        "location": "New York",
        "position": "Software Engineer",
        "status": "active",
        "data": {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "123-456-7890",
            "department": "Engineering"
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
