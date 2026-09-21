#!/usr/bin/env python3
"""Rewrite text with the humanizer prompt until an AI detector scores it below a threshold.

Usage:
    python humanize_loop.py input.txt -o output.txt
    cat input.txt | python humanize_loop.py --detector gptzero --threshold 0.2
"""
import argparse
import os
import re
import sys
from pathlib import Path

import anthropic
import requests

PROMPT_PATH = Path(__file__).parent / "prompts" / "humanizer.md"
DEFAULT_MODEL = "claude-opus-5"


# ---------- detectors ----------
# Each detector returns (ai_score 0..1, list of (sentence, score) pairs, highest first).

def detect_sapling(text):
    key = os.environ["SAPLING_API_KEY"]
    r = requests.post(
        "https://api.sapling.ai/api/v1/aidetect",
        json={"key": key, "text": text, "sent_scores": True},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    sentences = [(s["sentence"], s["score"]) for s in data.get("sentence_scores", [])]
    return data["score"], sorted(sentences, key=lambda s: -s[1])


def detect_gptzero(text):
    key = os.environ["GPTZERO_API_KEY"]
    r = requests.post(
        "https://api.gptzero.me/v2/predict/text",
        headers={"x-api-key": key, "Content-Type": "application/json"},
        json={"document": text},
        timeout=60,
    )
    r.raise_for_status()
    doc = r.json()["documents"][0]
    probs = doc.get("class_probabilities") or {}
    score = probs.get("ai", doc.get("completely_generated_prob", 0.0))
    sentences = [
        (s["sentence"], s.get("generated_prob", 0.0)) for s in doc.get("sentences", [])
    ]
    return score, sorted(sentences, key=lambda s: -s[1])


DETECTORS = {"sapling": detect_sapling, "gptzero": detect_gptzero}


# ---------- humanizer ----------

def humanize(client, model, system_prompt, text, flagged, iteration):
    instructions = (
        "Embedded mode: return ONLY the final rewritten text, with no preamble, "
        "notes, pattern list, or quotation marks around it.\n"
    )
    if flagged:
        listed = "\n".join(f"- ({score:.0%}) {sent}" for sent, score in flagged)
        instructions += (
            "\nAn AI detector flagged these sentences as most likely AI-written. "
            "Rework them more thoroughly (vary sentence length and structure, prefer plain "
            "words), while keeping every claim intact:\n" + listed + "\n"
        )
    if iteration > 1:
        instructions += (
            "\nThis text has already been through the humanizer. Do not just swap synonyms; "
            "restructure sentences and paragraphs where it helps.\n"
        )

    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"{instructions}\n<text>\n{text}\n</text>"}],
    )
    out = "".join(b.text for b in msg.content if b.type == "text").strip()
    # Strip a stray <text> wrapper if the model echoed it back.
    return re.sub(r"^<text>\s*|\s*</text>$", "", out).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", nargs="?", help="Input text file (default: stdin)")
    p.add_argument("-o", "--output", help="Write final text here (default: stdout)")
    p.add_argument("--detector", choices=DETECTORS, default="sapling")
    p.add_argument("--threshold", type=float, default=0.3,
                   help="Stop when the AI score is below this (0..1, default 0.3)")
    p.add_argument("--max-iterations", type=int, default=6)
    p.add_argument("--flagged", type=int, default=5,
                   help="How many top-flagged sentences to feed back each round")
    p.add_argument("--model", default=DEFAULT_MODEL)
    args = p.parse_args()

    text = Path(args.input).read_text() if args.input else sys.stdin.read()
    text = text.strip()
    if not text:
        sys.exit("No input text.")

    detect = DETECTORS[args.detector]
    client = anthropic.Anthropic()
    system_prompt = PROMPT_PATH.read_text()

    score, sentences = detect(text)
    print(f"[0] AI score: {score:.1%}", file=sys.stderr)
    best_text, best_score = text, score

    iteration = 0
    while score >= args.threshold and iteration < args.max_iterations:
        iteration += 1
        flagged = [s for s in sentences if s[1] >= 0.5][: args.flagged]
        text = humanize(client, args.model, system_prompt, text, flagged, iteration)
        score, sentences = detect(text)
        print(f"[{iteration}] AI score: {score:.1%}", file=sys.stderr)
        if score < best_score:
            best_text, best_score = text, score

    if best_score < args.threshold:
        print(f"Passed: {best_score:.1%} < {args.threshold:.0%}", file=sys.stderr)
    else:
        print(f"Did not pass after {iteration} rounds; returning best ({best_score:.1%}).",
              file=sys.stderr)

    if args.output:
        Path(args.output).write_text(best_text + "\n")
    else:
        print(best_text)


if __name__ == "__main__":
    main()
