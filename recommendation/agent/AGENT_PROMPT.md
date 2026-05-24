# Task B: Recommendation Agent — Master Prompt

Use this prompt to guide any AI coding agent (Cursor, Copilot, Claude Code, etc.)
to implement the full solution for Task B of the DSN x BCT LLM Agent Challenge.

---

## CONTEXT

This is Task B of a two-task hackathon. Task A already built a FAISS vector index
and retrieval layer over Yelp, Amazon Reviews, and Goodreads datasets. Task B
copies that index and builds a separate recommendation system on top of it.

The agent must:
- Deliver personalised item recommendations ranked by relevance to a specific user
- Handle cold-start users (no history) via an onboarding conversation
- Handle cross-domain scenarios (recommend across Yelp, Amazon, Goodreads)
- Support multi-turn conversations where recommendations refine over time
- Reason explicitly before recommending (chain-of-thought before output)

---

## MASTER AGENT PROMPT

You are an expert ML engineer building a Personalised Recommendation Agent
for a hackathon. The agent must hold a multi-turn conversation with a user,
understand their preferences (either from history or onboarding questions),
reason over a candidate item pool, and return ranked recommendations.

Build a full working Python solution with five layers:

---

### LAYER 1: DATA LAYER (Copied + Extended from Task A)

Copy the FAISS index and metadata.json from Task A into this project at:
  task_b/data/faiss_index/reviews.index
  task_b/data/metadata.json

In addition, build an item catalogue from the same metadata.json.
The item catalogue is a deduplicated list of all reviewable items extracted
from the metadata, used as the pool of items to rank and recommend.

Build this catalogue with the script task_b/data/build_catalogue.py:

- Load metadata.json
- Deduplicate by item_name + platform + item_category
- For each unique item compute:
    - item_id: slugified string of platform + item_name
    - platform: str
    - item_name: str
    - item_category: str
    - item_metadata: dict
    - avg_rating: float (mean of all ratings for this item across all users)
    - review_count: int
    - top_keywords: list[str] (TF-IDF over all reviews for this item, top 5)
    - embedding: list[float] (embed item_name + item_category + top_keywords
      using sentence-transformers "all-MiniLM-L6-v2")
- Save catalogue as task_b/data/catalogue.json
- Save item embeddings as a separate FAISS index at:
  task_b/data/faiss_index/items.index
  (this is separate from the review index; it indexes items, not reviews)

---

### LAYER 2: PREFERENCE + COLD-START LAYER

File: task_b/preference/profiler.py

This layer produces a unified UserPreferenceProfile for any user,
regardless of whether they are known or new.

#### 2a. Known User Profiling

For a known user (exists in metadata.json):

- Load all their past reviews from metadata.json using composite_user_id
- Compute:
    - preferred_categories: list[str] sorted by frequency in their history
    - preferred_platforms: list[str] sorted by frequency
    - avg_rating_given: float
    - rating_strictness: "lenient" | "moderate" | "strict"
      (lenient: mean > 3.8, strict: mean < 2.8, else moderate)
    - liked_keywords: list[str] (TF-IDF over reviews where rating >= 4)
    - disliked_keywords: list[str] (TF-IDF over reviews where rating <= 2)
    - preference_embedding: np.array (mean of embeddings of all their
      highly-rated reviews, rating >= 4)
- Return as a UserPreferenceProfile dataclass

#### 2b. Cold-Start Profiling

For a new user (not in metadata.json), build a synthetic profile
from their onboarding answers.

The onboarding conversation asks exactly these 5 questions in order.
The agent asks one question at a time and waits for the answer before asking the next:

  Q1: "What type of items are you most interested in getting recommendations for?
       (e.g. restaurants and food, products, books, or a mix)"

  Q2: "How would you describe your budget preference?
       (e.g. budget-friendly, mid-range, or premium)"

  Q3: "What are two or three things you absolutely love or always look for
       when choosing something?"

  Q4: "Is there anything you strongly dislike or always try to avoid?"

  Q5: "Tell me about something you recently enjoyed — could be a meal,
       a product, a book, anything."

After all 5 answers are collected:
- Map Q1 answer to preferred_categories and preferred_platforms
- Map Q2 answer to avg_rating_given:
    budget -> 3.0, mid-range -> 3.5, premium -> 4.5
- Extract keywords from Q3 as liked_keywords
- Extract keywords from Q4 as disliked_keywords
- Embed Q5 answer as preference_embedding using sentence-transformers
- Return as a UserPreferenceProfile dataclass identical in structure
  to the known user profile

This means the ranking layer receives the same input regardless of
whether the user is known or new.

---

### LAYER 3: RANKING LAYER

File: task_b/ranking/ranker.py

This layer scores every item in the catalogue against the user's
preference profile and returns the top N ranked items.

Scoring formula per item:

  score = (
      0.40 * semantic_similarity    +  # cosine sim between item embedding
                                        # and user preference_embedding
      0.25 * category_match         +  # 1.0 if item category in preferred_categories
                                        # else 0.0
      0.20 * keyword_overlap        +  # Jaccard similarity between item top_keywords
                                        # and user liked_keywords
      0.10 * avg_rating_weight      +  # item avg_rating normalized to 0-1
      0.05 * popularity_weight         # log(review_count) normalized to 0-1
  )

  penalty = 0.3 * dislike_overlap   # Jaccard between item keywords and
                                     # user disliked_keywords; subtract from score

  final_score = score - penalty

Steps:
- Load catalogue.json and items.index
- For each item compute final_score against user profile
- Sort descending by final_score
- Return top N items (default N=10) as a ranked list
- Each returned item includes:
    - rank: int
    - item_id: str
    - item_name: str
    - platform: str
    - item_category: str
    - item_metadata: dict
    - avg_rating: float
    - score: float
    - match_reason: str (one sentence explaining why this was recommended,
      generated from the scoring components, NOT from the LLM —
      a simple template string is fine here)

Cross-domain behaviour is automatic: the catalogue includes items from
all three platforms, so the ranker naturally surfaces cross-domain results.
To explicitly test cross-domain, add a flag exclude_platform: str that
removes all items from a given platform before ranking (simulates a user
whose history is only on one platform getting recs from others).

---

### LAYER 4: CONVERSATIONAL AGENT LAYER

File: task_b/agent/conversational_agent.py

This is the core of Task B. A Groq-powered multi-turn conversational
agent that reasons before recommending.

Use Groq SDK with model: "llama3-70b-8192"

The agent manages a ConversationState object:

  @dataclass
  class ConversationState:
      session_id: str
      user_id: str | None          # None for cold-start users
      platform: str | None
      is_cold_start: bool
      onboarding_complete: bool
      onboarding_answers: dict     # Q1-Q5 answers keyed by question number
      onboarding_step: int         # which question we are on (0-5)
      preference_profile: UserPreferenceProfile | None
      current_recommendations: list[dict]
      conversation_history: list[dict]  # {"role": "user"|"assistant", "content": str}
      filters: dict                # active filters e.g. {"category": "food"}
      exclude_platform: str | None

The agent operates in two modes depending on state:

#### Mode 1: Onboarding Mode (is_cold_start=True, onboarding_complete=False)

- Ask onboarding questions one at a time
- Store each answer in onboarding_answers
- After Q5 is answered, call profiler.build_cold_start_profile()
- Set onboarding_complete=True
- Automatically run the ranker and generate first recommendations
- Transition to Recommendation Mode

#### Mode 2: Recommendation Mode (onboarding_complete=True or known user)

The agent reasons before every response using this internal chain-of-thought
structure (include this in the system prompt):

SYSTEM PROMPT:
"""
You are an intelligent recommendation agent. You help users discover items
they will love based on their preferences and history.

Before every response you must reason internally using this structure:

REASONING (not shown to user):
1. What has the user expressed interest in or asked for in this turn?
2. How does this change or refine their preference profile?
3. Should I re-rank, filter, or expand the current recommendations?
4. What is the most helpful thing to say to this user right now?

RESPONSE (shown to user):
- A short natural language explanation of your recommendations
- The ranked list of items
- A follow-up question or prompt to refine further

Rules:
- Never show your internal reasoning to the user
- Always explain WHY you are recommending each item in one sentence
- If the user asks to exclude something, update the filter and re-rank
- If the user seems unsatisfied, ask a clarifying question
- Keep responses concise and conversational
- You may recommend across platforms (Yelp, Amazon, Goodreads) freely
"""

USER PROMPT per turn:
"""
SESSION CONTEXT:
User ID: {user_id or "new user"}
Platform history: {preferred_platforms}
Preference summary: likes {liked_keywords}, dislikes {disliked_keywords}
Active filters: {filters}

CURRENT TOP 10 RECOMMENDATIONS (for your reference, do not dump this list raw):
{formatted_recommendations}

CONVERSATION SO FAR:
{conversation_history}

USER'S LATEST MESSAGE:
{latest_user_message}

Respond naturally. Highlight the most relevant 3-5 recommendations
for this turn. Ask one follow-up question to refine further.
Format recommendations as a numbered list with one-line explanations.
"""

After the LLM responds:
- Parse any filter instructions from the response
  (e.g. if user said "only show me books" set filters.category = "book")
- Re-run ranker with updated filters if needed
- Append both user message and assistant response to conversation_history
- Return updated ConversationState + assistant response text

---

### LAYER 5: API LAYER

File: task_b/api/main.py

FastAPI application with these endpoints:

POST /session/start
  Body:
  {
    "user_id": "yelp_abc123" | null,   // null for cold-start
    "platform": "yelp" | null
  }
  Returns:
  {
    "session_id": "uuid4 string",
    "is_cold_start": bool,
    "message": "first agent message (either first onboarding Q or first recs)"
  }

POST /session/chat
  Body:
  {
    "session_id": "uuid4 string",
    "message": "user message text"
  }
  Returns:
  {
    "session_id": str,
    "assistant_message": str,
    "recommendations": [
      {
        "rank": 1,
        "item_name": str,
        "platform": str,
        "item_category": str,
        "avg_rating": float,
        "match_reason": str
      },
      ...
    ],
    "onboarding_complete": bool,
    "turn_number": int
  }

GET /session/{session_id}/history
  Returns full conversation history for a session

POST /recommend/direct
  Body:
  {
    "user_id": "yelp_abc123",
    "top_n": 10,
    "exclude_platform": null | "yelp",
    "filters": {}
  }
  Returns top N recommendations without conversation (for evaluation/testing)

Store active sessions in an in-memory dict keyed by session_id.
Sessions expire after 30 minutes of inactivity.

---

### PROJECT STRUCTURE

task_b/
  data/
    build_catalogue.py       # builds item catalogue from Task A metadata
    catalogue.json           # deduplicated item pool (generated)
    metadata.json            # copied from Task A
    faiss_index/
      reviews.index          # copied from Task A
      items.index            # item-level FAISS index (generated)
  preference/
    profiler.py              # Layer 2: known user + cold-start profiling
  ranking/
    ranker.py                # Layer 3: scoring and ranking logic
  agent/
    conversational_agent.py  # Layer 4: Groq multi-turn agent
  api/
    main.py                  # Layer 5: FastAPI app
  requirements.txt
  Dockerfile
  README.md

---

### REQUIREMENTS

groq
fastapi
uvicorn
faiss-cpu
sentence-transformers
scikit-learn
numpy
pandas
python-dotenv
uuid

---

### DOCKERFILE

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Build item catalogue (assumes metadata.json and reviews.index are already copied)
RUN python -m data.build_catalogue
EXPOSE 8001
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]

---

### ENVIRONMENT VARIABLES

GROQ_API_KEY=your_groq_api_key_here

---

### EVALUATION ALIGNMENT

Make sure the solution is built to score well on:

Ranking Quality (NDCG@10 / Hit Rate) — 30pts:
  The scoring formula in the ranker must produce a well-ordered list.
  The /recommend/direct endpoint makes it easy to run offline evaluation.
  To compute NDCG@10, hold out the last review of known users as ground
  truth and check whether that item appears in the top 10 recommendations.

Cold-Start & Cross-Domain — 25pts:
  Cold-start is handled via the 5-question onboarding flow.
  Cross-domain is automatic since the catalogue spans all three platforms.
  Use the exclude_platform flag to demonstrate cross-domain capability.

Contextual Relevance (human eval) — 20pts:
  The conversational agent must give natural, helpful, context-aware responses.
  The reasoning prompt ensures the agent explains its choices clearly.

Solution Paper — 15pts:
  The scoring formula, onboarding flow, and chain-of-thought reasoning are
  all highly explainable and should be documented clearly in the paper.

Code Reproducibility — 10pts:
  Docker + one-command catalogue build ensures end-to-end reproducibility.

---

### BONUS: NIGERIAN CONTEXTUALISATION

Add a nigerian_context: bool flag to both /session/start and /recommend/direct.
When enabled, inject this addition into the agent system prompt:

"When making recommendations, be aware of the Nigerian consumer context.
Favour items and experiences that reflect Nigerian preferences where relevant:
value for money is highly important, brand familiarity matters, and where
possible draw comparisons to locally familiar equivalents. Use warm,
conversational language appropriate to Nigerian users."

Also add a is_nigerian_user field to UserPreferenceProfile.
When True, boost items with "value", "affordable", or "popular" in their
keywords by 0.05 in the scoring formula.

---

### EXAMPLE INTERACTION FLOW

Cold-Start User:

  POST /session/start  { "user_id": null }
  -> "Hi! I'd love to help you find something great. What type of items
      are you most interested in? (restaurants and food, products, books, or a mix)"

  POST /session/chat   { "message": "I'm looking for food recommendations" }
  -> "Great! How would you describe your budget preference?
      (budget-friendly, mid-range, or premium)"

  ... (3 more onboarding questions) ...

  POST /session/chat   { "message": "I recently loved a spicy shawarma place" }
  -> "Perfect, I have a great feel for your taste now! Here are my top picks:
      1. Chicken Republic — Fast Food (Yelp) ★4.1 — Matches your love of quick,
         flavourful meals at a great price.
      2. ...
      What city or area should I focus on for food spots?"

Known User Refinement:

  POST /session/chat   { "message": "skip the fast food, show me sit-down places" }
  -> Agent updates filter, re-ranks, responds with refined list
