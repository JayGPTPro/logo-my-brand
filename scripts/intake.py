"""Step 1 and 2: get the product, understand the product.

  intake  <ASIN | Amazon URL | folder of product photos | "Brand name">  [--brand NAME] [--host www.amazon.de]
  understand <run>

intake writes product.json and originals/ (the listing's gallery, or the folder's images).
understand looks at the photos and the copy with gpt-5.4 and writes brief.json: what the product is,
who buys it, where a logo physically lives on it, the category's cliches, and three strategic
directions for the mark. The brand name comes from the listing (or --brand); if neither has one the
run stops, because a brand name is the one thing the seller must decide.
"""
import argparse
import html
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (append_cost, curl, download, log, read_json, run_dir, slugify, vision_cost,  # noqa: E402
                    vision_json, write_json, client)

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


# ------------------------------------------------------------------ amazon parsing
def asin_from(text):
    m = re.search(r"(?:/dp/|/gp/product/|/gp/aw/d/|/product/)([A-Z0-9]{10})", text)
    if m:
        return m.group(1)
    m = re.fullmatch(r"[A-Z0-9]{10}", text.strip())
    return m.group(0) if m else None


def host_from(text, default="www.amazon.com"):
    m = re.match(r"https?://([^/?#]+)", text.strip(), re.I)
    if not m:
        return default
    h = m.group(1).lower()
    if "amazon." in h:
        return h if h.startswith("www.") else "www." + h.split("www.")[-1]
    return default


def blocked(page):
    if not page or len(page) < 20000:
        return True
    low = page.lower()
    return ("api-services-support@amazon.com" in page) or ("type the characters you see" in low) or \
        ("bm-verify" in page) or ("_sec/verify" in page) or ("captcha" in low and "productTitle" not in page)


def parse_listing(page):
    def grab(pattern, flags=re.S):
        m = re.search(pattern, page, flags)
        return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""

    title = grab(r'id="productTitle"[^>]*>\s*(.*?)\s*<')
    brand = grab(r'id="bylineInfo"[^>]*>\s*(.*?)\s*</a>')
    brand = re.sub(r"^Visit the (.+?) Store$", r"\1", brand.strip())
    brand = re.sub(r"^Brand:\s*", "", brand).strip()
    # The buy-box price only: the first a-offscreen on a listing is often another offer or another product.
    core = re.search(r'id="corePrice_feature_div".*?class="a-offscreen">\s*([^<]{1,20})\s*<', page, re.S) or \
        re.search(r'id="apex_desktop".*?class="a-offscreen">\s*([^<]{1,20})\s*<', page, re.S)
    price = html.unescape(core.group(1)).strip() if core else ""
    if not price.startswith("$"):
        # Amazon shows the viewer's currency; the dollar price still sits in the page. Take the most frequent one.
        from collections import Counter
        dollars = Counter(re.findall(r"\$\d{1,4}\.\d\d", page))
        price = dollars.most_common(1)[0][0] if dollars else ""
    bullets = [html.unescape(re.sub(r"<[^>]+>", "", b)).strip()
               for b in re.findall(r'<li[^>]*class="a-spacing-mini"[^>]*>\s*<span[^>]*>(.*?)</span>', page, re.S)]
    bullets = [b for b in bullets if b][:8]
    crumbs = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in
              re.findall(r'<a class="a-link-normal a-color-tertiary"[^>]*>(.*?)</a>', page, re.S)]
    urls = []
    for key in ("hiRes", "large"):
        for u in re.findall(r'"%s"\s*:\s*"(https://[^"]+)"' % key, page):
            u = u.replace("\\/", "/")
            if "/images/I/" in u and u not in urls and not u.endswith(".gif"):
                urls.append(u)
        if urls:
            break
    return {"title": title, "brand": brand, "price": price, "bullets": bullets,
            "breadcrumbs": crumbs, "image_urls": urls}


def fetch_listing(asin, host, run):
    url = f"https://{host}/dp/{asin}"
    log(f"Fetching {url} (one attempt)")
    page = curl(url)
    (run / "page.html").write_text(page or "")
    if blocked(page):
        return None
    data = parse_listing(page)
    data.update({"asin": asin, "source": url, "host": host})
    originals = run / "originals"
    originals.mkdir(exist_ok=True)
    got = []
    for i, u in enumerate(data["image_urls"][:7], 1):
        dest = originals / f"{i:02d}{'.png' if u.lower().endswith('.png') else '.jpg'}"
        if download(u, dest):
            got.append(dest.name)
            log(f"  {dest.name}  {dest.stat().st_size // 1024} KB")
        else:
            log(f"  {dest.name}  failed (not retrying)")
    data["images"] = got
    return data


def copy_folder(src, run):
    originals = run / "originals"
    originals.mkdir(exist_ok=True)
    files = sorted(p for p in Path(src).iterdir() if p.suffix.lower() in IMAGE_EXTS)
    got = []
    for i, p in enumerate(files[:7], 1):
        dest = originals / f"{i:02d}{p.suffix.lower()}"
        shutil.copy2(p, dest)
        got.append(dest.name)
    meta = read_json(Path(src) / "product.json", {}) or {}
    return {"title": meta.get("title", Path(src).name), "brand": meta.get("brand", ""), "price": meta.get("price", ""),
            "bullets": meta.get("bullets", []), "breadcrumbs": [], "image_urls": [], "images": got,
            "source": str(Path(src).resolve()), "asin": meta.get("asin", "")}


def cmd_intake(a):
    text = a.source.strip()
    src = Path(text).expanduser()
    if src.is_dir():
        slug = slugify(a.brand or src.name)
        run = run_dir(slug, a.root)
        data = copy_folder(src, run)
    elif asin_from(text):
        asin = asin_from(text)
        host = a.host or host_from(text)
        run = run_dir(a.brand and slugify(a.brand) or asin, a.root)
        data = fetch_listing(asin, host, run)
        if data is None:
            log("Amazon blocked the fetch (captcha). Options: open the listing in your browser, save the page "
                "as HTML and run `intake <saved.html> --asin ...`, or put the product photos in a folder and run "
                "`intake <folder> --brand NAME`.")
            sys.exit(2)
    elif src.suffix.lower() in (".html", ".htm") and src.exists():
        data = parse_listing(src.read_text(errors="ignore"))
        asin = a.asin or asin_from(src.read_text(errors="ignore")) or "saved-page"
        run = run_dir(a.brand and slugify(a.brand) or asin, a.root)
        data.update({"asin": asin, "source": str(src), "host": a.host or "www.amazon.com"})
        originals = run / "originals"
        originals.mkdir(exist_ok=True)
        data["images"] = []
        for i, u in enumerate(data["image_urls"][:7], 1):
            dest = originals / f"{i:02d}.jpg"
            if download(u, dest):
                data["images"].append(dest.name)
    else:
        # A brand name with no product: a pre-launch seller. The brief then comes from --about.
        slug = slugify(text)
        run = run_dir(slug, a.root)
        data = {"title": a.about or "", "brand": text, "price": "", "bullets": [], "breadcrumbs": [],
                "image_urls": [], "images": [], "source": "brand name only", "asin": "", "kind": a.kind or "business"}
    if a.brand:
        data["brand"] = a.brand
    if a.about:
        data["about"] = a.about
    if a.kind:
        data["kind"] = a.kind
    if a.city:
        data["city"] = a.city
        data["about"] = (data.get("about", "") + f" Located in {a.city}.").strip()
    if a.website:
        data["website"] = a.website
    data["slug"] = run.name
    write_json(run / "product.json", data)
    log(f"Brand: {data['brand'] or '(none in the listing)'}")
    log(f"Title: {data['title'][:100]}")
    log(f"Images: {len(data['images'])}  ->  {run}")
    if not data["brand"]:
        log("No brand name found. Re-run with --brand NAME (the name is the seller's decision, not the skill's).")
        sys.exit(3)
    print(run)


# ------------------------------------------------------------------ understand
UNDERSTAND_PROMPT = """You are a senior brand strategist. You build the creative brief for a BRAND LOGO from whatever
the brand already has: an Amazon listing and its photos, a product description, or a few lines about a business
(a pizza place, a clinic, a service, a software product). {mode_line}

Brand name (exact, never change the spelling): "{brand}"
Listing title or what the brand sells: "{title}"
Price: "{price}"
Category path: {crumbs}
Bullets:
{bullets}
{about}
{shelf}
Look at the photos (when there are any) as a designer would. Then return JSON with these fields:

- "product": one plain sentence saying what the thing or the business is, for someone who has not seen it.
- "category": the category in 2 to 4 words (e.g. "kitchen: fondue sets", "food: pizza restaurant", "services: dental clinic").
- "audience": who buys it and why, one sentence. Name the occasion if there is one (gift, hosting, daily use, lunch break).
- "price_tier": "budget" | "mid" | "premium", from the price, the materials you see, or the description.
- "materials": the materials and finishes you can SEE on the product, or the physical world of the business (wood counter,
  kraft pizza boxes, neon, uniforms...). Empty list when nothing is known.
- "product_colors": 2 to 4 hex colors that are physically on the product or the place itself (not the background); empty if unknown.
- "logo_surfaces": where a brand mark physically lives for THIS brand, in order of visibility. 3 to 5 entries, each
  {{"surface": "...", "method": "printed|embossed|debossed|engraved|woven label|sticker|hang tag|laser|foil",
    "size_mm": approximate longest side in mm, "colors_available": 1 or 2 or "full"}}.
  Examples: a cloth pouch gets a woven label 30 mm, a cast-iron pot gets an embossed mark 25 mm on the lid,
  a gift box gets a printed lockup 90 mm, a ceramic gets a debossed symbol on the base 12 mm.
- "photo_roles": one entry per photo in the order given, each "packshot" (product on plain background, no text),
  "lifestyle" (product in a scene, no or little text), "infographic" (text, arrows, callouts, badges), or
  "packaging" (the box or pouch is the subject). The logo gets placed on packshot, lifestyle and packaging photos only.
- "adjectives": 5 brand adjectives that fit this product, audience and price tier. Specific words, not "quality".
- "cliches": 5 to 8 visual cliches of this category that the logo must avoid (shapes, colors, type styles). Be concrete.
- "shelf_keyword": the 2 to 4 word search a buyer types to find this (an Amazon search for a product; for a business,
  what they type into Google or Maps, e.g. "pizza delivery Haifa").
- "competitor_hint": for a business or a non-Amazon product: the kind of competitors to look up and where (e.g. "other
  pizza places in Haifa on Google Maps and Wolt"; "DTC castor oil brands with Shopify stores"). Empty for Amazon products.
- "current_mark": the brand mark or logo you can SEE printed on the product or packaging in the photos today, in one
  sentence (style, color, where), or "" if none is visible.
- "copy": short lines for the mockups, written once, plain and specific, no superlatives:
  {{"tagline": 3 to 6 words, "card_line": one sentence under 14 words for a thank-you card,
    "ad_headline": under 9 words for a Sponsored Brands ad, "store_line": one sentence under 16 words for the store header}}.
- "name_notes": what the brand name evokes, its initials, any letter with graphic potential, any pronunciation trap.
- "directions": exactly 3 strategic directions for the logo, as different from each other as possible, each
  {{"key": "A"|"B"|"C", "name": 2-3 words, "mark_type": one of wordmark|lettermark|monogram|pictorial|abstract|emblem|combination,
    "idea": ONE sentence that a designer could build from, with an ownable twist (a sentence that could describe a competitor's logo is not an idea),
    "why_it_wins": one sentence about THIS shelf and THIS buyer,
    "palette": [2 or 3 hex colors; the first is the main brand color; it must work printed in one color],
    "type_feel": the typographic voice in 5 to 8 words (e.g. "wide geometric sans, tight tracking, lowercase"),
    "risk": the honest weakness of this direction in one short sentence}}.
  Rules for the directions: at least one direction is a wordmark or lettermark (sellers need a name that reads at
  40 px); at most one direction may depict the product or its use; no direction may rely on a category cliche
  from your own list; the palettes must differ from each other; when shelf facts are given, no direction's MAIN
  color may be a hue the shelf already owns, and at least one direction must take one of the shelf's whitespace
  opportunities literally; when trend facts are given, at least one direction sits in the gap between the shelf
  and the new wave, and none leans on a trait listed as already overused.

Return only the JSON object."""


def shelf_facts(shelf):
    """The competitor shelf, condensed for the brief prompt (empty before the shelf step has run)."""
    if not shelf:
        return ""
    cen = shelf.get("census", {})
    rd = shelf.get("read", {})
    brands = ", ".join(b.get("brand", "") for b in rd.get("brands", [])[:10] if b.get("brand"))
    return ("Shelf facts, measured on page one of Amazon for \"%s\":\n- colors the shelf already owns: %s; free hues: %s\n"
            "- brands there: %s\n- shared visual habits: %s\n- type habits: %s\n- whitespace nobody uses: %s\n- what would make us disappear: %s\n") % (
        shelf.get("keyword", ""), ", ".join(cen.get("owned", [])) or "none dominant", ", ".join(cen.get("free", [])),
        brands, "; ".join(rd.get("visual_habits", [])), rd.get("type_habits", ""),
        "; ".join(rd.get("whitespace", [])), "; ".join(rd.get("avoid", [])))


def cmd_understand(a):
    run = Path(a.run)
    prod = read_json(run / "product.json")
    if not prod:
        sys.exit("no product.json; run intake first")
    c = client()
    images = [run / "originals" / n for n in prod.get("images", [])][:5]
    kind = prod.get("kind") or ("business" if not prod.get("asin") and not images else "product")
    mode_line = ("This is a BUSINESS or a product with no Amazon listing: there may be no photos; build the brief from the "
                 "description, and make the surfaces the places a customer meets this brand." if kind == "business"
                 else "This is a physical product sold online.")
    prompt = UNDERSTAND_PROMPT.format(
        mode_line=mode_line,
        brand=prod["brand"], title=prod.get("title", ""), price=prod.get("price", ""),
        crumbs=" > ".join(prod.get("breadcrumbs", [])) or "(unknown)",
        bullets="\n".join("- " + b for b in prod.get("bullets", [])) or "(none)",
        about=("About the brand, from the seller: " + prod["about"]) if prod.get("about") else "",
        shelf=shelf_facts(read_json(run / "shelf.json")) + "\n" + __import__("trends").trend_facts(read_json(run / "trends.json")))
    log(f"Reading {len(images)} photos and the copy with {a.model or 'the vision model'}...")
    brief, usage = vision_json(c, prompt, images)
    append_cost(run, "understand", vision_cost(usage))
    if not brief or "directions" not in brief:
        sys.exit("the brief came back malformed; run understand again")
    brief["brand"] = prod["brand"]
    brief["kind"] = kind
    brief["built"] = __import__("common").now()
    write_json(run / "brief.json", brief)
    log(f"Product: {brief.get('product')}")
    log(f"Adjectives: {', '.join(brief.get('adjectives', []))}")
    for d in brief["directions"]:
        log(f"  {d['key']} {d['name']} [{d['mark_type']}]: {d['idea']}")
    log(f"Logo lives on: " + "; ".join(f"{s['surface']} ({s['method']}, {s.get('size_mm')} mm)"
                                        for s in brief.get("logo_surfaces", [])[:3]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("intake")
    p.add_argument("source")
    p.add_argument("--brand")
    p.add_argument("--about", help="for a brand with no listing yet: what the product is, in a sentence or two")
    p.add_argument("--host")
    p.add_argument("--asin")
    p.add_argument("--root")
    p.add_argument("--kind", choices=["product", "business"], help="default: product for an ASIN or a photo folder, business for a bare name")
    p.add_argument("--city", help="for a local business: the city (goes into the brief and the competitor search)")
    p.add_argument("--website", help="the brand's own site, if any")
    p.set_defaults(fn=cmd_intake)
    p = sub.add_parser("understand")
    p.add_argument("run")
    p.add_argument("--model")
    p.set_defaults(fn=cmd_understand)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
