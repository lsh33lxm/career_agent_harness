"""Remove only boundary-connected dark pixels; preserve all other RGBA values."""

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path

from PIL import Image


def clean(source: Path, destination: Path) -> dict:
    if source.resolve() == destination.resolve() or destination.exists():
        raise ValueError("Output must be a new derivative, never the source")
    original = Image.open(source).convert("RGBA")
    width, height = original.size
    pixels = list(original.getdata())
    selected: set[int] = set()
    pending = deque(
        [x for x in range(width)]
        + [(height - 1) * width + x for x in range(width)]
        + [y * width for y in range(height)]
        + [y * width + width - 1 for y in range(height)]
    )
    while pending:
        index = pending.popleft()
        if index in selected or max(pixels[index][:3]) > 24:
            continue
        selected.add(index)
        x, y = index % width, index // width
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height:
                pending.append(ny * width + nx)
    result = pixels.copy()
    for index in selected:
        result[index] = (*pixels[index][:3], 0)
    output = Image.new("RGBA", original.size)
    output.putdata(result)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination)
    saved = list(Image.open(destination).convert("RGBA").getdata())
    assert all(saved[i] == pixels[i] for i in range(len(pixels)) if i not in selected)
    return {
        "threshold": "max(R,G,B) <= 24; four-connected from every boundary pixel",
        "selected_pixels": len(selected),
        "changed_pixels": sum(a != b for a, b in zip(pixels, saved, strict=True)),
        "non_selected_unchanged": True,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(json.dumps(clean(args.source, args.destination), indent=2))
