# Take Home Model Router

This repository contains a prompt-routing backend. Given a prompt, it scores the configured language models and returns the model that should handle the request.

The repository includes the trained classifier artifacts, routing policy, FastAPI service, command-line interface, and tests. It does not generate an answer or call a model provider. Its job ends after it returns a model ID.

This repository packages the core S2 Sweep implementation at its savings operating point. It is not a TrustRouter-plus-Burr integration and has no Burr or TrustRouter framework dependency at runtime.

Each request uses the S2 quality-cost winner 70% of the time and selects uniformly from the eligible models 30% of the time. The response exposes `policy.selection_mode` as `scored` or `random`, along with `random_selection_probability: 0.3`.

The offline benchmark figures in [`evidence/offline_routerbench_summary.json`](evidence/offline_routerbench_summary.json) describe the classifier-only policy before the exploration layer. They do not measure the final stochastic serving policy.

The take-home assignment is to build the user-facing experience around this router and explore how it can work with Claude and ChatGPT. See [Instructions.md](Instructions.md) for the assignment details.

## How it works

```text
Prompt
  -> request validation
  -> prompt feature extraction
  -> per-model quality and token predictions
  -> quality/cost routing policy
  -> selected model ID and ranked candidate scores
```

The main endpoint is `POST /v1/route`. It accepts a prompt and optional routing settings, then returns a `selected_model` field. That field is the handoff point for a front end or provider integration.

The API also exposes:

- `GET /healthz` for service health
- `GET /v1/models` for the supported model IDs
- `/docs` for interactive FastAPI documentation

## Run it locally

The project requires Python 3.11 and [`uv`](https://docs.astral.sh/uv/).

LightGBM also needs an OpenMP runtime. On macOS, install it with:

```bash
brew install libomp
```

Install the project and start the API:

```bash
uv sync --dev
uv run take-home-router serve --host 127.0.0.1 --port 8000
```

In another terminal, send a prompt:

```bash
curl -s http://127.0.0.1:8000/v1/route \
  -H 'content-type: application/json' \
  --data @examples/request.json
```

You can also classify a prompt without starting the server:

```bash
uv run take-home-router route \
  --prompt "Write a Python LRU cache and explain its complexity" \
  --explain
```

## API request

```json
{
  "prompt": "Write a Python function that merges two sorted lists.",
  "metadata": {
    "cost_saving_preference": 50,
    "include_explanations": true,
    "request_id": "example-123"
  }
}
```

`metadata` is optional. It can also contain a `candidate_models` list to limit the models considered by the router. The response includes the selected model, routing policy details, and scores for the eligible candidates.

## Repository layout

```text
src/take_home_router/   classifier, routing policy, API, and CLI
artifacts/              trained model and calibration files
config/router.json      model catalog and routing configuration
evidence/               offline benchmark summary
examples/request.json   sample API request
tests/                  unit and integration tests
```

## Checks

Run the full test, lint, and type-check suite with:

```bash
make check
```

The backend is intentionally provider-independent. No API credentials are required to run the classifier itself.
