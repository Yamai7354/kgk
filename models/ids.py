from uuid import uuid4


def new_id() -> str:
    """Generate a new opaque identifier for graph nodes."""
    return str(uuid4())
