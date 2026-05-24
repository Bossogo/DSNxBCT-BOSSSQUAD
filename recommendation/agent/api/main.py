"""
FastAPI Application — Task B: Recommendation Agent
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from conversational_agent import ConversationalAgent
from preference.profiler import Profiler
from ranking.ranker import Ranker

app = FastAPI(
    title="Task B: Recommendation Agent",
    description=(
        "Personalised multi-turn recommendation agent with cold-start support. "
        "Covers Yelp, Amazon Reviews, and Goodreads."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = None
profiler = None
ranker = None
session_last_active = {}


@app.on_event("startup")
def startup():
    global agent, profiler, ranker
    agent = ConversationalAgent()
    profiler = agent.profiler
    ranker = agent.ranker


# ── Request / Response Models ─────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    user_id: Optional[str] = None
    platform: Optional[str] = None
    nigerian_context: Optional[bool] = False

class RecommendationItem(BaseModel):
    rank: int
    item_name: str
    platform: str
    item_category: str
    avg_rating: float
    match_reason: str
    item_id: Optional[str] = None
    review_count: Optional[int] = 0
    top_keywords: Optional[list[str]] = []
    item_metadata: Optional[dict] = {}

class StartSessionResponse(BaseModel):
    session_id: str
    is_cold_start: bool
    message: str
    recommendations: Optional[list[RecommendationItem]] = []
    onboarding_complete: bool = False

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    assistant_message: str
    recommendations: list[RecommendationItem]
    onboarding_complete: bool
    turn_number: int

class DirectRecommendRequest(BaseModel):
    user_id: str
    platform: Optional[str] = None
    top_n: Optional[int] = 10
    exclude_platform: Optional[str] = None
    filters: Optional[dict] = {}
    nigerian_context: Optional[bool] = False

# ── Session Cleanup ───────────────────────────────────────────────────────────

def expire_old_sessions():
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    expired = [
        sid for sid, last in session_last_active.items()
        if last < cutoff
    ]
    for sid in expired:
        agent.sessions.pop(sid, None)
        session_last_active.pop(sid, None)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "message": "Recommendation Agent is running. See /docs for API reference."
    }


@app.post("/session/start", response_model=StartSessionResponse)
def start_session(request: StartSessionRequest):
    """
    Start a new recommendation session.
    Pass user_id + platform for known users.
    Pass neither for cold-start (onboarding flow begins).
    """
    expire_old_sessions()

    state, first_message = agent.create_session(
        user_id=request.user_id,
        platform=request.platform,
        nigerian_context=request.nigerian_context or False,
    )

    session_last_active[state.session_id] = datetime.utcnow()

    recommendations = []
    if not state.is_cold_start:
        recommendations = [
            RecommendationItem(
                rank=r["rank"],
                item_name=r["item_name"],
                platform=r["platform"],
                item_category=r["item_category"],
                avg_rating=r["avg_rating"],
                match_reason=r["match_reason"],
                item_id=r.get("item_id"),
                review_count=r.get("review_count", 0),
                top_keywords=r.get("top_keywords", []),
                item_metadata=r.get("item_metadata", {}),
            )
            for r in state.current_recommendations
        ]

    return StartSessionResponse(
        session_id=state.session_id,
        is_cold_start=state.is_cold_start,
        message=first_message,
        recommendations=recommendations,
        onboarding_complete=state.onboarding_complete,
    )


@app.post("/session/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message in an active session.
    The agent responds with updated recommendations and a follow-up question.
    """
    if request.session_id not in agent.sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    session_last_active[request.session_id] = datetime.utcnow()

    try:
        state, response = agent.chat(request.session_id, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    recommendations = [
        RecommendationItem(
            rank=r["rank"],
            item_name=r["item_name"],
            platform=r["platform"],
            item_category=r["item_category"],
            avg_rating=r["avg_rating"],
            match_reason=r["match_reason"],
            item_id=r.get("item_id"),
            review_count=r.get("review_count", 0),
            top_keywords=r.get("top_keywords", []),
            item_metadata=r.get("item_metadata", {}),
        )
        for r in state.current_recommendations
    ]

    return ChatResponse(
        session_id=state.session_id,
        assistant_message=response,
        recommendations=recommendations,
        onboarding_complete=state.onboarding_complete,
        turn_number=state.turn_number,
    )


@app.get("/session/{session_id}/history")
def get_history(session_id: str):
    """Returns the full conversation history for a session."""
    if session_id not in agent.sessions:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    state = agent.sessions[session_id]
    return {
        "session_id": session_id,
        "turn_number": state.turn_number,
        "onboarding_complete": state.onboarding_complete,
        "conversation_history": state.conversation_history,
    }


@app.post("/recommend/direct")
def recommend_direct(request: DirectRecommendRequest):
    """
    Get recommendations directly without conversation (for evaluation / NDCG testing).
    Useful for offline evaluation: hold out last review and check Hit Rate / NDCG@10.
    """
    user_id = request.user_id
    platform = request.platform
    
    if not platform and "_" in user_id:
        platform = user_id.split("_")[0]
        
    composite_id = f"{platform}_{user_id}" if platform and not user_id.startswith(f"{platform}_") else user_id

    if not profiler.is_known_user(composite_id):
        raise HTTPException(
            status_code=404,
            detail=f"User '{composite_id}' not found. Use /session/start for cold-start users."
        )

    profile = profiler.build_known_user_profile(
        composite_id,
        nigerian_context=request.nigerian_context or False,
    )

    recommendations = ranker.rank(
        profile=profile,
        top_n=request.top_n or 10,
        filters=request.filters or {},
        exclude_platform=request.exclude_platform,
    )

    return {
        "user_id": composite_id,
        "top_n": request.top_n,
        "exclude_platform": request.exclude_platform,
        "filters": request.filters,
        "recommendations": recommendations,
        "user_profile": {
            "preferred_categories": profile.preferred_categories,
            "preferred_platforms": profile.preferred_platforms,
            "avg_rating_given": profile.avg_rating_given,
            "rating_strictness": profile.rating_strictness,
            "liked_keywords": profile.liked_keywords,
            "disliked_keywords": profile.disliked_keywords,
        },
    }
