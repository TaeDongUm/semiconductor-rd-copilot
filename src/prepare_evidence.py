from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence_extraction import build_evidence_prompt


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare evidence-extraction prompts without calling an LLM API.")
    parser.add_argument("--case", default="data/cases/hbm_thermal.json")
    parser.add_argument("--papers", default="evals/golden/hbm_thermal/v1/golden.jsonl")
    parser.add_argument("--sources", default="data/evidence/hbm_thermal_sources.jsonl")
    parser.add_argument("--output-dir", default="prompts/evidence/hbm_thermal")
    args = parser.parse_args()

    case = _load_json(Path(args.case))
    papers = {row["candidate_id"]: row for row in _load_jsonl(Path(args.papers))}
    sources = _load_jsonl(Path(args.sources))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for source in sources:
        paper_id = source["paper_id"]
        paper = papers.get(paper_id)
        if not paper:
            continue
        prompt = build_evidence_prompt(
            case=case,
            paper=paper,
            source_text=source["source_summary"],
            source_scope=source.get("source_scope", "abstract"),
        )
        output_path = output_dir / f"{paper_id}.md"
        output_path.write_text(prompt, encoding="utf-8")
        written += 1

    print(f"Prepared {written} evidence prompts in {output_dir}")
    print("No LLM API was called.")


if __name__ == "__main__":
    main()
