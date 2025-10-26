from pydantic import BaseModel, EmailStr
from typing import Optional
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
