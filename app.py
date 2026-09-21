#!/usr/bin/env python3
"""Web UI for the humanizer loop. Run: python app.py, then open http://localhost:8000"""
import json
import os

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request

load_dotenv()

from humanize_loop import run_loop  # noqa: E402

app = Flask(__name__)


@app.get("/")
def index():
    missing = [k for k in ("ANTHROPIC_API_KEY", "SAPLING_API_KEY") if not os.environ.get(k)]
    return render_template("index.html", missing=missing)


@app.post("/run")
def run():
    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return {"error": "No text given."}, 400
    threshold = min(max(float(body.get("threshold", 0.3)), 0.01), 0.99)
    max_iterations = min(max(int(body.get("max_iterations", 6)), 1), 15)

    def stream():
        # One JSON object per line, so the page can show each round as it finishes.
        try:
            for event in run_loop(text, "sapling", threshold, max_iterations):
                yield json.dumps(event) + "\n"
        except Exception as e:  # surface API errors in the page instead of a dead stream
            yield json.dumps({"error": f"{type(e).__name__}: {e}"}) + "\n"

    return Response(stream(), mimetype="application/x-ndjson")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8000)), debug=False, threaded=True)
