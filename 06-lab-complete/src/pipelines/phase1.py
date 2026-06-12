from datetime import datetime, UTC
import pandas as pd
from core.config import load_settings
from core.utils import now_utc, write_csv, read_json, ensure_parent
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from retrieval.qa import answer_question


def main() -> None:
    """Build baseline pipeline end-to-end."""
    print("--- Phase 1: Baseline RAG Pipeline ---")
    settings = load_settings()
    run_date = now_utc()

    # 1. Load or fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("Fetching fresh records from Crossref API...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading cached raw records from {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)

    print(f"Total raw records loaded: {len(records)}")

    # 2. Clean data
    print("Running cleaning pipeline...")
    df = build_clean_dataframe(records, run_date)
    print(f"Total cleaned records: {len(df)}")

    # 3. Save clean CSV/JSON
    write_csv(df, settings.paths.clean_csv)
    ensure_parent(settings.paths.clean_json)
    df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"Cleaned dataset saved to {settings.paths.clean_csv} and {settings.paths.clean_json}")

    # 4. Build Chroma index
    print("Building local embedding index...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"Embedding index successfully built.")

    # 5. Create or load evaluation set
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("Generating new evaluation test set...")
        test_set = build_test_set(df, settings.paths.eval_testset)
    else:
        print(f"Loading existing test set from {settings.paths.eval_testset}...")
        test_set = read_json(settings.paths.eval_testset)

    print(f"Test set loaded with {len(test_set)} samples.")

    # 6. Evaluate
    print("Evaluating baseline RAG agent...")
    metrics_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print("Baseline evaluation completed.")
    print(f"Summary metrics: {metrics_bundle.summary}")

    # 7. Run quality checks and freshness report
    print("Running data quality checks...")
    quality_report = run_data_quality_checks(df, settings, "baseline_quality")
    
    print("Building freshness report...")
    freshness_report = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 8. Generate phase 1 markdown report
    print("Generating baseline reports...")
    source_summary = {
        "source_api": settings.source_api,
        "query": settings.source_query,
        "max_results": settings.max_results,
        "ingested_count": len(records),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=metrics_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"Baseline markdown report written to {settings.paths.baseline_report}")

    # 9. Demo agent on some sample questions
    print("Running agent demo qa...")
    demo_questions = [
        test_set[0]["question"] if len(test_set) > 0 else "What is Retrieval-Augmented Generation?",
        test_set[1]["question"] if len(test_set) > 1 else "Who wrote about agentic workflows?",
    ]
    demo_results = []
    for q in demo_questions:
        res = answer_question(q, settings, index)
        demo_results.append({
            "question": q,
            "answer": res.answer,
            "retrieved_titles": res.retrieved_titles
        })
    import json
    ensure_parent(settings.paths.demo_answers)
    settings.paths.demo_answers.write_text(json.dumps(demo_results, indent=2), encoding="utf-8")
    print(f"Demo QA answers saved to {settings.paths.demo_answers}")
    print("Phase 1 baseline finished successfully.")

