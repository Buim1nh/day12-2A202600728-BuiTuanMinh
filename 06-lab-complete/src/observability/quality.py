import pandas as pd
from typing import Any
from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Create data quality checks."""
    total_rows = len(df)
    
    # Check row count
    row_count_check = total_rows > 0

    # Check paper_id unique and not null
    null_paper_ids = int(df["paper_id"].isna().sum()) if total_rows > 0 else 0
    empty_paper_ids = int((df["paper_id"] == "").sum()) if total_rows > 0 else 0
    paper_id_not_null_check = (null_paper_ids == 0) and (empty_paper_ids == 0)
    
    unique_paper_ids = df["paper_id"].nunique() if total_rows > 0 else 0
    paper_id_unique_check = (unique_paper_ids == total_rows) if total_rows > 0 else True

    # Check title not null
    null_titles = int(df["title"].isna().sum()) if total_rows > 0 else 0
    empty_titles = int((df["title"] == "").sum()) if total_rows > 0 else 0
    title_not_null_check = (null_titles == 0) and (empty_titles == 0)

    # Check length of summary (should be at least 50 chars)
    short_summaries = int((df["summary_chars"] < 50).sum()) if "summary_chars" in df.columns and total_rows > 0 else 0
    summary_length_check = (short_summaries == 0) if total_rows > 0 else True

    # Check freshness threshold
    stale_count = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns and total_rows > 0 else 0
    freshness_check = (stale_count == 0) if total_rows > 0 else True

    success = (
        row_count_check
        and paper_id_not_null_check
        and paper_id_unique_check
        and title_not_null_check
        and summary_length_check
        and freshness_check
    )

    report = {
        "report_name": report_name,
        "success": success,
        "metrics": {
            "total_rows": total_rows,
            "null_paper_ids": null_paper_ids,
            "empty_paper_ids": empty_paper_ids,
            "unique_paper_ids": unique_paper_ids,
            "null_titles": null_titles,
            "empty_titles": empty_titles,
            "short_summaries": short_summaries,
            "stale_count": stale_count,
        },
        "checks": {
            "row_count_check": bool(row_count_check),
            "paper_id_not_null_check": bool(paper_id_not_null_check),
            "paper_id_unique_check": bool(paper_id_unique_check),
            "title_not_null_check": bool(title_not_null_check),
            "summary_length_check": bool(summary_length_check),
            "freshness_check": bool(freshness_check),
        }
    }

    # Write report
    report_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(report_path, report)

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tally freshness report."""
    total_rows = len(df)
    
    if total_rows == 0:
        report = {
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "total_rows": 0,
            "is_fresh": True,
        }
        write_json(report_path, report)
        return report

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
    is_fresh = stale_rows == 0

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": bool(is_fresh),
    }

    write_json(report_path, report)
    return report

