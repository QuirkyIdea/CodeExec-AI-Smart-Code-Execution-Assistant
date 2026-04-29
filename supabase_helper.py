"""
Supabase Helper — Dataset storage and retrieval via Supabase REST API.

All uploaded datasets are stored in a single `uploaded_datasets` table
with columns: id (bigint PK), dataset_name (text), row_data (jsonb),
created_at (timestamptz).
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
TABLE = "uploaded_datasets"

def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

def _rest_url(table: str = TABLE):
    return f"{SUPABASE_URL}/rest/v1/{table}"


def upload_dataset(dataset_name: str, df) -> dict:
    """Upload a pandas DataFrame to Supabase as JSONB rows."""
    rows = df.to_dict(orient="records")
    # Insert in batches of 500
    batch_size = 500
    total_inserted = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        payload = [{"dataset_name": dataset_name, "row_data": row} for row in batch]
        resp = requests.post(_rest_url(), headers=_headers(), json=payload)
        if resp.status_code not in (200, 201):
            return {"status": "error", "error": f"Insert failed (HTTP {resp.status_code}): {resp.text}"}
        total_inserted += len(batch)
    return {"status": "success", "rows_inserted": total_inserted, "dataset_name": dataset_name}


def list_datasets() -> list:
    """List unique dataset names and their row counts."""
    # Use PostgREST to get distinct dataset names
    url = f"{_rest_url()}?select=dataset_name"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return []
    data = resp.json()
    # Count rows per dataset
    name_counts = {}
    for row in data:
        name = row.get("dataset_name", "")
        name_counts[name] = name_counts.get(name, 0) + 1
    return [{"name": name, "size": count, "modified": 0} for name, count in name_counts.items()]


def delete_dataset(dataset_name: str) -> dict:
    """Delete all rows for a given dataset name."""
    url = f"{_rest_url()}?dataset_name=eq.{dataset_name}"
    resp = requests.delete(url, headers=_headers())
    if resp.status_code in (200, 204):
        return {"status": "success"}
    return {"status": "error", "error": f"Delete failed (HTTP {resp.status_code}): {resp.text}"}


def get_dataset_preview(dataset_name: str, limit: int = 5) -> dict:
    """Fetch a few rows from a dataset for LLM context."""
    import pandas as pd
    url = f"{_rest_url()}?dataset_name=eq.{dataset_name}&select=row_data&limit={limit}"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200 or not resp.json():
        return {"found": False}
    rows = [r["row_data"] for r in resp.json()]
    df = pd.DataFrame(rows)
    return {
        "found": True,
        "columns": list(df.columns),
        "dtypes": df.dtypes.to_string(),
        "shape": df.shape,
        "preview": df.to_string(),
    }


def load_table(table_name: str, limit: int = 10000):
    """Load a dataset from Supabase as a pandas DataFrame.
    Checks uploaded_datasets first, then falls back to a direct table.
    """
    import pandas as pd

    # Try uploaded_datasets first
    url = f"{_rest_url()}?dataset_name=eq.{table_name}&select=row_data&limit={limit}"
    headers = _headers()
    headers["Prefer"] = "return=representation"
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200 and resp.json():
        rows = [r["row_data"] for r in resp.json()]
        return pd.DataFrame(rows)

    # Fallback: try querying a direct table
    url2 = f"{SUPABASE_URL}/rest/v1/{table_name}?select=*&limit={limit}"
    resp2 = requests.get(url2, headers=headers)
    if resp2.status_code == 200 and resp2.json():
        return pd.DataFrame(resp2.json())

    raise ValueError(f"No data found for '{table_name}' in Supabase.")
