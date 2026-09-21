# humanizer-loop

Runs text through the humanizer prompt (`prompts/humanizer.md`, based on Wikipedia's "Signs of AI writing") with Claude, checks it with an AI detector, and repeats until the detector's AI score drops below a threshold. Each round, the sentences the detector flagged most strongly are fed back so the rewrite focuses on them. The script keeps the lowest-scoring version it has seen.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # then fill in the keys
```

- `ANTHROPIC_API_KEY`: from https://console.anthropic.com
- `SAPLING_API_KEY`: free tier at https://sapling.ai (dashboard, API key)

## Website

```sh
python app.py
```

Open http://localhost:8000, paste text, and press Humanize. The page shows the AI score for each round, the sentences that are still flagged, and the best version, with a copy button. It uses Claude Sonnet and Sapling.

## Command line

The CLI reads the same keys from the environment (`export` them or `source .env`).

```sh
python humanize_loop.py input.txt -o output.txt
python humanize_loop.py input.txt --detector gptzero --threshold 0.2 --max-iterations 8
cat input.txt | python humanize_loop.py > output.txt
```

Progress (the score for each round) goes to stderr; the final text goes to stdout or `-o`.

| Option | Default | Meaning |
|---|---|---|
| `--detector` | `sapling` | `sapling` or `gptzero` |
| `--threshold` | `0.3` | Stop once the AI score is below this (0 to 1) |
| `--max-iterations` | `6` | Maximum rewrite rounds |
| `--flagged` | `5` | Number of top-flagged sentences fed back per round |
| `--model` | `claude-sonnet-5` | Claude model used for rewriting |

## Adding a detector

Write a function that takes the text and returns `(score, [(sentence, score), ...])`, then add it to `DETECTORS` in `humanize_loop.py`.
