# Take Home Model Router

This repository contains a prompt-routing backend. Given a prompt, it scores the configured language models and returns the model that should handle the request.

The repository includes the trained classifier artifacts, routing policy, FastAPI service, command-line interface, and tests. It does not generate an answer or call a model provider. Its job ends after it returns a model ID.

This repository packages the core S2 Sweep implementation at its savings setting, not a TrustRouter-plus-Burr integration. Everything needed to run it is included here, with no Burr or TrustRouter framework dependency at runtime.

Each request uses the S2 quality-cost winner 70% of the time and selects uniformly from the eligible models 30% of the time. The response exposes `policy.selection_mode` as `scored` or `random`, along with `random_selection_probability: 0.3`.

The offline benchmark figures in [`evidence/offline_routerbench_summary.json`](evidence/offline_routerbench_summary.json) describe the classifier-only policy before the exploration layer. They do not measure the final stochastic serving policy.

The take-home assignment is to build the user-facing experience around this router and explore how it can work with Claude and ChatGPT. See [Instructions.md](Instructions.md) for the assignment details.

## How it works

​```text
Prompt
  -> request validation
  -> prompt feature extraction
  -> per-model quality and token predictions
  -> quality/cost routing policy
  -> selected model ID and ranked candidate scores
​```

The main endpoint is `POST /v1/route`. It accepts a prompt and optional routing settings, then returns a `selected_model` field. That field is the handoff point for a front end or provider integration.

The API also exposes:

- `GET /healthz` for service health
- `GET /v1/models` for the supported model IDs
- `/docs` for interactive FastAPI documentation

## Run it locally

The project requires Python 3.11 and [`uv`](https://docs.astral.sh/uv/).

LightGBM also needs an OpenMP runtime. On macOS, install it with:

​```bash
brew install libomp
​```

Install the project and start the API:

​```bash
uv sync --dev
uv run take-home-router serve --host 127.0.0.1 --port 8000
​```

In another terminal, send a prompt:

​```bash
curl -s http://127.0.0.1:8000/v1/route \
  -H 'content-type: application/json' \
  --data @examples/request.json
​```

You can also classify a prompt without starting the server:

​```bash
uv run take-home-router route \
  --prompt "Write a Python LRU cache and explain its complexity" \
  --explain
​```

## API request

​```json
{
  "prompt": "Write a Python function that merges two sorted lists.",
  "metadata": {
    "cost_saving_preference": 50,
    "include_explanations": true,
    "request_id": "example-123"
  }
}
​```

`metadata` is optional. It can also contain a `candidate_models` list to limit the models considered by the router. The response includes the selected model, routing policy details, and scores for the eligible candidates.

## Repository layout

​```text
src/take_home_router/   classifier, routing policy, API, and CLI
artifacts/              trained model and calibration files
config/router.json      model catalog and routing configuration
evidence/               offline benchmark summary
examples/request.json   sample API request
tests/                  unit and integration tests
​```

## Checks

Run the full test, lint, and type-check suite with:

​```bash
make check
​```

The backend is intentionally provider-independent. No API credentials are required to run the classifier itself.

---

## Take-home submission notes

This section documents what was built on top of the router for the assignment (see [Instructions.md](Instructions.md)).

### What's here

- `frontend/` — React + Vite + Tailwind chat UI (Task 1 & 2).
- `userscript/trust-router.user.js` — Tampermonkey/Violentmonkey userscript prototype for claude.ai and chatgpt.com (Task 3).
- A CORS change to `src/take_home_router/api.py` (`allow_origins=["*"]`) so the frontend can call the API from a different origin during local dev. **This is wide open on purpose for the take-home and should be scoped to the real frontend origin before any real deployment.**

### Running the full stack locally

​```bash
# Terminal 1 — backend
uv sync --dev
uv run take-home-router serve --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd frontend
npm install
cp .env.example .env      # VITE_ROUTER_API_URL defaults to http://127.0.0.1:8000
npm run dev
​```

Open the printed local URL (typically `http://localhost:5173`). There's a login screen first — see below.

### Task 1 — Chat frontend

Single-page chat UI: prompt input, message thread, loading state (animated bubble) and error state (inline error bubble + a "routing trace" panel that flips to an error marker) if the backend is unreachable or returns a non-2xx response. A right-hand "routing trace" panel mirrors the backend's own README pipeline diagram (`validate → features → predict → policy → select`) and lights up as a request resolves, then shows the selected model, `selection_mode` (`scored`/`random`), latency, and the full ranked candidate list with quality scores.

**Login gate:** added per request, but there is no auth backend anywhere in this repository or the assignment. It's a client-side name/email form that stores a session in `sessionStorage` — a UI gate, not a security boundary. This is called out in the UI copy itself and in `frontend/src/components/LoginGate.jsx` so it isn't mistaken for real auth in review.

### Task 2 — Router integration

`frontend/src/lib/api.js` posts to `POST /v1/route` with `include_explanations: true` and surfaces `RouterApiError` distinctly from a successful-but-unhelpful response, so the UI can tell "backend unreachable" apart from "backend rejected the request" (e.g. an unknown `candidate_models` entry, which the backend returns as a 422).

The response is intentionally *not* massaged before display — `selected_model`, `policy.selection_mode`, and per-candidate `utility`/`predicted_quality` are shown as the backend returns them, since the assignment asks the routing decision to be visible, not reinterpreted.

### Task 3 — Handoff to claude.ai / chatgpt.com

Two layers, from simplest to most automated:

1. **In-app handoff (`frontend/src/components/HandoffModal.jsx`)**: after a prompt is routed, "Hand off to claude.ai/chatgpt.com →" copies the prompt to the clipboard and opens the destination site in a new tab. Neither site accepts a prompt via query string or postMessage from an arbitrary origin, so copy-and-open is the honest floor for a same-tab handoff.
2. **Userscript (`userscript/trust-router.user.js`)**: install in Tampermonkey/Violentmonkey, and it watches the composer on claude.ai or chatgpt.com directly, debounces, POSTs the draft to your local router, and renders a small floating badge with the routing decision — so the recommendation shows up *while you're typing on the actual site*, with no copy/paste step. It deliberately does not auto-click either site's model picker; see "compatibility decisions" below for why, and "what's next" for what a real integration would need.

A userscript was chosen over a packaged browser extension for the prototype: no manifest, no build step, and it can be reviewed as a single readable file, which fits a 20-minute take-home conversation better than a full `manifest.json` + background worker + content script bundle. A companion local service (an extra process the userscript or frontend calls) wasn't necessary here since the FastAPI backend already serves this role directly.

### Model mapping / compatibility decisions

`config/router.json`'s catalog is RouterBench-era (`claude-v1`, `claude-v2`, `claude-instant-v1`, `gpt-4-1106-preview`, `gpt-3.5-turbo-1106`, plus open-weight models like Llama 2, Mixtral, WizardLM, Yi-34B). None of these IDs are selectable on claude.ai or chatgpt.com today. `frontend/src/lib/modelMap.js` is the documented compatibility layer:

- Anthropic-family IDs → `claude.ai`, OpenAI-family IDs → `chatgpt.com`, tagged `frontier` or `fast` tier.
- Every open-weight ID (no first-party surface on either site) is approximated onto the cheapest/fastest supported destination and flagged `isFallback: true` — surfaced in the UI as "(approx.)" rather than presented as an exact match.
- This is a stated approximation, not a claim that (e.g.) Mixtral-8x7B and a "fast" ChatGPT tier are equivalent — it's the closest intent match available without a real multi-provider routing layer.

### What's unfinished / what production would need

- **Real auth** on both the frontend and a proper session-bound backend, instead of the demo login gate.
- **Provider APIs instead of DOM automation.** The userscript reads the composer and shows a recommendation, but doesn't switch either site's model picker, because that means depending on unstable, undocumented DOM structure in someone's account UI. A production version should route through Anthropic's and OpenAI's actual APIs (with the user's own API key) rather than automating the consumer web app.
- **A real model catalog.** The classifier would need retraining/recalibration against current model choices instead of the RouterBench-era catalog and the approximate mapping layer above.
- **Cost tracking**, since `Instructions.md` asks for expense receipts if any are incurred — this build used no paid APIs (the router runs entirely locally with no external calls), so there's nothing to report.
