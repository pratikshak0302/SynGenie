# SynGenie — Smart Synthetic Data Generator

Streamlit app to generate synthetic datasets from user-defined schemas. Integrates with AWS Bedrock (optional) for AI-generated text fields with a Faker fallback.

Quick start

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. (Optional) Enable Bedrock by setting environment variables (do NOT store credentials in code):

```powershell
setx ENABLE_BEDROCK true
setx BEDROCK_MODEL "your-bedrock-model-id"
# Configure AWS credentials via environment or IAM role
```

3. Run the app:

```bash
streamlit run app.py
```

Notes
- By default AI calls are disabled. Set `ENABLE_BEDROCK=true` to enable.
- The Bedrock call is best-effort; failures fall back to Faker generated text.
- For production, prefer IAM roles, least-privilege policies, and batching of large model calls.