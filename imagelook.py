# Standard library
import os
import time
import uuid
import json
import hashlib
from io import BytesIO
from urllib.parse import urlparse

# Third-party libraries
import requests
from PIL import Image
from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException

def load_classes_from_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_trusted_domains(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ Trusted domain file not found: {path}")
        return []

def compute_image_hash(content_bytes):
    return hashlib.md5(content_bytes).hexdigest()

def collect_hashes_from_directory(directory):
    hashes = set()
    for root, _, files in os.walk(directory):
        for file in files:
            path = os.path.join(root, file)
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                    hashes.add(compute_image_hash(content))
            except Exception as e:
                print(f"⚠️ Could not read {path}: {e}")
    return hashes

def search_and_save_images(terms, class_name, version, count=5, mode="train", base_path="../Training", trusted_domains=None):
    assert mode in ("train", "validation"), "Mode must be 'train' or 'validation'"

    # Define paths
    output_folder = os.path.join(base_path, version, f"{mode}_data", class_name)
    compare_folder = os.path.join(base_path, version, "train_data", class_name)

    os.makedirs(output_folder, exist_ok=True)

    # Collect hashes from train_data to avoid duplicates
    train_hashes = collect_hashes_from_directory(compare_folder)

    with DDGS() as ddgs:
        for term in terms:
            print(f"\n🔍 Searching images for: {term}")
            retries = 0
            while retries < 3:
                try:
                    results = ddgs.images(term, max_results=count * 2)
                    break
                except RatelimitException:
                    print(f"⚠️ Rate limit hit. Retry {retries+1}/3. Waiting 10 seconds...")
                    time.sleep(10)
                    retries += 1
            else:
                print(f"❌ Failed to fetch results for '{term}' due to rate limit.")
                continue

            saved = 0
            for result in results:
                if saved >= count:
                    break

                url = result["image"]
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code != 200:
                        continue

                    content = response.content
                    hash_now = compute_image_hash(content)

                    if hash_now in train_hashes:
                        print(f"❌ Duplicate found in train_data: {url}")
                        continue

                    image = Image.open(BytesIO(content))
                    image_format = image.format.upper()
                    if image_format not in ("JPEG", "JPG", "PNG", "WEBP"):
                        print(f"[X] Unsupported format: {image_format}")
                        continue

                    if image.width < 50 or image.height < 50:
                        print(f"[X] Image too small: {image.width}x{image.height}")
                        continue

                    size_mb = len(content) / (1024 * 1024)
                    if size_mb > 5:
                        print(f"[X] Image too large: {size_mb:.2f}MB")
                        continue

                    domain = urlparse(url).netloc.lower()
                    if trusted_domains and not any(d in domain for d in trusted_domains):
                        print(f"[X] Untrusted domain: {domain}")
                        continue

                    extension = image_format.lower()
                    filename = f"{class_name.replace(" ","_")}_{uuid.uuid4().hex}.{extension}"
                    with open(os.path.join(output_folder, filename), "wb") as f:
                        f.write(content)

                    print(f"  ✅ Saved: {filename}")
                    saved += 1

                except Exception as e:
                    print(f"  ⚠️ Error with {url}: {e}")

            print("⏳ Waiting before the next search...\n")
            time.sleep(1)

if __name__ == "__main__":
    try:
        base_path = "../Training"
        version = "v3"
        count = 1
        mode = "validation" # train or "validation"
        trusted_domains = load_trusted_domains(os.path.join(base_path, version, "trusted_domains.txt"))
        classes = load_classes_from_json(os.path.join(base_path, version, "classes_test.json"))

        for entry in classes:
            class_name = entry["class"]["name"]
            terms = entry["class"]["terms_to_seek"]
            
            print(f"\n🔽 Processing class: {class_name}")
            search_and_save_images(
                terms=terms,
                class_name=class_name,
                version=version,
                count=count,
                mode=mode,
                base_path=base_path,
                # trusted_domains=trusted_domains
            )

    except KeyboardInterrupt:
        print("\n⛔ Interrupted by user. Exiting cleanly.")
