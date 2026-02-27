# SynGenie — Smart Synthetic Data Generator

A **Streamlit-based web application** that generates realistic synthetic datasets on-demand using user-defined schemas. Leverages generative AI (AWS Bedrock with Claude/Titan models) to produce AI-powered realistic text fields, with intelligent fallback to Faker for robustness.

Built during the **AWS GenAI Hackathon (July–August 2025)** to accelerate data pipeline development, testing, and prototyping without exposing real customer data.

---

## Features

### Core Capabilities

- **Dynamic Schema Definition**: Interactively define columns with multiple data types in the Streamlit sidebar
- **Rich Data Types**: 
  - **Numeric**: Integer, Float (random ranges)
  - **Text**: Name, Email, Address, Company (Faker-backed)
  - **AI-Powered**: Text (AI) — LLM-generated realistic descriptions using AWS Bedrock
  - **Temporal**: Date (random dates in 2-year window)
- **Scalable Generation**: Generate 10 to 100,000+ rows with vectorized NumPy operations
- **Multi-Format Export**:
  - CSV (standard Comma-Separated Values)
  - Parquet (columnar, compressed, with schema preservation)
  - JSON metadata (generation timestamp, schema, model info)
- **Interactive Visualization**: Histogram-based charts with customizable bins for numeric columns
- **Session Persistence**: Keep generated datasets in memory across sidebar schema changes (via `st.session_state`)
- **Progress Indication**: Live progress bar during generation (per column)

### AI Integration (AWS Bedrock)

- **Generative AI Support**: Integrates with Amazon Bedrock to invoke Claude or Titan models
- **Fallback Strategy**: If Bedrock is unavailable or disabled, seamlessly falls back to Faker-generated synthetic text
- **Batch Efficiency**: Generates entire column via single model prompt (JSON array output)
- **Error Handling**: Graceful handling of auth errors, timeouts, and malformed responses
- **Environment-Based Control**: Toggle AI via `ENABLE_BEDROCK` env var; no code changes needed

### Security & Best Practices

- **No Hardcoded Credentials**: Uses AWS SDK credential chain (env vars, profiles, IAM roles)
- **Least Privilege**: Bedrock calls designed to work with minimal IAM permissions
- **Optional by Default**: AI features disabled unless explicitly enabled
- **Configurable Model**: Override Bedrock model ID via `BEDROCK_MODEL` environment variable

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend / UI** | Streamlit (Python web framework) |
| **Data Processing** | Pandas (DataFrames), NumPy (vectorized arrays) |
| **Synthetic Generation** | Faker (realistic name/email/address), NumPy (numeric) |
| **Generative AI** | AWS Bedrock (Claude/Titan via Boto3) |
| **Cloud SDK** | Boto3, Botocore (AWS SDK for Python) |
| **Data Export** | PyArrow (Parquet), CSV (built-in) |
| **Python Version** | 3.8+ |

---

## Quick Start

### 1. Environment Setup

```bash
# Create a virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Or on macOS/Linux
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Configure AWS & Bedrock

```powershell
# Windows PowerShell
setx ENABLE_BEDROCK true
setx BEDROCK_MODEL "anthropic.claude-3-sonnet-20240229-v1:0"

# Or set AWS_PROFILE for IAM role selection
setx AWS_PROFILE "your-profile-name"
```

For macOS/Linux:
```bash
export ENABLE_BEDROCK=true
export BEDROCK_MODEL="anthropic.claude-3-sonnet-20240229-v1:0"
export AWS_PROFILE="profile-name"
```

### 4. Run the App

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501` in your default browser.

---

## Usage Guide

### Defining a Schema

1. **Sidebar → Configuration**:
   - Set **Number of rows** (10–100,000)
   - Set **Number of columns** (1–20)

2. **For each column**:
   - Enter a **Name** (e.g., "customer_id", "feedback_text")
   - Select a **Type** from the dropdown

3. Click **Generate Data**

### Supported Column Types

| Type | Example Output | Source |
|------|---|---|
| Integer | 543, 892, 12 | NumPy random |
| Float | 123.45, 67.89 | NumPy random |
| Name | "John Smith", "Maria Garcia" | Faker |
| Email | "john.smith@example.com" | Faker |
| Address | "123 Main St, Springfield, IL 62701" | Faker |
| Company | "Acme Corp", "TechStart Inc" | Faker |
| Date | 2024-05-15, 2023-11-02 | Random 2-year window |
| Text (AI) | "High-quality product with great durability..." | AWS Bedrock (or Faker fallback) |

### Visualization & Export

**After generation:**

1. **Data Preview**: Browse the first 50 rows
2. **Charts**: Select a numeric column → adjust histogram bins → view distribution
3. **Downloads**:
   - **CSV**: Standard tabular format
   - **Parquet**: Compressed, schema-preserving columnar format
   - **Metadata (JSON)**: Generation timestamp, schema definition, model info

4. **Session Control**: Use "Clear stored dataset" button to reset and rebuild schema

---

## AWS Bedrock Integration

### How It Works

When `Text (AI)` column is selected and **ENABLE_BEDROCK=true**:

1. **Boto3 Client Creation**: Initializes a Bedrock client via AWS credential chain
2. **Prompt Construction**: Builds a system prompt asking the model to generate N realistic texts as a JSON array
3. **API Call**: Invokes the specified Bedrock model with JSON payload
4. **Response Parsing**: Extracts JSON array from response, validates, and returns texts
5. **Fallback**: If call fails (auth error, timeout, malformed response), silently returns Faker-generated text

### Example Bedrock API Request

```json
{
  "input": "Generate 100 short texts for this task: Short realistic text example (e.g., product description, review, or support message). Return only a JSON array of strings (no extra commentary)."
}
```

### Supported Models

- **Claude 3 Sonnet**: `anthropic.claude-3-sonnet-20240229-v1:0`
- **Claude 3 Haiku**: `anthropic.claude-3-haiku-20240307-v1:0`
- **Titan Text**: `amazon.titan-text-express-v1:0`

(Check [AWS Bedrock Model Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html) for current model IDs.)

### IAM Policy Requirements

For minimal Bedrock integration, attach this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:us-east-1:*:foundation-model/*"
    }
  ]
}
```

---

## Architecture & Design Decisions

### Column Generation Strategy

- **Numeric (Integer/Float)**: NumPy vectorized operations for O(1) performance
- **Faker Types**: Looped Faker calls (unavoidable loop overhead)
- **AI Text**: Single Bedrock API call requesting JSON array (avoids N API calls)
- **Date**: Pandas timestamp arithmetic for fast date range generation

### Session State Persistence

- Generated DataFrames stored in `st.session_state["df"]`
- Metadata (timestamp, schema, model) stored in `st.session_state["metadata"]`
- Survives sidebar changes without regenerating
- Clear via button action

### Error Handling

- **Bedrock**: Catches `NoCredentialsError`, timeouts, JSON parse errors → silent fallback to Faker
- **Parquet Export**: Gracefully degrades if PyArrow not installed
- **User Input**: Validates row count, column count ranges

---

## Examples

### Example 1: Customer Feedback Dataset

**Schema:**
- `customer_id` (Integer)
- `email` (Email)
- `feedback_text` (Text (AI))
- `rating` (Integer)

**Generate:** 500 rows → Download CSV → Use in ML pipeline, A/B testing, or dashboards

### Example 2: Product Catalog

**Schema:**
- `product_name` (Name)
- `description` (Text (AI))
- `price` (Float)
- `supplier` (Company)
- `created_date` (Date)

**Generate:** 1,000 rows → Parquet export → Ingest into data warehouse

---

## Troubleshooting

### Bedrock Not Working

1. Check AWS credentials:
   ```bash
   aws sts get-caller-identity
   ```
2. Verify Bedrock is available in your region (us-east-1, us-west-2, etc.)
3. Ensure IAM principal has `bedrock:InvokeModel` permission
4. Check `ENABLE_BEDROCK` is set to `true`
5. Verify `BEDROCK_MODEL` matches a valid model ID

### Parquet Export Fails

- Install PyArrow: `pip install pyarrow`
- Or use CSV export instead

### Large Dataset Generation Hangs

- Faker loops are slow for 100k+ rows
- Consider:
  - Reducing to 10k–50k rows for initial testing
  - Using Integer/Float types (vectorized, fast) instead of Faker types
  - Running on a faster machine or cloud instance

### Session Resets Between Runs

- This is expected Streamlit behavior on file changes
- Use "Download CSV/Parquet" to save results before closing

---

## Future Enhancements

- [ ] Streaming generation for 1M+ rows
- [ ] Custom Faker locale support
- [ ] Bedrock batch processing API integration
- [ ] Constraint-based generation (e.g., valid credit card numbers)
- [ ] Data quality metrics & statistical summaries
- [ ] Multi-language support for AI text
- [ ] API endpoint (FastAPI) for non-interactive data generation

---

## License & Attribution

Built during the AWS GenAI Hackathon (July–August 2025).

**Tech Stack**: Python, Streamlit, Pandas, NumPy, Faker, AWS Bedrock, Boto3

---

## Contributing

Feedback and issues welcome. Please file GitHub issues or reach out to the maintainers.