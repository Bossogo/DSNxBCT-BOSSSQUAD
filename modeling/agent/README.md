# Task A: User Modeling Agent

### DSN x BCT LLM Agent Challenge

An agent that simulates how a specific user would review an unseen item,
capturing their tone, rating behaviour, and contextual nuance.

---

## Architecture

```
User ID + Item Details
        │
        ▼
┌───────────────────┐
│   DATA LAYER      │  HuggingFace datasets → FAISS vector index
│   (ingest.py)     │  Yelp, Amazon Reviews, Goodreads
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ RETRIEVAL LAYER   │  Semantic search over user's own review history
│ (retriever.py)    │  + behavioural profile extraction
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ GENERATION LAYER  │  Groq LLaMA 3 70B generates simulated review
│ (generator.py)    │  conditioned on retrieved history + profile
└────────┬──────────┘
         │
         ▼
  Simulated Review + Predicted Rating
```

---

## Quickstart (Local)

1. Clone the repo and install dependencies:

```bash
pip install -r requirements.txt
```

2. Set your Groq API key:

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

3. Run data ingestion:

```bash
python -m data.ingest                              # dev mode, uses all CPU cores
python -m data.ingest --full                       # full dataset (final submission)
python -m data.ingest --num-processes 1            # force single-process mode
python -m data.ingest --num-processes 8 --batch-size 64
python -m data.ingest --num-processes 8 --embed-chunk-size 5000
python -m data.ingest --amazon-path data/raw/amazon_reviews.jsonl --goodreads-path data/raw/goodreads_reviews.jsonl
```

4. Start the API:

```bash
uvicorn api.main:app --reload
```

5. Open API docs at: http://localhost:8000/docs

---

## Docker

```bash
docker build -t task-a-agent .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key_here task-a-agent
```

---

## Example API Call

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "yelp",
    "user_id": "abc123",
    "item": {
      "name": "Chicken Republic Lekki",
      "category": "Fast Food",
      "location": "Lagos",
      "price_range": "mid",
      "description": "Popular fast food chain known for jollof rice"
    },
    "nigerian_context": true
  }'
```

Example response:

```json
{
  "composite_user_id": "yelp_abc123",
  "simulated_review": "The jollof rice was decent but for that price you expect more...",
  "predicted_rating": 3.5,
  "confidence": "high",
  "retrieved_reviews_used": [
    {
      "item_name": "Mega Chicken Ikeja",
      "item_category": "Fast Food",
      "review_text": "Good fast food but extremely overpriced for what you get.",
      "rating": 3.0,
      "platform": "yelp",
      "item_metadata": {
        "location": "Lagos"
      }
    }
  ],
  "user_profile": {
    "mean_rating": 3.2,
    "std_rating": 0.8,
    "typical_review_length": "short",
    "common_themes": ["service", "price", "taste", "value"],
    "total_reviews": 23
  }
}
```

---

## Endpoints

| Method | Endpoint   | Description                      |
| ------ | ---------- | -------------------------------- |
| GET    | /platforms | List available platforms         |
| GET    | /users     | List users for a platform        |
| POST   | /simulate  | Simulate a review for a new item |

---

## Evaluation Alignment

| Criterion                  | How it is addressed                                       |
| -------------------------- | --------------------------------------------------------- |
| Review Text Quality        | LLaMA 3 70B conditioned on real user history              |
| Rating Accuracy (RMSE)     | Rating predicted from user tendency + semantic similarity |
| Behavioural Fidelity       | Retrieved reviews capture tone, themes, length patterns   |
| Code Reproducibility       | Docker + one-command ingestion                            |
| Nigerian Contextualisation | `nigerian_context=true` flag on /simulate endpoint        |

---

## Datasets

- Yelp: https://huggingface.co/datasets/Yelp/yelp_review_full
- Amazon: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023
- Goodreads: https://huggingface.co/datasets/baharehahmadi/goodreads

### Local fallback files (for Amazon/Goodreads)

If HuggingFace script-based loaders are unavailable in your `datasets` version, ingestion now falls back to local files.

Supported formats: `.parquet`, `.jsonl`, `.json`, `.csv`

Default fallback paths:

- `data/raw/amazon_reviews.jsonl`
- `data/raw/goodreads_reviews.jsonl`

You can generate these with the helper script:

```bash
# Amazon only (downloads All_Beauty JSONL fallback)
python -m data.prepare_raw_data

# Amazon + Goodreads conversion from local .json.gz
python -m data.prepare_raw_data --goodreads-gz /path/to/goodreads_reviews.json.gz

# Amazon + Goodreads conversion from URL .json.gz
python -m data.prepare_raw_data --goodreads-gz https://example.com/goodreads_reviews.json.gz

# Use an existing Goodreads jsonl file directly
python -m data.prepare_raw_data --goodreads-jsonl /path/to/goodreads_reviews.jsonl
```

You can also pass explicit paths:

```bash
python -m data.ingest \
  --amazon-path /absolute/or/relative/path/to/amazon_reviews.jsonl \
  --goodreads-path /absolute/or/relative/path/to/goodreads_reviews.jsonl
```

Or set environment variables:

```bash
export AMAZON_REVIEWS_PATH=/path/to/amazon_reviews.jsonl
export GOODREADS_REVIEWS_PATH=/path/to/goodreads_reviews.jsonl
python -m data.ingest
```
