<<<<<<< HEAD
"""
AgriSense AI - Fruit Detection Training (Apple / Dragon Fruit / Tomato [/ Other])

Trains the model that decides WHICH fruit is in the photo
(ml/models/fruit_detection_model.pth). The grade models are separate.

Expected layout (project root / Dataset):

    Dataset/
        Apple/<any grade folders>/*.jpg
        Tomatoes/<any grade folders>/*.jpg
        DragonFruit_Training/{train,val,test}/<grade folders>/*.jpg
        Other/**/*.jpg            (optional: non-fruit / unsupported images)

Why this script differs from the previous version:
  * The Apple/Tomato photos are 4000x3000 phone shots on floors/paper, while the
    Dragon Fruit images are 640x640 pre-augmented crops on white/pink backgrounds.
    The old model learned "photo style" instead of "fruit", so every real phone
    photo was called Dragon Fruit. To counter that we:
      - start from ImageNet-pretrained weights (general fruit/shape features),
      - use strong augmentation (random crops/aspect, blur, light colour jitter,
        random white-background-like erasing) so background/style is not a cue,
      - balance classes with a weighted sampler.
  * Apple/Tomato photos are split by capture session (same minute) so
    near-duplicate shots of the same fruit do not leak into val/test.
  * Big photos are shrunk once into ml/.cache so CPU training is practical.

Usage (from the project root):
    .venv\\Scripts\\python.exe ml\\train_fruit_detector.py
    .venv\\Scripts\\python.exe ml\\train_fruit_detector.py --epochs 12 --check-dir C:\\Users\\Atharv\\Downloads
"""

import argparse
import copy
import random
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms

ML_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ML_DIR.parent
DEFAULT_DATA_DIR = PROJECT_DIR / "Dataset"
DEFAULT_MODEL_PATH = ML_DIR / "models" / "fruit_detection_model.pth"
CACHE_DIR = ML_DIR / ".cache" / "fruit_detector"

IMAGE_SIZE = 224
CACHE_MAX_SIDE = 384
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

# Folder name in Dataset/ -> class name used by ml_engine.py
UNSPLIT_CLASS_FOLDERS = {
    "Apple": "apple",
    "Tomatoes": "tomato",
    "Tomato": "tomato",
    "Other": "other",
}
PRESPLIT_CLASS_FOLDERS = {
    "DragonFruit_Training": "dragonfruit",
}


# ============================================================
# METRICS (no scikit-learn needed)
# ============================================================

def confusion_matrix(labels, predictions, num_classes):
    matrix = [[0] * num_classes for _ in range(num_classes)]
    for actual, predicted in zip(labels, predictions):
        matrix[actual][predicted] += 1
    return matrix


def per_class_metrics(labels, predictions, num_classes):
    matrix = confusion_matrix(labels, predictions, num_classes)
    rows = []
    for i in range(num_classes):
        tp = matrix[i][i]
        actual = sum(matrix[i])
        predicted = sum(row[i] for row in matrix)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append((precision, recall, f1, actual))
    macro_f1 = sum(r[2] for r in rows) / num_classes
    return rows, macro_f1, matrix


# ============================================================
# DATA COLLECTION
# ============================================================

def list_images(folder):
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )


def session_key(path):
    """Group phone photos taken in the same minute (IMG_YYYYMMDD_HHMMSS)."""
    match = re.search(r"(\d{8})_(\d{4})\d{2}", path.stem)
    return match.group(1) + match.group(2) if match else path.stem


def group_split(paths, seed, val_frac=0.15, test_frac=0.15):
    groups = defaultdict(list)
    for path in paths:
        groups[(path.parent.name, session_key(path))].append(path)

    keys = sorted(groups)
    random.Random(seed).shuffle(keys)

    total = len(paths)
    split = {"train": [], "val": [], "test": []}
    for key in keys:
        if len(split["test"]) < total * test_frac:
            split["test"].extend(groups[key])
        elif len(split["val"]) < total * val_frac:
            split["val"].extend(groups[key])
        else:
            split["train"].extend(groups[key])
    return split


def collect_samples(data_dir, seed):
    """Return {split: [(path, class_name), ...]}."""
    samples = {"train": [], "val": [], "test": []}

    for folder_name, class_name in UNSPLIT_CLASS_FOLDERS.items():
        folder = data_dir / folder_name
        if not folder.is_dir():
            continue
        for split_name, paths in group_split(list_images(folder), seed).items():
            samples[split_name].extend((p, class_name) for p in paths)

    for folder_name, class_name in PRESPLIT_CLASS_FOLDERS.items():
        folder = data_dir / folder_name
        if not folder.is_dir():
            continue
        for split_name in samples:
            split_dir = folder / split_name
            if split_dir.is_dir():
                samples[split_name].extend(
                    (p, class_name) for p in list_images(split_dir)
                )

    # Dataset/Extra/<class>/**  -> training only (e.g. Fruits-360 images from
    # ml/download_extra_data.py). Val/test stay on real phone photos so the
    # scores reflect how the app behaves on farmer uploads.
    extra_dir = data_dir / "Extra"
    if extra_dir.is_dir():
        for class_dir in sorted(p for p in extra_dir.iterdir() if p.is_dir()):
            samples["train"].extend(
                (p, class_dir.name.lower()) for p in list_images(class_dir)
            )

    classes = sorted({c for split in samples.values() for _, c in split})
    required = {"apple", "dragonfruit", "tomato"}
    missing = required - set(classes)
    if missing:
        raise SystemExit(f"Missing classes in {data_dir}: {sorted(missing)}")
    return samples, classes


# ============================================================
# IMAGE CACHE (shrink 4000x3000 photos once)
# ============================================================

def load_image(path):
    image = Image.open(path)
    image.draft("RGB", (CACHE_MAX_SIDE * 2, CACHE_MAX_SIDE * 2))  # fast JPEG decode
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((CACHE_MAX_SIDE, CACHE_MAX_SIDE), Image.BICUBIC)
    return image


def cached_path(path, data_dir):
    relative = path.relative_to(data_dir)
    return (CACHE_DIR / relative).with_suffix(".jpg")


def build_cache(samples, data_dir):
    all_paths = [p for split in samples.values() for p, _ in split]
    todo = [p for p in all_paths if not cached_path(p, data_dir).exists()]
    if not todo:
        return
    print(f"\nShrinking {len(todo)} images into cache (one-time)...")
    for index, path in enumerate(todo, 1):
        target = cached_path(path, data_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        load_image(path).save(target, quality=92)
        if index % 200 == 0 or index == len(todo):
            print(f"  {index}/{len(todo)}")


class FruitDataset(Dataset):
    def __init__(self, items, classes, data_dir, transform):
        self.items = items
        self.class_to_idx = {c: i for i, c in enumerate(classes)}
        self.targets = [self.class_to_idx[c] for _, c in items]
        self.data_dir = data_dir
        self.transform = transform

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        path, class_name = self.items[index]
        image = Image.open(cached_path(path, self.data_dir)).convert("RGB")
        return self.transform(image), self.class_to_idx[class_name]


# ============================================================
# TRANSFORMS
# ============================================================

train_transform = transforms.Compose([
    transforms.RandomResizedCrop(
        IMAGE_SIZE, scale=(0.35, 1.0), ratio=(0.6, 1.66)
    ),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(25),
    # Keep hue shifts tiny: colour is what separates red tomato from pink
    # dragon fruit, so we must not teach the model to ignore it.
    transforms.ColorJitter(brightness=0.35, contrast=0.35, saturation=0.3, hue=0.02),
    transforms.RandomApply([transforms.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.3),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
    # Random blank patches so plain backgrounds stop being a class cue.
    transforms.RandomErasing(p=0.35, scale=(0.02, 0.2), value="random"),
])

# Must match IMAGE_TRANSFORM in ml_engine.py
eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(MEAN, STD),
])


=======
import copy
import time
from pathlib import Path
import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, WeightedRandomSampler
from sklearn.metrics import classification_report, confusion_matrix

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path(r"D:\data-set\Fruit_Detection_Training")
DRAGONFRUIT_DATA_DIR = Path(r"D:\data-set\DragonFruit_Training")
MODEL_PATH = Path(__file__).resolve().parent / "models" / "fruit_detection_model.pth"

IMAGE_SIZE = 224
BATCH_SIZE = 16
NUM_EPOCHS = 3
LEARNING_RATE = 0.0001

torch.set_num_threads(2)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 60)
print("AGRISENSE AI - FRUIT DETECTION TRAINING")
print("=" * 60)

print(f"Device: {DEVICE}")
print(f"Dataset: {DATA_DIR}")
print(f"Model will be saved to: {MODEL_PATH}")


# ============================================================
# DATA TRANSFORMS
# ============================================================

train_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(15),
    transforms.ColorJitter(
        brightness=0.2,
        contrast=0.2,
        saturation=0.2
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


val_test_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


class FruitDetectionDataset(torch.utils.data.Dataset):
    def __init__(self, split, transform):
        fruit_dataset = datasets.ImageFolder(
            DATA_DIR / split,
            transform=transform
        )
        dragonfruit_dataset = datasets.ImageFolder(
            DRAGONFRUIT_DATA_DIR / split,
            transform=transform
        )

        if fruit_dataset.classes != ["apple", "other", "tomato"]:
            raise ValueError(
                f"Unexpected fruit detector classes: {fruit_dataset.classes}"
            )
        if dragonfruit_dataset.classes != ["grade_a", "grade_b", "grade_c"]:
            raise ValueError(
                "Dragon Fruit data must contain grade_a, grade_b, and "
                f"grade_c folders; found {dragonfruit_dataset.classes}"
            )

        self.fruit_dataset = fruit_dataset
        self.dragonfruit_dataset = dragonfruit_dataset
        self.classes = ["apple", "dragonfruit", "other", "tomato"]
        self.class_to_idx = {
            class_name: index
            for index, class_name in enumerate(self.classes)
        }
        self.targets = [
            self.class_to_idx[fruit_dataset.classes[target]]
            for target in fruit_dataset.targets
        ] + [
            self.class_to_idx["dragonfruit"]
            for _ in dragonfruit_dataset.targets
        ]

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, index):
        if index < len(self.fruit_dataset):
            image, target = self.fruit_dataset[index]
            fruit_name = self.fruit_dataset.classes[target]
            return image, self.class_to_idx[fruit_name]

        image, _ = self.dragonfruit_dataset[
            index - len(self.fruit_dataset)
        ]
        return image, self.class_to_idx["dragonfruit"]


# ============================================================
# LOAD DATASETS
# ============================================================

train_dataset = FruitDetectionDataset("train", train_transform)
val_dataset = FruitDetectionDataset("val", val_test_transform)
test_dataset = FruitDetectionDataset("test", val_test_transform)


print("\nClasses:")
print(train_dataset.class_to_idx)

print("\nDataset sizes:")
print(f"Train: {len(train_dataset)}")
print(f"Validation: {len(val_dataset)}")
print(f"Test: {len(test_dataset)}")


# ============================================================
# DATALOADERS
# ============================================================

class_counts = torch.bincount(
    torch.tensor(train_dataset.targets),
    minlength=len(train_dataset.classes)
).float()
sample_weights = torch.tensor(
    [1.0 / class_counts[target] for target in train_dataset.targets],
    dtype=torch.double
)
train_sampler = WeightedRandomSampler(
    sample_weights,
    num_samples=len(train_dataset),
    replacement=True
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    sampler=train_sampler,
    num_workers=0
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0
)


>>>>>>> bf43a2d8074be319d22b9f9093bbf0fcfff833a6
# ============================================================
# MODEL
# ============================================================

<<<<<<< HEAD
def create_model(num_classes):
    try:
        weights = models.EfficientNet_B0_Weights.IMAGENET1K_V1
        model = models.efficientnet_b0(weights=weights)
        print("Loaded ImageNet-pretrained EfficientNet-B0.")
    except Exception as error:  # offline etc.
        print(f"WARNING: could not load pretrained weights ({error}). "
              "Training from scratch will be much less accurate.")
        model = models.efficientnet_b0(weights=None)

    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    return model


def set_backbone_trainable(model, trainable):
    for param in model.features.parameters():
        param.requires_grad = trainable
    if not trainable:
        return
    # Fine-tune only the later blocks; early blocks keep generic edge/colour
    # features, which also makes CPU training faster.
    for block in model.features[:4]:
        for param in block.parameters():
            param.requires_grad = False


# ============================================================
# TRAIN / EVAL
# ============================================================

def run_epoch(model, loader, criterion, device, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss, predictions, labels = 0.0, [], []

    with torch.set_grad_enabled(training):
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            outputs = model(images)
            loss = criterion(outputs, targets)
            if training:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * images.size(0)
            predictions.extend(outputs.argmax(1).cpu().tolist())
            labels.extend(targets.cpu().tolist())

    accuracy = sum(p == t for p, t in zip(predictions, labels)) / max(len(labels), 1)
    return total_loss / max(len(labels), 1), accuracy, predictions, labels


def report(name, predictions, labels, classes):
    rows, macro_f1, matrix = per_class_metrics(labels, predictions, len(classes))
    print(f"\n{name} RESULTS")
    print("-" * 60)
    print(f"{'class':>12} {'precision':>10} {'recall':>10} {'f1':>10} {'images':>8}")
    for class_name, (precision, recall, f1, support) in zip(classes, rows):
        print(f"{class_name:>12} {precision:>10.3f} {recall:>10.3f} {f1:>10.3f} {support:>8}")
    accuracy = sum(p == t for p, t in zip(predictions, labels)) / max(len(labels), 1)
    print(f"Accuracy {accuracy * 100:.1f}% | macro F1 {macro_f1:.3f}")
    print("Confusion matrix (rows=actual, cols=predicted):")
    print("          " + " ".join(f"{c[:10]:>10}" for c in classes))
    for class_name, row in zip(classes, matrix):
        print(f"{class_name[:10]:>10}" + " ".join(f"{v:>10}" for v in row))


def check_folder(model, classes, folder, device):
    """Predict on real-world photos (e.g. your Downloads) as a sanity check."""
    paths = [p for p in list_images(Path(folder)) if p.parent == Path(folder)]
    if not paths:
        return
    print(f"\nREAL-PHOTO CHECK: {folder}")
    print("-" * 60)
    model.eval()
    with torch.no_grad():
        for path in paths:
            try:
                image = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            except Exception:
                continue
            probs = torch.softmax(model(eval_transform(image).unsqueeze(0).to(device)), 1)[0]
            ranked = sorted(zip(classes, probs.tolist()), key=lambda x: -x[1])
            summary = ", ".join(f"{c}={p * 100:.1f}%" for c, p in ranked)
            print(f"{path.name[:40]:<40} -> {ranked[0][0]:<12} ({summary})")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--epochs", type=int, default=10,
                        help="Fine-tuning epochs after the head warm-up (default 10)")
    parser.add_argument("--warmup-epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=4,
                        help="Stop if val macro-F1 does not improve for N epochs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--check-dir", type=Path,
                        default=Path.home() / "Downloads",
                        help="Folder of real photos to sanity-check after training")
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(max(1, torch.get_num_threads()))

    print("=" * 60)
    print("AGRISENSE AI - FRUIT DETECTION TRAINING")
    print("=" * 60)
    print(f"Device:  {device}")
    print(f"Dataset: {args.data_dir}")
    print(f"Output:  {args.model_path}")

    samples, classes = collect_samples(args.data_dir, args.seed)
    print(f"\nClasses: {classes}")
    if "other" not in classes:
        print("NOTE: no Dataset/Other folder - non-fruit photos are rejected only "
              "by the confidence thresholds in ml_engine.py.")
    for split_name, items in samples.items():
        counts = Counter(c for _, c in items)
        print(f"{split_name:>5}: {len(items):5d}  " +
              ", ".join(f"{c}={counts.get(c, 0)}" for c in classes))

    build_cache(samples, args.data_dir)

    train_ds = FruitDataset(samples["train"], classes, args.data_dir, train_transform)
    val_ds = FruitDataset(samples["val"], classes, args.data_dir, eval_transform)
    test_ds = FruitDataset(samples["test"], classes, args.data_dir, eval_transform)

    # Balance classes, and inside each class balance real photos vs Extra
    # images so the downloaded studio shots do not drown the phone photos.
    extra_dir = args.data_dir / "Extra"
    def source(path):
        return "extra" if extra_dir in path.parents else "real"
    group_counts = Counter((c, source(p)) for p, c in samples["train"])
    sources_per_class = Counter(c for c, _ in group_counts)
    weights = [
        1.0 / (sources_per_class[c] * group_counts[(c, source(p))])
        for p, c in samples["train"]
    ]
    sampler = WeightedRandomSampler(weights, num_samples=len(train_ds), replacement=True)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                              num_workers=args.workers)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, num_workers=args.workers)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, num_workers=args.workers)

    model = create_model(len(classes)).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)

    best_f1, best_state, stale = -1.0, copy.deepcopy(model.state_dict()), 0
    total_epochs = args.warmup_epochs + args.epochs
    start = time.time()

    for epoch in range(total_epochs):
        if epoch == 0:
            set_backbone_trainable(model, False)
            optimizer = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
            scheduler = None
            print(f"\nPhase 1: training classifier head ({args.warmup_epochs} epochs)")
        if epoch == args.warmup_epochs:
            set_backbone_trainable(model, True)
            optimizer = torch.optim.AdamW(
                filter(lambda p: p.requires_grad, model.parameters()),
                lr=args.lr, weight_decay=1e-4)
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer, T_max=max(args.epochs, 1))
            print(f"\nPhase 2: fine-tuning backbone ({args.epochs} epochs)")

        epoch_start = time.time()
        train_loss, train_acc, _, _ = run_epoch(model, train_loader, criterion, device, optimizer)
        val_loss, val_acc, val_pred, val_true = run_epoch(model, val_loader, criterion, device)
        if scheduler:
            scheduler.step()

        _, val_f1, _ = per_class_metrics(val_true, val_pred, len(classes))

        print(f"Epoch {epoch + 1:2d}/{total_epochs} | "
              f"train loss {train_loss:.4f} acc {train_acc * 100:5.1f}% | "
              f"val loss {val_loss:.4f} acc {val_acc * 100:5.1f}% F1 {val_f1:.4f} | "
              f"{time.time() - epoch_start:.0f}s")

        if val_f1 > best_f1:
            best_f1, best_state, stale = val_f1, copy.deepcopy(model.state_dict()), 0
            print("  -> new best")
        elif epoch >= args.warmup_epochs:
            stale += 1
            if stale >= args.patience:
                print("Early stopping.")
                break

    model.load_state_dict(best_state)
    print(f"\nTraining time: {(time.time() - start) / 60:.1f} min | best val macro F1 {best_f1:.4f}")

    _, _, val_pred, val_true = run_epoch(model, val_loader, criterion, device)
    report("VALIDATION", val_pred, val_true, classes)
    _, _, test_pred, test_true = run_epoch(model, test_loader, criterion, device)
    report("TEST", test_pred, test_true, classes)

    if args.check_dir and args.check_dir.is_dir():
        check_folder(model, classes, args.check_dir, device)

    # Back up the previous model before overwriting it.
    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    if args.model_path.exists():
        backup = args.model_path.with_name(
            f"{args.model_path.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}.pth")
        shutil.copy2(args.model_path, backup)
        print(f"\nPrevious model backed up to {backup}")

    torch.save({
        "model_state_dict": model.state_dict(),
        "classes": classes,
        "class_to_idx": {c: i for i, c in enumerate(classes)},
        "image_size": IMAGE_SIZE,
    }, args.model_path)

    print("\n" + "=" * 60)
    print("MODEL SAVED:", args.model_path)
    print("Classes:", classes)
    print("=" * 60)


if __name__ == "__main__":
    main()
=======
print("\nLoading EfficientNet-B0...")

model = models.efficientnet_b0(weights=None)

# Replace classifier for all supported produce and the reject class.
num_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    num_features,
    len(train_dataset.classes)
)

# Reuse the existing fruit detector's learned features and known fruit
# output rows, while keeping a newly initialized Dragon Fruit output row.
checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False
)
old_state = (
    checkpoint["model_state_dict"]
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint
    else checkpoint
)
old_classes = (
    checkpoint.get("classes", ["apple", "other", "tomato"])
    if isinstance(checkpoint, dict)
    else ["apple", "other", "tomato"]
)
model_state = model.state_dict()
for key, value in old_state.items():
    if key in model_state and model_state[key].shape == value.shape:
        model_state[key] = value
model.load_state_dict(model_state)

old_class_to_idx = {
    class_name: index for index, class_name in enumerate(old_classes)
}
with torch.no_grad():
    for class_name in ("apple", "other", "tomato"):
        old_index = old_class_to_idx[class_name]
        new_index = train_dataset.class_to_idx[class_name]
        model.classifier[1].weight[new_index].copy_(
            old_state["classifier.1.weight"][old_index]
        )
        model.classifier[1].bias[new_index].copy_(
            old_state["classifier.1.bias"][old_index]
        )

model = model.to(DEVICE)


# ============================================================
# LOSS + OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss()

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# ============================================================
# TRAINING FUNCTIONS
# ============================================================

def train_one_epoch(model, loader, criterion, optimizer):

    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item() * images.size(0)

        _, predicted = torch.max(outputs, 1)

        total += labels.size(0)

        correct += (predicted == labels).sum().item()

    epoch_loss = running_loss / total
    epoch_accuracy = correct / total

    return epoch_loss, epoch_accuracy


def validate(model, loader, criterion, class_names):

    model.eval()

    running_loss = 0.0
    total = 0
    all_predictions = []
    all_labels = []

    with torch.no_grad():

        for images, labels in loader:

            images = images.to(DEVICE)
            labels = labels.to(DEVICE)

            outputs = model(images)

            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)

            total += labels.size(0)
            all_predictions.extend(
                outputs.argmax(dim=1).cpu().tolist()
            )
            all_labels.extend(labels.cpu().tolist())

    epoch_loss = running_loss / total
    epoch_accuracy = sum(
        predicted == label
        for predicted, label in zip(all_predictions, all_labels)
    ) / total
    metrics = classification_report(
        all_labels,
        all_predictions,
        labels=list(range(len(class_names))),
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    return epoch_loss, epoch_accuracy, metrics, all_predictions, all_labels


# ============================================================
# TRAIN
# ============================================================

best_val_macro_f1 = -1.0
best_model_weights = copy.deepcopy(model.state_dict())

print("\nStarting training...")
print("=" * 60)

start_time = time.time()

for epoch in range(NUM_EPOCHS):

    epoch_start = time.time()

    train_loss, train_accuracy = train_one_epoch(
        model,
        train_loader,
        criterion,
        optimizer
    )

    val_loss, val_accuracy, val_metrics, _, _ = validate(
        model,
        val_loader,
        criterion,
        val_dataset.classes
    )
    val_macro_f1 = val_metrics["macro avg"]["f1-score"]
    other_f1 = val_metrics["other"]["f1-score"]

    epoch_time = time.time() - epoch_start

    print(
        f"Epoch [{epoch + 1}/{NUM_EPOCHS}] "
        f"| Train Loss: {train_loss:.4f} "
        f"| Train Acc: {train_accuracy * 100:.2f}% "
        f"| Val Loss: {val_loss:.4f} "
        f"| Val Acc: {val_accuracy * 100:.2f}% "
        f"| Val Macro F1: {val_macro_f1:.4f} "
        f"| Other F1: {other_f1:.4f} "
        f"| Time: {epoch_time:.1f}s"
    )

    if val_macro_f1 > best_val_macro_f1:

        best_val_macro_f1 = val_macro_f1

        best_model_weights = copy.deepcopy(
            model.state_dict()
        )

        print(
            f"  New best validation macro F1: "
            f"{best_val_macro_f1:.4f}"
        )


# ============================================================
# RESTORE BEST MODEL
# ============================================================

model.load_state_dict(best_model_weights)

total_time = time.time() - start_time

print("\n" + "=" * 60)
print("TRAINING COMPLETED")
print("=" * 60)

print(
    f"Best Validation Macro F1: "
    f"{best_val_macro_f1:.4f}"
)

print(
    f"Total Training Time: "
    f"{total_time / 60:.2f} minutes"
)


# ============================================================
# TEST
# ============================================================

test_loss, test_accuracy, test_metrics, test_predictions, test_labels = validate(
    model,
    test_loader,
    criterion,
    test_dataset.classes
)

print("\nTEST RESULTS")
print("-" * 60)

print(f"Test Loss: {test_loss:.4f}")
print(f"Test Accuracy: {test_accuracy * 100:.2f}%")
print(
    "Test Macro F1: "
    f"{test_metrics['macro avg']['f1-score']:.4f}"
)
print("\nPer-class test metrics:")
for class_name in test_dataset.classes:
    class_metrics = test_metrics[class_name]
    print(
        f"{class_name}: "
        f"precision={class_metrics['precision']:.4f}, "
        f"recall={class_metrics['recall']:.4f}, "
        f"F1={class_metrics['f1-score']:.4f}"
    )
print("\nTest confusion matrix (rows=actual, columns=predicted):")
print(
    confusion_matrix(
        test_labels,
        test_predictions,
        labels=list(range(len(test_dataset.classes)))
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "class_to_idx": train_dataset.class_to_idx,
        "classes": train_dataset.classes,
        "image_size": IMAGE_SIZE
    },
    MODEL_PATH
)

print("\n" + "=" * 60)
print("MODEL SAVED SUCCESSFULLY")
print("=" * 60)

print(MODEL_PATH)

print("\nClasses:")
print(train_dataset.classes)
>>>>>>> bf43a2d8074be319d22b9f9093bbf0fcfff833a6
