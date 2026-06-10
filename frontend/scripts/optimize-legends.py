"""Compress legend WebP assets for faster page loads. Requires: pip install pillow"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'public' / 'legends'

def compress(name: str, width: int, quality: int, suffix: str) -> None:
    src = ROOT / f'{name}.webp'
    if not src.exists():
        print('skip', name)
        return
    img = Image.open(src).convert('RGB')
    w, h = img.size
    if w > width:
        nh = int(h * width / w)
        img = img.resize((width, nh), Image.Resampling.LANCZOS)
    out = ROOT / f'{name}{suffix}.webp'
    img.save(out, 'WEBP', quality=quality, method=6)
    print(out.name, round(out.stat().st_size / 1024), 'KB')

if __name__ == '__main__':
    for n in ('ronaldo', 'messi', 'neymar'):
        compress(n, 640, 78, '')
        compress(n, 960, 72, '-backdrop')
