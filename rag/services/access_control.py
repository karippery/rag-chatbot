"""

Document-level security access control.

Security model
--------------
Each document is tagged with a ``SecurityLevel`` (LOW → MID → HIGH → VERY_HIGH).
Each user role maps to a *maximum* permitted level; that level and every level
below it are accessible to the user.

Role → maximum level mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
* GUEST          → LOW
* EMPLOYEE       → MID
* MANAGER        → HIGH
* CEO            → VERY_HIGH
* VICE_PRESIDENT → VERY_HIGH

Unauthenticated / ``None`` users are treated as GUEST (LOW access only).
Unknown roles also fall back to LOW so new roles don't accidentally gain
elevated access.

Usage
-----
::

    allowed_levels, effective_max = get_user_allowed_security_levels(request.user)
    chunks = DocumentChunk.objects.filter(security_level__in=allowed_levels)
"""

import logging
from typing import List, Tuple

from documents.models import Document

logger = logging.getLogger(__name__)


def get_user_allowed_security_levels(user) -> Tuple[List[str], str]:
    """
    Derive the set of security levels a user is permitted to access.

    The function imports ``User`` lazily to avoid circular import issues
    at module load time (``users`` depends on ``documents``; importing at the
    top level would create a cycle).

    Args:
        user: A Django ``User`` instance, or ``None`` for unauthenticated
              requests.

    Returns:
        A ``(allowed_levels, effective_max_level)`` tuple where:

        * ``allowed_levels``    is a list of ``Document.SecurityLevel`` values
                                the user may query.
        * ``effective_max_level`` is the single highest level in that list,
                                  useful for tagging ``QueryHistory`` records.

    Examples:
        >>> allowed, max_level = get_user_allowed_security_levels(None)
        >>> allowed
        ['LOW']
        >>> max_level
        'LOW'
    """
    # Lazy import to break the documents ↔ users circular dependency.
    from users.models import User

    # Maps each role to the highest security level the role may access.
    ROLE_TO_MAX_LEVEL = {
        User.Role.GUEST:          Document.SecurityLevel.LOW,
        User.Role.EMPLOYEE:       Document.SecurityLevel.MID,
        User.Role.MANAGER:        Document.SecurityLevel.HIGH,
        User.Role.CEO:            Document.SecurityLevel.VERY_HIGH,
        User.Role.VICE_PRESIDENT: Document.SecurityLevel.VERY_HIGH,
    }

    # Cumulative access: a user at level X can see everything at or below X.
    SECURITY_LEVEL_ACCESS = {
        Document.SecurityLevel.LOW: [
            Document.SecurityLevel.LOW,
        ],
        Document.SecurityLevel.MID: [
            Document.SecurityLevel.LOW,
            Document.SecurityLevel.MID,
        ],
        Document.SecurityLevel.HIGH: [
            Document.SecurityLevel.LOW,
            Document.SecurityLevel.MID,
            Document.SecurityLevel.HIGH,
        ],
        Document.SecurityLevel.VERY_HIGH: [
            Document.SecurityLevel.LOW,
            Document.SecurityLevel.MID,
            Document.SecurityLevel.HIGH,
            Document.SecurityLevel.VERY_HIGH,
        ],
    }

    # Unauthenticated users get the minimum access level.
    if user is None:
        logger.debug("Unauthenticated user — granting LOW access only.")
        return [Document.SecurityLevel.LOW], Document.SecurityLevel.LOW

    effective_max = ROLE_TO_MAX_LEVEL.get(user.role)

    if effective_max is None:
        # Unknown role — fail safe to the lowest level rather than raising.
        logger.warning(
            "Unknown user role — defaulting to LOW security access.",
            extra={"user_id": user.id, "role": user.role},
        )
        effective_max = Document.SecurityLevel.LOW

    allowed_levels = SECURITY_LEVEL_ACCESS.get(effective_max, [Document.SecurityLevel.LOW])

    logger.debug(
        "Security levels resolved for user.",
        extra={
            "user_id": user.id,
            "role": user.role,
            "effective_max_level": effective_max,
            "allowed_levels": allowed_levels,
        },
    )

    return allowed_levels, effective_max