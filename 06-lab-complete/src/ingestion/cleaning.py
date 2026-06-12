import re
import pandas as pd
from datetime import datetime
from ingestion.crossref import PaperRecord
from core.utils import normalize_whitespace, compact_join


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records to dataframe ready for embedding."""
    if not records:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories",
            "primary_category", "published", "updated", "abs_url",
            "pdf_url", "comment", "authors_joined", "categories_joined",
            "summary_chars", "text_for_embedding", "age_days"
        ])

    data = []
    for r in records:
        # String normalization
        title = normalize_whitespace(r.title or "")
        summary = normalize_whitespace(r.summary or "")
        
        # Clean authors and categories lists
        clean_authors = [normalize_whitespace(a) for a in r.authors if a]
        clean_categories = [normalize_whitespace(c) for c in r.categories if c]
        
        primary_category = normalize_whitespace(r.primary_category or "General")

        data.append({
            "paper_id": r.paper_id.strip() if r.paper_id else "",
            "title": title,
            "summary": summary,
            "authors": clean_authors,
            "categories": clean_categories,
            "primary_category": primary_category,
            "published": r.published.strip() if r.published else "2026-01-01",
            "updated": r.updated.strip() if r.updated else "2026-01-01",
            "abs_url": r.abs_url.strip() if r.abs_url else "",
            "pdf_url": r.pdf_url.strip() if r.pdf_url else "",
            "comment": normalize_whitespace(r.comment or ""),
        })

    df = pd.DataFrame(data)

    # Filter bad rows (missing paper_id, title, or summary)
    df = df[df["paper_id"].astype(bool) & df["title"].astype(bool) & df["summary"].astype(bool)]

    if df.empty:
        return pd.DataFrame(columns=[
            "paper_id", "title", "summary", "authors", "categories",
            "primary_category", "published", "updated", "abs_url",
            "pdf_url", "comment", "authors_joined", "categories_joined",
            "summary_chars", "text_for_embedding", "age_days"
        ])

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Generate helper columns
    df["authors_joined"] = df["authors"].apply(lambda x: compact_join(x, sep=", "))
    df["categories_joined"] = df["categories"].apply(lambda x: compact_join(x, sep=", "))
    df["summary_chars"] = df["summary"].apply(len)
    df["text_for_embedding"] = df.apply(
        lambda row: f"Title: {row['title']}\nAbstract: {row['summary']}", axis=1
    )

    # Parse published date and calculate age_days
    # Convert run_date to date object
    run_date_only = run_date.date()
    
    def calculate_age(pub_str):
        try:
            pub_date = pd.to_datetime(pub_str).date()
            return (run_date_only - pub_date).days
        except Exception:
            return 365  # fallback if parsing fails

    df["age_days"] = df["published"].apply(calculate_age)

    # Sort descending by published date
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)

    return df

