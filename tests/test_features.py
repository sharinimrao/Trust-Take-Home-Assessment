from __future__ import annotations

import math

import pytest

from take_home_router.features import extract_prompt_features, signed_hash_prompt_embedding


def test_prompt_feature_contract_is_deterministic_and_normalized() -> None:
    prompt = "Explain this:\n```python\nprint('hello')\n```"

    first = extract_prompt_features(prompt)
    second = extract_prompt_features(prompt)

    assert first == second
    assert first.prompt_chars == len(prompt)
    assert first.prompt_approx_tokens == max(1, len(prompt) // 4)
    assert first.has_code_fence is True
    assert len(first.emb) == 48
    assert math.isclose(
        math.sqrt(sum(value * value for value in first.emb)),
        1.0,
        rel_tol=1e-12,
    )


def test_hash_embedding_keeps_punctuation_and_bigrams_in_the_contract() -> None:
    assert signed_hash_prompt_embedding("call foo()") != signed_hash_prompt_embedding("call foo")
    assert signed_hash_prompt_embedding("one two") != signed_hash_prompt_embedding("two one")


def test_prompt_validation_fails_closed() -> None:
    with pytest.raises(ValueError, match="non-whitespace"):
        extract_prompt_features("  \n")
    with pytest.raises(ValueError, match="positive"):
        signed_hash_prompt_embedding("hello", dimensions=0)
