


from fastapi import Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User


def required_roles(*allowed_roles: UserRole):
    """Dependency factory: returns a dependency that checks the current user's role."""
    def _check_role(current_user:User = Depends(get_current_user))-> User:
        if current_user.user_role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail= f"requires one of : {[r.value for r in allowed_roles]}"
            )
        return current_user
    return _check_role