"""Step 3c: where the category's design is going, measured on recent brands, not remembered.

  trends <run> [--queries "..." "..."] [--max 24]

Pulls two to three image searches worth of recent brand identities in the category (new DTC brands, award
and showcase pages, recent packaging), keeps the ones the vision model confirms are logos or packaging,
and reads them as a design-trend analyst: what repeats among the NEW brands, what the old shelf still does,
and the gap between the two. Writes trends.json and a strip of the sources in trends/. The brief's
second pass and the creative-director pass both receive the trend facts.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_cost, client, download, log, read_json, vision_cost, vision_json, write_json  # noqa: E402
from shelf import bing_image_urls  # noqa: E402

QUERIES = [
    "new {cat} brand identity 2026 logo",
    "{cat} DTC brand packaging design 2025",
    "{cat} branding Behance logo wordmark",
]

READ_TRENDS = """You are a brand-design trend analyst. These {n} images are recent brand identities and packaging in the
category "{cat}" found on the web (showcases, new DTC brands, award pages). Our brand "{brand}" competes on a
shelf whose habits are: {habits}.

First, for each image say whether it is a brand identity / packaging / logo (usable) or something else (a product
photo, a stock image, an image with a stock-photo watermark, an article screenshot, or a different category): "usable": [indexes].
Then, from the usable ones only, return:
- "moving_to": 5 to 7 concrete traits the NEW brands share (letterform width and weight, case, serif or sans,
  symbol or no symbol, color families, layout, texture, tone). Concrete, measurable where possible.
- "moving_away_from": 3 to 5 traits the old shelf does that the new brands have dropped.
- "gap": 3 opportunities that sit between the shelf's habits and the new wave, that a brand launching now can own.
- "overused_now": 3 traits that are already everywhere in the new wave (avoid them too; they will date fast).
- "one_line": what the category's design is becoming, in one sentence a seller understands.
Return JSON only."""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--queries", nargs="*")
    ap.add_argument("--max", type=int, default=24)
    a = ap.parse_args()
    run = Path(a.run).resolve()
    brief = read_json(run / "brief.json") or {}
    shelf = read_json(run / "shelf.json") or {}
    cat = (brief.get("category", "") or "").split(":")[-1].strip() or brief.get("product", "")[:40]
    queries = a.queries or [q.format(cat=cat) for q in QUERIES]
    out = run / "trends"
    out.mkdir(exist_ok=True)
    urls, seen = [], set()
    for q in queries:
        for u in bing_image_urls(q, n=12):
            if u not in seen:
                seen.add(u)
                urls.append((q, u))
    log(f"{len(urls)} candidate images for \"{cat}\" from {len(queries)} searches")
    from PIL import Image
    got = []
    for i, (q, u) in enumerate(urls[: a.max * 2], 1):
        f = out / f"src-{i:02d}.img"
        if not download(u, f, min_bytes=3000):
            continue
        try:
            with Image.open(f) as im:
                im.load()
                if min(im.size) < 200:
                    f.unlink(missing_ok=True)
                    continue
                im = im.convert("RGB")
                im.thumbnail((900, 900))
                dest = out / f"src-{i:02d}.jpg"
                im.save(dest, quality=85)
            f.unlink(missing_ok=True)
            got.append({"file": f"trends/{dest.name}", "url": u, "query": q})
        except Exception:
            f.unlink(missing_ok=True)
        if len(got) >= a.max:
            break
    if len(got) < 6:
        log("too few trend images landed; the trend section is skipped")
        write_json(run / "trends.json", {"category": cat, "sources": got, "read": {}})
        return
    c = client()
    habits = "; ".join(shelf.get("read", {}).get("visual_habits", [])[:5]) or "not measured"
    read, usage = vision_json(c, READ_TRENDS.format(n=len(got), cat=cat, brand=brief.get("brand", ""), habits=habits),
                              [run / g["file"] for g in got], max_px=512)
    append_cost(run, "trends", vision_cost(usage))
    read = read or {}
    usable = set(i for i in read.get("usable", []) if isinstance(i, int))
    for i, g in enumerate(got, 1):
        g["usable"] = i in usable
    for g in got:
        if not g["usable"]:
            (run / g["file"]).unlink(missing_ok=True)
    kept = [g for g in got if g["usable"]]
    write_json(run / "trends.json", {"category": cat, "queries": queries, "sources": kept, "read": read})
    log(f"{len(kept)} recent identities read. {read.get('one_line', '')}")
    for t in read.get("gap", []):
        log(f"  gap: {t}")


def trend_facts(trends):
    """The trend read, condensed for the brief and the creative-director prompts."""
    if not trends or not trends.get("read"):
        return ""
    r = trends["read"]
    return ("Design-trend facts for the category, measured on %d recent brand identities:\n- where it is going: %s\n"
            "- what new brands dropped: %s\n- the gap to own: %s\n- already overused in the new wave (avoid): %s\n- in one line: %s\n") % (
        len(trends.get("sources", [])), "; ".join(r.get("moving_to", [])), "; ".join(r.get("moving_away_from", [])),
        "; ".join(r.get("gap", [])), "; ".join(r.get("overused_now", [])), r.get("one_line", ""))


if __name__ == "__main__":
    main()
