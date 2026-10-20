"""Step 3: the competitor shelf.

  shelf <run> [--keyword "..."] [--competitors FILE_OR_FOLDER] [--max 12]

Pulls the first page of Amazon results for the brief's shelf keyword (one fetch, no retries), keeps the
real tiles (ASIN, title, price, main image), downloads the thumbnails, measures the colors the shelf
already owns, and has the vision model read the brands and logo habits off the tiles. Writes shelf.json
and shelf.html (the shelf as a buyer sees it, with the color census under it).

When Amazon blocks the fetch: pass --competitors with a saved results page (.html), a folder of
competitor images, or a JSON list [{"brand":..., "title":..., "image": path_or_url}].
"""
import argparse
import colorsys
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (append_cost, client, curl, download, esc, file_data_uri, log, read_json,  # noqa: E402
                    vision_cost, vision_json, write_json)
from intake import blocked  # noqa: E402

HUES = [("red", 345, 15), ("orange", 15, 45), ("yellow", 45, 70), ("green", 70, 170), ("cyan", 170, 200),
        ("blue", 200, 260), ("purple", 260, 300), ("pink", 300, 345)]


def parse_results(page, our_asin=""):
    items = []
    for block in re.findall(r'(<div[^>]+data-asin="[A-Z0-9]{10}"[^>]+data-component-type="s-search-result".*?)'
                            r'(?=<div[^>]+data-asin="|$)', page, re.S):
        asin = re.search(r'data-asin="([A-Z0-9]{10})"', block).group(1)
        if asin == our_asin:
            continue
        img = re.search(r'<img[^>]+class="s-image"[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', block) or \
            re.search(r'<img[^>]+alt="([^"]*)"[^>]+class="s-image"[^>]+src="([^"]+)"', block)
        if not img:
            continue
        g = img.groups()
        src, alt = (g[0], g[1]) if g[0].startswith("http") else (g[1], g[0])
        src = re.sub(r"\._[A-Z0-9_,]+_(\.[a-z]+)$", r"\1", src)   # the full-size image, not the 218 px thumb
        price = re.search(r'class="a-offscreen">([^<]{1,20})<', block)
        sponsored = "Sponsored" in block[:4000]
        items.append({"asin": asin, "title": re.sub(r"^Sponsored Ad\s*-\s*", "", html.unescape(alt))[:140], "image": src,
                      "price": price.group(1) if price else "", "sponsored": sponsored})
    return items


def census(paths):
    """Which hues the shelf already owns: share of saturated pixels per hue family across all tiles."""
    from PIL import Image
    counts = {h[0]: 0 for h in HUES}
    counts.update({"black": 0, "white": 0})
    sat_total = 0
    for p in paths:
        try:
            im = Image.open(p).convert("RGB")
        except Exception:
            continue
        im.thumbnail((120, 120))
        for r, g, b in list(im.getdata()):
            h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if l > 0.93:
                counts["white"] += 1
                continue
            if l < 0.12:
                counts["black"] += 1
                continue
            if s < 0.25:
                continue
            deg = h * 360
            for name, lo, hi in HUES:
                if (lo <= deg < hi) or (lo > hi and (deg >= lo or deg < hi)):
                    counts[name] += 1
                    sat_total += 1
                    break
    share = {k: round(v / sat_total, 3) if sat_total else 0 for k, v in counts.items() if k not in ("black", "white")}
    owned = [k for k, v in sorted(share.items(), key=lambda kv: -kv[1]) if v >= 0.18]
    free = [k for k, v in sorted(share.items(), key=lambda kv: kv[1]) if v <= 0.04]
    return {"hue_share": share, "owned": owned, "free": free}


READ_SHELF = """These are the competitors a buyer meets when looking for "{kw}" (Amazon results for a product; for a
business, the competitors' photos and logos). Our brand "{brand}" will sit among them. Read the tiles like a
shopper scanning the page on a phone.

Return JSON:
- "brands": for up to {n} tiles in order, {{"tile": index starting at 1, "brand": the brand name you can read on the
  packaging or infer from the title, "logo_style": the brand mark's style if visible in 4 to 8 words, else "not visible",
  "logo_box": when a brand logo or brand name is printed on the product or its packaging in the image, its bounding box
  as [x, y, w, h] fractions of the image width and height (0 to 1), generous enough to include the whole mark; else null,
  "dominant_color": hex}}.
- "visual_habits": 4 to 6 habits this shelf shares (colors, type, badges, backgrounds, packaging looks). Concrete.
- "type_habits": what the brand names look like typographically on this shelf (case, weight, serif or sans), one sentence.
- "whitespace": 3 opportunities that nobody on this shelf is using (a color, a type voice, a symbol language, a tone).
- "avoid": 3 things that would make our brand disappear on this shelf.
Return only JSON."""


GRID_COLS = "ABCDEFGHIJ"


def grid_overlay(src, dest, n=10):
    """The photo with a labelled 10 x 10 grid drawn over it: the vision model names cells far more reliably
    than it estimates fractions."""
    from PIL import Image, ImageDraw
    im = Image.open(src).convert("RGB")
    im.thumbnail((900, 900))
    W, H = im.size
    d = ImageDraw.Draw(im, "RGBA")
    for i in range(1, n):
        d.line([(W * i / n, 0), (W * i / n, H)], fill=(255, 0, 0, 110), width=1)
        d.line([(0, H * i / n), (W, H * i / n)], fill=(255, 0, 0, 110), width=1)
    for c in range(n):
        for r in range(n):
            d.text((W * c / n + 3, H * r / n + 2), f"{GRID_COLS[c]}{r + 1}", fill=(255, 0, 0, 230))
    im.save(dest)
    return dest


LOCATE = """Each image is a product photo with a red labelled grid (columns A to J, rows 1 to 10). For each image, in order,
find the BRAND LOGO or brand name printed on the product or its packaging (not Amazon badges, not feature callouts,
not model numbers). Return JSON {{"tiles": [{{"tile": 1, "brand": "...", "cells": ["C7", "D7", "E7"]}}, ...]}} where
cells lists EVERY grid cell the mark touches (a wide wordmark spans several columns). Use "cells": [] when no brand
mark is printed anywhere in the photo. {n} images."""

VERIFY = """Each image is a crop that should show one brand's logo or printed brand name. For each, in order, return
{{"crops": [{{"i": 1, "ok": true/false, "reads": "the brand text you can read, or empty"}}]}}: ok is true only when a
brand mark or brand name is clearly visible and fills a reasonable part of the crop. A product's display readout, a
feature callout, a badge like "20 songs", a model number or plain product parts are NOT a brand mark: ok false. {n} crops.
Return JSON only."""


def _cells_box(cells, W, H, pad):
    cols = [GRID_COLS.index(x[0]) for x in cells if len(x) >= 2 and x[0] in GRID_COLS and x[1:].isdigit()]
    rows = [int(x[1:]) - 1 for x in cells if len(x) >= 2 and x[0] in GRID_COLS and x[1:].isdigit()]
    if not cols:
        return None
    c0, c1, r0, r1 = min(cols), max(cols) + 1, min(rows), max(rows) + 1
    box = (max(0, int((c0 - pad) * W / 10)), max(0, int((r0 - pad) * H / 10)),
           min(W, int((c1 + pad) * W / 10)), min(H, int((r1 + pad) * H / 10)))
    if box[2] - box[0] < 16 or box[3] - box[1] < 8:
        return None
    return box


def crop_logos(run, kept, read, c=None):
    """Cut the competitor marks out of their own product photos: grid localisation, a zoom pass on a fresh
    grid, then a read-back. A zoom the read-back rejects falls back to the first cut; a first cut it rejects
    is dropped (the shelf then shows the brand name instead)."""
    from PIL import Image
    import tempfile
    if c is None:
        return []
    todo = [(i, it) for i, it in enumerate(kept, 1) if not it.get("logo")]   # entries with a logo from their site keep it
    if not todo:
        return [run / it["logo"] for it in kept if it.get("logo")]
    with tempfile.TemporaryDirectory() as t:
        grids = [grid_overlay(run / it["local"], Path(t) / f"g{i:02d}.jpg") for i, it in todo]
        loc, usage = vision_json(c, LOCATE.format(n=len(grids)), grids, max_px=900)
        append_cost(run, "shelf locate", vision_cost(usage))
    first, names = {}, {}
    for t_ in (loc or {}).get("tiles", []):
        k = t_.get("tile")
        if not isinstance(k, int) or k < 1 or k > len(todo):
            continue
        i, it = todo[k - 1]
        cells = [x.strip().upper() for x in t_.get("cells", []) if isinstance(x, str)]
        if not cells:
            continue
        im = Image.open(run / it["local"]).convert("RGB")
        box = _cells_box(cells, *im.size, pad=0.35)
        if box:
            first[i] = im.crop(box)
            names[i] = t_.get("brand", "")
    if not first:
        return []
    order = sorted(first)
    zoomed = {}
    with tempfile.TemporaryDirectory() as t:
        for i in order:
            first[i].save(Path(t) / f"f{i:02d}.png")
        grids2 = [grid_overlay(Path(t) / f"f{i:02d}.png", Path(t) / f"z{i:02d}.jpg") for i in order]
        loc2, usage = vision_json(c, LOCATE.format(n=len(grids2)), grids2, max_px=900)
        append_cost(run, "shelf zoom", vision_cost(usage))
    for t_ in (loc2 or {}).get("tiles", []):
        k = t_.get("tile")
        if not isinstance(k, int) or k < 1 or k > len(order):
            continue
        i = order[k - 1]
        cells = [x.strip().upper() for x in t_.get("cells", []) if isinstance(x, str)]
        W, H = first[i].size
        box = _cells_box(cells, W, H, pad=0.3) if cells else None
        if box and (box[2] - box[0]) * (box[3] - box[1]) < 0.85 * W * H:
            zoomed[i] = first[i].crop(box)

    reads = {}

    def verify(cands):
        with tempfile.TemporaryDirectory() as t:
            paths = []
            for n, (i, im) in enumerate(cands, 1):
                pth = Path(t) / f"v{n:02d}.png"
                im.save(pth)
                paths.append(pth)
            ver, usage = vision_json(c, VERIFY.format(n=len(paths)), paths, max_px=512)
        append_cost(run, "shelf verify", vision_cost(usage))
        oks = {x.get("i"): x for x in (ver or {}).get("crops", [])}
        for n, (i, _) in enumerate(cands, 1):
            if oks.get(n, {}).get("reads"):
                reads[i] = oks[n]["reads"]
        return [bool(oks.get(n, {}).get("ok")) for n in range(1, len(cands) + 1)]

    accepted = {}
    zc = [(i, zoomed[i]) for i in order if i in zoomed]
    if zc:
        for (i, im), ok in zip(zc, verify(zc)):
            if ok:
                accepted[i] = im
    fc = [(i, first[i]) for i in order if i not in accepted]
    if fc:
        for (i, im), ok in zip(fc, verify(fc)):
            if ok:
                accepted[i] = im
    for i, im in accepted.items():
        dest = run / "shelf" / f"logo-{i:02d}.png"
        im.save(dest)
        kept[i - 1]["logo"] = f"shelf/{dest.name}"
        named = next((b.get("brand") for b in read.get("brands", []) if b.get("tile") == i and b.get("brand")), "")
        kept[i - 1]["brand"] = reads.get(i) or names.get(i) or named   # what was read ON the mark wins
    for b in read.get("brands", []):
        i = b.get("tile")
        if i and i <= len(kept):
            if not kept[i - 1].get("brand"):
                kept[i - 1]["brand"] = b.get("brand", "")
            kept[i - 1]["logo_style"] = b.get("logo_style", "")
    return [run / it["logo"] for it in kept if it.get("logo")]


def bing_image_urls(query, n=8):
    """Image search result URLs for a query (Bing's async endpoint answers curl; Google and DDG do not)."""
    import html as _h
    from urllib.parse import quote_plus
    q = quote_plus(query)
    page = curl(f"https://www.bing.com/images/async?q={q}&first=0&count={n * 2}&mmasync=1", timeout=20)
    urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', page or "") or \
        re.findall(r'"murl":"(https?://[^"]+)"', _h.unescape(page or ""))
    seen, out = set(), []
    for u in urls:
        if u not in seen and not u.lower().endswith(".svg"):
            seen.add(u)
            out.append(u)
    return out[:n]


PICK_LOGO = """Each image is a web search result for "{brand} logo". Which images show the actual logo of the brand
"{brand}" (a clean brand mark or logotype, alone or on packaging, not a product photo, not another company, not a
stock image)? Return JSON {{"ok": [indexes starting at 1 that are the real logo, best first], "reads": "the brand
text you can read in the best one"}}. {n} images."""


def logo_from_web(brand, dest, c, run, extra_urls=()):
    """The brand's logo as the web shows it: up to 6 candidates (given URLs first, then an image search),
    downloaded once each, read back by the vision model, the best kept at dest. Returns True when one passed."""
    if not brand or brand.lower() in ("unknown", "not clear", "not visible", ""):
        return False
    cands = list(extra_urls) + bing_image_urls(f"{brand} logo")
    cands = [u for i, u in enumerate(cands) if u not in cands[:i]][:6]
    if not cands:
        return False
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        got = []
        for i, u in enumerate(cands, 1):
            f = Path(t) / f"c{i}.img"
            if download(u, f, min_bytes=800):
                try:
                    with Image.open(f) as im:
                        im.load()
                        if min(im.size) < 48:
                            continue
                        out = Path(t) / f"c{i}.png"
                        im.convert("RGBA").save(out)
                        got.append((u, out))
                except Exception:
                    continue
        if not got:
            return False
        res, usage = vision_json(c, PICK_LOGO.format(brand=brand, n=len(got)), [p for _, p in got], max_px=512)
        append_cost(run, f"web logo {brand}", vision_cost(usage))
        oks = [i for i in (res or {}).get("ok", []) if isinstance(i, int) and 1 <= i <= len(got)]
        if not oks:
            return False
        src = got[oks[0] - 1][1]
        im = Image.open(src).convert("RGBA")
        im.thumbnail((900, 900))
        # flatten onto white so dark-on-transparent marks stay visible on the sheet
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        bg.save(dest)
        return True


def logo_from_site(domain, dest):
    """A competitor's logo from its own website: the header <img> that calls itself a logo, else og:image,
    else the Google favicon at 128 px. One fetch of the homepage, one of the image."""
    import html as _h
    from urllib.parse import urljoin
    domain = re.sub(r"^https?://", "", domain.strip()).strip("/")
    home = f"https://{domain}"
    page = curl(home, timeout=20)
    cands = []
    for m in re.finditer(r"<img[^>]+>", page or "", re.I):
        tag = m.group(0)
        if re.search(r"logo", tag, re.I):
            src = re.search(r'(?:src|data-src)="([^"]+)"', tag)
            if src:
                cands.append(_h.unescape(src.group(1)))
    og = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', page or "", re.I)
    if og:
        cands.append(_h.unescape(og.group(1)))
    cands.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=128")
    for u in cands[:4]:
        u = urljoin(home + "/", u)
        if u.lower().endswith(".svg"):
            continue
        if download(u, dest, min_bytes=600):
            try:
                from PIL import Image
                with Image.open(dest) as im:
                    im.load()
                    if min(im.size) >= 64:
                        im.convert("RGBA").save(dest)
                        return True
            except Exception:
                pass
            Path(dest).unlink(missing_ok=True)
    return False


def tiles_sheet(run, items, cen, read, kw):
    logo_strip = "".join(
        (f"<div class='lg'><img src='{file_data_uri(run / it['logo'])}'><span>{esc(it.get('brand', ''))}</span></div>" if it.get("logo")
         else f"<div class='lg name'><b>{esc(it.get('brand', '') or it.get('title', '')[:18])}</b><span>{esc(it.get('logo_style', 'no mark visible'))}</span></div>")
        for it in items)
    cards = []
    for i, it in enumerate(items, 1):
        img = it.get("local")
        src = file_data_uri(run / img) if img and (run / img).exists() else it.get("image", "")
        b = next((x for x in read.get("brands", []) if x.get("tile") == i), {})
        cards.append(f"""<div class="t"><div class="im"><img src="{src}"></div>
        <div class="tt">{esc(it.get('title', '')[:70])}</div>
        <div class="pr">{esc(it.get('price', ''))}</div>
        <div class="br"><b>{esc(b.get('brand', ''))}</b> <span>{esc(b.get('logo_style', ''))}</span></div></div>""")
    bars = "".join(f"<div class='bar'><span style='width:{int(v * 300)}px;background:{hue_css(k)}'></span>{k} {int(v * 100)}%</div>"
                   for k, v in sorted(cen["hue_share"].items(), key=lambda kv: -kv[1]))
    lists = "".join(f"<h3>{esc(t)}</h3><ul>{''.join('<li>' + esc(x) + '</li>' for x in read.get(k, []))}</ul>"
                    for t, k in (("Shelf habits", "visual_habits"), ("Whitespace", "whitespace"), ("Avoid", "avoid")))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Shelf: {esc(kw)}</title><style>
    body{{font-family:-apple-system,Inter,Arial,sans-serif;margin:0;background:#fff;color:#111}}
    .wrap{{padding:28px 32px}} h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#666;margin-bottom:18px}}
    .grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}}
    .t{{border:1px solid #e6e6e6;border-radius:8px;padding:10px;font-size:11px;background:#fff}}
    .im{{height:150px;display:flex;align-items:center;justify-content:center}} .im img{{max-width:100%;max-height:150px}}
    .tt{{margin-top:8px;color:#0f1111;line-height:1.3;height:42px;overflow:hidden}} .pr{{font-weight:700;margin:4px 0}}
    .br b{{color:#007185}} .br span{{color:#777}}
    .cen{{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:26px}}
    .bar{{font-size:12px;margin:3px 0;display:flex;align-items:center;gap:8px}} .bar span{{display:inline-block;height:12px;border-radius:3px}}
    h3{{font-size:13px;margin:12px 0 4px;text-transform:uppercase;letter-spacing:.06em;color:#666}} ul{{margin:0;padding-left:18px;font-size:13px}} li{{margin:2px 0}}
    .own{{font-size:13px;margin-top:8px}}
    .logos{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}} .lg{{background:#fff;border:1px solid #e6e6e6;border-radius:8px;height:110px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;padding:8px;font-size:10px;color:#666;text-align:center}}
    .lg img{{max-width:90%;max-height:64px;object-fit:contain}} .lg.name b{{font-size:14px;color:#222;letter-spacing:.04em}}
    </style></head><body><div class="wrap">
    <h1>The shelf for "{esc(kw)}"</h1><div class="sub">{len(items)} tiles from page one. Brand "{esc(read.get('_brand', ''))}" will stand among these.</div>
    <h3>The competitors' marks, cut from their own photos</h3><div class="logos">{logo_strip}</div>
    <h3 style="margin-top:22px">The products as the buyer sees them</h3><div class="grid">{''.join(cards)}</div>
    <div class="cen"><div><h3>Colors the shelf already owns</h3>{bars}
    <div class="own">Owned: <b>{', '.join(cen['owned']) or 'nothing dominant'}</b> &nbsp; Free: <b>{', '.join(cen['free']) or 'none'}</b></div>
    <p style="font-size:12px;color:#666">Type on this shelf: {esc(read.get('type_habits', ''))}</p></div><div>{lists}</div></div>
    </div></body></html>"""


def hue_css(k):
    return {"red": "#d33", "orange": "#f28c28", "yellow": "#e8c21a", "green": "#3a9d4f", "cyan": "#2bb3c0",
            "blue": "#2d6cdf", "purple": "#7b4fd1", "pink": "#e35b9f"}.get(k, "#999")


def load_competitors(src, run, our_asin):
    p = Path(src)
    if p.is_dir():
        items = []
        for f in sorted(x for x in p.iterdir() if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")):
            items.append({"asin": "", "title": f.stem, "image": str(f), "price": "", "local_src": f})
        return items
    if p.suffix.lower() in (".html", ".htm"):
        return parse_results(p.read_text(errors="ignore"), our_asin)
    data = json.loads(p.read_text())
    return [{"asin": d.get("asin", ""), "title": d.get("title", d.get("brand", "")), "image": d.get("image", ""),
             "price": d.get("price", ""), "brand": d.get("brand", ""), "domain": d.get("domain") or d.get("website", ""),
             "note": d.get("note", "")} for d in data]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--keyword")
    ap.add_argument("--competitors")
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--logo-urls", help='JSON {"Brand": ["https://...png", ...]}: logo image URLs you found (the browser pane on Bing or Google Images); tried before the web search')
    a = ap.parse_args()
    run = Path(a.run)
    prod = read_json(run / "product.json") or {}
    brief = read_json(run / "brief.json") or {}
    kw = a.keyword or brief.get("shelf_keyword") or prod.get("title", "")[:40]
    host = prod.get("host", "www.amazon.com")
    if a.competitors:
        items = load_competitors(a.competitors, run, prod.get("asin", ""))
        source = a.competitors
    else:
        url = f"https://{host}/s?k={quote_plus(kw)}"
        log(f"Fetching {url} (one attempt)")
        page = curl(url)
        (run / "shelf-page.html").write_text(page or "")
        if blocked(page):
            log("Amazon blocked the search fetch. Open the search in a browser, save the page as HTML, and run "
                "shelf again with --competitors <saved.html> (or a folder of competitor images).")
            sys.exit(2)
        items = parse_results(page, prod.get("asin", ""))
        source = url
    items = items[:a.max]
    tiles = run / "shelf"
    tiles.mkdir(exist_ok=True)
    kept = []
    for i, it in enumerate(items, 1):
        dest = tiles / f"{i:02d}.jpg"
        ok = False
        if it.get("local_src"):
            shutil.copy2(it["local_src"], dest)
            ok = True
        elif it.get("image", "").startswith("http"):
            ok = download(it["image"], dest, min_bytes=1500)
        elif it.get("image") and Path(it["image"]).exists():
            shutil.copy2(it["image"], dest)
            ok = True
        if it.get("domain"):
            ldest = tiles / f"logo-{i:02d}.png"
            if logo_from_site(it["domain"], ldest):
                it["logo"] = f"shelf/{ldest.name}"
                log(f"  {it.get('brand') or it['domain']}: logo from {it['domain']}")
                if not ok:
                    shutil.copy2(ldest, dest)   # no product photo: the logo stands in as the tile
                    ok = True
        if ok:
            it["local"] = f"shelf/{dest.name}"
            kept.append(it)
    log(f"{len(kept)} competitor tiles for \"{kw}\"")
    if not kept:
        sys.exit("no competitor tiles landed")
    cen = census([run / it["local"] for it in kept])
    c = client()
    read, usage = vision_json(c, READ_SHELF.format(kw=kw, brand=prod.get("brand", ""), n=len(kept)),
                              [run / it["local"] for it in kept], max_px=512)
    append_cost(run, "shelf", vision_cost(usage))
    read = read or {}
    read["_brand"] = prod.get("brand", "")
    given = {}
    if a.logo_urls and Path(a.logo_urls).exists():
        given = {k.lower(): (v if isinstance(v, list) else [v]) for k, v in json.loads(Path(a.logo_urls).read_text()).items()}
    web = 0
    for i, it in enumerate(kept, 1):
        if it.get("logo"):
            continue
        b = next((x.get("brand", "") for x in read.get("brands", []) if x.get("tile") == i), "") or it.get("brand", "")
        if not b or b.lower() in ("unknown", "not clear", "not visible"):
            continue
        dest = run / "shelf" / f"logo-{i:02d}.png"
        if logo_from_web(b, dest, c, run, given.get(b.lower(), [])):
            it["logo"] = f"shelf/{dest.name}"
            it["brand"] = b
            it["logo_source"] = "web"
            web += 1
    log(f"{web} competitor logos found on the web")
    logos = crop_logos(run, kept, read, c)
    log(f"{len(logos) - web} competitor marks cut from their photos")
    for it in kept:
        it.pop("local_src", None)
    shelf = {"keyword": kw, "source": source, "tiles": kept, "census": cen, "read": read}
    write_json(run / "shelf.json", shelf)
    (run / "shelf.html").write_text(tiles_sheet(run, kept, cen, read, kw))
    log(f"Colors owned by the shelf: {', '.join(cen['owned']) or 'none dominant'}; free: {', '.join(cen['free'])}")
    for w in read.get("whitespace", []):
        log(f"  whitespace: {w}")
    log(f"wrote {run / 'shelf.html'}")


if __name__ == "__main__":
    main()
