from pydantic import BaseModel, UUID4, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"

class Employee(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    department: str
    position: str
    location: str
    status: EmployeeStatus
    company: str

class EmployeeResponse(BaseModel):
    id: UUID4
    location: str
    position: str
    status: str
    data: Dict[str, Any]  # Contains email and other flexible fields
    created_at: datetime
    updated_at: datetime

class SearchResponse(BaseModel):
    items: List[EmployeeResponse]
    total: int
    page: int
    page_size: int
