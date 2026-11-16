"""
Download extra TRAINING-ONLY images for the fruit detector from the public
Fruits-360 dataset (https://github.com/fruits-360, license CC BY-SA 4.0).

Why: Dataset/Apple is mostly yellow/pale apples, so the detector thinks any
shiny RED apple is a tomato. This adds red apple varieties, more tomatoes,
dragon fruit (pitahaya) and an "other" class (mango, potato, pomegranate...).

Saved to Dataset/Extra/<class>/<variety>/*.jpg. train_fruit_detector.py uses
Dataset/Extra for training only; val/test stay on the real phone photos.

Usage:  .venv\\Scripts\\python.exe ml\\download_extra_data.py
"""

import json
import random
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "fruits-360/fruits-360-100x100"
BRANCH = "main"
OUT_DIR = Path(__file__).resolve().parent.parent / "Dataset" / "Extra"

# class -> (images per variety, [Fruits-360 Training folders])
PLAN = {
    "apple": (50, [
        "Apple Red 1", "Apple Red 2", "Apple Red 3", "Apple Red Delicious 1",
        "Apple Braeburn 1", "Apple Crimson Snow 1", "Apple Pink Lady 1",
        "Apple Red Yellow 1", "Apple Red Yellow 2", "Apple Golden 1",
    ]),
    "tomato": (50, [
        "Tomato 1", "Tomato 2", "Tomato 3", "Tomato 4", "Tomato 5",
        "Tomato Heart 1", "Tomato Maroon 1", "Tomato Maroon 2",
    ]),
    "dragonfruit": (40, ["Pitahaya Red 1", "Pitahaya red 2", "Pitahaya red 3"]),
    "other": (20, [
        "Mango 1", "Mango Red 1", "Potato Red 1", "Potato White 1", "Onion Red 1",
        "Pomegranate 1", "Peach 1", "Nectarine 1", "Plum 1", "Cherry 1",
        "Strawberry 1", "Orange 1", "Lemon 1", "Banana 1", "Guava 1", "Pear 1",
        "Pepper Red 1", "Beetroot 1", "Kiwi 1", "Kaki 1", "Papaya 1",
        "Eggplant 1", "Cucumber 1", "Lychee 1", "Quince 1",
    ]),
}


def get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "agrisense-trainer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def download(url, target):
    request = urllib.request.Request(url, headers={"User-Agent": "agrisense-trainer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        target.write_bytes(response.read())


def main():
    rng = random.Random(42)
    total = 0
    for class_name, (per_variety, folders) in PLAN.items():
        for folder in folders:
            target_dir = OUT_DIR / class_name / folder.replace(" ", "_")
            if target_dir.is_dir() and any(target_dir.iterdir()):
                print(f"skip (exists) {class_name}/{folder}")
                continue
            api = (f"https://api.github.com/repos/{REPO}/contents/Training/"
                   f"{urllib.parse.quote(folder)}?ref={BRANCH}")
            try:
                files = [f for f in get_json(api) if f["name"].lower().endswith(".jpg")]
            except Exception as error:
                print(f"FAILED to list {folder}: {error}")
                continue
            chosen = rng.sample(files, min(per_variety, len(files)))
            target_dir.mkdir(parents=True, exist_ok=True)
            for item in chosen:
                try:
                    download(item["download_url"], target_dir / item["name"])
                    total += 1
                except Exception as error:
                    print(f"  failed {item['name']}: {error}")
            print(f"{class_name:>11} <- {folder}: {len(chosen)}")
            time.sleep(0.5)

    (OUT_DIR / "SOURCE.txt").write_text(
        "Images from Fruits-360 (https://github.com/fruits-360), "
        "license CC BY-SA 4.0. Used for training only.\n")
    print(f"\nDownloaded {total} images into {OUT_DIR}")


if __name__ == "__main__":
    main()
