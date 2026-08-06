"""Deterministic prompt features used by the bundled classifier artifacts."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from itertools import pairwise

EMBEDDING_DIMENSIONS = 48
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class PromptFeatures:
    prompt_chars: int
    prompt_approx_tokens: int
    has_code_fence: bool
    emb: tuple[float, ...]


def signed_hash_prompt_embedding(
    prompt: str, dimensions: int = EMBEDDING_DIMENSIONS
) -> tuple[float, ...]:
    """Reproduce the exact normalized signed-hash embedding used in training."""

    if dimensions <= 0:
        raise ValueError("dimensions must be positive")
    tokens = _TOKEN_PATTERN.findall(prompt.lower())[:2_000]
    terms = [*tokens, *(f"{left}\0{right}" for left, right in pairwise(tokens))]
    vector = [0.0] * dimensions
    for term in terms:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    normalized = vector if norm == 0.0 else [value / norm for value in vector]
    return tuple(normalized)


def extract_prompt_features(prompt: str) -> PromptFeatures:
    """Build exactly the prompt-only feature contract used to fit the artifacts."""

    if not prompt.strip():
        raise ValueError("prompt must contain non-whitespace text")
    return PromptFeatures(
        prompt_chars=len(prompt),
        prompt_approx_tokens=max(1, len(prompt) // 4),
        has_code_fence="```" in prompt,
        emb=signed_hash_prompt_embedding(prompt),
    )
