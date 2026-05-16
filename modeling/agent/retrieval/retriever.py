"""
Layer 2: Retrieval Layer
Given a user ID and a new item, retrieves the user's most relevant past reviews.
Also computes a behavioural profile summary for the user.
"""

import os
import json
import numpy as np
from collections import Counter
from sentence_transformers import SentenceTransformer
import faiss
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "../data/faiss_index/reviews.index")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "../data/metadata.json")
TOP_K = 5
# ──────────────────────────────────────────────────────────────────────────────


class Retriever:
    def __init__(self):
        print("Loading retrieval components...")
        self.model = SentenceTransformer(EMBED_MODEL)
        self.index = faiss.read_index(INDEX_PATH)

        with open(METADATA_PATH, "r") as f:
            self.metadata = json.load(f)

        # Build lookup: composite_user_id -> list of (faiss_idx, record)
        self.user_index_map = {}
        for i, record in enumerate(self.metadata):
            uid = record["composite_user_id"]
            if uid not in self.user_index_map:
                self.user_index_map[uid] = []
            self.user_index_map[uid].append(i)

        print(f"Retriever ready. {len(self.metadata)} reviews, "
              f"{len(self.user_index_map)} users indexed.")

    def get_platforms(self):
        platforms = list({r["platform"] for r in self.metadata})
        return sorted(platforms)

    def get_users(self, platform, limit=50):
        users = {}
        for record in self.metadata:
            if record["platform"] == platform:
                uid = record["composite_user_id"]
                users[uid] = users.get(uid, 0) + 1
        result = [
            {"composite_user_id": uid, "review_count": count}
            for uid, count in users.items()
        ]
        result.sort(key=lambda x: x["review_count"], reverse=True)
        return result[:limit]

    def _compute_user_profile(self, user_records):
        """Compute behavioural statistics for a user."""
        ratings = [r["rating"] for r in user_records]
        texts = [r["review_text"] for r in user_records if r["review_text"]]

        mean_rating = round(float(np.mean(ratings)), 2)
        std_rating = round(float(np.std(ratings)), 2)

        # Typical review length
        avg_len = np.mean([len(t.split()) for t in texts]) if texts else 0
        if avg_len < 30:
            typical_length = "short"
        elif avg_len < 80:
            typical_length = "medium"
        else:
            typical_length = "long"

        # Common themes via TF-IDF
        common_themes = []
        if len(texts) >= 2:
            try:
                tfidf = TfidfVectorizer(
                    max_features=10,
                    stop_words="english",
                    ngram_range=(1, 2),
                )
                tfidf.fit(texts)
                common_themes = list(tfidf.get_feature_names_out())
            except Exception:
                # fallback: simple word frequency
                all_words = " ".join(texts).lower().split()
                stopwords = {"the", "a", "and", "is", "it", "i", "was", "to",
                             "of", "in", "this", "for", "that", "my", "with"}
                filtered = [w for w in all_words if w not in stopwords and len(w) > 3]
                common_themes = [w for w, _ in Counter(filtered).most_common(10)]

        return {
            "mean_rating": mean_rating,
            "std_rating": std_rating,
            "typical_review_length": typical_length,
            "common_themes": common_themes,
            "total_reviews": len(user_records),
        }

    def retrieve(self, platform, user_id, item):
        """
        Main retrieval method.

        Args:
            platform: str - "yelp", "amazon", or "goodreads"
            user_id: str - raw user ID (without platform prefix)
            item: dict - new item details (name, category, description, etc.)

        Returns:
            dict with retrieved_reviews and user_profile
        """
        composite_id = f"{platform}_{user_id}"

        if composite_id not in self.user_index_map:
            raise ValueError(f"User '{composite_id}' not found in index.")

        user_faiss_indices = self.user_index_map[composite_id]
        user_records = [self.metadata[i] for i in user_faiss_indices]

        # Build query text from new item
        item_text = " ".join([
            item.get("name", ""),
            item.get("category", ""),
            item.get("description", ""),
            item.get("location", ""),
        ])

        query_embedding = self.model.encode([item_text]).astype("float32")

        # Retrieve embeddings for this user's reviews only
        # We do this by fetching all user review embeddings from the FAISS index
        user_embeddings = np.zeros(
            (len(user_faiss_indices), self.index.d), dtype="float32"
        )
        for j, faiss_idx in enumerate(user_faiss_indices):
            self.index.reconstruct(faiss_idx, user_embeddings[j])

        # Compute cosine-style distances manually for user subset
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-9)
        user_norms = user_embeddings / (
            np.linalg.norm(user_embeddings, axis=1, keepdims=True) + 1e-9
        )
        scores = user_norms @ query_norm.T  # shape: (n_user_reviews, 1)
        scores = scores.flatten()

        top_indices = np.argsort(scores)[::-1][:TOP_K]
        retrieved = [user_records[i] for i in top_indices]

        user_profile = self._compute_user_profile(user_records)

        return {
            "composite_user_id": composite_id,
            "platform": platform,
            "user_id": user_id,
            "retrieved_reviews": retrieved,
            "user_profile": user_profile,
        }
