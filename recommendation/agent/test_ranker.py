import os
import sys
import json
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from preference.profiler import Profiler
from ranking.ranker import Ranker
from data.build_catalogue import slugify

def test_ranker():
    profiler = Profiler()
    ranker = Ranker()

    valid_users = {}
    for uid, records in profiler.user_map.items():
        filtered = [r for r in records if r["platform"] != "yelp"]
        if len(filtered) >= 3:
            valid_users[uid] = filtered

    print(f"Found {len(valid_users)} valid users.")

    ranks_all = []
    ranks_liked = []

    for uid, records in valid_users.items():
        history = records[:-1]
        target = records[-1]
        target_id = slugify(f"{target['platform']}_{target.get('item_name')}")

        original_records = profiler.user_map[uid]
        history_combined = [r for r in original_records if r != target]
        profiler.user_map[uid] = history_combined

        try:
            profile = profiler.build_known_user_profile(uid)
            recs = ranker.rank(profile, top_n=2293)
        finally:
            profiler.user_map[uid] = original_records

        rank = -1
        for r in recs:
            if r["item_id"] == target_id:
                rank = r["rank"]
                break

        if rank != -1:
            ranks_all.append((uid, target["rating"], rank))
            if target["rating"] >= 4.0:
                ranks_liked.append((uid, target["rating"], rank))

    print("\n--- Ranks for all target items ---")
    for uid, rating, rank in ranks_all[:15]:
        print(f"User: {uid} | Target Rating: {rating} | Rank: {rank}")

    print(f"\nAverage rank for all target items: {np.mean([r[2] for r in ranks_all]):.1f}")
    if ranks_liked:
        print(f"Average rank for liked target items (rating >= 4): {np.mean([r[2] for r in ranks_liked]):.1f}")
        print(f"Number of liked targets: {len(ranks_liked)}")
        hits_liked = sum(1 for r in ranks_liked if r[2] <= 10)
        print(f"Hits@10 for liked targets: {hits_liked} / {len(ranks_liked)} ({hits_liked/len(ranks_liked):.4f})")
        hits_liked_top50 = sum(1 for r in ranks_liked if r[2] <= 50)
        print(f"Hits@50 for liked targets: {hits_liked_top50} / {len(ranks_liked)} ({hits_liked_top50/len(ranks_liked):.4f})")
    else:
        print("No liked target items found in test.")

if __name__ == "__main__":
    test_ranker()
