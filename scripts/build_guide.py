"""Build the static guide using markdown-it already installed with the operations tools."""

import shutil
from pathlib import Path

from markdown_it import MarkdownIt

root = Path(__file__).resolve().parents[1]
source = root / "docs/unified-guide.md"
web = root / "fraudline/web"
body = MarkdownIt("commonmark", {"html": False}).enable("table").render(source.read_text(encoding="utf-8"))
(web / "guide.html").write_text(
    '<!doctype html><html lang="en"><head><meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Fraudline — A–Z learning guide</title><link rel="stylesheet" href="/assets/style.css?v=20261117-2">'
    '</head><body><main class="guide"><a href="/workbench#learn">← Back to the workbench</a>'
    '<p><a href="/assets/learning-guide.md" download>Download Markdown guide</a></p>'
    + body
    + "</main></body></html>",
    encoding="utf-8",
)
shutil.copy2(source, web / "learning-guide.md")
print(f"Built guide: {len(body):,} HTML characters")
