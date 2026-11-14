from app.models import WebhookEvent


def process_event(event: WebhookEvent) -> None:
    """Isolated business-processing step.

    The project scope uses simulated payment events only, so this is a
    deliberately small placeholder. Real business logic would go here.
    """
    return None