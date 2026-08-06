from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_offline_evidence_is_consistent_with_runtime_config() -> None:
    evidence = json.loads(
        (ROOT / "evidence" / "offline_routerbench_summary.json").read_text(encoding="utf-8")
    )
    config = json.loads((ROOT / "config" / "router.json").read_text(encoding="utf-8"))
    assert config["schema_version"] == 2
    assert config["random_selection_probability"] == 0.3

    source = evidence["source"]
    assert len(source["source_file_sha256"]) == 64
    assert len(source["source_bundle_sha256"]) == 64
    assert evidence["dataset"]["held_out_rows"] == config["benchmark"]["held_out_rows"]
    assert evidence["schema_version"] == 2
    assert evidence["serving_policy"] == {
        "metrics_cover_classifier_only": True,
        "random_selection_probability": config["random_selection_probability"],
        "note": (
            "The recorded replay predates the uniform random exploration layer and does not "
            "estimate its quality or cost."
        ),
    }

    s2 = evidence["finalists"]["s2_improved"]
    hybrid = evidence["finalists"]["hybrid_no_a3"]
    assert s2["included_in_this_repository"] is True
    assert hybrid["included_in_this_repository"] is False
    assert s2["lambda_penalty"] == config["lambda_penalty"]
    assert (
        abs(
            float(s2["quality_retained_percent"])
            - float(config["benchmark"]["quality_retained_percent"])
        )
        < 0.05
    )
    assert (
        abs(float(s2["cost_savings_percent"]) - float(config["benchmark"]["cost_savings_percent"]))
        < 0.05
    )
    assert s2["routing_latency_p50_ms"] == config["benchmark"]["routing_cpu_p50_ms"]
    assert s2["routing_latency_p95_ms"] == config["benchmark"]["routing_cpu_p95_ms"]
