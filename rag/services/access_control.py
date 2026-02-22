from typing import List, Tuple

from documents.models import Document

ROLE_TO_MAX_LEVEL = None  # Lazy import to avoid circular imports

SECURITY_LEVEL_ACCESS = {
    Document.SecurityLevel.LOW:       [Document.SecurityLevel.LOW],
    Document.SecurityLevel.MID:       [Document.SecurityLevel.LOW, Document.SecurityLevel.MID],
    Document.SecurityLevel.HIGH:      [Document.SecurityLevel.LOW, Document.SecurityLevel.MID, Document.SecurityLevel.HIGH],
    Document.SecurityLevel.VERY_HIGH: [Document.SecurityLevel.LOW, Document.SecurityLevel.MID, Document.SecurityLevel.HIGH, Document.SecurityLevel.VERY_HIGH],
}


def get_user_allowed_security_levels(user) -> Tuple[List[str], str]:
    """
    Derives allowed security levels from the user's role.
    Returns (allowed_levels_list, effective_max_level).
    Falls back to LOW for unknown roles or None users.
    """
    from users.models import User

    ROLE_TO_MAX_LEVEL = {
        User.Role.GUEST:          Document.SecurityLevel.LOW,
        User.Role.EMPLOYEE:       Document.SecurityLevel.MID,
        User.Role.MANAGER:        Document.SecurityLevel.HIGH,
        User.Role.CEO:            Document.SecurityLevel.VERY_HIGH,
        User.Role.VICE_PRESIDENT: Document.SecurityLevel.VERY_HIGH,
    }

    if user is None:
        return [Document.SecurityLevel.LOW], Document.SecurityLevel.LOW

    effective_max = ROLE_TO_MAX_LEVEL.get(user.role, Document.SecurityLevel.LOW)
    allowed_levels = SECURITY_LEVEL_ACCESS.get(effective_max, [Document.SecurityLevel.LOW])
    return allowed_levels, effective_max

