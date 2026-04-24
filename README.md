# 🛡️ AI-Driven Security Center Operation

<div align="center">

![Search](https://img.shields.io/badge/Vector%20Search-FAISS-blue?style=for-the-badge&logo=apache)
![Embeddings](https://img.shields.io/badge/Embeddings-SentenceTransformers-green?style=for-the-badge&logo=huggingface)
![LLM](https://img.shields.io/badge/Summarization-Transformers-orange?style=for-the-badge&logo=transformer)
![API](https://img.shields.io/badge/API-FastAPI-teal?style=for-the-badge&logo=fastapi)
![Finetune](https://img.shields.io/badge/LoRA-Finetuning-purple?style=for-the-badge&logo=huggingface)

**Enterprise-ready RAG for security alerts** — index EDR logs with embeddings, retrieve high-signal context using FAISS, and generate analyst-ready briefs with a lightweight summarizer. Includes LoRA finetuning utilities for threat-intel classification and a FastAPI service.

</div>

---

## 🌟 Overview

This project provides an end-to-end workflow for Security Operations Centers:

- Build a vector index over JSONL EDR logs
- Search relevant context for alerts
- Summarize findings into an investigation brief
- Expose search and contextualization via an API
- Optionally finetune an LLM for classification with LoRA

### ✨ Key Features

- 🔎 **High-quality retrieval**: Sentence-Transformers + FAISS (inner-product, normalized)
- 🎯 **Smart retrieval layer**: widen FAISS `retrieve_k`, optional metadata filters, IOC overlap narrowing, and cross-encoder reranking before summarization
- 🧠 **LLM contextualization**: Transformers summarization pipeline with SOC-specific prompt
- ⚙️ **Configurable**: All knobs via `app/config.py` or environment variables
- 🧪 **Finetune-ready**: LoRA training pipeline for LLaMA 3 SFT classification
- 📈 **Reporting**: Weekly HTML KPI report from triage logs
- ✅ **Tests**: Pytest coverage for filters, persistence, retrieval, rerank, and API wiring

## 🏗️ Architecture

```
┌──────────────────────┐   ┌────────────────────┐   ┌──────────────────────┐
│  JSONL EDR Logs      │ → │  Embeddings +      │ → │  FAISS Vector Store   │
│  (ingest.py)         │   │  Document Builder  │   │  (vector_store.py)    │
└──────────────────────┘   └────────────────────┘   └──────────────────────┘
             │                          │                         │
             └─────────────── search ───┼─────────────────────────┘
                                        │
                              ┌──────────────────────┐
                              │  LLM Contextualizer  │
                              │  (contextualize.py)  │
                              └─────────┬────────────┘
                                        │
                              ┌──────────────────────┐
                              │  FastAPI Endpoints   │
                              │   /search, /context  │
                              └──────────────────────┘
```

## 🛠️ Tech Stack

- **Vector Search**: FAISS (`IndexFlatIP` with normalized embeddings)
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (configurable)
- **Summarization**: `google/flan-t5-base` by default (configurable)
- **API**: FastAPI + Uvicorn
- **Finetuning**: LoRA with PEFT + TRL SFTTrainer
- **Reports**: Jinja2 HTML report generation

## 🚀 Quick Start

### 1) Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Build index from JSONL EDR logs

```bash
PYTHONPATH=$(pwd) python scripts/build_index.py /path/to/*.jsonl --index-dir indexes/default
```

Optional flags:
- `--grouping actorname` (default)
- `--embedding-model sentence-transformers/all-MiniLM-L6-v2`

### 2b) Append new logs to an existing index

```bash
PYTHONPATH=$(pwd) python scripts/append_index.py /path/to/new_batch.jsonl --index-dir indexes/default
```

Use `--dry-run` to count documents without writing. The embedding model must match the original index.

### 3) Search the index

```bash
PYTHONPATH=$(pwd) python scripts/search.py "svchost suspicious access" --top-k 10
```

### 3b) Advanced search (filters + optional rerank)

```bash
PYTHONPATH=$(pwd) python scripts/advanced_search.py "beacon 203.0.113.50" \
  --top-k 5 --retrieve-k 20 --min-events 2 --ioc-narrow --json
```

Add `--rerank` to run the cross-encoder (downloads weights on first use).

### 4) Contextualize an alert

```bash
PYTHONPATH=$(pwd) python scripts/contextualize.py "svchost contacted external IP 10.193.66.115"
```

### 5) Run the API

```bash
chmod +x scripts/serve_api.sh
./scripts/serve_api.sh
```

Then visit `http://localhost:8000/docs`.

## 🔌 API Endpoints

- `GET /healthz` — health check
- `GET /index/info` — vector index metadata (document count, embedding model, paths, consistency flags)
- **Auth** (JWT, shared SQLite with cases): `POST /auth/register` (JSON username/password), `POST /auth/token` (OAuth2 password form, same as `curl -d username=...&password=...`), `GET /auth/me` (Bearer token). Set **`JWT_SECRET_KEY`** in production.
- **Cases** (`/cases/...`) require `Authorization: Bearer <access_token>`; each user only sees and mutates cases they created.
- `POST /search` → `[ { score, doc_id, text, metadata } ]`  
  Optional JSON fields (all optional, backward compatible): `retrieve_k`, `filters` (metadata / score / time bounds), `use_rerank`, `narrow_by_ioc_overlap`
- `POST /search/advanced` — same body and response as `/search` (explicit alias for tooling)
- `POST /contextualize` → `{ brief, num_context, rerank }`
- `POST /triage` → `{ alert, brief, search_results, rerank }`

## ⚙️ Configuration (`app/config.py`)

Override via env vars or `.env` file.

- **Paths**: `data_dir`, `index_dir`
- **Embeddings**: `embedding_model_name`, `search_top_k`
- **Retrieval**: `retrieve_multiplier`, `retrieve_max_candidates`, `rerank_enabled`, `rerank_model_name`
- **API**: `api_host`, `api_port`
- **Auth**: `jwt_secret_key`, `jwt_expire_minutes` (also `JWT_SECRET_KEY` / `JWT_EXPIRE_MINUTES` via env)
- **Contextualizer**: `summarizer_model_name`
- **Finetune**: `llama_base_model`, `lora_output_dir`, `hf_token`

## 🧪 Tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=$(pwd) pytest
```

## 🧪 LoRA Finetuning (optional)

Prepare a JSON/JSONL/CSV with `text` and `label` fields.

```bash
PYTHONPATH=$(pwd) python -m app.finetune.train_lora /path/to/data.jsonl \
  --model meta-llama/Meta-Llama-3-8B-Instruct \
  --output artifacts/finetune_lora \
  --epochs 2 --batch 2 --lr 2e-4
```

The loader converts data to SFT format and trains a LoRA adapter. Artifacts are saved under `lora_output_dir`.

## 📊 Weekly Report (from triage JSONL)

Generate an HTML summary of KPIs (alerts triaged, median MTTI, relevant match rate):

```bash
PYTHONPATH=$(pwd) python scripts/generate_weekly_report.py triage_results.jsonl --out reports/weekly_report.html
```

## 📁 Project Layout

```
app/
  api/main.py            # FastAPI service
  config.py              # Central settings
  indexing/
    ingest.py            # Parse JSONL logs -> documents
    vector_store.py      # FAISS vector store
    search_filters.py    # Post-retrieval filters + lightweight IOC parsing
  llm/
    contextualize.py     # Summarization for alert context
    rerank.py            # Cross-encoder reranker (lazy-loaded)
    retrieval.py         # Retrieval pipeline orchestration
  finetune/
    dataset.py           # Threat dataset loader -> SFT mapping
    train_lora.py        # LoRA finetuning CLI
  reports/
    weekly.py            # KPI report generator
scripts/
  build_index.py         # Build the FAISS index
  append_index.py        # Append documents to an existing index
  search.py              # Query the index
  advanced_search.py     # Filters, wide retrieval, optional rerank
  contextualize.py       # Retrieval + summarization CLI
  generate_weekly_report.py  # Render weekly HTML report
  serve_api.sh           # Run API server
tests/                   # Pytest suite (filters, store, retrieval, API)
```
