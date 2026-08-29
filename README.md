# FormalImG

This repository contains the benchmark and evaluation code for the paper **FormalImG: Evaluating Structural Compositional Generalization for T2I Models**.

FormalImG evaluates whether text-to-image (T2I) models can satisfy increasingly coupled semantic constraints. It represents instructions with a first-order-logic DSL and evaluates two complementary scenarios:

- **Natural**: open-domain image generation evaluated by a VLM judge.
- **Knolling**: top-down object arrangements evaluated by visual grounding and executable logical verification.

The benchmark contains 4,000 instructions: 2,000 Natural and 2,000 Knolling instances. Each scenario has 200 instances at every structural complexity level from `K = 1` to `K = 10`.

## Repository Layout

```text
benchmarks/
  natural/                     2,000 Natural instances
  knolling/                    2,000 Knolling instances
configs/
  dsl_natural.json             Natural-scenario DSL vocabulary and predicates
  dsl_knolling.json            Knolling-scenario DSL vocabulary and predicates
src/
  draw.py                      API wrapper for image generation
  draw_llm.py                  Text-only layout generation for analysis
  engine/                      DSL validation and CNF transformation utilities
  tasks/natural/eval.py        VLM-as-judge evaluation for Natural
  tasks/knolling/grounding.py  Visual grounding for Knolling
  tasks/knolling/eval.py       Executable DSL verification for Knolling
scripts/                       End-to-end entry points for the two scenarios
```

## Benchmark Format

Each instance is a JSON file with the following fields:

```json
{
  "prompt": "natural-language instruction",
  "dsl": "first-order-logic representation",
  "cnf": "lifted logical representation",
  "k": 1,
  "object_classes": ["object category"]
}
```

`k` is the structural compositional complexity defined in the paper. `dsl` is the original instruction representation, and `cnf` is the lifted form used for fine-grained analysis.

## Setup

The code requires Python 3 and the packages listed in `requirements.txt`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill `PRI_API_KEY` in `.env`. Set `PRI_URL` when using an OpenAI-compatible gateway; leave it empty to use the default endpoint supported by the client. `.env` is ignored by Git and must never contain committed credentials.

The API-based generation, grounding, and Natural evaluation code use `PRI_API_KEY` and `PRI_URL`. The convenience scripts load `.env` automatically. When invoking Python files directly, export these variables in the shell first:

```bash
export PRI_API_KEY="YOUR_API_KEY"
export PRI_URL="YOUR_OPENAI_COMPATIBLE_BASE_URL"
export PYTHONPATH=.
```

## Evaluation

Run all commands from this `code/` directory.

### Natural Scenario

The end-to-end command for the provided image-generation wrapper is:

```bash
bash scripts/eval_natural.sh
```

The script generates images with the configured `gpt-image-1` wrapper and evaluates them with the judge model configured as `VLM_MODEL` in `src/tasks/natural/eval.py`. Images are written to `responses/natural/<model>/imgs/`; JSON results and visualizations are written to `responses/natural/<model>/results/` and `responses/natural/<model>/check/`.

To evaluate another T2I model, place one PNG image per benchmark instance in `responses/natural/<model>/imgs/`, named `<id>.png` to match `benchmarks/natural/<id>.json`, then run:

```bash
python src/tasks/natural/eval.py --model <model>
```

### Knolling Scenario

The end-to-end command for the provided image-generation wrapper is:

```bash
bash scripts/eval_knolling.sh
```

The Knolling pipeline first generates or collects images, uses Qwen3-VL-8B-Instruct to ground objects and colors, derives geometric relations from the grounded boxes, and finally executes the target DSL expression.

To evaluate another T2I model, put images in `responses/knolling/<model>/imgs/` using the same `<id>.png` naming convention, then run:

```bash
python src/tasks/knolling/grounding.py --model <model> --concurrency_limit 1
python src/tasks/knolling/eval.py --model <model>
```

Grounding outputs are stored in `responses/knolling/<model>/grounding/json/`. The verifier writes per-instance results to `responses/knolling/<model>/results/` and diagnostic visualizations to `responses/knolling/<model>/grounding/check/`.

## Text-Only Layout Analysis

`src/draw_llm.py` is used for the text-only Knolling analysis in the paper. It asks a language model to produce a layout specification from each benchmark instruction and saves the resulting object lists under `responses/knolling/<model>/grounding/json/`:

```bash
python src/draw_llm.py --model <language-model>
```

The generated layouts can then be checked with the same Knolling verifier.
