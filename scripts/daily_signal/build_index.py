# -*- coding: utf-8 -*-
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import json
import hashlib
import unicodedata

ROOT = Path(__file__).resolve().parents[2] / "surfaces/gui/public/youtube"
CHANNEL_ROOT = ROOT / "Channel"
MANIFEST = ROOT / "manifest.json"

class TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.parts.append(data)

def title_for(path: Path) -> str:
    parser = TitleParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    title = "".join(parser.parts).strip()
    return title or path.stem

def discover():
    previous = {}
    if MANIFEST.exists():
        for channel in json.loads(MANIFEST.read_text(encoding="utf-8"))["channels"]:
            previous.update((doc["path"], doc) for doc in channel["documents"])
    channels = []
    for channel_dir in sorted((p for p in CHANNEL_ROOT.iterdir() if p.is_dir()), key=lambda p: p.name.casefold()):
        docs = []
        for path in channel_dir.glob("*.html"):
            stat = path.stat()
            rel = unicodedata.normalize("NFC", path.relative_to(ROOT).as_posix())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            prior = previous.get(rel, {})
            modified = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
            if prior.get("sha256") == digest:
                modified = prior["modified"]
            docs.append({
                "id": rel,
                "path": rel,
                "title": title_for(path),
                "sha256": digest,
                "modified": modified,
                "date": modified[:10].replace("-", "."),
                "channel": channel_dir.name,
            })
        docs.sort(key=lambda item: (item["modified"], item["path"]), reverse=True)
        channels.append({"id": channel_dir.name, "name": channel_dir.name, "documents": docs})
    return {"channels": channels}

def main():
    manifest = discover()
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    total = sum(len(channel["documents"]) for channel in manifest["channels"])
    print(f"wrote {MANIFEST.name}: {len(manifest['channels'])} channels, {total} reports")

if __name__ == "__main__":
    main()
