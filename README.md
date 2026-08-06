# Take Home Model Router

A self-contained backend that classifies a prompt and returns the generation model that should handle it. The repository packages the actual trained classifier weights, a strict request contract, an auditable selection policy, a FastAPI service, and a local CLI. It does not call any generation provider.

## Why this model

TrustRouter's final offline study produced two practical finalists. This repository deliberately implements the second option by retained quality, the **S2 savings router**, because the assignment excludes the best quality classifier.

| Offline RouterBench result | S2 in this repository | Excluded S2+A2 hybrid |
|---|---:|---:|
| Quality retained | 96.9% | 99.1% |
| Cost savings | 18.7% | 9.0% |
| Router CPU p50 / p95 | 2.28 / 2.53 ms | 2.82 / 3.30 ms |
| Generation calls per request | 1 | 1 |

The excluded hybrid averages S2's final prediction with a separate A2 router prediction. This implementation does **not** contain that ensemble. S2 does use a leakage-safe pairwise score as one input feature because that feature is part of the measured S2 artifact itself.

These numbers come from an offline replay over 282 held-out RouterBench rows. They are useful comparative evidence, not a live production claim.

## Architecture

```mermaid
flowchart LR
    A[Prompt + routing metadata] --> B[Pydantic validation]
    B --> C[Prompt feature extractor]
    C --> D[48-D signed-hash embedding]
    D --> E[Auxiliary scalar feature]
    E --> F[Per-candidate LightGBM heads]
    F --> G[Platt calibration + token estimate]
    G --> H[Quality-cost policy]
    H --> I[Selected model ID + ranked audit scores]
```

The serving path has four intentionally small layers:

1. **Features**: prompt length, approximate tokens, code-fence status, and the exact 48-dimensional signed-hash representation used during training.
2. **Classifier**: one quality booster and one output-token regressor for each candidate model. The quality output is Platt calibrated.
3. **Policy**: a transparent quality-minus-cost objective with deterministic tie-breaking.
4. **Delivery**: a typed in-process service exposed through FastAPI and a CLI.

All artifacts load and validate at startup. Unknown candidates, schema drift, missing files, invalid calibration state, and non-finite predictions fail closed.

## Implementation plan

The repository was built against this delivery plan:

1. **Select the model**: compare TrustRouter's finalists and choose S2, the strongest measured classifier below the excluded best-quality hybrid.
2. **Isolate inference**: reproduce only S2's feature contract, auxiliary scalar, trained LightGBM heads, calibration, and policy. Do not carry over TrustRouter's framework or provider integrations.
3. **Define the boundary**: accept a prompt plus routing metadata and return one selected model with ranked, auditable candidate scores.
4. **Package the system**: expose the same typed service through a CLI, HTTP API, distributable wheel, and non-root container.
5. **Close the feedback loop**: test deterministic features, model artifacts, golden prediction parity, policy behavior, API validation, strict typing, linting, and package builds.

Each phase is complete in this version. The validation commands and remaining production limitations are documented below.

## Quick start

The project requires Python 3.11 and [`uv`](https://docs.astral.sh/uv/).

LightGBM requires an OpenMP runtime. Install it once when developing on macOS:

```bash
brew install libomp
```

The provided Debian container installs `libgomp1` automatically.

From the repository root:

```bash
uv sync --dev
uv run take-home-router route \
  --prompt "Write a Python LRU cache and explain its complexity" \
  --explain
```

Start the API:

```bash
uv run take-home-router serve --host 127.0.0.1 --port 8000
```

Then route a prompt:

```bash
curl -s http://127.0.0.1:8000/v1/route \
  -H 'content-type: application/json' \
  --data @examples/request.json
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## API contract

### `POST /v1/route`

```json
{
  "prompt": "Write a Python function that merges two sorted lists.",
  "metadata": {
    "candidate_models": [
      "mistralai/mistral-7b-chat",
      "gpt-4-1106-preview"
    ],
    "cost_saving_preference": 50,
    "include_explanations": true,
    "request_id": "example-123"
  }
}
```

- `prompt` is required and must contain non-whitespace text.
- `candidate_models` optionally restricts selection to a known subset.
- `cost_saving_preference` ranges from `0` for quality-only selection to `100` for cost-only selection. `50` reproduces the benchmark-tuned ordering.
- `include_explanations` returns the five largest LightGBM feature contributions for each candidate.
- `request_id` is echoed when supplied. The service generates one otherwise.

The response includes the selected model and the evidence used to choose it:

```json
{
  "request_id": "example-123",
  "classifier": "s2-savings-router",
  "classifier_version": "routerbench-mini-seed-23",
  "selected_model": "mistralai/mistral-7b-chat",
  "routing_latency_ms": 2.4,
  "policy": {
    "cost_saving_preference": 50.0,
    "quality_weight": 0.5,
    "cost_weight": 0.5,
    "lambda_penalty": 3.0
  },
  "candidates": [
    {
      "model": "mistralai/mistral-7b-chat",
      "predicted_quality": 0.78,
      "expected_output_tokens": 184,
      "uncertainty": 0.41,
      "benchmark_mean_cost_usd": 0.0000294,
      "quality_component": 0.39,
      "cost_penalty": 0.0000441,
      "utility": 0.3899559,
      "top_contributions": []
    }
  ]
}
```

Values above are illustrative. Run the request to obtain predictions from the bundled artifacts.

Additional endpoints:

- `GET /healthz`: process and model readiness.
- `GET /v1/models`: classifier version and supported candidate IDs.

## Model details

For each candidate model, S2 computes:

- a calibrated probability that the candidate will answer successfully,
- an expected output-token count,
- uncertainty derived from the calibrated Bernoulli probability,
- additive LightGBM feature contributions for inspection.

At the default preference, selection is equivalent to:

```text
utility(candidate) = predicted_quality(candidate)
                     - 3.0 * benchmark_mean_cost(candidate)
```

The public preference control scales the quality and cost terms without retraining:

```text
p = cost_saving_preference / 100
utility = (1 - p) * predicted_quality - p * 3.0 * benchmark_mean_cost
```

At `p = 0.5`, multiplying both terms by `0.5` does not change the benchmark ordering. Equal utilities prefer the cheaper candidate, then the lexicographically smaller model ID.

### Artifact provenance

The checked-in artifacts were trained by TrustRouter's leakage-aware RouterBench mini benchmark with seed 23:

```text
artifacts/
├── auxiliary/a2_matrixfact.json  # scalar feature model used by S2
└── s2/
    ├── metadata.json             # frozen feature and candidate schema
    └── <candidate>/
        ├── quality.txt            # LightGBM success classifier
        ├── tokens.txt             # LightGBM output-length regressor
        └── calibration.json       # held-out Platt calibration
```

The feature implementation is intentionally reproduced locally rather than imported from TrustRouter. The application contains no TrustRouter registry, proxy, gateway, benchmark harness, dashboard, session state, or generation client.

## Repository layout

```text
src/take_home_router/
├── features.py   # exact prompt-to-feature contract
├── model.py      # artifact validation and calibrated inference
├── policy.py     # auditable quality-cost selection
├── service.py    # in-process orchestration
├── schemas.py    # public request and response models
├── api.py        # FastAPI endpoints and lifecycle
└── cli.py        # local route, models, and serve commands

tests/            # unit, artifact, service, and HTTP tests
config/router.json
artifacts/
examples/request.json
```

## Engineering choices

- **Actual weights are included.** A reviewer can run meaningful inference without credentials, provider calls, or a training download.
- **Startup is strict.** The service refuses to start when artifact and policy candidate sets differ.
- **The hot path is deterministic.** Feature hashing, candidate ordering, and tie-breaking are stable.
- **Predictions are inspectable.** Responses can include ranked alternatives, decomposed utility, uncertainty, and top feature contributions.
- **The service is select-only.** It cannot spend money or leak a prompt to a model provider.
- **Model access is synchronized.** A process-level lock avoids relying on undocumented concurrent access behavior in shared LightGBM booster objects. Horizontal scaling remains process based.

## Validation

```bash
make check
```

This runs:

- Ruff lint and format checks,
- strict Pyright type checking,
- unit tests for feature and policy invariants,
- real artifact loading and inference tests,
- full in-process service tests,
- HTTP lifecycle and validation tests.

Build and run the non-root container:

```bash
docker build -t take-home-router .
docker run --rm -p 8000:8000 take-home-router
```

## Limitations and production follow-up

This is a complete, executable model-serving take-home, but the bundled artifacts are research artifacts rather than a current production fleet.

- Candidate IDs and cost observations reflect historical RouterBench models.
- The deterministic signed-hash representation is reproducible and offline, but weaker than a production semantic embedding. A production version should retrain with a frozen BGE/PCA pipeline.
- Quality and calibration can drift as prompts, providers, and models change. Production needs outcome collection, calibration monitoring, and scheduled retraining.
- Mean benchmark cost is a policy anchor, not live pricing. Current token prices and latency should be injected and retuned.
- Capability constraints for tools, images, PDFs, structured output, and context limits should filter candidates before classification.
- The reported latency excludes network, queueing, cold-start, and generation time.

Those constraints are stated explicitly so the repository demonstrates both a working system and the judgment required to operate it responsibly.
