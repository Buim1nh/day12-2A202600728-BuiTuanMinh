import pandas as pd
from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate various types of data corruption on clean dataframe."""
    if len(df) < 12:
        raise ValueError(f"DataFrame must have at least 12 rows to apply corruption, got {len(df)}")

    cdf = df.copy()
    log = {
        "original_row_count": len(df),
        "corruptions": []
    }

    # 1. Drop 5 latest records (first 5 rows as df is sorted by published descending)
    dropped_papers = cdf.iloc[:5]["paper_id"].tolist()
    cdf = cdf.iloc[5:].reset_index(drop=True)
    log["corruptions"].append({
        "type": "drop_latest_records",
        "count": 5,
        "dropped_paper_ids": dropped_papers
    })

    # 2. Blank summary on 2 rows (index 0, 1)
    blanked_papers = cdf.iloc[0:2]["paper_id"].tolist()
    cdf.loc[0:1, "summary"] = ""
    cdf.loc[0:1, "summary_chars"] = 0
    log["corruptions"].append({
        "type": "blank_summary",
        "paper_ids": blanked_papers
    })

    # 3. Inject noise into summary on 2 rows (index 2, 3)
    noised_papers = cdf.iloc[2:4]["paper_id"].tolist()
    noise_str = " [NOISE_CORRUPTION_INJECTED_X_Y_Z]"
    cdf.loc[2:3, "summary"] = cdf.loc[2:3, "summary"] + noise_str
    cdf.loc[2:3, "summary_chars"] = cdf.loc[2:3, "summary"].apply(len)
    log["corruptions"].append({
        "type": "inject_noise",
        "paper_ids": noised_papers
    })

    # 4. Truncate title on 2 rows (index 4, 5)
    truncated_papers = cdf.iloc[4:6]["paper_id"].tolist()
    cdf.loc[4:5, "title"] = cdf.loc[4:5, "title"].apply(lambda t: t[:10])
    log["corruptions"].append({
        "type": "truncate_title",
        "paper_ids": truncated_papers
    })

    # 5. Make published date stale on 2 rows (index 6, 7)
    stale_papers = cdf.iloc[6:8]["paper_id"].tolist()
    cdf.loc[6:7, "published"] = "1990-01-01"
    cdf.loc[6:7, "age_days"] = cdf.loc[6:7, "age_days"] + 13000  # make age_days extremely large
    log["corruptions"].append({
        "type": "stale_published_date",
        "paper_ids": stale_papers
    })

    # 6. Add duplicate rows of 2 papers (index 8, 9)
    duplicated_papers = cdf.iloc[8:10]["paper_id"].tolist()
    dup_rows = cdf.iloc[8:10].copy()
    cdf = pd.concat([cdf, dup_rows], ignore_index=True)
    log["corruptions"].append({
        "type": "duplicate_rows",
        "paper_ids": duplicated_papers
    })

    # 7. Rebuild text_for_embedding
    cdf["text_for_embedding"] = cdf.apply(
        lambda row: f"Title: {row['title']}\nAbstract: {row['summary']}", axis=1
    )

    log["final_row_count"] = len(cdf)

    # 8. Write corruption log to output_log_path
    write_json(output_log_path, log)

    return cdf

