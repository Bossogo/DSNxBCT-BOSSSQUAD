"""
Layer 3: Generation Layer
Uses Groq LLM to simulate a user's review for a new item,
based on their retrieved history and behavioural profile.
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama3-70b-8192"
# ──────────────────────────────────────────────────────────────────────────────


class Generator:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set in environment.")
        self.client = Groq(api_key=api_key)

    def _build_system_prompt(self, nigerian_context=False):
        base = (
            "You are a user simulation agent. Your job is to impersonate a specific "
            "reviewer based on their past review history. You must match their tone, "
            "vocabulary, sentence length, rating strictness, and the aspects of items "
            "they typically care about. Do not break character. Do not add disclaimers. "
            "Write exactly as this user would write."
        )
        if nigerian_context:
            base += (
                " Where contextually appropriate, reflect Nigerian consumer preferences, "
                "colloquialisms, and cultural references in the review. For example, "
                "references to value for money, brand awareness in Nigerian markets, "
                "and locally relevant comparisons."
            )
        return base

    def _format_retrieved_reviews(self, reviews):
        lines = []
        for i, r in enumerate(reviews, 1):
            lines.append(
                f"Review {i} ({r['item_name']} | Rating: {r['rating']}/5):\n"
                f"{r['review_text']}\n"
            )
        return "\n".join(lines)

    def _build_user_prompt(self, retrieval_result, item):
        profile = retrieval_result["user_profile"]
        reviews_text = self._format_retrieved_reviews(
            retrieval_result["retrieved_reviews"]
        )

        item_metadata_str = ", ".join(
            f"{k}: {v}" for k, v in item.items()
            if k not in ("name", "category") and v
        )

        prompt = f"""You are simulating reviews for a user with the following behavioural profile:

PLATFORM: {retrieval_result['platform']}
USER ID: {retrieval_result['user_id']}
AVERAGE RATING: {profile['mean_rating']}/5
RATING CONSISTENCY: {profile['std_rating']} standard deviation (lower = more consistent)
TYPICAL REVIEW LENGTH: {profile['typical_review_length']}
COMMON THEMES THEY MENTION: {', '.join(profile['common_themes'])}
TOTAL PAST REVIEWS: {profile['total_reviews']}

Here are their {len(retrieval_result['retrieved_reviews'])} most relevant past reviews for context:

{reviews_text}
---

Now simulate this user's review for the following new item they have NOT reviewed:

ITEM NAME: {item.get('name', 'Unknown')}
ITEM CATEGORY: {item.get('category', 'Unknown')}
ITEM DETAILS: {item_metadata_str if item_metadata_str else 'No additional details'}

Respond in this exact JSON format:
{{
  "simulated_review": "...",
  "predicted_rating": <float between 1.0 and 5.0, one decimal place>,
  "confidence": "low" | "medium" | "high"
}}

Only return the JSON. No explanation. No preamble. No markdown fences.
"""
        return prompt

    def _parse_response(self, raw_text):
        """Parse LLM response into a dict, with fallback handling."""
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?|```", "", raw_text).strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract JSON object with regex
            match = re.search(r'\{.*\}', clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        # Hard fallback
        return {
            "simulated_review": raw_text.strip(),
            "predicted_rating": 3.0,
            "confidence": "low",
        }

    def generate(self, retrieval_result, item, nigerian_context=False):
        """
        Generate a simulated review for a new item using the user's history.

        Args:
            retrieval_result: dict from Retriever.retrieve()
            item: dict with new item details
            nigerian_context: bool - inject Nigerian cultural context

        Returns:
            dict with simulated_review, predicted_rating, confidence
        """
        system_prompt = self._build_system_prompt(nigerian_context)
        user_prompt = self._build_user_prompt(retrieval_result, item)

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=512,
        )

        raw_text = response.choices[0].message.content
        result = self._parse_response(raw_text)

        # Clamp rating to 1-5
        result["predicted_rating"] = round(
            max(1.0, min(5.0, float(result.get("predicted_rating", 3.0)))), 1
        )

        return result
