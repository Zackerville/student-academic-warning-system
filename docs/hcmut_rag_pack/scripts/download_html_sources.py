import csv
from pathlib import Path
import requests
from bs4 import BeautifulSoup

base = Path(__file__).resolve().parents[1]
out = base / "downloaded_html"
out.mkdir(exist_ok=True)
manifest = base / "manifest" / "sources_manifest.csv"

with manifest.open("r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    if row["status"] != "link_only":
        continue
    url = row["source_url"]
    name = Path(row["local_path_or_link_file"]).stem
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    html_path = out / f"{name}.html"
    md_path = out / f"{name}.md"
    html_path.write_bytes(r.content)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = "
".join(line.strip() for line in soup.get_text("
").splitlines() if line.strip())
    md_path.write_text(f"# {row['title']}

Source: {url}

{text}
", encoding="utf-8")
    print(md_path)
