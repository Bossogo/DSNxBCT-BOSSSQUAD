"""
FastAPI Application
Wraps the three layers into a clean REST API.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from retrieval.retriever import Retriever
from generation.generator import Generator

app = FastAPI(
    title="Task A: User Modeling Agent",
    description="Simulates user reviews for unseen items based on their review history.",
    version="1.0.0",
)

# Initialize layers once at startup
retriever = None
generator = None


@app.on_event("startup")
def startup():
    global retriever, generator
    retriever = Retriever()
    generator = Generator()


# ── Request/Response Models ───────────────────────────────────────────────────

class ItemInput(BaseModel):
    name: str
    category: str
    location: Optional[str] = ""
    price_range: Optional[str] = ""
    description: Optional[str] = ""

class SimulateRequest(BaseModel):
    platform: str
    user_id: str
    item: ItemInput
    nigerian_context: Optional[bool] = False

class SimulateResponse(BaseModel):
    composite_user_id: str
    simulated_review: str
    predicted_rating: float
    confidence: str
    retrieved_reviews_used: int
    user_profile: dict

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "User Modeling Agent is running. See /docs for API reference."}


@app.get("/platforms")
def get_platforms():
    """Returns list of available platforms."""
    return {"platforms": retriever.get_platforms()}


@app.get("/users")
def get_users(platform: str, limit: int = 50):
    """Returns users for a given platform sorted by review count."""
    users = retriever.get_users(platform=platform, limit=limit)
    if not users:
        raise HTTPException(
            status_code=404,
            detail=f"No users found for platform '{platform}'"
        )
    return {"platform": platform, "users": users}


@app.post("/simulate", response_model=SimulateResponse)
def simulate(request: SimulateRequest):
    """
    Simulate a user's review for a new item.

    Provide a platform, user_id, and item details.
    Returns a simulated review, predicted rating, and user profile.
    """
    try:
        retrieval_result = retriever.retrieve(
            platform=request.platform,
            user_id=request.user_id,
            item=request.item.dict(),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    try:
        generation_result = generator.generate(
            retrieval_result=retrieval_result,
            item=request.item.dict(),
            nigerian_context=request.nigerian_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

    return SimulateResponse(
        composite_user_id=retrieval_result["composite_user_id"],
        simulated_review=generation_result["simulated_review"],
        predicted_rating=generation_result["predicted_rating"],
        confidence=generation_result["confidence"],
        retrieved_reviews_used=len(retrieval_result["retrieved_reviews"]),
        user_profile=retrieval_result["user_profile"],
    )
