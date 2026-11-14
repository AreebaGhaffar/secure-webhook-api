from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WebhookEventIn(BaseModel):
    """The body we expect from the webhook sender."""

    event_id: str = Field(min_length=1, max_length=255)
    event_type: str = Field(min_length=1, max_length=100)
    created_at: datetime
    data: dict[str, Any]