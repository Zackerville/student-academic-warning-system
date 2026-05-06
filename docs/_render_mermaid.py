"""Convert Mermaid blocks in SLIDES.md → mermaid.ink image URLs.

Lý do: Marp không render Mermaid native. mermaid.ink là service free
nhận source qua URL base64 và trả về PNG/SVG. Marp PDF export sẽ tự
fetch các URL này khi build.

Usage:
    python3 docs/_render_mermaid.py

Nó sẽ:
  1. Đọc docs/SLIDES.md
  2. Replace mỗi ```mermaid ... ``` thành ![](<mermaid.ink URL>)
  3. Ghi đè SLIDES.md (backup .bak)

Trade-off:
  - ✅ Zero install, hoạt động ngay
  - ✅ Ảnh sắc nét vector (SVG)
  - ⚠️  Cần internet KHI export PDF (lúc trình chiếu thì PDF đã offline)

Nếu muốn offline hoàn toàn, dùng option B:
  npm i -g @mermaid-js/mermaid-cli
  rồi tự render từng .mmd → .png và embed.
"""
from __future__ import annotations

import base64
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SLIDES = ROOT / "SLIDES.md"
BACKUP = ROOT / "SLIDES.md.bak"

# mermaid.ink endpoints:
#   /img/<b64>      — PNG (default)
#   /svg/<b64>      — SVG (sharp at any zoom — preferred for Marp PDF)
ENDPOINT = "https://mermaid.ink/svg"

MERMAID_BLOCK_RE = re.compile(
    r"```mermaid\n(?P<src>.*?)\n```",
    re.DOTALL,
)


def encode(source: str) -> str:
    """URL-safe base64 of UTF-8 mermaid source, no padding."""
    raw = source.encode("utf-8")
    b = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return b


def convert(text: str) -> tuple[str, int]:
    count = 0

    def _replace(match: re.Match) -> str:
        nonlocal count
        count += 1
        src = match.group("src").strip()
        url = f"{ENDPOINT}/{encode(src)}"
        # KHÔNG giữ source code mermaid trong HTML comment — markdown-it bị
        # confuse với ```mermaid``` bên trong <!-- --> → render raw text ra slide.
        # Source gốc đã có trong .bak, dùng SLIDES.md.bak khi cần edit.
        return f"![Mermaid diagram {count}]({url})"

    return MERMAID_BLOCK_RE.sub(_replace, text), count


def main() -> None:
    if not SLIDES.exists():
        raise SystemExit(f"Missing {SLIDES}")
    text = SLIDES.read_text(encoding="utf-8")

    # Already converted? skip
    if "mermaid.ink/svg" in text:
        print("⚠️  SLIDES.md đã có mermaid.ink links — skip để tránh double-encode.")
        print("   Nếu muốn re-render, restore từ SLIDES.md.bak rồi chạy lại.")
        return

    # Backup
    shutil.copy(SLIDES, BACKUP)
    print(f"✓ Backup → {BACKUP.name}")

    converted, count = convert(text)
    SLIDES.write_text(converted, encoding="utf-8")
    print(f"✓ Replaced {count} Mermaid blocks → mermaid.ink/svg URLs")
    print(f"✓ Wrote {SLIDES.name}")
    print()
    print("Bước tiếp theo:")
    print("  1. Mở SLIDES.md trong VSCode")
    print("  2. Marp preview — diagrams sẽ render (cần internet)")
    print("  3. Export PDF — Marp tự fetch SVG embed vào PDF")
    print("  4. Sau khi có PDF, bạn có thể presented offline thoải mái")


if __name__ == "__main__":
    main()
