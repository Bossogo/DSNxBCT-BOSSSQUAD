"""
Layer 1: Data Ingestion and Indexing
Loads reviews from HuggingFace datasets, embeds them, and indexes into FAISS.
"""

import os
import json
import argparse
import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import faiss
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL = "all-MiniLM-L6-v2"
MIN_REVIEWS_PER_USER = 10
DEV_CAP = 50_000          # reviews per platform in dev mode
INDEX_DIR = os.path.join(os.path.dirname(__file__), "faiss_index")
METADATA_PATH = os.path.join(os.path.dirname(__file__), "metadata.json")
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "raw")
DEFAULT_AMAZON_PATH = os.path.join(RAW_DATA_DIR, "amazon_reviews.jsonl")
DEFAULT_GOODREADS_PATH = os.path.join(RAW_DATA_DIR, "goodreads_reviews.jsonl")
YELP_REVIEW_PATH = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_review.json")
YELP_BUSINESS_PATH = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_business.json")
YELP_USER_PATH = os.path.join(RAW_DATA_DIR, "yelp_academic_dataset_user.json")
# ──────────────────────────────────────────────────────────────────────────────


def normalize_rating(rating, platform):
    """Normalize all ratings to a 1-5 float scale."""
    try:
        if platform == "yelp":
            return float(rating)  # already 1-5
        if platform == "amazon":
            return float(rating)  # already 1-5
        if platform == "goodreads":
            # Goodreads uses 1-5 but sometimes 0; treat 0 as None and skip
            r = float(rating)
            return r if r >= 1 else None
        return float(rating)
    except (TypeError, ValueError):
        return None


def _load_yelp_business_lookup():
    """Load business data into a dict keyed by business_id."""
    print("  Loading Yelp business lookup...")
    lookup = {}
    with open(YELP_BUSINESS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            lookup[row["business_id"]] = {
                "name": row.get("name", "Unknown Business"),
                "address": row.get("address", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "categories": row.get("categories", "Business"),
                "stars": row.get("stars"),
                "review_count": row.get("review_count"),
            }
    print(f"  Loaded {len(lookup)} businesses.")
    return lookup


def _load_yelp_user_lookup():
    """Load user data into a dict keyed by user_id (excluding friends list)."""
    print("  Loading Yelp user lookup...")
    lookup = {}
    with open(YELP_USER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            lookup[row["user_id"]] = {
                "name": row.get("name", ""),
                "review_count": row.get("review_count", 0),
                "yelping_since": row.get("yelping_since", ""),
                "useful": row.get("useful", 0),
                "funny": row.get("funny", 0),
                "cool": row.get("cool", 0),
                "elite": row.get("elite", ""),
                "fans": row.get("fans", 0),
                "average_stars": row.get("average_stars", 0.0),
                "compliment_hot": row.get("compliment_hot", 0),
                "compliment_more": row.get("compliment_more", 0),
                "compliment_profile": row.get("compliment_profile", 0),
                "compliment_cute": row.get("compliment_cute", 0),
                "compliment_list": row.get("compliment_list", 0),
                "compliment_note": row.get("compliment_note", 0),
                "compliment_plain": row.get("compliment_plain", 0),
                "compliment_cool": row.get("compliment_cool", 0),
                "compliment_funny": row.get("compliment_funny", 0),
                "compliment_writer": row.get("compliment_writer", 0),
                "compliment_photos": row.get("compliment_photos", 0),
            }
    print(f"  Loaded {len(lookup)} users.")
    return lookup


def load_yelp(cap):
    print("Loading Yelp dataset from local raw files...")

    # Build lookup dicts first
    biz_lookup = _load_yelp_business_lookup()
    user_lookup = _load_yelp_user_lookup()

    records = []
    user_counter = defaultdict(int)
    skipped = 0

    print("  Streaming reviews and joining...")
    with open(YELP_REVIEW_PATH, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if cap and i >= cap:
                break
            row = json.loads(line)

            uid = row.get("user_id", "")
            bid = row.get("business_id", "")

            # Skip if we can't resolve both user and business
            user_info = user_lookup.get(uid)
            biz_info = biz_lookup.get(bid)
            if not user_info or not biz_info:
                skipped += 1
                continue

            review_text = (row.get("text") or "").strip()
            if not review_text:
                skipped += 1
                continue

            rating = normalize_rating(row.get("stars"), "yelp")
            if rating is None:
                skipped += 1
                continue

            records.append({
                "composite_user_id": f"yelp_{uid}",
                "platform": "yelp",
                "user_id": uid,
                "user_name": user_info["name"],
                "review_text": review_text,
                "rating": rating,
                "item_name": biz_info["name"],
                "item_category": biz_info["categories"] or "Business",
                "item_metadata": {
                    "business_id": bid,
                    "address": biz_info["address"],
                    "city": biz_info["city"],
                    "state": biz_info["state"],
                    "business_avg_stars": biz_info["stars"],
                    "business_review_count": biz_info["review_count"],
                },
                "user_metadata": {
                    "review_count": user_info["review_count"],
                    "yelping_since": user_info["yelping_since"],
                    "useful": user_info["useful"],
                    "funny": user_info["funny"],
                    "cool": user_info["cool"],
                    "elite": user_info["elite"],
                    "fans": user_info["fans"],
                    "average_stars": user_info["average_stars"],
                    "compliment_hot": user_info["compliment_hot"],
                    "compliment_more": user_info["compliment_more"],
                    "compliment_profile": user_info["compliment_profile"],
                    "compliment_cute": user_info["compliment_cute"],
                    "compliment_list": user_info["compliment_list"],
                    "compliment_note": user_info["compliment_note"],
                    "compliment_plain": user_info["compliment_plain"],
                    "compliment_cool": user_info["compliment_cool"],
                    "compliment_funny": user_info["compliment_funny"],
                    "compliment_writer": user_info["compliment_writer"],
                    "compliment_photos": user_info["compliment_photos"],
                },
                "timestamp": row.get("date", ""),
                "review_useful": row.get("useful", 0),
                "review_funny": row.get("funny", 0),
                "review_cool": row.get("cool", 0),
            })
            user_counter[uid] += 1

    # Free lookup dicts to reclaim memory
    del biz_lookup
    del user_lookup

    print(f"  Built {len(records)} records, skipped {skipped} unresolvable/empty reviews.")
    return records, user_counter


def _resolve_data_path(explicit_path, env_var_name, default_path):
    path = explicit_path or os.environ.get(env_var_name) or default_path
    return path


def _load_local_table(path, source_name):
    if not path:
        print(f"{source_name} local file path is empty. Skipping.")
        return []
    if not os.path.exists(path):
        print(f"{source_name} local file not found at '{path}'. Skipping.")
        return []

    print(f"Loading {source_name} from local file: {path}")
    ext = os.path.splitext(path.lower())[1]
    if ext == ".parquet":
        df = pd.read_parquet(path)
    elif ext in (".jsonl", ".jl"):
        df = pd.read_json(path, lines=True)
    elif ext == ".json":
        try:
            df = pd.read_json(path, lines=False)
        except ValueError:
            df = pd.read_json(path, lines=True)
    elif ext == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError(
            f"Unsupported {source_name} format '{ext}'. "
            "Use one of: .parquet, .jsonl, .json, .csv"
        )

    df = df.where(pd.notnull(df), None)
    rows = df.to_dict(orient="records")
    print(f"Loaded {len(rows)} rows from local {source_name} file.")
    return rows


def _pick_first(row, keys, default=""):
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def load_amazon(cap, amazon_path=None):
    print("Loading Amazon Reviews dataset...")
    rows = None
    try:
        ds = load_dataset(
            "McAuley-Lab/Amazon-Reviews-2023",
            "raw_review_All_Beauty",
            split="full",
        )
        rows = ds
        print("Loaded Amazon from HuggingFace.")
    except Exception as e:
        print(f"Amazon HuggingFace load failed: {e}")
        local_path = _resolve_data_path(
            explicit_path=amazon_path,
            env_var_name="AMAZON_REVIEWS_PATH",
            default_path=DEFAULT_AMAZON_PATH,
        )
        try:
            rows = _load_local_table(local_path, "Amazon reviews")
        except Exception as local_err:
            print(f"Amazon local load failed: {local_err}. Skipping.")
            return [], defaultdict(int)

    records = []
    user_counter = defaultdict(int)

    for i, row in enumerate(rows):
        if cap and i >= cap:
            break
        uid = str(_pick_first(row, ["user_id", "reviewerID"], f"amazon_user_{i}"))
        rating_raw = _pick_first(row, ["rating", "overall", "stars"], 3)
        rating = normalize_rating(rating_raw, "amazon")
        if rating is None:
            continue
        review_text = str(_pick_first(row, ["text", "reviewText", "review_body"], "")).strip()
        if not review_text:
            continue

        records.append({
            "composite_user_id": f"amazon_{uid}",
            "platform": "amazon",
            "user_id": uid,
            "review_text": review_text,
            "rating": rating,
            "item_name": _pick_first(
                row,
                ["title", "product_title", "item_name"],
                "Unknown Product",
            ),
            "item_category": "Beauty",
            "item_metadata": {
                "asin": _pick_first(row, ["asin", "parent_asin"], ""),
            },
            "timestamp": str(
                _pick_first(row, ["timestamp", "unixReviewTime", "reviewTime"], "")
            ),
        })
        user_counter[uid] += 1

    return records, user_counter


def load_goodreads(cap, goodreads_path=None):
    print("Loading Goodreads dataset...")
    rows = None
    try:
        ds = load_dataset("baharehahmadi/goodreads", split="train")
        rows = ds
        print("Loaded Goodreads from HuggingFace.")
    except Exception as e:
        print(f"Goodreads HuggingFace load failed: {e}")
        local_path = _resolve_data_path(
            explicit_path=goodreads_path,
            env_var_name="GOODREADS_REVIEWS_PATH",
            default_path=DEFAULT_GOODREADS_PATH,
        )
        try:
            rows = _load_local_table(local_path, "Goodreads reviews")
        except Exception as local_err:
            print(f"Goodreads local load failed: {local_err}. Skipping.")
            return [], defaultdict(int)

    records = []
    user_counter = defaultdict(int)

    for i, row in enumerate(rows):
        if cap and i >= cap:
            break
        uid = str(_pick_first(row, ["user_id", "user", "reviewer_id"], f"gr_user_{i}"))
        rating_raw = _pick_first(row, ["rating", "book_rating", "stars"], 0)
        rating = normalize_rating(rating_raw, "goodreads")
        if rating is None:
            continue
        review_text = str(_pick_first(row, ["review_text", "text", "review"], "")).strip()
        if not review_text:
            continue

        records.append({
            "composite_user_id": f"goodreads_{uid}",
            "platform": "goodreads",
            "user_id": uid,
            "review_text": review_text,
            "rating": rating,
            "item_name": _pick_first(row, ["book_title", "title", "book"], "Unknown Book"),
            "item_category": "Book",
            "item_metadata": {
                "author": _pick_first(row, ["author", "authors"], ""),
                "book_id": _pick_first(row, ["book_id"], ""),
                "isbn": _pick_first(row, ["isbn"], ""),
            },
            "timestamp": str(_pick_first(row, ["date_added", "timestamp", "review_time"], "")),
        })
        user_counter[uid] += 1

    return records, user_counter


def filter_quality_users(records, user_counter, min_reviews=MIN_REVIEWS_PER_USER):
    """Keep only records from users with enough review history."""
    quality_users = {uid for uid, count in user_counter.items() if count >= min_reviews}
    filtered = [r for r in records if r["user_id"] in quality_users]
    print(f"  Kept {len(filtered)} reviews from {len(quality_users)} quality users")
    return filtered


def build_embed_text(record):
    """Build the text string that will be embedded for a review."""
    parts = [
        record["review_text"],
        record["item_name"],
        record["item_category"],
    ]
    meta = record.get("item_metadata", {})
    parts += [str(v) for v in meta.values() if v]
    return " ".join(p for p in parts if p)


def embed_texts(texts, batch_size=64, num_processes=None, embed_chunk_size=5000):
    """
    Embed texts with sentence-transformers.
    Uses all available CPU cores by default via multiprocessing.
    """
    cpu_count = os.cpu_count() or 1
    if num_processes is None:
        num_processes = cpu_count
    num_processes = max(1, int(num_processes))

    model = SentenceTransformer(EMBED_MODEL)

    if num_processes == 1:
        try:
            torch.set_num_threads(cpu_count)
            torch.set_num_interop_threads(max(1, cpu_count // 2))
        except RuntimeError:
            pass
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
        )
        return np.array(embeddings).astype("float32")

    print(f"Using {num_processes} CPU processes for embedding...")
    pool = model.start_multi_process_pool(target_devices=["cpu"] * num_processes)
    try:
        total_texts = len(texts)
        chunk_size = max(1, int(embed_chunk_size))
        total_chunks = (total_texts + chunk_size - 1) // chunk_size
        embeddings_parts = []

        for chunk_index, start in enumerate(range(0, total_texts, chunk_size), 1):
            end = min(start + chunk_size, total_texts)
            print(
                f"Embedding chunk {chunk_index}/{total_chunks} "
                f"(rows {start + 1}-{end} of {total_texts})..."
            )
            chunk_embeddings = model.encode_multi_process(
                texts[start:end],
                pool,
                batch_size=batch_size,
            )
            embeddings_parts.append(np.array(chunk_embeddings, dtype="float32"))
            print(f"Finished chunk {chunk_index}/{total_chunks}")
    finally:
        model.stop_multi_process_pool(pool)

    return np.vstack(embeddings_parts).astype("float32")


def ingest(
    full=False,
    num_processes=None,
    batch_size=64,
    embed_chunk_size=5000,
    amazon_path=None,
    goodreads_path=None,
):
    cap = None if full else DEV_CAP

    # Load all platforms
    yelp_records, yelp_users = load_yelp(cap)
    # amazon_records, amazon_users = load_amazon(cap, amazon_path=amazon_path)
    # goodreads_records, goodreads_users = load_goodreads(cap, goodreads_path=goodreads_path)

    # Filter quality users per platform
    yelp_records = filter_quality_users(yelp_records, yelp_users)
    # amazon_records = filter_quality_users(amazon_records, amazon_users)
    # goodreads_records = filter_quality_users(goodreads_records, goodreads_users)

    all_records = yelp_records  # + amazon_records + goodreads_records
    print(f"\nTotal records to index: {len(all_records)}")

    if not all_records:
        print("No records to index. Exiting.")
        return

    # Embed all reviews
    print("\nEmbedding reviews (this may take a while)...")
    texts = [build_embed_text(r) for r in all_records]
    embeddings = embed_texts(
        texts=texts,
        batch_size=batch_size,
        num_processes=num_processes,
        embed_chunk_size=embed_chunk_size,
    )

    # Build FAISS index
    print("\nBuilding FAISS index...")
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    # Save index
    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(INDEX_DIR, "reviews.index"))
    print(f"FAISS index saved to {INDEX_DIR}/reviews.index")

    # Save metadata
    with open(METADATA_PATH, "w") as f:
        json.dump(all_records, f)
    print(f"Metadata saved to {METADATA_PATH}")
    print(f"\nIngestion complete. {len(all_records)} reviews indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Disable dev cap")
    parser.add_argument(
        "--num-processes",
        type=int,
        default=None,
        help="CPU processes for embedding (default: all available cores).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Embedding batch size per process.",
    )
    parser.add_argument(
        "--embed-chunk-size",
        type=int,
        default=5000,
        help="Chunk size for multiprocess embedding logs and batching.",
    )
    parser.add_argument(
        "--amazon-path",
        type=str,
        default=None,
        help="Path to local Amazon reviews file (.parquet/.jsonl/.json/.csv).",
    )
    parser.add_argument(
        "--goodreads-path",
        type=str,
        default=None,
        help="Path to local Goodreads reviews file (.parquet/.jsonl/.json/.csv).",
    )
    args = parser.parse_args()
    ingest(
        full=args.full,
        num_processes=args.num_processes,
        batch_size=args.batch_size,
        embed_chunk_size=args.embed_chunk_size,
        amazon_path=args.amazon_path,
        goodreads_path=args.goodreads_path,
    )
