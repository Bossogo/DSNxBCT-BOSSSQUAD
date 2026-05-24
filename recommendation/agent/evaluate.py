"""
Offline Evaluation Script — Task B: Recommendation Agent
Computes Hit@10 and NDCG@10 by holding out the last review of known users
on platforms with valid item names (e.g. Amazon) and scoring the remaining history.
"""

import os
import sys
import numpy as np
import math
from tqdm import tqdm

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preference.profiler import Profiler, UserPreferenceProfile
from ranking.ranker import Ranker

def compute_ndcg_at_k(rank: int) -> float:
    """Compute NDCG@K for a single target item when it is placed at rank (1-indexed)."""
    if 1 <= rank <= 10:
        return 1.0 / math.log2(rank + 1)
    return 0.0

def evaluate():
    print("Initializing evaluation...")
    profiler = Profiler()
    ranker = Ranker()

    print("Grouping user reviews for platforms with valid item names...")
    # Group reviews by composite_user_id for platforms other than Yelp
    valid_users = {}
    for uid, records in profiler.user_map.items():
        # Exclude Yelp since it contains only "Unknown Business"
        filtered_records = [r for r in records if r["platform"] != "yelp"]
        if len(filtered_records) >= 3:
            valid_users[uid] = filtered_records

    eval_users = list(valid_users.keys())
    print(f"Found {len(eval_users)} users with >= 3 reviews on valid platforms (e.g. Amazon).")

    if not eval_users:
        print("ERROR: No valid users found for evaluation.")
        return

    hits = 0
    ndcgs = 0.0
    total_eval = 0

    print(f"Running offline evaluation on all {len(eval_users)} valid users...")
    for uid in tqdm(eval_users):
        records = valid_users[uid]
        
        # Hold out the last review
        history_records = records[:-1]
        target_record = records[-1]
        
        # Get target item details
        target_platform = target_record["platform"]
        target_name = target_record.get("item_name", "Unknown")
        
        # Slugify to match item_id in catalogue
        from data.build_catalogue import slugify
        target_item_id = slugify(f"{target_platform}_{target_name}")

        # Temporarily override user records in profiler to build profile excluding the held-out review
        # Note: We keep Yelp records in history if the user has them, but exclude the held-out target
        original_records = profiler.user_map[uid]
        history_combined = [r for r in original_records if r != target_record]
        profiler.user_map[uid] = history_combined
        
        try:
            profile = profiler.build_known_user_profile(uid, nigerian_context=False)
            recs = ranker.rank(profile, top_n=10)
        finally:
            # Restore original records
            profiler.user_map[uid] = original_records

        # Find target item rank in recommendations
        rank = -1
        for r in recs:
            if r["item_id"] == target_item_id:
                rank = r["rank"]
                break
        
        if rank != -1:
            hits += 1
            ndcgs += compute_ndcg_at_k(rank)
        
        total_eval += 1

    hit_rate = hits / total_eval if total_eval > 0 else 0.0
    avg_ndcg = ndcgs / total_eval if total_eval > 0 else 0.0

    print("\n" + "="*50)
    print("EVALUATION RESULTS (NDCG@10 / Hit Rate)")
    print("="*50)
    print(f"Evaluated Users: {total_eval}")
    print(f"Hit Rate @ 10:   {hit_rate:.4f} ({hits}/{total_eval})")
    print(f"NDCG @ 10:       {avg_ndcg:.4f}")
    print("="*50)

if __name__ == "__main__":
    evaluate()
