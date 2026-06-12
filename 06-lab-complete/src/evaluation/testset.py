import pandas as pd
from typing import Any
from core.utils import write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create evaluation test set from cleaned dataframe."""
    if df.empty:
        raise ValueError("Cleaned DataFrame is empty. Cannot generate test set.")

    # Select representative papers (e.g., up to 6 papers)
    sample_size = min(len(df), 6)
    representative_papers = df.head(sample_size).to_dict(orient="records")

    test_set: list[dict[str, Any]] = []
    question_counter = 0

    for paper in representative_papers:
        title = paper["title"]
        paper_id = paper["paper_id"]

        # 1. Summary question
        question_counter += 1
        test_set.append({
            "id": f"q_{question_counter:03d}",
            "question_type": "summary",
            "question": f"What is the summary of the paper titled '{title}'?",
            "ground_truth": paper["summary"],
            "ground_truth_doc_ids": [paper_id]
        })

        # 2. Authors question
        question_counter += 1
        test_set.append({
            "id": f"q_{question_counter:03d}",
            "question_type": "authors",
            "question": f"Who authored the paper '{title}'?",
            "ground_truth": paper["authors_joined"],
            "ground_truth_doc_ids": [paper_id]
        })

        # 3. Date question
        question_counter += 1
        test_set.append({
            "id": f"q_{question_counter:03d}",
            "question_type": "date",
            "question": f"When was the paper '{title}' published?",
            "ground_truth": paper["published"],
            "ground_truth_doc_ids": [paper_id]
        })

        # 4. Categories question
        question_counter += 1
        test_set.append({
            "id": f"q_{question_counter:03d}",
            "question_type": "categories",
            "question": f"What categories are associated with the paper '{title}'?",
            "ground_truth": paper["categories_joined"],
            "ground_truth_doc_ids": [paper_id]
        })

    # Write as JSON to output_path
    write_json(output_path, test_set)

    return test_set

