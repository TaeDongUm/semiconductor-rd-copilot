from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .case_definition import write_case
from .evidence_extraction import build_evidence_prompt
from .openalex import OpenAlexClient, OpenAlexError, PaperRecord
from .problem_decomposition import (
    build_problem_decomposition_prompt,
    parse_problem_decomposition,
)
from .query_generator import generate_query_plan
from .retrieve_case import _merge_papers, query_plan_to_dict, write_jsonl


def _read_problem(problem: str | None, problem_file: Path | None) -> str:
    if problem and problem.strip():
        return problem.strip()
    if problem_file:
        text = problem_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    raise ValueError("provide --problem or --problem-file")


def prepare_manual_problem_step(problem: str, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "00_problem.txt").write_text(problem.strip() + "\n", encoding="utf-8")
    prompt_path = run_dir / "01_problem_decomposition_prompt.md"
    prompt_path.write_text(build_problem_decomposition_prompt(problem), encoding="utf-8")
    return prompt_path


def accept_problem_decomposition(response_path: Path, run_dir: Path) -> tuple[Path, Path]:
    response = response_path.read_text(encoding="utf-8")
    case = parse_problem_decomposition(response)

    case_path = run_dir / "02_case.json"
    write_case(case, case_path)

    plan = generate_query_plan(case)
    query_path = run_dir / "03_query_plan.json"
    query_path.write_text(
        json.dumps(query_plan_to_dict(plan), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return case_path, query_path


def retrieve_for_run(
    case_path: Path,
    run_dir: Path,
    *,
    mode: str = "hybrid",
    per_query: int = 5,
    limit: int = 15,
    include_closed_access: bool = False,
    client: OpenAlexClient | None = None,
) -> Path:
    from .case_definition import load_case

    case = load_case(case_path)
    plan = generate_query_plan(case)
    client = client or OpenAlexClient()
    groups: list[list[PaperRecord]] = []

    if mode in {"keyword", "hybrid"}:
        groups.append(
            client.search_many(
                [item.query for item in plan.keyword_queries],
                mode="keyword",
                per_query=per_query,
                open_access_only=not include_closed_access,
                limit=limit,
            )
        )
    if mode in {"semantic", "hybrid"}:
        groups.append(
            client.search(
                plan.semantic_query,
                mode="semantic",
                per_page=min(limit, 50),
                open_access_only=not include_closed_access,
            )
        )

    papers = _merge_papers(groups, limit)
    output = run_dir / "04_papers.jsonl"
    write_jsonl(papers, output)
    return output


def _paper_prompt_payload(record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "paper_id": f"R{index:02d}",
        "title": str(record.get("title") or ""),
        "doi": str(record.get("doi") or record.get("openalex_id") or ""),
    }


def prepare_evidence_prompts(case_path: Path, papers_path: Path, run_dir: Path) -> list[Path]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in papers_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    output_dir = run_dir / "05_evidence_prompts"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    for index, paper in enumerate(rows, start=1):
        abstract = str(paper.get("abstract") or "").strip()
        if not abstract:
            continue
        payload = _paper_prompt_payload(paper, index)
        prompt = build_evidence_prompt(
            case=case,
            paper=payload,
            source_text=abstract,
            source_scope="abstract",
        )
        path = output_dir / f"{payload['paper_id']}.md"
        path.write_text(prompt, encoding="utf-8")
        paths.append(path)

    manifest = {
        "paper_count": len(rows),
        "prompt_count": len(paths),
        "prompts": [str(path.relative_to(run_dir)) for path in paths],
    }
    (run_dir / "05_evidence_prompt_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the manual/API-independent front half of an engineering investigation."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Create a ChatGPT-ready decomposition prompt")
    prepare.add_argument("--problem")
    prepare.add_argument("--problem-file", type=Path)
    prepare.add_argument("--run-dir", type=Path, required=True)

    accept = sub.add_parser("accept", help="Validate a ChatGPT JSON response and build queries")
    accept.add_argument("--response", type=Path, required=True)
    accept.add_argument("--run-dir", type=Path, required=True)

    retrieve = sub.add_parser("retrieve", help="Call OpenAlex using a reviewed case/query plan")
    retrieve.add_argument("--case", type=Path, required=True)
    retrieve.add_argument("--run-dir", type=Path, required=True)
    retrieve.add_argument("--mode", choices=["keyword", "semantic", "hybrid"], default="hybrid")
    retrieve.add_argument("--per-query", type=int, default=5)
    retrieve.add_argument("--limit", type=int, default=15)
    retrieve.add_argument("--include-closed-access", action="store_true")

    evidence = sub.add_parser("prepare-evidence", help="Create ChatGPT-ready evidence prompts")
    evidence.add_argument("--case", type=Path, required=True)
    evidence.add_argument("--papers", type=Path, required=True)
    evidence.add_argument("--run-dir", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "prepare":
        problem = _read_problem(args.problem, args.problem_file)
        path = prepare_manual_problem_step(problem, args.run_dir)
        print(f"problem decomposition prompt: {path}")
        print("Paste this prompt into ChatGPT and save the JSON-only response for the accept step.")
        return

    if args.command == "accept":
        case_path, query_path = accept_problem_decomposition(args.response, args.run_dir)
        print(f"case: {case_path}")
        print(f"query plan: {query_path}")
        print("Review/edit the case or query plan before retrieval if needed.")
        return

    if args.command == "retrieve":
        try:
            papers_path = retrieve_for_run(
                args.case,
                args.run_dir,
                mode=args.mode,
                per_query=args.per_query,
                limit=args.limit,
                include_closed_access=args.include_closed_access,
            )
        except OpenAlexError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"papers: {papers_path}")
        return

    if args.command == "prepare-evidence":
        paths = prepare_evidence_prompts(args.case, args.papers, args.run_dir)
        print(f"evidence prompts: {len(paths)}")
        print(f"directory: {args.run_dir / '05_evidence_prompts'}")
        return


if __name__ == "__main__":
    main()
