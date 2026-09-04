"""Failure-tolerant server-to-server delivery to AGENT acquisition."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import urllib.request

log = logging.getLogger("elyio.acquisition")

def emit_scan_success(*, acquisition_session_id: str | None, occurred_at: str, recognition_attempt_id: str, platform: str | None = None) -> None:
    if not acquisition_session_id: return
    endpoint = os.environ.get("ACQUISITION_S2S_URL", "https://agent.elyio.co/acquisition-api/v1/events").rstrip("/")
    secret = os.environ.get("ACQUISITION_S2S_SECRET", "")
    if not secret: return
    payload = {"event_id": f"elyio-scan-{recognition_attempt_id}", "brand": "elyio", "acquisition_session_id": acquisition_session_id, "event_name": "scan_success", "occurred_at": occurred_at, "platform": platform}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    def send() -> None:
        try:
            request = urllib.request.Request(endpoint, data=raw, headers={"Content-Type": "application/json", "X-Acquisition-Signature": hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest(), "X-Acquisition-Authority": "AUTHORITATIVE"})
            with urllib.request.urlopen(request, timeout=1.5) as response: response.read(128)
        except Exception as exc: log.warning("acquisition delivery failed event=%s error=%s", payload["event_id"], type(exc).__name__)
    threading.Thread(target=send, name="acquisition-scan", daemon=True).start()
