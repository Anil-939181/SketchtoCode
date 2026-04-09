import os
from pathlib import Path
from collections import Counter
import yaml

dataset_path = Path('/home/rguktrkvalley/Desktop/Sketch2Code/dataset')
labels_path = dataset_path / 'labels'

label_files = list(labels_path.rglob('*.txt'))
print(f"Total label files found: {len(label_files)}")

class_counts = Counter()
empty_files = 0
total_boxes = 0

for lf in label_files:
    if lf.name == "classes.txt":
        print(f"Found classes.txt at: {lf}")
        try:
            with open(lf, 'r') as f:
                print("Classes:", f.read().splitlines())
        except Exception as e:
            pass
        continue

    try:
        with open(lf, 'r') as f:
            lines = f.readlines()
            if not lines:
                empty_files += 1
            for line in lines:
                parts = line.strip().split()
                if not parts: continue
                class_id = int(parts[0])
                class_counts[class_id] += 1
                total_boxes += 1
    except Exception as e:
        print(f"Error reading {lf}: {e}")

print(f"\nStats:")
print(f"Empty files (images with no background/objects): {empty_files}")
print(f"Total bounding boxes: {total_boxes}")
print(f"\nClass Distribution:")
for cid, count in sorted(class_counts.items()):
    print(f"Class {cid}: {count} instances")

yaml_files = list(dataset_path.glob('*.yaml'))
if yaml_files:
    print(f"\nFound yaml: {yaml_files[0]}")
    with open(yaml_files[0], 'r') as f:
        print(f.read())
