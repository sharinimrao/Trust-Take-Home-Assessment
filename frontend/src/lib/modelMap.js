/**
 * The router's classifier was trained on RouterBench, so `selected_model`
 * comes back as a snapshot-era model ID (e.g. "gpt-4-1106-preview",
 * "claude-v2") rather than a model you can actually pick on claude.ai or
 * chatgpt.com today. This module is the documented compatibility layer
 * between what the router says and where we can actually send the prompt.
 *
 * Mapping rules (documented per Instructions.md "document any mapping,
 * fallback, or compatibility decisions you make"):
 *
 * 1. Anthropic-family legacy IDs (claude-v1, claude-v2, claude-instant-v1)
 *    route to claude.ai. claude.ai does not let a signed-in user pick a
 *    specific legacy snapshot from the composer, so we surface the
 *    destination and the *tier* the router selected (frontier vs. fast)
 *    rather than pretending we can force claude-v2 specifically.
 * 2. OpenAI-family legacy IDs (gpt-4-1106-preview, gpt-3.5-turbo-1106)
 *    route to chatgpt.com on the same tier logic.
 * 3. Everything else in the RouterBench catalog (WizardLM, Llama 2,
 *    Mistral/Mixtral, Yi-34B) is an open-weight model with no first-party
 *    surface on claude.ai or chatgpt.com. These are marked `fallback: true`
 *    and routed to whichever of the two destinations represents the
 *    cheapest/fastest tier, since that's the closest intent match to a
 *    router picking an inexpensive open model. This is a deliberate
 *    approximation, not a claim of equivalence, and is called out in the
 *    UI whenever it applies.
 */

export const DESTINATIONS = {
  CLAUDE: 'claude.ai',
  CHATGPT: 'chatgpt.com',
};

const MODEL_MAP = {
  'claude-v1': { destination: DESTINATIONS.CLAUDE, tier: 'frontier', fallback: false },
  'claude-v2': { destination: DESTINATIONS.CLAUDE, tier: 'frontier', fallback: false },
  'claude-instant-v1': { destination: DESTINATIONS.CLAUDE, tier: 'fast', fallback: false },
  'gpt-4-1106-preview': { destination: DESTINATIONS.CHATGPT, tier: 'frontier', fallback: false },
  'gpt-3.5-turbo-1106': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: false },

  // No first-party claude.ai / chatgpt.com surface for these — approximated
  // onto the cheapest/fastest supported destination tier.
  'WizardLM/WizardLM-13B-V1.2': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
  'meta/llama-2-70b-chat': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
  'meta/code-llama-instruct-34b-chat': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
  'mistralai/mistral-7b-chat': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
  'mistralai/mixtral-8x7b-chat': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
  'zero-one-ai/Yi-34B-Chat': { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true },
};

const DEFAULT_MAPPING = { destination: DESTINATIONS.CHATGPT, tier: 'fast', fallback: true };

/**
 * Resolve a raw `selected_model` value from the router into a destination
 * we can hand the prompt off to, plus metadata about whether that mapping
 * is exact or an approximation.
 */
export function resolveDestination(selectedModel) {
  const mapping = MODEL_MAP[selectedModel] ?? DEFAULT_MAPPING;
  return {
    modelId: selectedModel,
    destination: mapping.destination,
    tier: mapping.tier,
    isFallback: mapping.fallback || !MODEL_MAP[selectedModel],
  };
}
