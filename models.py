from datetime import datetime
from pydantic import BaseModel


class UnifiedEvent(BaseModel):
    """
    All adapters should normalize their data into this shape.
    """
    source_id: str
    product_name: str
    status: str
    message: str
    timestamp: datetime
    event_id: str

