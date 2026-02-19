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

if __name__ == "__main__":
    example = UnifiedEvent(
        source_id="openai-status",
        product_name="OpenAI API - Chat Completions",
        status="degraded_performance",
        message="Degraded performance due to upstream issue",
        timestamp=datetime.now(),
        event_id="demo-openai-chat-1",
    )
    print(example.model_dump_json())

