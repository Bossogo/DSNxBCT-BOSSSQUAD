import os
import json
from collections import Counter

def diagnose():
    print("Loading metadata...")
    with open("data/metadata.json", "r") as f:
        metadata = json.load(f)

    print("Loading catalogue...")
    with open("data/catalogue.json", "r") as f:
        catalogue = json.load(f)
    catalogue_ids = {item["item_id"] for item in catalogue}

    # Group by user for Amazon
    amazon_users = {}
    for r in metadata:
        if r["platform"] == "amazon":
            uid = r["composite_user_id"]
            if uid not in amazon_users:
                amazon_users[uid] = []
            amazon_users[uid].append(r)

    eval_users = [uid for uid, recs in amazon_users.items() if len(recs) >= 3]
    print(f"Found {len(eval_users)} Amazon users with >= 3 reviews.")

    # Check if their last items are in the catalogue
    from data.build_catalogue import slugify
    hits_possible = 0
    for uid in eval_users:
        last_rec = amazon_users[uid][-1]
        target_id = slugify(f"amazon_{last_rec.get('item_name')}")
        if target_id in catalogue_ids:
            hits_possible += 1
        else:
            print(f"Missing from catalogue: {target_id}")

    print(f"Out of {len(eval_users)} eval users, {hits_possible} have target items in the catalogue.")

if __name__ == "__main__":
    diagnose()
