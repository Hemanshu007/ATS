"""Application status transition state machine and shared constants."""

ALLOWED_STATUS_TRANSITIONS = {
    "applied": ["screening", "rejected"],
    "screening": ["interview", "rejected"],
    "interview": ["offer", "rejected"],
    "offer": ["hired", "rejected"],
    "hired": [],       # terminal
    "rejected": [],    # terminal
}

VALID_STATUSES = list(ALLOWED_STATUS_TRANSITIONS.keys())

ACTIVE_STATUSES = ["applied", "screening", "interview", "offer"]

ALLOWED_CONTENT_TYPES = ["application/pdf"]
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
