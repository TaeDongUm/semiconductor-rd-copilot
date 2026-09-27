from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.problem_decomposition import build_problem_decomposition_prompt
from src.ui_data import (
    STATUS_SYMBOLS,
    build_matrix_rows,
    demo_metrics,
    find_default_demo_run,
    flatten_evidence,
    load_demo_bundle,
    load_retrieval_evaluation,
    load_output_evaluation_comparison,
    output_comparison_rows,
    retrieval_comparison_rows,
    retrieval_summary_metrics,
)

PROJECT_ROOT = Path(__file__).resolve().parent


@st.cache_data
def load_verified_demo():
    return load_demo_bundle(find_default_demo_run(PROJECT_ROOT))


@st.cache_data
def load_verified_retrieval_evaluation():
    return load_retrieval_evaluation(PROJECT_ROOT)


def render_header() -> None:
    st.set_page_config(
        page_title="Semiconductor R&D Copilot",
        page_icon="🔬",
        layout="wide",
    )
    st.title("Semiconductor R&D Copilot")
    st.caption(
        "공개 연구 근거를 바탕으로 반도체 기술 조사 과정을 구조화하고, "
        "근거·Trade-off·Unknown을 분리해 다음 검증 항목을 제안하는 PoC"
    )


def render_verified_demo(bundle: dict) -> None:
    case = bundle["case"]
    decision = bundle["decision"]
    metrics = demo_metrics(bundle)

    st.subheader("검증된 HBM Thermal End-to-End 데모")
    e2e = bundle.get("end_to_end_evaluation") or {}
    st.info(
        "이 화면은 browser OpenAlex 검색과 manual ChatGPT Evidence Extraction으로 수행한 최종 End-to-End Run을 표시합니다. "
        "검색·Evidence·Decision·Evaluation 단계의 산출물을 같은 Run에 보존했습니다."
    )
    if e2e:
        st.success(
            f"Overall Gate: {e2e.get('overall_gate', '-')} · "
            f"Retrieval Recall@20: {float(e2e.get('retrieval_recall', 0))*100:.1f}% · "
            f"Output Constraint Recall: {float(e2e.get('output_constraint_recall', 0))*100:.1f}%"
        )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Papers", metrics["papers"])
    c2.metric("Evidence", metrics["accepted_evidence_responses"])
    c3.metric("Validation errors", metrics["validation_errors"])
    c4.metric("Approaches", metrics["approaches"])
    c5.metric("Unknowns", metrics["unknowns"])
    c6.metric("Hypotheses", metrics["hypotheses"])

    st.markdown("### 1. Engineering Problem")
    st.write(case["problem_statement"])
    with st.expander("Engineering Constraints", expanded=True):
        for item in case["constraints"]:
            st.markdown(f"**{item['id']} · {item['name']}**")
            st.caption("검색 용어: " + ", ".join(item.get("search_terms", [])))

    result_tab, retrieval_tab, output_tab, papers_tab, evidence_tab, validation_tab, brief_tab = st.tabs(
        ["Decision Map", "Retrieval Eval", "Output Eval", "Papers", "Evidence", "Validation", "Investigation Brief"]
    )

    with result_tab:
        st.markdown("### 2. Approach × Constraint Matrix")
        st.caption("+ benefit · − downside · ± trade-off · • 관련 근거 · ? 근거 부족")
        st.dataframe(build_matrix_rows(case, decision), use_container_width=True, hide_index=True)

        st.markdown("### 3. Unknowns")
        unknowns = decision.get("unknowns", [])
        if not unknowns:
            st.success("현재 검증 데이터에서 Unknown이 없습니다.")
        else:
            grouped: dict[str, list[dict]] = {}
            for item in unknowns:
                grouped.setdefault(item["approach"], []).append(item)
            for approach, items in grouped.items():
                with st.expander(f"{approach} · {len(items)} unknown(s)"):
                    for item in items:
                        st.markdown(f"- **{item['constraint']}** — {item['reason']}")

        st.markdown("### 4. Candidate Hypotheses & Next Validation")
        hypotheses = decision.get("hypotheses", [])
        if not hypotheses:
            st.warning("현재 생성된 Candidate Hypothesis가 없습니다.")
        for hypothesis in hypotheses:
            with st.container(border=True):
                st.markdown(f"**{hypothesis['hypothesis_id']}**")
                st.write(hypothesis["text"])
                st.caption("Basis evidence: " + ", ".join(hypothesis.get("basis_evidence_ids", [])))
                st.markdown("**Next validation**")
                st.write(hypothesis["validation"])

        conflicts = decision.get("conflicts", [])
        st.markdown("### 5. Conflicting Evidence")
        if conflicts:
            st.json(conflicts, expanded=False)
        else:
            st.success("현재 검증된 Evidence에서는 직접적인 positive-vs-negative conflict가 감지되지 않았습니다.")

    with retrieval_tab:
        st.markdown("### Retrieval Evaluation · V1 → V2")
        try:
            retrieval = load_verified_retrieval_evaluation()
            summary = retrieval_summary_metrics(retrieval)
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("OpenAlex Source Coverage", summary["source_coverage"])
            r2.metric("Multi-query Recall@20", summary["multi_v2"], summary["multi_delta"])
            r3.metric("V1 Multi-query Recall@20", summary["multi_v1"])
            r4.metric("V2 Multi-query Recall@50", summary["best_at_50"])
            st.dataframe(retrieval_comparison_rows(retrieval), use_container_width=True, hide_index=True)
            st.caption(
                "동일한 Golden Corpus v1(7편)을 고정하고 Query/Ranking 전략만 변경했습니다. "
                "7/7 논문이 OpenAlex에 색인되어 있어 V1 실패를 source coverage가 아닌 retrieval/ranking 문제로 분리할 수 있었습니다."
            )
            st.info(
                "이 HBM Thermal 소규모 Benchmark에서는 Multi-query + RRF가 가장 안정적이었습니다. "
                "Semantic 단독 검색은 Recall@20 14.3%로 개선되지 않았으며, 결과를 다른 도메인으로 일반화하지 않습니다."
            )
        except FileNotFoundError as exc:
            st.warning(f"Retrieval 평가 결과를 찾지 못했습니다: {exc}")


    with output_tab:
        st.markdown("### AI Output Evaluation")
        output_eval = bundle.get("output_evaluation")
        e2e = bundle.get("end_to_end_evaluation")
        if output_eval:
            o1, o2, o3, o4 = st.columns(4)
            o1.metric("Citation validity", f"{float(output_eval.get('citation_validity', 0))*100:.1f}%")
            o2.metric("Constraint precision", f"{float(output_eval.get('constraint_precision', 0))*100:.1f}%")
            o3.metric("Constraint recall", f"{float(output_eval.get('constraint_recall', 0))*100:.1f}%")
            o4.metric("Constraint F1", f"{float(output_eval.get('constraint_f1', 0))*100:.1f}%")
            try:
                comparison = load_output_evaluation_comparison(PROJECT_ROOT)
                st.markdown("#### V1 → V2")
                st.dataframe(output_comparison_rows(comparison), use_container_width=True, hide_index=True)
                st.caption(
                    f"Missed mapping {comparison.get('missed_constraint_mappings', {}).get('v1', '-')} → "
                    f"{comparison.get('missed_constraint_mappings', {}).get('v2', '-')} · "
                    f"Quality Gate {comparison.get('quality_gate', {}).get('v1', '-')} → "
                    f"{comparison.get('quality_gate', {}).get('v2', '-')}"
                )
            except FileNotFoundError:
                pass
            st.write({
                "unsupported_constraint_mappings": output_eval.get("unsupported_constraint_mappings", 0),
                "missed_constraint_mappings": output_eval.get("missed_constraint_mappings", 0),
                "hypothesis_traceability": f"{float(output_eval.get('hypothesis_traceability', 0))*100:.1f}%",
                "quality_gate": output_eval.get("deterministic_gate", "-"),
            })
            st.caption(
                "Deterministic evaluator는 citation / constraint / numeric / hypothesis traceability를 검증합니다. "
                "자유서술 전체의 의미적 정확성을 완전히 증명하는 평가는 아닙니다."
            )
        else:
            st.warning("Output evaluation artifact가 없습니다.")

        if e2e:
            st.markdown("### End-to-End Gate")
            st.json(e2e, expanded=False)

    with papers_tab:
        st.markdown("### 근거 논문")
        for index, paper in enumerate(bundle["papers"], start=1):
            with st.expander(f"R{index:02d} · {paper['title']}", expanded=index == 1):
                st.write(paper.get("abstract", ""))
                st.markdown(f"**DOI:** `{paper.get('doi', '-')}`")
                st.markdown(f"**Year:** {paper.get('publication_year', '-')}")
                st.markdown(f"**Source:** {paper.get('source_name', '-')}")
                st.markdown("**Matched queries:** " + ", ".join(paper.get("matched_queries", [])))
                if paper.get("oa_url"):
                    st.link_button("Source", paper["oa_url"])

    with evidence_tab:
        st.markdown("### 검증된 Evidence")
        rows = flatten_evidence(bundle["evidence"])
        for row in rows:
            title = f"{row['evidence_id']} · {row['approach']} · {row['polarity']}"
            with st.expander(title):
                st.write(row["claim"])
                st.caption(
                    f"Paper {row['paper_id']} · Constraints: {', '.join(row['constraint_ids'])} · Kind: {row['kind']}"
                )
                metrics_list = row.get("metrics") or []
                if metrics_list:
                    st.markdown("**Reported metrics**")
                    for metric in metrics_list:
                        comparison = f" ({metric.get('comparison')})" if metric.get("comparison") else ""
                        st.markdown(f"- {metric.get('name')}: **{metric.get('value')}**{comparison}")
                if row.get("notes"):
                    st.caption(row["notes"])

    with validation_tab:
        validation = bundle["validation"]
        provenance = bundle["provenance"]
        left, right = st.columns(2)
        with left:
            st.markdown("### Evidence Validation")
            st.json(validation, expanded=True)
        with right:
            st.markdown("### Retrieval Provenance")
            st.json(provenance, expanded=True)
        st.info(
            "이 Run의 downstream Evidence/Decision 단계는 검증된 실제 논문을 동일 스키마로 주입해 확인했습니다. "
            "OpenAlex retrieval 품질은 별도의 Retrieval Eval 탭에서 Golden Corpus 기반 V1/V2 Benchmark로 검증합니다."
        )

    with brief_tab:
        st.markdown(bundle["brief"])
        st.download_button(
            "Investigation Brief 다운로드",
            data=bundle["brief"],
            file_name="hbm_thermal_investigation_brief.md",
            mime="text/markdown",
        )


def render_new_problem_mode() -> None:
    st.subheader("새 공학 문제 준비")
    st.warning(
        "현재 이 화면에서는 새 문제를 자동으로 분석한 척하지 않습니다. "
        "문제 입력 후 ChatGPT에 전달할 Problem Decomposition Prompt만 생성합니다."
    )
    problem = st.text_area(
        "반도체 공학 문제",
        height=180,
        placeholder=(
            "예: HBM 적층 수가 증가하면서 내부 열 축적과 thermal resistance가 커진다. "
            "reliability와 manufacturability까지 고려해 조사하고 싶다."
        ),
    )
    if problem.strip():
        prompt = build_problem_decomposition_prompt(problem)
        st.markdown("### ChatGPT에 전달할 Prompt")
        st.code(prompt, language="text")
        st.download_button(
            "Prompt 다운로드",
            data=prompt,
            file_name="problem_decomposition_prompt.md",
            mime="text/markdown",
        )
        st.caption(
            "ChatGPT가 반환한 JSON은 기존 CLI workflow에서 검증한 뒤 Multi-query/OpenAlex 검색 단계로 연결합니다."
        )


def main() -> None:
    render_header()
    mode = st.sidebar.radio("Mode", ["검증된 HBM 데모", "새 공학 문제 준비"])
    st.sidebar.markdown("---")
    st.sidebar.caption("MVP · Evidence-constrained investigation")

    if mode == "검증된 HBM 데모":
        try:
            render_verified_demo(load_verified_demo())
        except Exception as exc:  # UI boundary: show a user-readable error
            st.error(f"데모 데이터를 불러오지 못했습니다: {exc}")
    else:
        render_new_problem_mode()


if __name__ == "__main__":
    main()
