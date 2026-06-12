from datetime import datetime
import pandas as pd
from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, ensure_parent
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report


def main() -> None:
    """Run corruption -> evaluate -> repair -> compare flow."""
    print("--- Phase 2: Corruption and Repair Pipeline ---")
    settings = load_settings()
    run_date = now_utc()

    # 1. Load baseline metrics and clean dataset
    print(f"Loading baseline metrics from {settings.paths.baseline_metrics}...")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    
    print(f"Loading clean dataset from {settings.paths.clean_json}...")
    df_clean = pd.read_json(settings.paths.clean_json)

    # 2. Create corrupted dataframe
    print("Simulating data corruption...")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)

    # 3. Save corrupted artifacts
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    ensure_parent(settings.paths.corrupted_clean_json)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"Corrupted dataset saved.")

    # 4. Rebuild index and evaluate on corrupted data
    print("Rebuilding embedding index for corrupted dataset...")
    corrupted_index = LocalEmbeddingIndex.build(df_corrupted, settings, settings.paths.corrupted_embeddings_json)
    
    print("Evaluating corrupted RAG agent...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"Corrupted metrics: {corrupted_bundle.summary}")

    # 5. Run quality checks / freshness on corrupted data
    print("Running quality checks on corrupted dataset...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json")

    # 6. Repair data by loading raw snapshot and running clean pipeline again
    print("Repairing data: re-loading raw records and cleaning...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, run_date)

    # Save repaired artifacts
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    ensure_parent(settings.paths.repaired_clean_json)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"Repaired dataset saved.")

    # 7. Rebuild repaired index and evaluate
    print("Rebuilding embedding index for repaired dataset...")
    repaired_index = LocalEmbeddingIndex.build(df_repaired, settings, settings.paths.repaired_embeddings_json)
    
    print("Evaluating repaired RAG agent...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"Repaired metrics: {repaired_bundle.summary}")

    # Run quality checks / freshness on repaired data
    print("Running quality checks on repaired dataset...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness.json")

    # 8. Generate comparison report
    print("Generating comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Comparison report written to {settings.paths.comparison_report}")
    print("Phase 2 corruption and repair pipeline finished successfully.")

