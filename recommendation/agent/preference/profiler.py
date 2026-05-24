"""
Layer 2: Preference + Cold-Start Profiler
Produces a unified UserPreferenceProfile for known and new users alike.
"""

import os
import json
import re
import numpy as np
from dataclasses import dataclass, field
from collections import Counter
from typing import Optional
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"
METADATA_PATH = os.path.join(os.path.dirname(__file__), "../data/metadata.json")

ONBOARDING_QUESTIONS = [
    "What type of items are you most interested in getting recommendations for? "
    "(e.g. restaurants and food, products, books, or a mix)",

    "How would you describe your budget preference? "
    "(e.g. budget-friendly, mid-range, or premium)",

    "What are two or three things you absolutely love or always look for "
    "when choosing something?",

    "Is there anything you strongly dislike or always try to avoid?",

    "Tell me about something you recently enjoyed — could be a meal, "
    "a product, a book, anything.",
]
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class UserPreferenceProfile:
    user_id: Optional[str]
    is_cold_start: bool
    preferred_categories: list = field(default_factory=list)
    preferred_platforms: list = field(default_factory=list)
    avg_rating_given: float = 3.5
    rating_strictness: str = "moderate"    # "lenient" | "moderate" | "strict"
    liked_keywords: list = field(default_factory=list)
    disliked_keywords: list = field(default_factory=list)
    preference_embedding: Optional[np.ndarray] = None
    is_nigerian_user: bool = False


class Profiler:
    def __init__(self):
        self.model = SentenceTransformer(EMBED_MODEL)
        with open(METADATA_PATH, "r") as f:
            self.metadata = json.load(f)

        # Build lookup: composite_user_id -> list of records
        self.user_map = {}
        for record in self.metadata:
            uid = record["composite_user_id"]
            if uid not in self.user_map:
                self.user_map[uid] = []
            self.user_map[uid].append(record)

    def is_known_user(self, composite_user_id: str) -> bool:
        return composite_user_id in self.user_map

    def _extract_keywords(self, texts, max_features=10):
        if not texts:
            return []
        
        # Strip punctuation and clean text
        cleaned_texts = [re.sub(r"[^\w\s]", " ", t).lower() for t in texts]
        
        if len(texts) < 2:
            # Simple fallback for sparse data
            all_words = " ".join(cleaned_texts).split()
            stopwords = {
                "the", "a", "and", "is", "it", "i", "was", "to",
                "of", "in", "this", "for", "that", "my", "with", "very",
                "what", "type", "would", "describe", "preference", "things",
                "love", "enjoyed", "recently", "always", "strongly", "dislike",
                "avoid", "look", "getting", "interested", "about", "could", "meal",
                "product", "book", "anything", "most", "some", "someone", "something"
            }
            filtered = [w for w in all_words if w not in stopwords and len(w) > 3]
            return [w for w, _ in Counter(filtered).most_common(max_features)]
        
        try:
            tfidf = TfidfVectorizer(
                max_features=max_features,
                stop_words="english",
                ngram_range=(1, 2),
            )
            tfidf.fit(cleaned_texts)
            return list(tfidf.get_feature_names_out())
        except Exception:
            # Fallback if TF-IDF vectorizer errors out
            all_words = " ".join(cleaned_texts).split()
            stopwords = {"the", "a", "and", "is", "it", "i", "was", "to", "of", "in"}
            filtered = [w for w in all_words if w not in stopwords and len(w) > 3]
            return [w for w, _ in Counter(filtered).most_common(max_features)]

    def build_known_user_profile(
        self,
        composite_user_id: str,
        nigerian_context: bool = False,
    ) -> UserPreferenceProfile:
        records = self.user_map[composite_user_id]

        ratings = [r["rating"] for r in records]
        categories = [r.get("item_category", "") for r in records]
        platforms = [r.get("platform", "") for r in records]

        avg_rating = float(np.mean(ratings))

        if avg_rating > 3.8:
            strictness = "lenient"
        elif avg_rating < 2.8:
            strictness = "strict"
        else:
            strictness = "moderate"

        # Keywords from liked vs disliked reviews
        liked_texts = [r["review_text"] for r in records if r["rating"] >= 4]
        disliked_texts = [r["review_text"] for r in records if r["rating"] <= 2]

        liked_keywords = self._extract_keywords(liked_texts)
        disliked_keywords = self._extract_keywords(disliked_texts)

        # Preference embedding: mean of embeddings from highly rated reviews
        if liked_texts:
            liked_embeddings = self.model.encode(liked_texts[:20]).astype("float32")
            preference_embedding = np.mean(liked_embeddings, axis=0)
        else:
            all_texts = [r["review_text"] for r in records if r.get("review_text")]
            if all_texts:
                preference_embedding = np.mean(
                    self.model.encode(all_texts[:20]).astype("float32"), axis=0
                )
            else:
                preference_embedding = np.zeros(384, dtype="float32")

        # Preferred categories and platforms by frequency
        preferred_categories = [
            cat for cat, _ in Counter(categories).most_common(5) if cat
        ]
        preferred_platforms = [
            p for p, _ in Counter(platforms).most_common(3) if p
        ]

        return UserPreferenceProfile(
            user_id=composite_user_id,
            is_cold_start=False,
            preferred_categories=preferred_categories,
            preferred_platforms=preferred_platforms,
            avg_rating_given=round(avg_rating, 2),
            rating_strictness=strictness,
            liked_keywords=liked_keywords,
            disliked_keywords=disliked_keywords,
            preference_embedding=preference_embedding,
            is_nigerian_user=nigerian_context,
        )

    def build_cold_start_profile(
        self,
        onboarding_answers: dict,
        nigerian_context: bool = False,
    ) -> UserPreferenceProfile:
        """
        Build a synthetic profile from 5 onboarding question answers.
        onboarding_answers: {1: str, 2: str, 3: str, 4: str, 5: str}
        """
        q1 = onboarding_answers.get(1, "").lower()
        q2 = onboarding_answers.get(2, "").lower()
        q3 = onboarding_answers.get(3, "")
        q4 = onboarding_answers.get(4, "")
        q5 = onboarding_answers.get(5, "")

        # Q1 -> preferred_categories and preferred_platforms
        category_map = {
            "food": ("Food", "yelp"),
            "restaurant": ("Food", "yelp"),
            "product": ("Product", "amazon"),
            "book": ("Book", "goodreads"),
        }
        preferred_categories = []
        preferred_platforms = []
        for keyword, (cat, plat) in category_map.items():
            if keyword in q1:
                preferred_categories.append(cat)
                preferred_platforms.append(plat)

        if "mix" in q1 or not preferred_categories:
            preferred_categories = ["Food", "Product", "Book"]
            preferred_platforms = ["yelp", "amazon", "goodreads"]

        # Q2 -> avg_rating_given
        if "budget" in q2:
            avg_rating = 3.0
            strictness = "strict"
        elif "premium" in q2 or "high" in q2:
            avg_rating = 4.5
            strictness = "lenient"
        else:
            avg_rating = 3.5
            strictness = "moderate"

        # Q3 -> liked_keywords
        liked_keywords = self._extract_keywords([q3], max_features=5) if q3 else []

        # Q4 -> disliked_keywords
        disliked_keywords = self._extract_keywords([q4], max_features=5) if q4 else []

        # Q5 -> preference_embedding
        if q5.strip():
            preference_embedding = self.model.encode([q5]).astype("float32")[0]
        else:
            preference_embedding = np.zeros(384, dtype="float32")

        return UserPreferenceProfile(
            user_id=None,
            is_cold_start=True,
            preferred_categories=preferred_categories,
            preferred_platforms=preferred_platforms,
            avg_rating_given=avg_rating,
            rating_strictness=strictness,
            liked_keywords=liked_keywords,
            disliked_keywords=disliked_keywords,
            preference_embedding=preference_embedding,
            is_nigerian_user=nigerian_context,
        )

    def get_onboarding_question(self, step: int) -> str:
        """Returns the onboarding question for a given step (1-indexed)."""
        if 1 <= step <= len(ONBOARDING_QUESTIONS):
            return ONBOARDING_QUESTIONS[step - 1]
        return ""
