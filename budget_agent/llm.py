import json
from typing import Optional
from urllib import error, request


def explain_with_ollama(prompt: str, model: str = "llama3.1") -> Optional[str]:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
    req = request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=8) as response:
            body = json.loads(response.read().decode("utf-8"))
            return body.get("response")
    except (error.URLError, TimeoutError, json.JSONDecodeError):
        return None
