from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"
    VIEWER = "VIEWER"

