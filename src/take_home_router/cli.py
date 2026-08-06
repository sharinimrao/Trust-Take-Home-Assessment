"""Command-line interface for local routing and API serving."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import uvicorn

from take_home_router.schemas import PromptMetadata, RouteRequest
from take_home_router.service import ClassifierService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    route = subparsers.add_parser("route", help="classify one prompt locally")
    prompt_source = route.add_mutually_exclusive_group()
    prompt_source.add_argument("--prompt", help="prompt text to classify")
    prompt_source.add_argument("--prompt-file", type=Path, help="UTF-8 file containing a prompt")
    route.add_argument("--candidate", action="append", dest="candidates")
    route.add_argument("--cost-saving", type=float, default=None, metavar="0-100")
    route.add_argument("--explain", action="store_true")
    route.add_argument("--request-id")

    subparsers.add_parser("models", help="list candidate generation models")

    serve = subparsers.add_parser("serve", help="start the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--workers", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = cast(str, args.command)
    if command == "serve":
        port = cast(int, args.port)
        workers = cast(int, args.workers)
        if not 1 <= port <= 65_535:
            parser.error("--port must be between 1 and 65535")
        if workers <= 0:
            parser.error("--workers must be positive")
        uvicorn.run(
            "take_home_router.api:app",
            host=cast(str, args.host),
            port=port,
            workers=workers,
        )
        return 0

    try:
        service = ClassifierService.from_environment()
        if command == "models":
            print(service.catalog().model_dump_json(indent=2))
            return 0
        prompt = _read_prompt(
            cast(str | None, args.prompt), cast(Path | None, args.prompt_file), parser
        )
        request = RouteRequest(
            prompt=prompt,
            metadata=PromptMetadata(
                candidate_models=cast(list[str] | None, args.candidates),
                cost_saving_preference=cast(float | None, args.cost_saving),
                include_explanations=cast(bool, args.explain),
                request_id=cast(str | None, args.request_id),
            ),
        )
        response = service.route(request)
        print(json.dumps(response.model_dump(mode="json"), indent=2, sort_keys=True))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


def _read_prompt(
    inline: str | None, prompt_file: Path | None, parser: argparse.ArgumentParser
) -> str:
    if inline is not None:
        return inline
    if prompt_file is not None:
        return prompt_file.read_text(encoding="utf-8")
    if sys.stdin.isatty():
        parser.error("provide --prompt, --prompt-file, or pipe a prompt on stdin")
    return sys.stdin.read()


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":  # pragma: no cover
    entrypoint()
