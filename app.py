import streamlit as st
import pandas as pd
import random
import os
import time
import json
from io import StringIO, BytesIO
from datetime import datetime

import numpy as np
import boto3
import botocore
from faker import Faker

fake = Faker()

# Feature toggle: set ENABLE_BEDROCK=true in env to enable Bedrock calls
ENABLE_BEDROCK = os.environ.get("ENABLE_BEDROCK", "false").lower() in ("1", "true", "yes")
# Model identifier for Bedrock (override with env var if needed)
BEDROCK_MODEL = os.environ.get("BEDROCK_MODEL", "model-id-placeholder")

# ---- Helpers ----
NUMERIC_TYPES = ["Integer", "Float"]
TEXT_TYPES = ["Name", "Email", "Address", "Text (AI)", "Company"]
DATE_TYPES = ["Date"]
ALL_TYPES = NUMERIC_TYPES + TEXT_TYPES + DATE_TYPES

def generate_column(col_type, n_rows):
    if col_type == "Integer":
        return np.random.randint(0, 1000, size=n_rows).tolist()
    if col_type == "Float":
        return np.round(np.random.uniform(0, 1000, size=n_rows), 2).tolist()
    if col_type == "Name":
        return [fake.name() for _ in range(n_rows)]
    if col_type == "Email":
        return [fake.email() for _ in range(n_rows)]
    if col_type == "Address":
        return [fake.address().replace("\n", ", ") for _ in range(n_rows)]
    if col_type == "Company":
        return [fake.company() for _ in range(n_rows)]
    if col_type == "Date":
        # generate random dates in last 2 years using pandas/numpy
        start = pd.Timestamp.today() - pd.Timedelta(days=365 * 2)
        end = pd.Timestamp.today()
        rand_days = np.random.randint(0, (end - start).days + 1, size=n_rows)
        return (start + pd.to_timedelta(rand_days, unit="D")).date.tolist()
    if col_type == "Text (AI)":
        prompt_template = "Short realistic text example (e.g., product description, review, or support message)."
        # If enabled, try calling Bedrock once for a batch; otherwise fallback to Faker
        if ENABLE_BEDROCK:
            texts = call_bedrock_batch(n_rows, prompt_template)
            if texts is not None and len(texts) == n_rows:
                return texts
            # fallback to faker if bedrock fails
        prompts = [
            "Sample product description",
            "Example support ticket",
            "Short customer review",
            "User feedback text",
        ]
        return [random.choice(prompts) + f" #{i}" for i in range(n_rows)]
    return [None] * n_rows


def call_bedrock_batch(n_rows, prompt_template, timeout=10):
    """Attempt to call Bedrock to generate a JSON array of strings. Returns list or None on failure."""
    try:
        client = boto3.client("bedrock-runtime")
    except Exception:
        try:
            client = boto3.client("bedrock")
        except Exception:
            return None

    system_prompt = (
        f"Generate {n_rows} short texts for this task: {prompt_template}. "
        "Return only a JSON array of strings (no extra commentary)."
    )
    payload = {"input": system_prompt}
    try:
        # Attempt generic invoke; exact API may vary depending on SDK/version.
        resp = client.invoke_model(modelId=BEDROCK_MODEL, contentType="application/json", body=json.dumps(payload))
        body = resp.get("body")
        if hasattr(body, "read"):
            body = body.read().decode("utf-8")
        # Try to extract JSON array
        parsed = json.loads(body)
        if isinstance(parsed, list):
            return parsed[:n_rows]
        # Sometimes model returns a dict with 'output'
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v[:n_rows]
        # Last resort: try to find a JSON array substring
        start = body.find("[")
        end = body.rfind("]")
        if start != -1 and end != -1 and end > start:
            return json.loads(body[start : end + 1])[:n_rows]
    except botocore.exceptions.NoCredentialsError:
        return None
    except Exception:
        return None
    return None

def build_dataset(schema, n_rows):
    data = {}
    for col in schema:
        name = col["name"]
        col_type = col["type"]
        data[name] = generate_column(col_type, n_rows)
    return pd.DataFrame(data)

# ---- Streamlit UI ----
st.set_page_config(page_title="SynGenie - Smart Synthetic Data", layout="wide")

st.title("SynGenie – Smart Synthetic Data Generator")
st.caption("Define your schema, generate synthetic data, preview, visualize, and export.")

st.sidebar.header("Configuration")
n_rows = st.sidebar.number_input("Number of rows", min_value=10, max_value=100000, value=100, step=10)

st.sidebar.markdown("### Schema Columns")
num_cols = st.sidebar.number_input("Number of columns", min_value=1, max_value=20, value=3, step=1)

schema = []
for i in range(int(num_cols)):
    st.sidebar.markdown(f"**Column {i+1}**")
    col_name = st.sidebar.text_input(f"Name for column {i+1}", value=f"col_{i+1}", key=f"name_{i}")
    col_type = st.sidebar.selectbox(
        f"Type for column {i+1}",
        options=ALL_TYPES,
        index=i % len(ALL_TYPES),
        key=f"type_{i}",
    )
    schema.append({"name": col_name, "type": col_type})

st.sidebar.markdown("---")
generate_btn = st.sidebar.button("Generate Data")

# If a dataset is stored in session, show quick controls
if "df" in st.session_state:
    st.sidebar.markdown("### Current Stored Dataset")
    stored_df = st.session_state["df"]
    st.sidebar.write(f"Rows: {stored_df.shape[0]} — Columns: {stored_df.shape[1]}")
    if st.sidebar.button("Clear stored dataset"):
        del st.session_state["df"]
        if "metadata" in st.session_state:
            del st.session_state["metadata"]
        st.experimental_rerun()

if generate_btn:
    with st.spinner("Generating synthetic dataset..."):
        progress = st.progress(0)
        # build_dataset is synchronous; show progress per-column
        data = {}
        for idx, col in enumerate(schema):
            data[col["name"]] = generate_column(col["type"], int(n_rows))
            progress.progress(int((idx + 1) / len(schema) * 100))
        df = pd.DataFrame(data)
        progress.empty()

    # persist dataset and metadata in session state
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "n_rows": int(n_rows),
        "schema": schema,
        "bedrock_enabled": ENABLE_BEDROCK,
        "bedrock_model": BEDROCK_MODEL if ENABLE_BEDROCK else None,
    }
    st.session_state["df"] = df
    st.session_state["metadata"] = metadata

    st.subheader("Data Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # Download as CSV
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Download CSV",
        data=csv_buffer.getvalue(),
        file_name="synthetic_data.csv",
        mime="text/csv",
    )

    # Download as Parquet
    try:
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, index=False)
        st.download_button(
            label="Download Parquet",
            data=parquet_buffer.getvalue(),
            file_name="synthetic_data.parquet",
            mime="application/octet-stream",
        )
    except Exception:
        st.info("Parquet export requires `pyarrow` or `fastparquet`. See README.")

    # Download metadata
    if "metadata" in st.session_state:
        st.download_button(
            label="Download Metadata (JSON)",
            data=json.dumps(st.session_state["metadata"], indent=2),
            file_name="synthetic_data_metadata.json",
            mime="application/json",
        )

    # Simple charts
    st.subheader("Quick Visual Insights")
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

    if numeric_cols:
        chart_col = st.selectbox("Select numeric column to visualize", options=numeric_cols)
        bins = st.slider("Histogram bins", min_value=5, max_value=200, value=20)
        series = df[chart_col].dropna().astype(float)
        if not series.empty:
            counts, edges = np.histogram(series, bins=bins)
            hist_df = pd.DataFrame({"bin_left": edges[:-1], "count": counts})
            hist_df = hist_df.set_index("bin_left")
            st.bar_chart(hist_df["count"])
        else:
            st.info("Selected column has no numeric data to plot.")
    else:
        st.info("No numeric columns available for charting. Add an Integer or Float column to see charts.")
else:
    st.info("Configure your schema in the sidebar and click **Generate Data**.")
