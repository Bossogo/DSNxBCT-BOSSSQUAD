import os
import shutil

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    task_a_data_dir = os.path.abspath(os.path.join(base_dir, "../../modeling/agent/data"))
    task_a_env_path = os.path.abspath(os.path.join(base_dir, "../../modeling/agent/.env"))

    # Define target directories
    dirs = [
        "data",
        "data/faiss_index",
        "preference",
        "ranking",
        "agent",
        "api"
    ]

    print("Creating directories...")
    for d in dirs:
        path = os.path.join(base_dir, d)
        os.makedirs(path, exist_ok=True)
        print(f"Created {path}")

    # Copy metadata.json
    src_meta = os.path.join(task_a_data_dir, "metadata.json")
    dst_meta = os.path.join(base_dir, "data/metadata.json")
    if os.path.exists(src_meta):
        print(f"Copying {src_meta} to {dst_meta}...")
        shutil.copy2(src_meta, dst_meta)
    else:
        print(f"WARNING: Source metadata.json not found at {src_meta}")

    # Copy reviews.index
    src_index = os.path.join(task_a_data_dir, "faiss_index/reviews.index")
    dst_index = os.path.join(base_dir, "data/faiss_index/reviews.index")
    if os.path.exists(src_index):
        print(f"Copying {src_index} to {dst_index}...")
        shutil.copy2(src_index, dst_index)
    else:
        print(f"WARNING: Source reviews.index not found at {src_index}")

    # Copy .env
    dst_env = os.path.join(base_dir, ".env")
    if os.path.exists(task_a_env_path):
        print(f"Copying {task_a_env_path} to {dst_env}...")
        shutil.copy2(task_a_env_path, dst_env)
    else:
        print(f"WARNING: Source .env not found at {task_a_env_path}")

    print("Setup completed successfully.")

if __name__ == "__main__":
    main()
