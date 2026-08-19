"""
Retrieval eval harness: recall@5 before (vector-only) vs after (hybrid BM25 +
RRF, and hybrid + cross-encoder rerank) against a hand-authored ~20 question
Q&A fixture over the bundled Led Zeppelin sample document.

Usage:
    python -m eval.run_eval
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from tabulate import tabulate

from app.services.qa import QAService
from app.services.retrieval import retrieve
from eval.lib import get_or_create_eval_doc, hit_at_k, load_qa_pairs

logging.basicConfig(level=logging.WARNING)

RESULTS_DIR = Path(__file__).parent / "results"
MODES = ["vector", "hybrid", "hybrid_rerank"]
MODE_LABELS = {
    "vector": "vector (before)",
    "hybrid": "hybrid (BM25+RRF)",
    "hybrid_rerank": "hybrid+rerank (after)",
}
FINAL_K = 5


async def run() -> dict:
    doc_id = await get_or_create_eval_doc()
    qa_pairs = load_qa_pairs()

    per_question_rows = []
    hits = {mode: 0 for mode in MODES}

    for qa in qa_pairs:
        question = qa["question"]
        relevant = qa["relevant_chunk_indices"]

        # expand_query() is called once per question and reused across every
        # mode, isolating the retrieval-stage comparison from paraphrase
        # variance and keeping LLM calls to len(qa_pairs), not len(qa_pairs)*len(MODES).
        queries = await QAService.expand_query(question)

        row = {"id": qa["id"], "question": question, "relevant_chunk_indices": relevant}
        for mode in MODES:
            retrieved = await retrieve(queries, doc_id, mode=mode, final_k=FINAL_K)
            hit = hit_at_k(retrieved, relevant)
            hits[mode] += int(hit)
            row[mode] = {
                "hit": hit,
                "retrieved_indices": [c.index for c in retrieved],
            }
        per_question_rows.append(row)

    n = len(qa_pairs)
    recall_at_5 = {mode: hits[mode] / n for mode in MODES}

    return {
        "doc_id": doc_id,
        "n_questions": n,
        "final_k": FINAL_K,
        "recall_at_5": recall_at_5,
        "per_question": per_question_rows,
    }


def render_console_table(results: dict) -> str:
    summary_rows = [
        [MODE_LABELS[mode], f"{results['recall_at_5'][mode]:.2%}"] for mode in MODES
    ]
    return tabulate(summary_rows, headers=["Mode", f"recall@{results['final_k']}"], tablefmt="github")


def render_markdown_report(results: dict) -> str:
    lines = [
        "# Retrieval Eval Report",
        "",
        f"Document: Led Zeppelin sample PDF (`{results['doc_id']}`) — "
        f"{results['n_questions']} hand-authored questions, recall@{results['final_k']}.",
        "",
        "## Summary",
        "",
        "| Mode | recall@5 |",
        "|---|---|",
    ]
    for mode in MODES:
        lines.append(f"| {MODE_LABELS[mode]} | {results['recall_at_5'][mode]:.2%} |")

    lines += ["", "## Per-question detail", "", "| id | question | " + " | ".join(MODE_LABELS[m] for m in MODES) + " |",
              "|---|---|" + "---|" * len(MODES)]
    for row in results["per_question"]:
        cells = " | ".join("✅" if row[m]["hit"] else "❌" for m in MODES)
        lines.append(f"| {row['id']} | {row['question']} | {cells} |")

    return "\n".join(lines) + "\n"


async def main() -> None:
    start = time.perf_counter()
    results = await run()
    elapsed = time.perf_counter() - start

    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "report.json").write_text(json.dumps(results, indent=2))
    (RESULTS_DIR / "report.md").write_text(render_markdown_report(results))

    print(render_console_table(results))
    print(f"\n({elapsed:.1f}s) Full report written to eval/results/report.md and report.json")


if __name__ == "__main__":
    asyncio.run(main())
