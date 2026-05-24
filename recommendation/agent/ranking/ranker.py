"""
Layer 3: Ranking Layer
Scores every item in the catalogue against a user preference profile
and returns the top N ranked recommendations.
"""

import os
import json
import math
import numpy as np
from typing import Optional
import faiss
from sentence_transformers import SentenceTransformer

from preference.profiler import UserPreferenceProfile

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"
CATALOGUE_PATH = os.path.join(os.path.dirname(__file__), "../data/catalogue.json")
ITEMS_INDEX_PATH = os.path.join(
    os.path.dirname(__file__), "../data/faiss_index/items.index"
)
# ──────────────────────────────────────────────────────────────────────────────


class Ranker:
    def __init__(self):
        print("Loading ranking components...")
        self.model = SentenceTransformer(EMBED_MODEL)
        self.item_index = faiss.read_index(ITEMS_INDEX_PATH)

        with open(CATALOGUE_PATH, "r") as f:
            self.catalogue = json.load(f)

        # Pre-load all item embeddings for fast scoring
        n = len(self.catalogue)
        dim = self.item_index.d
        self.item_embeddings = np.zeros((n, dim), dtype="float32")
        for i in range(n):
            self.item_index.reconstruct(i, self.item_embeddings[i])

        # Precompute normalised avg_rating and log(review_count) for all items
        ratings = np.array([item["avg_rating"] for item in self.catalogue], dtype="float32")
        counts = np.array(
            [math.log1p(item["review_count"]) for item in self.catalogue], dtype="float32"
        )
        self._rating_norm = (ratings - 1.0) / 4.0          # scale 1-5 to 0-1
        max_count = counts.max() if counts.max() > 0 else 1.0
        self._count_norm = counts / max_count

        print(f"Ranker ready. {len(self.catalogue)} items in catalogue.")

    def _jaccard(self, set_a: list, set_b: list) -> float:
        if not set_a or not set_b:
            return 0.0
        a, b = set(set_a), set(set_b)
        intersection = len(a & b)
        union = len(a | b)
        return intersection / union if union > 0 else 0.0

    def _cosine_sim(self, vec_a: np.ndarray, mat_b: np.ndarray) -> np.ndarray:
        """Cosine similarity between a single vector and a matrix of vectors."""
        norm_a = vec_a / (np.linalg.norm(vec_a) + 1e-9)
        norms_b = np.linalg.norm(mat_b, axis=1, keepdims=True) + 1e-9
        norm_b = mat_b / norms_b
        return norm_b @ norm_a

    def _build_match_reason(self, item: dict, components: dict) -> str:
        reasons = []
        if components["semantic_similarity"] > 0.5:
            reasons.append("closely matches your taste profile")
        if components["category_match"] > 0:
            reasons.append(f"fits your preferred category ({item['item_category']})")
        if components["keyword_overlap"] > 0.1:
            reasons.append("shares themes you enjoy")
        if item["avg_rating"] >= 4.0:
            reasons.append(f"highly rated at {item['avg_rating']}/5")
        if not reasons:
            reasons.append("popular in your area of interest")
        return "Recommended because it " + ", and ".join(reasons) + "."

    def _get_candidates(self, filters: dict, exclude_platform: Optional[str]) -> list[int]:
        """Return catalogue indices that pass the given hard filters."""
        indices = []
        for i, item in enumerate(self.catalogue):
            if exclude_platform and item["platform"] == exclude_platform:
                continue
            match = True
            for field, value in filters.items():
                item_val = str(item.get(field, "")).lower()
                filter_val = str(value).lower()
                if filter_val not in item_val:
                    match = False
                    break
            if match:
                indices.append(i)
        return indices

    def rank(
        self,
        profile: UserPreferenceProfile,
        top_n: int = 10,
        filters: Optional[dict] = None,
        exclude_platform: Optional[str] = None,
    ) -> list[dict]:
        """
        Score and rank all catalogue items against the user preference profile.

        Args:
            profile: UserPreferenceProfile from the profiler layer
            top_n: number of top results to return
            filters: dict of field -> value to hard-filter items (e.g. {"item_category": "Food"})
            exclude_platform: if set, exclude all items from this platform (cross-domain testing)

        Returns:
            list of ranked item dicts with score, match_reason, and filters_relaxed flag
        """
        filters = filters or {}
        filters_relaxed = False

        # ── Progressive filter relaxation ─────────────────────────────────
        # Try 1: Full filters + exclusions
        candidate_indices = self._get_candidates(filters, exclude_platform)

        if not candidate_indices and (filters or exclude_platform):
            # Try 2: Drop item_category filter but keep exclusions
            relaxed_filters = {k: v for k, v in filters.items() if k != "item_category"}
            candidate_indices = self._get_candidates(relaxed_filters, exclude_platform)
            if candidate_indices:
                filters_relaxed = True

        if not candidate_indices and exclude_platform:
            # Try 3: Drop all filters AND exclusions
            candidate_indices = self._get_candidates({}, None)
            if candidate_indices:
                filters_relaxed = True

        if not candidate_indices:
            # Try 4: Absolute fallback — entire catalogue
            candidate_indices = list(range(len(self.catalogue)))
            filters_relaxed = True

        candidate_indices = np.array(candidate_indices)
        candidate_embeddings = self.item_embeddings[candidate_indices]
        candidate_rating_norm = self._rating_norm[candidate_indices]
        candidate_count_norm = self._count_norm[candidate_indices]

        # Semantic similarity
        pref_emb = profile.preference_embedding
        if pref_emb is None:
            pref_emb = np.zeros(self.item_embeddings.shape[1], dtype="float32")
        semantic_scores = self._cosine_sim(pref_emb, candidate_embeddings)

        # Category match
        category_scores = np.array([
            1.0 if self.catalogue[i]["item_category"] in profile.preferred_categories else 0.0
            for i in candidate_indices
        ])

        # Keyword overlap (liked)
        keyword_scores = np.array([
            self._jaccard(self.catalogue[i]["top_keywords"], profile.liked_keywords)
            for i in candidate_indices
        ])

        # Dislike penalty
        dislike_penalty = np.array([
            self._jaccard(self.catalogue[i]["top_keywords"], profile.disliked_keywords)
            for i in candidate_indices
        ])

        # Nigerian user boost
        nigerian_boost = np.zeros(len(candidate_indices), dtype="float32")
        if profile.is_nigerian_user:
            boost_keywords = {"value", "affordable", "popular", "budget", "cheap"}
            for j, i in enumerate(candidate_indices):
                item_kws = set(self.catalogue[i]["top_keywords"])
                if item_kws & boost_keywords:
                    nigerian_boost[j] = 0.05

        # Final score
        scores = (
            0.40 * semantic_scores
            + 0.25 * category_scores
            + 0.20 * keyword_scores
            + 0.10 * candidate_rating_norm
            + 0.05 * candidate_count_norm
            - 0.30 * dislike_penalty
            + nigerian_boost
        )

        # Sort descending
        sorted_local = np.argsort(scores)[::-1][:top_n]

        results = []
        for rank, local_idx in enumerate(sorted_local, 1):
            global_idx = candidate_indices[local_idx]
            item = self.catalogue[global_idx]

            components = {
                "semantic_similarity": float(semantic_scores[local_idx]),
                "category_match": float(category_scores[local_idx]),
                "keyword_overlap": float(keyword_scores[local_idx]),
            }

            results.append({
                "rank": rank,
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "platform": item["platform"],
                "item_category": item["item_category"],
                "item_metadata": item["item_metadata"],
                "avg_rating": item["avg_rating"],
                "review_count": item["review_count"],
                "top_keywords": item["top_keywords"],
                "score": round(float(scores[local_idx]), 4),
                "match_reason": self._build_match_reason(item, components),
                "filters_relaxed": filters_relaxed,
            })

        return results
