"""Step 5b: make the three options imaginable BEFORE the user picks.

  options <run> [--no-ai]

For each judge pick (A, B, C):
  1. a quick vector (no 2048 refine, no API) into options/<id>/svg
  2. the e-commerce composites with that mark: packaging set (box, thank-you card, hang tag, stickers),
     the Amazon listing with the brand byline, the Brand Store header, the Shopify home
  3. one gpt-image-2 render of the mark ON the product photo (the brief's first surface), unless --no-ai
Then one presentation deck for all three from the base skill's presentation_board.py (business card,
bag, signage, social, tote, box... chosen by the product's industry), exported slide by slide.

review.html shows all of it under each direction. The final kit after the pick redoes the chosen one
properly (2048 refine, audit, every size); nothing here is a deliverable.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import base_script, log, read_json, run_py, screenshot_html, write_json  # noqa: E402
import mockups  # noqa: E402

INDUSTRY = [  # keywords in brief.category -> presentation_board industry preset
    (("coffee", "tea", "roast"), "coffee"), (("food", "snack", "kitchen", "cook", "bake", "drink", "beverage", "fondue", "charcuterie", "serving"), "food"),
    (("beauty", "skin", "hair", "oil", "cosmetic", "wellness", "supplement", "health", "vitamin", "care"), "health"),
    (("apparel", "fashion", "cloth", "shoe", "bag", "jewel", "watch"), "fashion"), (("toy", "kid", "baby", "game", "party", "karaoke", "speaker", "audio"), "retail"),
]


# The base deck's surfaces, chosen for where this kind of brand actually lives (no fake business cards for a
# product brand; signage and cards for a shop).
DECK_MOCKUPS = {"product": ["box", "sticker", "social", "website", "shopping-bag", "tote"],
                "business": ["signage", "business-card", "bag", "cup", "social", "website"]}


def industry_for(brief):
    cat = (brief.get("category", "") + " " + brief.get("product", "")).lower()
    for keys, ind in INDUSTRY:
        if any(k in cat for k in keys):
            return ind
    return "retail"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--no-ai", action="store_true")
    a = ap.parse_args()
    run = Path(a.run).resolve()
    brief = read_json(run / "brief.json")
    judge = read_json(run / "judge.json") or {}
    picks = judge.get("picks", {})
    if not picks:
        sys.exit("no judge.json picks; run judge first")
    out = run / "options"
    out.mkdir(exist_ok=True)
    concepts = []
    for key, pid in picks.items():
        d = next((x for x in brief["directions"] if x["key"] == key), {})
        odir = out / pid
        # paid renders (on-product, scenes) survive a rerun; only free files are rebuilt
        keep_ai = [f for f in odir.glob("*") if f.name.startswith(("on-product", "scene"))] if odir.exists() else []
        if odir.exists():
            for f in odir.iterdir():
                if f not in keep_ai:
                    shutil.rmtree(f) if f.is_dir() else f.unlink()
        odir.mkdir(parents=True, exist_ok=True)
        log(f"Option {key} = {pid}: vector")
        code, o, e = run_py([Path(__file__).parent / "vectorize.py", run, pid, "--out-dir", odir, "--name", "logo", "--no-audit"])
        if code != 0 or not (odir / "final.json").exists():
            log(f"  vector failed for {pid}; skipped")
            continue
        fin = read_json(odir / "final.json")
        assets = mockups.assets(run, odir)
        assets["run"] = run
        pages = mockups.comp_pages(assets)
        for name in ("packaging", "label-and-box", "amazon-listing", "amazon-store-header", "shopify-home"):
            if name not in pages or (name in mockups.NEEDS_PHOTO and not assets["product_imgs"]):
                continue
            w, h, html = pages[name]
            (odir / f"{name}.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html}</body></html>")
            screenshot_html(odir / f"{name}.html", odir / f"{name}.png", w, h)
            (odir / f"{name}.html").unlink()
        log(f"  composites: packaging, listing, store header, shopify")
        if not a.no_ai:
            mockups.place_on_product(run, assets, odir, n=1, prefix="on-product")
            from common import svg_to_png
            import scenes
            lp = odir / "logo-on-white.png"
            svg_to_png(odir / "svg" / "logo.svg", lp, width=1600, height=1000, bg="#ffffff", padding=0.18)
            scenes.render(run, lp, odir, "scene")
        svg = odir / "svg"
        c = {"name": d.get("name", pid), "idea": d.get("idea", ""), "rationale": [d.get("why_it_wins", ""), f"Risk: {d.get('risk', '')}"],
             "lockup": str(svg / "logo.svg"), "symbol": str(svg / ("logo-symbol.svg" if (svg / "logo-symbol.svg").exists() else "logo.svg")),
             "lockup_on_dark": str(svg / "logo-white.svg"), "symbol_on_dark": str(svg / ("logo-symbol-white.svg" if (svg / "logo-symbol-white.svg").exists() else "logo-white.svg")),
             "symbol_on_tile": str(svg / ("logo-symbol-white.svg" if (svg / "logo-symbol-white.svg").exists() else "logo-white.svg")),
             "lockup_on_tile": str(svg / "logo-white.svg")}
        concepts.append((key, pid, c, fin))
    if not concepts:
        sys.exit("no option could be vectorized; nothing written")
    spec = {"industry": industry_for(brief)}
    manifest = {}
    for i, (key, pid, c, fin) in enumerate(concepts):
        # slide order from presentation_board: 1 cover, 2 brief, then per concept: mark slide, "in use" slide
        manifest[key] = {"id": pid, "folder": str((out / pid).relative_to(run)), "palette": fin["palette"],
                         "scenes": [m for m in (read_json(out / pid / "scenes.json") or []) if m.get("ok")],
                         "on_product": next((m["file"] for m in (read_json(out / pid / "on-product.json") or []) if m.get("ok")), None)}
    manifest["_industry"] = spec["industry"]
    # Test pack: the three options as neutral tiles plus the questionnaire, for a 50-person consumer test (PickFu, Prolific,
    # or the seller's own customers). Votes come back through `lmb.py votes`.
    tp = out / "test-pack"
    tp.mkdir(exist_ok=True)
    from PIL import Image
    for key, pid, c, fin in concepts:
        src = run / "concepts" / f"{pid}.png"
        if src.exists():
            im = Image.open(src).convert("RGB")
            im.thumbnail((1000, 1000))
            canvas = Image.new("RGB", (1000, 1000), "white")
            canvas.paste(im, ((1000 - im.size[0]) // 2, (1000 - im.size[1]) // 2))
            canvas.save(tp / f"option-{key}.png")
    (tp / "questionnaire.md").write_text(f"""# {brief['brand']}: 3 logo options, consumer test

Audience: {brief.get('audience', '')}
Show the three images in random order, labelled A, B, C. 50 respondents. Ask:

1. Which of these three would you trust most for {brief.get('product', 'this product')}? (one choice)
2. In one or two words, what does each brand sell? (open; scores the idea's clarity)
3. Which one would you remember tomorrow? (one choice, asked after a 5-second look)
4. Which one looks most expensive? Which one looks cheapest? (two choices)
5. Anything that bothers you in any of them? (open)

Where: PickFu (Amazon-shopper audience, about $50 for 50 answers), Prolific (custom audience), or an email to your own
customers. When the answers are in, write them as votes.json {{"A": {{"trust": n, "remember": n, "expensive": n}}, "B": ..., "C": ...}}
and run: lmb.py votes <run> votes.json  (the review is re-ranked on real buyers, not on the judge).
""")
    write_json(out / "options.json", manifest)
    log(f"options ready: {', '.join(k + '=' + v['id'] for k, v in manifest.items() if not k.startswith('_'))}  (deck industry: {spec['industry']})")


if __name__ == "__main__":
    main()
