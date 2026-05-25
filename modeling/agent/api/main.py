"""
FastAPI Application
Wraps the three layers into a clean REST API.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

class RetrievedReview(BaseModel):
    item_name: str
    item_category: str
    review_text: str
    rating: float
    platform: str
    item_metadata: Optional[dict] = {}
    user_name: Optional[str] = ""
    timestamp: Optional[str] = ""
    review_useful: Optional[int] = 0
    review_funny: Optional[int] = 0
    review_cool: Optional[int] = 0

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
    retrieved_reviews_used: list[RetrievedReview]
    user_profile: dict

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.api_route("/", methods=["GET", "HEAD"])
def root():
    return {"message": "User Modeling Agent is running. See /docs for API reference."}


@app.get("/platforms")
def get_platforms():
    """Returns list of available platforms."""
    return {"platforms": retriever.get_platforms()}


@app.get("/users")
def get_users(platform: str, page: int = 1, limit: int = 15, q: Optional[str] = None):
    """Returns users for a given platform sorted by review count with pagination and search."""
    skip = (page - 1) * limit
    users, total = retriever.get_users(platform=platform, skip=skip, limit=limit, query=q)
    return {
        "platform": platform,
        "users": users,
        "total": total,
        "page": page,
        "limit": limit
    }


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
        retrieved_reviews_used=retrieval_result["retrieved_reviews"],
        user_profile=retrieval_result["user_profile"],
    )
