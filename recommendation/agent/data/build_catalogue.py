"""
build_catalogue.py
Builds a deduplicated item catalogue from Task A's metadata.json.
Also creates a separate FAISS index over item embeddings.
"""

import os
import json
import re
import math
import numpy as np
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
import faiss

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"
METADATA_PATH = os.path.join(os.path.dirname(__file__), "metadata.json")
CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "catalogue.json")
INDEX_DIR = os.path.join(os.path.dirname(__file__), "faiss_index")
ITEMS_INDEX_PATH = os.path.join(INDEX_DIR, "items.index")
# ──────────────────────────────────────────────────────────────────────────────


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:80]


def build_catalogue():
    print("Loading metadata...")
    with open(METADATA_PATH, "r") as f:
        metadata = json.load(f)

    # Group reviews by item (platform + item_name + category)
    item_groups = defaultdict(list)
    for record in metadata:
        key = (
            record["platform"],
            record.get("item_name", "Unknown"),
            record.get("item_category", "General"),
        )
        item_groups[key].append(record)

    print(f"Found {len(item_groups)} unique items across all platforms.")

    model = SentenceTransformer(EMBED_MODEL)
    catalogue = []
    embeddings = []

    for (platform, item_name, item_category), reviews in item_groups.items():
        if item_name in ("Unknown", "Unknown Business", "Unknown Product", "Unknown Book"):
            continue

        ratings = [r["rating"] for r in reviews if r.get("rating")]
        texts = [r["review_text"] for r in reviews if r.get("review_text", "").strip()]

        avg_rating = round(float(np.mean(ratings)), 2) if ratings else 3.0
        review_count = len(reviews)

        # Extract top keywords via TF-IDF over all reviews for this item
        top_keywords = []
        if len(texts) >= 2:
            try:
                tfidf = TfidfVectorizer(
                    max_features=5,
                    stop_words="english",
                    ngram_range=(1, 2),
                )
                tfidf.fit(texts)
                top_keywords = list(tfidf.get_feature_names_out())
            except Exception:
                pass

        # Build embed text
        embed_text = " ".join([item_name, item_category] + top_keywords)

        item_id = slugify(f"{platform}_{item_name}")
        item_metadata = reviews[0].get("item_metadata", {})

        catalogue.append({
            "item_id": item_id,
            "platform": platform,
            "item_name": item_name,
            "item_category": item_category,
            "item_metadata": item_metadata,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "top_keywords": top_keywords,
            "embed_text": embed_text,
        })

    print(f"Building embeddings for {len(catalogue)} catalogue items...")
    texts_to_embed = [item["embed_text"] for item in catalogue]
    item_embeddings = model.encode(texts_to_embed, batch_size=64, show_progress_bar=True)
    item_embeddings = np.array(item_embeddings).astype("float32")

    # Remove embed_text from catalogue before saving (it's only needed for indexing)
    for item in catalogue:
        del item["embed_text"]

    # Save FAISS item index
    os.makedirs(INDEX_DIR, exist_ok=True)
    dim = item_embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(item_embeddings)
    faiss.write_index(index, ITEMS_INDEX_PATH)
    print(f"Item FAISS index saved to {ITEMS_INDEX_PATH}")

    # Save catalogue
    with open(CATALOGUE_PATH, "w") as f:
        json.dump(catalogue, f)
    print(f"Catalogue saved to {CATALOGUE_PATH} ({len(catalogue)} items)")


if __name__ == "__main__":
    build_catalogue()
