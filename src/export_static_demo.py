from __future__ import annotations

import argparse
import html
from pathlib import Path

from .ui_data import (
    build_matrix_rows,
    demo_metrics,
    find_default_demo_run,
    load_demo_bundle,
    load_retrieval_evaluation,
    load_output_evaluation_comparison,
    output_comparison_rows,
    retrieval_comparison_rows,
    retrieval_summary_metrics,
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_static_demo(bundle: dict, retrieval: dict | None = None, output_comparison: dict | None = None) -> str:
    case = bundle["case"]
    decision = bundle["decision"]
    metrics = demo_metrics(bundle)
    matrix = build_matrix_rows(case, decision)
    headers = list(matrix[0].keys()) if matrix else ["Approach"]

    metric_html = "".join(
        f'<div class="metric"><strong>{esc(label)}</strong><span>{value}</span></div>'
        for label, value in [
            ("Papers", metrics["papers"]),
            ("Evidence", metrics["accepted_evidence_responses"]),
            ("Validation errors", metrics["validation_errors"]),
            ("Approaches", metrics["approaches"]),
            ("Unknowns", metrics["unknowns"]),
            ("Hypotheses", metrics["hypotheses"]),
        ]
    )

    constraint_html = "".join(
        f'<li><strong>{esc(item["id"])} · {esc(item["name"])}</strong><br><small>{esc(", ".join(item.get("search_terms", [])))}</small></li>'
        for item in case.get("constraints", [])
    )

    matrix_head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    matrix_body = "".join(
        "<tr>" + "".join(f"<td>{esc(row.get(h, ''))}</td>" for h in headers) + "</tr>"
        for row in matrix
    )

    unknown_html = "".join(
        f'<li><strong>{esc(item["approach"])}</strong> × {esc(item["constraint"])} — {esc(item["reason"])}</li>'
        for item in decision.get("unknowns", [])
    ) or "<li>None</li>"

    hypothesis_html = "".join(
        f'''<article class="card">
        <h3>{esc(item["hypothesis_id"])}</h3>
        <p>{esc(item["text"])}</p>
        <p><strong>Basis:</strong> {esc(", ".join(item.get("basis_evidence_ids", [])))}</p>
        <p><strong>Next validation:</strong> {esc(item["validation"])}</p>
        </article>'''
        for item in decision.get("hypotheses", [])
    ) or '<p class="muted">No candidate hypothesis.</p>'

    papers_html = "".join(
        f'''<details>
        <summary>{esc(paper["title"])}</summary>
        <p>{esc(paper.get("abstract", ""))}</p>
        <p><strong>DOI:</strong> {esc(paper.get("doi", "-"))} · <strong>Year:</strong> {esc(paper.get("publication_year", "-"))}</p>
        <p><strong>Source:</strong> {esc(paper.get("source_name", "-"))}</p>
        </details>'''
        for paper in bundle.get("papers", [])
    )

    provenance = bundle.get("provenance", {})
    provenance_note = esc(provenance.get("claim", ""))

    retrieval_html = ""
    if retrieval is not None:
        summary = retrieval_summary_metrics(retrieval)
        rows = retrieval_comparison_rows(retrieval)
        row_html = "".join(
            "<tr>"
            f"<td>{esc(row['Strategy'])}</td>"
            f"<td>{esc(row['V1 Recall@20'])}</td>"
            f"<td>{esc(row['V2 Recall@20'])}</td>"
            f"<td>{esc(row['Delta'])}</td>"
            "</tr>"
            for row in rows
        )
        retrieval_html = f"""
<section>
<h2>Retrieval Evaluation · V1 → V2</h2>
<div class=\"metrics\">
<div class=\"metric\"><strong>OpenAlex Source Coverage</strong><span>{esc(summary['source_coverage'])}</span></div>
<div class=\"metric\"><strong>Multi-query Recall@20</strong><span>{esc(summary['multi_v2'])}</span></div>
<div class=\"metric\"><strong>Improvement</strong><span>{esc(summary['multi_delta'])}</span></div>
<div class=\"metric\"><strong>Multi-query Recall@50</strong><span>{esc(summary['best_at_50'])}</span></div>
</div>
<table>
<thead><tr><th>Strategy</th><th>V1 Recall@20</th><th>V2 Recall@20</th><th>Delta</th></tr></thead>
<tbody>{row_html}</tbody>
</table>
<p class=\"muted\">Golden Corpus v1 7편을 고정하고 Query/Ranking 전략만 변경했습니다. 7/7 논문이 OpenAlex에 색인되었습니다. 이 소규모 HBM Thermal benchmark에서는 Multi-query + RRF가 Recall@20 28.6% → 71.4%, Recall@50 42.9% → 85.7%로 개선되었습니다.</p>
</section>
"""


    output_eval = bundle.get("output_evaluation") or {}
    e2e_eval = bundle.get("end_to_end_evaluation") or {}
    output_html = ""
    if output_eval:
        output_html = f"""
<section>
<h2>AI Output Evaluation</h2>
<div class=\"metrics\">
<div class=\"metric\"><strong>Citation validity</strong><span>{float(output_eval.get('citation_validity', 0))*100:.1f}%</span></div>
<div class=\"metric\"><strong>Constraint precision</strong><span>{float(output_eval.get('constraint_precision', 0))*100:.1f}%</span></div>
<div class=\"metric\"><strong>Constraint recall</strong><span>{float(output_eval.get('constraint_recall', 0))*100:.1f}%</span></div>
<div class=\"metric\"><strong>Constraint F1</strong><span>{float(output_eval.get('constraint_f1', 0))*100:.1f}%</span></div>
</div>
<p><strong>Unsupported mapping:</strong> {esc(output_eval.get('unsupported_constraint_mappings', 0))} · <strong>Missed mapping:</strong> {esc(output_eval.get('missed_constraint_mappings', 0))} · <strong>Hypothesis traceability:</strong> {float(output_eval.get('hypothesis_traceability', 0))*100:.1f}%</p>
<p><strong>Quality Gate:</strong> {esc(output_eval.get('deterministic_gate', '-'))}</p>
<p class=\"muted\">Deterministic evaluator는 citation / constraint / numeric / hypothesis traceability를 검증합니다. 자유서술 전체의 의미적 정확성을 완전히 증명하는 평가는 아닙니다.</p>
</section>
"""

    e2e_html = ""
    if e2e_eval:
        e2e_html = f"""
<section>
<h2>End-to-End Gate</h2>
<div class=\"metrics\">
<div class=\"metric\"><strong>Source Coverage</strong><span>{esc(e2e_eval.get('source_coverage', '-'))}</span></div>
<div class=\"metric\"><strong>Retrieval Recall@20</strong><span>{float(e2e_eval.get('retrieval_recall', 0))*100:.1f}%</span></div>
<div class=\"metric\"><strong>Evidence Accepted</strong><span>{esc(e2e_eval.get('evidence_accepted', 0))}/{esc(e2e_eval.get('downstream_papers', 0))}</span></div>
<div class=\"metric\"><strong>Overall Gate</strong><span>{esc(e2e_eval.get('overall_gate', '-'))}</span></div>
</div>
<p class=\"muted\">Execution mode: {esc(e2e_eval.get('execution_mode', '-'))}</p>
</section>
"""


    output_comparison_html = ""
    if output_comparison is not None:
        rows = output_comparison_rows(output_comparison)
        row_html = "".join(
            "<tr>"
            f"<td>{esc(row['Metric'])}</td>"
            f"<td>{esc(row['V1'])}</td>"
            f"<td>{esc(row['V2'])}</td>"
            f"<td>{esc(row['Delta'])}</td>"
            "</tr>"
            for row in rows
        )
        output_comparison_html = f"""
<section>
<h2>AI Output Evaluation · V1 → V2</h2>
<table>
<thead><tr><th>Metric</th><th>V1</th><th>V2</th><th>Delta</th></tr></thead>
<tbody>{row_html}</tbody>
</table>
<p class=\"muted\">Missed mapping {esc(output_comparison.get('missed_constraint_mappings', {}).get('v1', '-'))} → {esc(output_comparison.get('missed_constraint_mappings', {}).get('v2', '-'))} · Quality Gate {esc(output_comparison.get('quality_gate', {}).get('v1', '-'))} → {esc(output_comparison.get('quality_gate', {}).get('v2', '-'))}</p>
</section>
"""

    return f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Semiconductor R&D Copilot — Verified Demo</title>
<style>
body {{ font-family: system-ui, -apple-system, sans-serif; margin: 0; background: #f6f7f9; color: #17191c; }}
main {{ max-width: 1200px; margin: auto; padding: 32px 20px 64px; }}
h1 {{ margin-bottom: 6px; }} .muted, small {{ color: #626973; }}
.notice {{ padding: 14px 16px; background: white; border: 1px solid #dfe3e8; border-radius: 10px; margin: 18px 0; }}
.metrics {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(140px,1fr)); gap: 10px; margin: 20px 0 28px; }}
.metric {{ background: white; border: 1px solid #dfe3e8; border-radius: 10px; padding: 14px; }}
.metric strong {{ display:block; font-size: 12px; color:#626973; }} .metric span {{ font-size: 26px; font-weight:700; }}
section {{ background:white; border:1px solid #dfe3e8; border-radius:12px; padding:20px; margin:16px 0; overflow:auto; }}
table {{ border-collapse: collapse; width: 100%; min-width: 900px; }} th,td {{ border-bottom:1px solid #e6e9ed; text-align:left; padding:10px; vertical-align:top; }}
th {{ font-size:12px; }} li {{ margin: 8px 0; }}
.card {{ border:1px solid #e3e6ea; border-radius:10px; padding:14px; margin:10px 0; }}
details {{ padding: 12px 0; border-bottom:1px solid #e6e9ed; }} summary {{ cursor:pointer; font-weight:600; }}
</style>
</head>
<body><main>
<h1>Semiconductor R&D Copilot</h1>
<p class="muted">Evidence-constrained semiconductor R&D investigation · verified HBM Thermal end-to-end demo</p>
<div class="notice"><strong>실행 방식</strong><br>{esc((bundle.get("end_to_end_evaluation") or {}).get("execution_mode", "verified stored run"))}<br><small>{provenance_note}</small></div>
<div class="metrics">{metric_html}</div>
<section><h2>Engineering Problem</h2><p>{esc(case['problem_statement'])}</p><h3>Constraints</h3><ul>{constraint_html}</ul></section>
<section><h2>Approach × Constraint Matrix</h2><p class="muted">+ benefit · − downside · ± trade-off · • 관련 근거 · ? 근거 부족</p><table><thead><tr>{matrix_head}</tr></thead><tbody>{matrix_body}</tbody></table></section>
<section><h2>Key Unknowns</h2><ul>{unknown_html}</ul></section>
<section><h2>Candidate Hypotheses & Next Validation</h2>{hypothesis_html}</section>
<section><h2>Evidence Papers</h2>{papers_html}</section>
{retrieval_html}
{output_comparison_html}
{output_html}
{e2e_html}
<section><h2>Interpretation Rule</h2><p>This demo does not identify a best technology or a proven root cause. It narrows the investigation space using verified evidence and preserves unresolved constraints for human review.</p></section>
</main></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("demo/index.html"))
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    run_dir = args.run_dir or find_default_demo_run(project_root)
    bundle = load_demo_bundle(run_dir)
    try:
        retrieval = load_retrieval_evaluation(project_root)
    except FileNotFoundError:
        retrieval = None
    try:
        output_comparison = load_output_evaluation_comparison(project_root)
    except FileNotFoundError:
        output_comparison = None
    content = render_static_demo(bundle, retrieval, output_comparison)
    output = args.output if args.output.is_absolute() else project_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
