"""
Prepare local fallback files for ingestion.

Outputs:
  - data/raw/amazon_reviews.jsonl
  - data/raw/goodreads_reviews.jsonl
"""

import argparse
import gzip
import json
import os
import shutil
import urllib.request

RAW_DIR = os.path.join(os.path.dirname(__file__), "raw")
AMAZON_2023_REVIEW_URL_TEMPLATE = (
    "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/"
    "raw/review_categories/{category}.jsonl.gz"
)
DEFAULT_AMAZON_OUTPUT = os.path.join(RAW_DIR, "amazon_reviews.jsonl")
DEFAULT_GOODREADS_OUTPUT = os.path.join(RAW_DIR, "goodreads_reviews.jsonl")


def ensure_raw_dir():
    os.makedirs(RAW_DIR, exist_ok=True)


def _is_url(value):
    return value.startswith("http://") or value.startswith("https://")


def _open_gzip_stream(path_or_url):
    if _is_url(path_or_url):
        response = urllib.request.urlopen(path_or_url)
        return gzip.GzipFile(fileobj=response), response
    return gzip.open(path_or_url, "rb"), None


def download_amazon_gz_to_jsonl(category, output_path):
    gz_url = AMAZON_2023_REVIEW_URL_TEMPLATE.format(category=category)
    print(f"Downloading Amazon category '{category}' from: {gz_url}")
    count = 0
    stream = None
    response = None
    try:
        stream, response = _open_gzip_stream(gz_url)
        with stream, open(output_path, "w", encoding="utf-8") as out_f:
            for raw_line in stream:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                out_f.write(line + "\n")
                count += 1
    finally:
        if response is not None:
            response.close()

    print(f"Saved Amazon fallback file: {output_path} ({count} rows)")


def convert_goodreads_gz_to_jsonl(gz_source, output_path):
    print(f"Converting Goodreads gzip source to JSONL: {gz_source}")
    count = 0
    stream = None
    response = None
    try:
        stream, response = _open_gzip_stream(gz_source)
        with stream, open(output_path, "w", encoding="utf-8") as out_f:
            for raw_line in stream:
                line = raw_line.decode("utf-8").strip()
                if not line:
                    continue
                obj = json.loads(line)
                out_f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                count += 1
    finally:
        if response is not None:
            response.close()

    print(f"Saved Goodreads fallback file: {output_path} ({count} rows)")


def copy_goodreads_jsonl(jsonl_source, output_path):
    if not os.path.exists(jsonl_source):
        raise FileNotFoundError(f"Goodreads JSONL source not found: {jsonl_source}")
    shutil.copyfile(jsonl_source, output_path)
    print(f"Copied Goodreads fallback file: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-amazon",
        action="store_true",
        help="Skip Amazon fallback file download.",
    )
    parser.add_argument(
        "--amazon-category",
        type=str,
        default="All_Beauty",
        help="Amazon 2023 category name (e.g., All_Beauty, Books, Electronics).",
    )
    parser.add_argument(
        "--amazon-output",
        type=str,
        default=DEFAULT_AMAZON_OUTPUT,
        help="Output path for Amazon jsonl fallback file.",
    )
    parser.add_argument(
        "--goodreads-gz",
        type=str,
        default=None,
        help="Path or URL to Goodreads .json.gz source (line-delimited JSON inside gzip).",
    )
    parser.add_argument(
        "--goodreads-jsonl",
        type=str,
        default=None,
        help="Path to existing Goodreads .jsonl file to copy as fallback.",
    )
    parser.add_argument(
        "--goodreads-output",
        type=str,
        default=DEFAULT_GOODREADS_OUTPUT,
        help="Output path for Goodreads jsonl fallback file.",
    )
    args = parser.parse_args()

    ensure_raw_dir()

    if not args.skip_amazon:
        download_amazon_gz_to_jsonl(
            category=args.amazon_category,
            output_path=args.amazon_output,
        )
    else:
        print("Skipping Amazon download.")

    if args.goodreads_jsonl:
        copy_goodreads_jsonl(args.goodreads_jsonl, args.goodreads_output)
    elif args.goodreads_gz:
        convert_goodreads_gz_to_jsonl(args.goodreads_gz, args.goodreads_output)
    else:
        print(
            "Goodreads fallback not prepared. Provide --goodreads-gz or "
            "--goodreads-jsonl if you want local Goodreads ingestion."
        )

    print("Raw data preparation complete.")


if __name__ == "__main__":
    main()
