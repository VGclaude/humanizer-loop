# humanizer-loop

Runs text through the humanizer prompt (`prompts/humanizer.md`, based on Wikipedia's "Signs of AI writing") with Claude, checks it with an AI detector, and repeats until the detector's AI score drops below a threshold. Each round, the sentences the detector flagged most strongly are fed back so the rewrite focuses on them. The script keeps the lowest-scoring version it has seen.

## Setup

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export SAPLING_API_KEY=...     # for --detector sapling (default), https://sapling.ai
export GPTZERO_API_KEY=...     # for --detector gptzero, https://gptzero.me
```

## Usage

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
| `--model` | `claude-opus-5` | Claude model used for rewriting |

## Adding a detector

Write a function that takes the text and returns `(score, [(sentence, score), ...])`, then add it to `DETECTORS` in `humanize_loop.py`.
