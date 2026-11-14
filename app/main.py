import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import WebhookEvent
from app.processing import process_event
from app.schemas import WebhookEventIn
from app.security import verify_signature

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fails at startup with a clear error if configuration is missing.
    app.state.webhook_secret = get_settings().webhook_secret
    yield


app = FastAPI(title="Secure Webhook Processing API", lifespan=lifespan)


class WebhookResponse(BaseModel):
    status: Literal["processed", "duplicate"]
    event_id: str


async def get_raw_body(request: Request) -> bytes:
    """The exact bytes the sender signed (never re-serialized)."""
    return await request.body()


@app.post("/webhooks", response_model=WebhookResponse)
def receive_webhook(
    request: Request,
    raw_body: bytes = Depends(get_raw_body),
    x_webhook_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> WebhookResponse:
    # 1. Verify the signature over the raw bytes.
    if not verify_signature(request.app.state.webhook_secret, raw_body, x_webhook_signature):
        raise HTTPException(status_code=401, detail="Invalid or missing signature")

    # 2. Validate the payload (malformed JSON also lands here as a 422).
    try:
        event_in = WebhookEventIn.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(
                include_url=False, include_context=False, include_input=False
            ),
        )

    # 3. One transaction: insert if new, otherwise it's a duplicate.
    try:
        stmt = (
            insert(WebhookEvent)
            .values(
                event_id=event_in.event_id,
                event_type=event_in.event_type,
                payload=event_in.model_dump(mode="json"),
                status="received",
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(WebhookEvent.id)
        )
        inserted_id = db.execute(stmt).scalar_one_or_none()

        if inserted_id is None:
            db.rollback()
            return WebhookResponse(status="duplicate", event_id=event_in.event_id)

        event = db.get(WebhookEvent, inserted_id)
        process_event(event)
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error while storing webhook event (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Internal server error")

    return WebhookResponse(status="processed", event_id=event_in.event_id)