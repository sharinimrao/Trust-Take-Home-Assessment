const BASE_URL = import.meta.env.VITE_ROUTER_API_URL || 'http://127.0.0.1:8000';

export class RouterApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'RouterApiError';
    this.status = status;
  }
}

/**
 * Send a prompt to POST /v1/route and return the parsed RouteResponse.
 * Throws RouterApiError with a human-readable message on failure.
 */
export async function routePrompt(prompt, { costSavingPreference, includeExplanations = true } = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/v1/route`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        prompt,
        metadata: {
          include_explanations: includeExplanations,
          ...(costSavingPreference !== undefined ? { cost_saving_preference: costSavingPreference } : {}),
        },
      }),
    });
  } catch (networkError) {
    throw new RouterApiError(
      `Could not reach the router at ${BASE_URL}. Is the backend running?`,
      0,
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response body wasn't JSON; fall back to statusText
    }
    throw new RouterApiError(`Routing failed (${response.status}): ${detail}`, response.status);
  }

  return response.json();
}

export async function fetchHealth() {
  const response = await fetch(`${BASE_URL}/healthz`);
  if (!response.ok) throw new RouterApiError('Health check failed', response.status);
  return response.json();
}

export async function fetchModelCatalog() {
  const response = await fetch(`${BASE_URL}/v1/models`);
  if (!response.ok) throw new RouterApiError('Could not load model catalog', response.status);
  return response.json();
}
