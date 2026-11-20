"""Orchestrator for the job-hunt pipeline on Microsoft Agent Framework.

The counterpart of CLAUDE.md from the Claude Code version: reads the CV, runs the
finder → matcher → writer chain, and saves the report. File writing happens only
here (the agents are read-only), so it is the orchestrator that writes the final
markdown to disk.

Run with:  cd src && python main.py

Note: for now this is plain sequential orchestration. Later it can be replaced
with a MAF Workflow (a graph with checkpointing and human-in-the-loop).
"""
from __future__ import annotations

import asyncio
from datetime import date

from agents import build_finder, build_matcher, build_writer
from config import REPORTS_DIR, read_cv


async def run_pipeline() -> str:
    cv = read_cv()

    # 1. Collect jobs --------------------------------------------------------
    finder = build_finder()
    finder_task = (
        "Collect suitable open job postings for this candidate. Use the "
        "available source tools and, if needed, web search. Return a compact "
        "list of jobs (source, title, company, location, url, description) — "
        "with no fit evaluation.\n\n"
        f"=== Candidate CV ===\n{cv}"
    )
    raw_jobs = (await finder.run(finder_task)).text
    print("[finder] collection complete")

    # 2. Evaluate fit -------------------------------------------------------
    matcher = build_matcher()
    matcher_task = (
        "Evaluate each job against the CV. Assign a MATCH / WEAK / NO_MATCH "
        "verdict and a brief justification. Sort MATCH to the top.\n\n"
        f"=== CV ===\n{cv}\n\n=== Jobs ===\n{raw_jobs}"
    )
    evaluated = (await matcher.run(matcher_task)).text
    print("[matcher] evaluation complete")

    # 3. Format the report --------------------------------------------------
    writer = build_writer()
    writer_task = (
        "Assemble a tidy markdown report on the evaluated jobs: a summary, a "
        "MATCH table, a WEAK table, and a short NO_MATCH list.\n\n"
        f"=== Evaluated jobs ===\n{evaluated}"
    )
    report_md = (await writer.run(writer_task)).text
    print("[writer] report formatted")

    # 4. Save — only the orchestrator writes files --------------------------
    REPORTS_DIR.mkdir(exist_ok=True)
    out_path = REPORTS_DIR / f"jobs-{date.today().isoformat()}.md"
    out_path.write_text(report_md, encoding="utf-8")
    print(f"[orchestrator] report saved: {out_path}")
    return str(out_path)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
