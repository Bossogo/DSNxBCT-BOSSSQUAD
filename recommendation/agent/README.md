# Task B: Recommendation Agent
### DSN x BCT LLM Agent Challenge

A personalised multi-turn recommendation agent that handles cold-start users,
cross-domain recommendations, and conversational refinement.

---

## Architecture

```
User starts session
        |
        v
Known user?
   Yes                       No
    |                         |
Build preference         Onboarding flow
profile from history     (5 questions)
    |                         |
    └──── UserPreferenceProfile ────┘
                  |
                  v
         Score + Rank item catalogue
         (semantic sim + category + keywords
          + rating + popularity - dislikes)
                  |
                  v
       Groq LLaMA 3 70B reasons over
       rankings + conversation history
                  |
                  v
    Natural language response + top 3-5 picks
    + follow-up question to refine further
```

---

## Quickstart (Local)

1. Copy Task A outputs into this project:

```bash
cp ../task_a/data/metadata.json data/
cp -r ../task_a/data/faiss_index data/
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your Groq API key:

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

4. Build item catalogue:

```bash
python -m data.build_catalogue
```

5. Start the API:

```bash
uvicorn api.main:app --reload --port 8001
```

6. Open API docs: http://localhost:8001/docs

---

## Docker

```bash
# Copy Task A data first
cp ../task_a/data/metadata.json data/
cp -r ../task_a/data/faiss_index data/

docker build -t task-b-agent .
docker run -p 8001:8001 -e GROQ_API_KEY=your_key_here task-b-agent
```

---

## Example: Cold-Start Flow

```bash
# Start session (no user_id = cold-start)
curl -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"nigerian_context": true}'

# Response:
# { "session_id": "abc-123", "is_cold_start": true,
#   "message": "Hi! I'd love to help... What type of items are you interested in?" }

# Answer each onboarding question
curl -X POST http://localhost:8001/session/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "message": "food and restaurants"}'

# ... 4 more questions, then recommendations appear automatically

# Refine recommendations
curl -X POST http://localhost:8001/session/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc-123", "message": "skip fast food, show me sit-down places"}'
```

## Example: Known User Flow

```bash
# Start session with known user
curl -X POST http://localhost:8001/session/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123", "platform": "yelp", "nigerian_context": true}'

# Immediately returns recommendations, no onboarding needed
```

## Example: Direct Evaluation Endpoint

```bash
# For NDCG@10 evaluation (hold out last review and check hit rate)
curl -X POST http://localhost:8001/recommend/direct \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "abc123",
    "platform": "yelp",
    "top_n": 10,
    "exclude_platform": "yelp"
  }'
# exclude_platform="yelp" demonstrates cross-domain: user history is on Yelp
# but recommendations come from Amazon and Goodreads
```

---

## Endpoints

| Method | Endpoint                     | Description                              |
|--------|------------------------------|------------------------------------------|
| POST   | /session/start               | Start a session (known or cold-start)    |
| POST   | /session/chat                | Send a message, get recommendations      |
| GET    | /session/{id}/history        | Get full conversation history            |
| POST   | /recommend/direct            | Direct recommendations (for evaluation)  |

---

## Scoring Alignment

| Criterion                  | Score | How it is addressed                                    |
|----------------------------|-------|--------------------------------------------------------|
| Ranking Quality NDCG@10    | 30    | Weighted scoring formula in ranker.py                  |
| Cold-Start & Cross-Domain  | 25    | 5-question onboarding + exclude_platform flag          |
| Contextual Relevance       | 20    | Chain-of-thought Groq agent with conversation history  |
| Solution Paper             | 15    | Fully explainable scoring formula and onboarding flow  |
| Code Reproducibility       | 10    | Docker + one-command catalogue build                   |
| Nigerian Contextualisation | Bonus | nigerian_context flag on all endpoints                 |
