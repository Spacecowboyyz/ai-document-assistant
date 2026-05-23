"""End-to-end API verification for Ollama or Groq mode. Usage:
  python scripts/verify_e2e.py --base-url http://127.0.0.1:8001 --mode ollama
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

FIXTURE = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample.pdf"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--mode", choices=["ollama", "groq"], required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    errors: list[str] = []

    with httpx.Client(timeout=120.0) as client:
        # Health
        r = client.get(f"{base}/health")
        if r.status_code != 200:
            errors.append(f"health: {r.status_code}")
        else:
            print("OK health", r.json().get("status"))

        # Models status
        r = client.get(f"{base}/api/v1/models/status")
        if r.status_code != 200:
            errors.append(f"models/status: {r.status_code}")
        else:
            status = r.json()
            print("OK models/status", json.dumps(status))
            if status.get("ai_provider") != args.mode:
                errors.append(
                    f"ai_provider expected {args.mode}, got {status.get('ai_provider')}"
                )
            if not status.get("models_ready"):
                errors.append("models_ready is false")

        email = f"verify-{uuid.uuid4().hex[:8]}@example.com"
        password = "VerifyPass123!"

        r = client.post(
            f"{base}/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        if r.status_code not in (200, 201):
            errors.append(f"register: {r.status_code} {r.text[:200]}")
            return report(errors)

        r = client.post(
            f"{base}/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if r.status_code != 200:
            errors.append(f"login: {r.status_code}")
            return report(errors)
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        if not FIXTURE.exists():
            errors.append(f"missing fixture {FIXTURE}")
            return report(errors)

        with FIXTURE.open("rb") as pdf:
            r = client.post(
                f"{base}/api/v1/upload",
                headers=headers,
                files={"file": ("sample.pdf", pdf, "application/pdf")},
            )
        if r.status_code != 200:
            errors.append(f"upload: {r.status_code} {r.text[:300]}")
            return report(errors)
        upload = r.json()
        doc_id = upload["doc_id"]
        chunk_count = upload.get("chunk_count", 0)
        print("OK upload", {"doc_id": doc_id, "chunk_count": chunk_count})
        if chunk_count < 1:
            errors.append("upload chunk_count < 1")

        session_id = str(uuid.uuid4())
        tokens: list[str] = []
        done = False
        with client.stream(
            "POST",
            f"{base}/api/v1/chat/{session_id}",
            headers={**headers, "Accept": "text/event-stream"},
            json={"question": "What is this document about?", "doc_id": doc_id},
        ) as stream:
            if stream.status_code != 200:
                errors.append(f"chat: {stream.status_code} {stream.read().decode()[:300]}")
                return report(errors)
            for line in stream.iter_lines():
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line[5:].strip())
                if payload.get("token"):
                    tokens.append(payload["token"])
                if payload.get("done"):
                    done = True
                    sources = payload.get("sources") or []
                    print(
                        "OK chat stream",
                        {
                            "token_count": len(tokens),
                            "done": done,
                            "sources": len(sources),
                        },
                    )
                    break

        if not tokens:
            errors.append("chat produced no tokens")
        if not done:
            errors.append("chat missing done event")

        r = client.get(f"{base}/api/v1/documents", headers=headers)
        if r.status_code != 200:
            errors.append(f"documents list: {r.status_code}")
        else:
            ids = [d["doc_id"] for d in r.json()]
            if doc_id not in ids:
                errors.append("uploaded doc not in documents list")
            else:
                print("OK documents list", len(ids))

    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        print("FAILURES:")
        for e in errors:
            print(" -", e)
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
