import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import get_engine
from app.main import app
from tests.helpers import make_event, signed_headers, to_body

WORKERS = 8


def test_concurrent_duplicate_requests_process_only_once(client, monkeypatch):
    calls = []

    def slow_process(event):
        # Keeps the first transaction open longer, so the other
        # requests really do collide with it.
        time.sleep(0.3)
        calls.append(event.event_id)

    monkeypatch.setattr("app.main.process_event", slow_process)

    body = to_body(make_event("evt_concurrent_1"))
    headers = signed_headers(body)
    barrier = threading.Barrier(WORKERS)

    def send_request():
        barrier.wait()  # all threads fire at the same moment
        with TestClient(app) as thread_client:
            return thread_client.post("/webhooks", content=body, headers=headers)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(send_request) for _ in range(WORKERS)]
        responses = [future.result() for future in futures]

    statuses = [r.json()["status"] for r in responses]

    assert all(r.status_code == 200 for r in responses)
    assert statuses.count("processed") == 1
    assert statuses.count("duplicate") == WORKERS - 1
    assert calls == ["evt_concurrent_1"]  # processing ran exactly once
    with get_engine().connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM webhook_events")).scalar()
    assert count == 1