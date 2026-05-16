# Task A: User Modeling Agent — Master Prompt

Use this prompt to guide any AI coding agent (Cursor, Copilot, Claude Code, etc.)
to implement the full three-layer solution for Task A.

---

## MASTER AGENT PROMPT

You are an expert ML engineer building a User Modeling Agent for a hackathon.
The agent must simulate how a specific user would review an unseen item,
capturing their tone, rating behaviour, and contextual nuance.

Build a full working Python solution with three layers:

---

### LAYER 1: DATA LAYER (Ingestion + Indexing)

- Use the HuggingFace `datasets` library to load reviews from Yelp, Amazon, and Goodreads
- Filter to only keep users with at least 10 reviews (quality threshold)
- For each review, store the following fields:
  - composite*user_id: f"{platform}*{user_id}"
  - platform: "yelp" | "amazon" | "goodreads"
  - review_text: str
  - rating: float (normalise all ratings to 1-5 scale)
  - item_name: str
  - item_category: str
  - item_metadata: dict (any extra fields like location, price, genre)
  - timestamp: str (if available)
- Embed each review using the `sentence-transformers` library,
  model: "all-MiniLM-L6-v2"
- Index all embeddings into a FAISS vector store
- Save the FAISS index and a corresponding metadata JSON file to disk
  so ingestion only runs once

Use this dataset loading strategy:

- Yelp: HuggingFace dataset "Yelp/yelp_review_full" — map stars field to rating
- Amazon: HuggingFace dataset "McAuley-Lab/Amazon-Reviews-2023",
  config "raw_review_All_Beauty" as a starting category — map rating field directly
- Goodreads: HuggingFace dataset "allenai/WildChat" is NOT correct;
  use "baharehahmadi/goodreads" or load from the UCSD Goodreads JSON files
  if HuggingFace version is unavailable — map rating field to 1-5 scale

Cap each platform at 50,000 reviews during development to keep ingestion fast.
Add a CLI flag --full to disable the cap for final submission.

---

### LAYER 2: RETRIEVAL LAYER

- Accept a composite_user_id and a new item dict as input
- Embed the new item's metadata (name + category + any descriptors) using
  the same sentence-transformers model
- Query the FAISS index filtered to only that user's reviews
  (filter by composite_user_id in metadata before or after FAISS search)
- Return the top 5 most semantically similar past reviews from that user
- Also compute a simple rating tendency summary for the user:
  - mean_rating: float
  - std_rating: float
  - common_themes: list[str] (extract top keywords using TF-IDF or simple frequency)
  - typical_review_length: "short" | "medium" | "long"

---

### LAYER 3: GENERATION LAYER

- Use the Groq Python SDK to call the LLM
- Model to use: "llama3-70b-8192"
- Build a structured prompt using the retrieved reviews and user summary
- The system prompt must establish the agent's role
- The user prompt must include:
  - The user's rating tendency summary
  - Their top 5 retrieved past reviews (verbatim, labelled)
  - The new item's details
  - Clear instruction to generate a review AND a star rating

Use this exact prompt template:

SYSTEM:
"""
You are a user simulation agent. Your job is to impersonate a specific
reviewer based on their past review history. You must match their tone,
vocabulary, sentence length, rating strictness, and the aspects of items
they typically care about. Do not break character. Do not add disclaimers.
Write exactly as this user would write.
"""

USER:
"""
You are simulating reviews for a user with the following behavioural profile:

PLATFORM: {platform}
USER ID: {user_id}
AVERAGE RATING: {mean_rating}/5
RATING STRICTNESS: {std_rating} standard deviation (lower = more consistent)
TYPICAL REVIEW LENGTH: {typical_review_length}
COMMON THEMES THEY MENTION: {common_themes}

Here are their 5 most relevant past reviews for context:

{retrieved_reviews}

---

Now simulate this user's review for the following new item they have NOT reviewed:

ITEM NAME: {item_name}
ITEM CATEGORY: {item_category}
ITEM DETAILS: {item_metadata}

Respond in this exact JSON format:
{{
  "simulated_review": "...",
  "predicted_rating": <float between 1.0 and 5.0>,
  "confidence": "low" | "medium" | "high"
}}

Only return the JSON. No explanation. No preamble.
"""

- Parse the JSON response and return it as a Python dict
- Handle JSON parsing errors gracefully with a fallback

---

### API LAYER (FastAPI)

Wrap all three layers in a FastAPI application with these endpoints:

GET /platforms
Returns: list of available platforms

GET /users?platform={platform}&limit=50
Returns: list of user IDs for that platform with their review count

POST /simulate
Body:
{
"platform": "yelp",
"user_id": "abc123",
"item": {
"name": "Chicken Republic Lekki",
"category": "Fast Food",
"location": "Lagos",
"price_range": "mid",
"description": "Popular fast food chain"
}
}
Returns:
{
"composite_user_id": "yelp_abc123",
"simulated_review": "...",
"predicted_rating": 3.5,
"confidence": "high",
"retrieved_reviews_used": 5,
"user_profile": {
"mean_rating": 3.2,
"typical_review_length": "short",
"common_themes": ["service", "price", "taste"]
}
}

---

### PROJECT STRUCTURE

task_a/
data/
ingest.py # Layer 1: data ingestion and indexing
faiss_index/ # saved FAISS index files
metadata.json # review metadata store
retrieval/
retriever.py # Layer 2: retrieval logic
generation/
generator.py # Layer 3: Groq LLM generation
api/
main.py # FastAPI app
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
datasets
transformers
scikit-learn
numpy
pandas
python-dotenv

---

### DOCKERFILE

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m data.ingest
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

---

### ENVIRONMENT VARIABLES

GROQ_API_KEY=your_groq_api_key_here

---

### EVALUATION ALIGNMENT

Make sure the solution is built to score well on:

- Review Text Quality (ROUGE / BERTScore): the simulated review must
  closely resemble how the user actually writes
- Rating Accuracy (RMSE): predicted_rating must reflect the user's
  rating tendencies, not just a generic average
- Behavioural Fidelity: tone, length, themes, and vocabulary must
  match the user's historical style
- Code Reproducibility: the project must run end to end with
  `docker build` and `docker run`

---

### BONUS (Nigerian Contextualisation)

The brief awards bonus marks for Nigerian contextualisation.
Add a flag `nigerian_context=True` to the /simulate endpoint.
When enabled, inject this into the system prompt:

"Where contextually appropriate, reflect Nigerian consumer preferences,
colloquialisms, and cultural references in the review. For example,
references to value for money, brand awareness in Nigerian markets,
and locally relevant comparisons."
