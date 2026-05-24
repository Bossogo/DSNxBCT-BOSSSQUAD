"""
Layer 4: Conversational Agent
Multi-turn Groq-powered agent that reasons before recommending.
Manages session state, onboarding, and recommendation refinement.
"""

import os
import uuid
import json
import re
from dataclasses import dataclass, field
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient
import numpy as np
from datetime import datetime

from preference.profiler import Profiler, UserPreferenceProfile, ONBOARDING_QUESTIONS
from ranking.ranker import Ranker

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_ONBOARDING_STEPS = len(ONBOARDING_QUESTIONS)
# ──────────────────────────────────────────────────────────────────────────────


def serialize_profile(profile: Optional[UserPreferenceProfile]) -> Optional[dict]:
    if not profile:
        return None
    embedding = None
    if profile.preference_embedding is not None:
        embedding = profile.preference_embedding.tolist()
    return {
        "user_id": profile.user_id,
        "is_cold_start": profile.is_cold_start,
        "preferred_categories": profile.preferred_categories,
        "preferred_platforms": profile.preferred_platforms,
        "avg_rating_given": profile.avg_rating_given,
        "rating_strictness": profile.rating_strictness,
        "liked_keywords": profile.liked_keywords,
        "disliked_keywords": profile.disliked_keywords,
        "preference_embedding": embedding,
        "is_nigerian_user": profile.is_nigerian_user,
    }


def deserialize_profile(data: Optional[dict]) -> Optional[UserPreferenceProfile]:
    if not data:
        return None
    embedding = None
    if data.get("preference_embedding") is not None:
        embedding = np.array(data["preference_embedding"], dtype="float32")
    return UserPreferenceProfile(
        user_id=data["user_id"],
        is_cold_start=data["is_cold_start"],
        preferred_categories=data["preferred_categories"],
        preferred_platforms=data["preferred_platforms"],
        avg_rating_given=data["avg_rating_given"],
        rating_strictness=data["rating_strictness"],
        liked_keywords=data["liked_keywords"],
        disliked_keywords=data["disliked_keywords"],
        preference_embedding=embedding,
        is_nigerian_user=data.get("is_nigerian_user", False),
    )


def serialize_state(state: "ConversationState") -> dict:
    answers = {str(k): v for k, v in state.onboarding_answers.items()}
    return {
        "_id": state.session_id,
        "user_id": state.user_id,
        "platform": state.platform,
        "is_cold_start": state.is_cold_start,
        "onboarding_complete": state.onboarding_complete,
        "onboarding_answers": answers,
        "onboarding_step": state.onboarding_step,
        "preference_profile": serialize_profile(state.preference_profile),
        "current_recommendations": state.current_recommendations,
        "conversation_history": state.conversation_history,
        "filters": state.filters,
        "exclude_platform": state.exclude_platform,
        "nigerian_context": state.nigerian_context,
        "turn_number": state.turn_number,
        "updated_at": datetime.utcnow(),
    }


def deserialize_state(data: dict) -> "ConversationState":
    raw_answers = data.get("onboarding_answers", {})
    answers = {int(k): v for k, v in raw_answers.items()}
    
    return ConversationState(
        session_id=data["_id"],
        user_id=data["user_id"],
        platform=data["platform"],
        is_cold_start=data["is_cold_start"],
        onboarding_complete=data["onboarding_complete"],
        onboarding_answers=answers,
        onboarding_step=data["onboarding_step"],
        preference_profile=deserialize_profile(data["preference_profile"]),
        current_recommendations=data["current_recommendations"],
        conversation_history=data["conversation_history"],
        filters=data["filters"],
        exclude_platform=data["exclude_platform"],
        nigerian_context=data.get("nigerian_context", False),
        turn_number=data["turn_number"],
    )


class MongoSessionStore:
    def __init__(self, mongo_uri: str):
        print(f"Connecting to MongoDB for session storage...")
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        # Check connection
        self.client.server_info()
        self.db = self.client.get_default_database()
        self.collection = self.db["sessions"]
        # Create a TTL index to auto-delete documents after 30 minutes (1800 seconds)
        self.collection.create_index("updated_at", expireAfterSeconds=1800)
        print("Connected to MongoDB. Sessions TTL index enabled (30m).")

    def __getitem__(self, key: str) -> "ConversationState":
        doc = self.collection.find_one({"_id": key})
        if not doc:
            raise KeyError(key)
        return deserialize_state(doc)

    def __setitem__(self, key: str, value: "ConversationState"):
        doc = serialize_state(value)
        self.collection.replace_one({"_id": key}, doc, upsert=True)

    def __contains__(self, key: str) -> bool:
        return self.collection.count_documents({"_id": key}, limit=1) > 0

    def pop(self, key: str, default=None):
        doc = self.collection.find_one_and_delete({"_id": key})
        if not doc:
            return default
        return deserialize_state(doc)


@dataclass
class ConversationState:
    session_id: str
    user_id: Optional[str]
    platform: Optional[str]
    is_cold_start: bool
    onboarding_complete: bool
    onboarding_answers: dict = field(default_factory=dict)
    onboarding_step: int = 0              # 0 = not started, 1-5 = question index
    preference_profile: Optional[UserPreferenceProfile] = None
    current_recommendations: list = field(default_factory=list)
    conversation_history: list = field(default_factory=list)
    filters: dict = field(default_factory=dict)
    exclude_platform: Optional[str] = None
    nigerian_context: bool = False
    turn_number: int = 0


class ConversationalAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set.")
        self.client = Groq(api_key=api_key)
        self.profiler = Profiler()
        self.ranker = Ranker()
        
        # Try Mongo Session Storage, fallback to memory
        mongo_uri = os.environ.get("MONGO_URI")
        if mongo_uri:
            try:
                self.sessions = MongoSessionStore(mongo_uri)
            except Exception as e:
                print(f"WARNING: MongoDB connection failed: {e}. Falling back to in-memory session storage.")
                self.sessions = {}
        else:
            print("MONGO_URI not set. Using in-memory session storage.")
            self.sessions = {}

    # ── Session Management ────────────────────────────────────────────────────

    def create_session(
        self,
        user_id: Optional[str] = None,
        platform: Optional[str] = None,
        nigerian_context: bool = False,
    ) -> tuple[ConversationState, str]:
        """
        Start a new session. Returns (state, first_message).
        If user_id is None, starts onboarding flow.
        If user_id is known, loads profile and generates first recommendations.
        """
        session_id = str(uuid.uuid4())
        
        if user_id:
            if "_" in user_id:
                composite_id = user_id
                platform = user_id.split("_")[0]
            else:
                composite_id = f"{platform}_{user_id}" if platform else user_id
        else:
            composite_id = None

        is_cold_start = composite_id is None or not self.profiler.is_known_user(composite_id)

        state = ConversationState(
            session_id=session_id,
            user_id=composite_id,
            platform=platform,
            is_cold_start=is_cold_start,
            onboarding_complete=not is_cold_start,
            nigerian_context=nigerian_context,
        )

        if not is_cold_start:
            # Known user: build profile and get recommendations immediately
            state.preference_profile = self.profiler.build_known_user_profile(
                composite_id, nigerian_context=nigerian_context
            )
            state.current_recommendations = self.ranker.rank(
                state.preference_profile, top_n=10
            )
            first_message = self._generate_recommendation_message(state, is_first=True)
        else:
            # Cold-start: begin onboarding
            state.onboarding_step = 1
            first_message = (
                "Hi! I'd love to help you discover something great. "
                "Let me ask you a few quick questions to personalise your recommendations.\n\n"
                + ONBOARDING_QUESTIONS[0]
            )

        state.conversation_history.append(
            {"role": "assistant", "content": first_message}
        )
        self.sessions[session_id] = state
        return state, first_message

    # ── Main Chat Handler ─────────────────────────────────────────────────────

    def chat(self, session_id: str, user_message: str) -> tuple[ConversationState, str]:
        """
        Handle a user message. Returns (updated_state, assistant_response).
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session '{session_id}' not found.")

        state = self.sessions[session_id]
        state.turn_number += 1
        state.conversation_history.append({"role": "user", "content": user_message})

        if state.is_cold_start and not state.onboarding_complete:
            response = self._handle_onboarding(state, user_message)
        else:
            response = self._handle_recommendation_turn(state, user_message)

        state.conversation_history.append({"role": "assistant", "content": response})
        self.sessions[session_id] = state
        return state, response

    # ── Onboarding Handler ────────────────────────────────────────────────────

    def _handle_onboarding(self, state: ConversationState, user_message: str) -> str:
        # Store the answer for the current step
        state.onboarding_answers[state.onboarding_step] = user_message
        state.onboarding_step += 1

        if state.onboarding_step <= MAX_ONBOARDING_STEPS:
            # Ask the next question
            return ONBOARDING_QUESTIONS[state.onboarding_step - 1]
        else:
            # All questions answered: build profile and generate recommendations
            state.preference_profile = self.profiler.build_cold_start_profile(
                state.onboarding_answers,
                nigerian_context=state.nigerian_context,
            )
            state.onboarding_complete = True
            state.current_recommendations = self.ranker.rank(
                state.preference_profile, top_n=10
            )
            return self._generate_recommendation_message(state, is_first=True)

    # ── Recommendation Turn Handler ───────────────────────────────────────────

    def _handle_recommendation_turn(
        self, state: ConversationState, user_message: str
    ) -> str:
        # 1. Pre-parse filter updates from user message (fast rule-based updates)
        self._update_filters_from_message(state, user_message)

        # 2. Re-rank with updated filters
        state.current_recommendations = self.ranker.rank(
            state.preference_profile,
            top_n=10,
            filters=state.filters,
            exclude_platform=state.exclude_platform,
        )

        # 3. Call LLM to generate response (and potentially output fallback filter updates)
        response_text = self._generate_recommendation_message(state, is_first=False, user_message=user_message)
        return response_text

    def _update_filters_from_message(self, state: ConversationState, message: str):
        """Simple rule-based filter extraction from user message."""
        msg = message.lower()

        # Category filters
        if any(w in msg for w in ["book", "reading", "novel", "fiction"]):
            state.filters["item_category"] = "Book"
        elif any(w in msg for w in ["food", "restaurant", "eat", "meal", "drink", "shawarma"]):
            state.filters["item_category"] = "Food"
        elif any(w in msg for w in ["product", "buy", "purchase", "shop"]):
            state.filters["item_category"] = "Product"

        # Platform exclusions
        if "not yelp" in msg or "skip yelp" in msg:
            state.exclude_platform = "yelp"
        elif "not amazon" in msg or "skip amazon" in msg:
            state.exclude_platform = "amazon"
        elif "not goodreads" in msg or "skip goodreads" in msg:
            state.exclude_platform = "goodreads"

        # Clear filters if user asks to reset
        if any(w in msg for w in ["reset", "clear", "show everything", "all categories"]):
            state.filters = {}
            state.exclude_platform = None

    # ── LLM Message Generation ────────────────────────────────────────────────

    def _build_system_prompt(self, nigerian_context: bool) -> str:
        base = """You are an intelligent recommendation agent. You help users discover items
they will love based on their preferences and history.

IMPORTANT CATALOG CONTEXT:
The current recommendation catalog contains ONLY Beauty & Skincare products from Amazon.
There are NO Food/Restaurant items, NO Book items, and NO Yelp or Goodreads items available.
If the user asks for food, restaurants, books, or mentions Yelp/Goodreads:
- Acknowledge their interest warmly.
- Explain that your catalog currently focuses on Beauty & Skincare products.
- Offer to show them the best beauty/skincare products that match their other preferences (e.g., budget, quality, ingredients).
- NEVER pretend to have food/book/restaurant items. NEVER invent or hallucinate items from platforms that are not in the catalog.
- NEVER tell the user to "search online" or "check Yelp" — you are the recommendation assistant, not a search engine.

Before every response you must reason internally using this structure:

<reasoning>
1. What has the user expressed interest in or asked for in this turn?
2. How does this change or refine their preference profile?
3. Should I re-rank, filter, or expand the current recommendations?
4. What is the most helpful thing to say to this user right now?
If you detect the user wants to apply or change filters, include a <filter_update> tag here with a JSON object, e.g. <filter_update>{"item_category": "Book"}</filter_update>, <filter_update>{"exclude_platform": "yelp"}</filter_update>, or <filter_update>{"reset": true}</filter_update>.
</reasoning>

<response>
- A short natural language explanation of your recommendations.
- A numbered list of the 3-5 most relevant items for this turn (select these from the CURRENT TOP 10 RECOMMENDATIONS in the prompt).
- One follow-up question to refine further.
</response>

Rules:
- You MUST output the reasoning section inside <reasoning>...</reasoning> tags.
- You MUST output the response section inside <response>...</response> tags.
- Never show your internal reasoning to the user outside the <reasoning> tags.
- Always explain WHY you are recommending each item in one sentence.
- If the user asks to exclude something, acknowledge it and adjust.
- Keep responses concise and conversational.
- Only recommend items that actually exist in the CURRENT TOP 10 RECOMMENDATIONS list provided to you. Do not invent items.
- Format each recommendation as: [Rank]. Item Name (Platform) ★Rating — Reason
"""
        if nigerian_context:
            base += """
- Be aware of the Nigerian consumer context. Favour value for money.
  Use warm, conversational language appropriate to Nigerian users (e.g. friendly, welcoming tone, standard English with Nigerian warmth, references to things like 'value for money', etc.).
  Where relevant, draw comparisons to locally familiar experiences or equivalents.
"""
        return base

    def _format_recommendations_for_prompt(self, recommendations: list) -> tuple[str, bool]:
        if not recommendations:
            return "No recommendations available.", False
        filters_were_relaxed = any(r.get("filters_relaxed", False) for r in recommendations)
        lines = []
        for r in recommendations[:10]:
            lines.append(
                f"{r['rank']}. {r['item_name']} ({r['platform']}) "
                f"★{r['avg_rating']} — {r['match_reason']}"
            )
        return "\n".join(lines), filters_were_relaxed

    def _format_conversation_history(self, history: list) -> str:
        lines = []
        for turn in history[-8:]:    # last 8 turns to stay within context
            role = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{role}: {turn['content']}")
        return "\n".join(lines)

    def _generate_recommendation_message(
        self,
        state: ConversationState,
        is_first: bool = False,
        user_message: str = "",
    ) -> str:
        profile = state.preference_profile
        recommendations_text, filters_relaxed = self._format_recommendations_for_prompt(state.current_recommendations)

        # Build a system note if filters were relaxed due to catalog limitations
        catalog_note = ""
        if filters_relaxed:
            catalog_note = (
                "\n[SYSTEM NOTE: The user's requested category or platform is not available in the current catalog. "
                "The filters have been relaxed to show the best available Beauty & Skincare items instead. "
                "Explain this warmly to the user — let them know the catalog currently focuses on "
                "Beauty & Skincare products and show them the best matches from what is available. "
                "Do NOT apologize excessively or say 'no recommendations'. Present the available items positively.]\n"
            )

        user_prompt = f"""SESSION CONTEXT:
User ID: {state.user_id or "new user (cold-start)"}
Is cold-start: {state.is_cold_start}
Preferred categories: {', '.join(profile.preferred_categories) if profile.preferred_categories else 'not specified'}
Preferred platforms: {', '.join(profile.preferred_platforms) if profile.preferred_platforms else 'all'}
Likes: {', '.join(profile.liked_keywords) if profile.liked_keywords else 'not specified'}
Dislikes: {', '.join(profile.disliked_keywords) if profile.disliked_keywords else 'none'}
Active filters: {state.filters if state.filters else 'none'}
Excluded platform: {state.exclude_platform or 'none'}
{catalog_note}
CURRENT TOP 10 RECOMMENDATIONS (use these, do not invent items):
{recommendations_text}

CONVERSATION SO FAR:
{self._format_conversation_history(state.conversation_history)}

USER'S LATEST MESSAGE:
{user_message if user_message else '[Session start — give a warm opening with top recommendations]'}

{'This is the first set of recommendations. Give a warm, engaging intro.' if is_first else 'Refine your response based on what the user just said.'}

Highlight the most relevant 3-5 items. Ask one follow-up question to refine further.
"""

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": self._build_system_prompt(state.nigerian_context)},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=700,
        )

        full_output = response.choices[0].message.content.strip()

        # Parse filter updates from LLM reasoning block if present
        self._parse_filter_updates_from_llm(state, full_output)

        # Parse response block to return to user
        parsed_response = self._parse_llm_response(full_output)
        return parsed_response

    def _parse_filter_updates_from_llm(self, state: ConversationState, output: str):
        match_filter = re.search(r"<filter_update>(.*?)</filter_update>", output, re.DOTALL | re.IGNORECASE)
        if match_filter:
            try:
                updates = json.loads(match_filter.group(1).strip())
                if updates.get("reset"):
                    state.filters = {}
                    state.exclude_platform = None
                else:
                    if "item_category" in updates:
                        state.filters["item_category"] = updates["item_category"]
                    if "exclude_platform" in updates:
                        state.exclude_platform = updates["exclude_platform"]
                
                # Re-rank immediately if we updated filters from LLM response
                state.current_recommendations = self.ranker.rank(
                    state.preference_profile,
                    top_n=10,
                    filters=state.filters,
                    exclude_platform=state.exclude_platform,
                )
            except Exception:
                pass

    def _parse_llm_response(self, output: str) -> str:
        # Regex to match content inside <response>...</response>
        match = re.search(r"<response>(.*?)</response>", output, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Fallback if reasoning tags exist but response tag is malformed
        if "</reasoning>" in output:
            parts = output.split("</reasoning>")
            res = parts[-1].strip()
            res = re.sub(r"</?response>", "", res, flags=re.IGNORECASE).strip()
            return res

        # Fallback to output raw if no reasoning or response tags are matched
        return output
