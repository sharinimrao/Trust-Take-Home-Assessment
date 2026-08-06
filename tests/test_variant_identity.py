from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src" / "take_home_router"


def _runtime_import_roots() -> set[str]:
    roots: set[str] = set()
    for path in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.partition(".")[0])
    return roots


def _dependency_name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip().lower()


def test_variant_is_core_s2_without_burr_framework_or_hybrid() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = cast(dict[str, object], pyproject["project"])
    dependencies = cast(list[str], project["dependencies"])
    assert "burr" not in {_dependency_name(requirement) for requirement in dependencies}

    import_roots = _runtime_import_roots()
    assert "burr" not in import_roots
    assert "router" not in import_roots

    source = "\n".join(path.read_text(encoding="utf-8") for path in SOURCE_ROOT.rglob("*.py"))
    assert "s2_a2_hybrid" not in source
    assert "WeightedEnsembleRouter" not in source
    assert not (ROOT / "artifacts" / "s2_a2_hybrid").exists()

    config = json.loads((ROOT / "config" / "router.json").read_text(encoding="utf-8"))
    assert config["classifier_name"] == "s2-savings-router"

    metadata = json.loads((ROOT / "artifacts" / "s2" / "metadata.json").read_text())
    assert "a2_score" in metadata["scalar_features"]

    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "core s2 sweep implementation" in readme
    assert "not a trustrouter-plus-burr integration" in readme
