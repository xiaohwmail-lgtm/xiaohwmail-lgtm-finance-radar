#!/usr/bin/env python3
"""Generate compact markdown brief from Finance Radar JSON for Hermes consumption."""
import json, sys, os
from datetime import datetime


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_brief(all_path, out_path, max_per_source=15, max_items=150):
    data = load_json(all_path)
    items = data.get("items_all", data.get("items", []))

    # Only OPML RSS items (the user's custom feeds)
    opml_items = [it for it in items if it.get("site_id") == "opmlrss"]

    # Sort by published_at descending
    opml_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    # Group by source
    groups = {}
    for item in opml_items:
        src = item.get("source", "其他")
        if src not in groups:
            groups[src] = []
        if len(groups[src]) < max_per_source:
            groups[src].append(item)

    total = min(len(opml_items), max_items)
    lines = [
        "# 财经雷达 OPML 简报",
        "> 生成: %s | %d 源 | 展示 %d 条" % (
            data.get("generated_at", "")[:19].replace("T", " "),
            len(groups), total
        ),
        "",
    ]

    count = 0
    for src, src_items in groups.items():
        lines.append("## %s" % src)
        for item in src_items:
            title = item.get("title_zh") or item.get("title") or ""
            url = item.get("url") or ""
            pub = item.get("published_at", "")[:16].replace("T", " ")
            lines.append("- [%s](%s) _%s_" % (title, url, pub))
            count += 1
            if count >= max_items:
                break
        lines.append("")
        if count >= max_items:
            break

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("radar-brief: %d items from %d sources -> %s (%d bytes)" % (
        count, len(groups), out_path, os.path.getsize(out_path)))


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    generate_brief(
        all_path=os.path.join(data_dir, "latest-24h-all.json"),
        out_path=os.path.join(data_dir, "radar-brief.md"),
    )
