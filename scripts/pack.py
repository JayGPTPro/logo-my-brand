"""Step 8: the kit a seller can upload tomorrow, and the one page that shows all of it.

  kit   <run>     kit/amazon, kit/shopify, kit/social, kit/print, kit/png + kit/README.md (usage rules, hex codes)
  board <run>     board.html: brief, shelf, three directions, the chosen mark, tests, mockups, the kit, next steps

Sizes (checked 18.10.2026 against the Amazon Ads and Shopify help pages and several vendor guides; the
console is the final word, so the README says where each one is uploaded):
  Amazon Brand Store logo        400 x 400 px square, PNG, under 5 MB
  Sponsored Brands logo          400 x 400 px square, PNG, under 1 MB
  Brand Store hero               3000 x 600 px
  Shopify header logo            800 x 200 px transparent PNG (themes show it at about 400 x 100) + SVG
  Shopify / web favicon          48 x 48 px PNG + favicon.ico (16/32/48)
  Social avatar                  1024 x 1024 px, symbol on brand color and on white
  Print                          black SVG + 300 dpi PNG, 3543 px long side (30 cm), one color
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (base_script, esc, file_data_uri, log, now, read_json, run_py, screenshot_html, svg_to_png,  # noqa: E402
                    total_cost)


def kit_files(run):
    fin = read_json(run / "final.json")
    brief = read_json(run / "brief.json")
    kit = run / "kit"
    svg = kit / "svg"
    name = Path(fin["master"]).stem
    main = fin["palette"][0]
    symbol = run / fin["symbol"] if fin.get("symbol") else svg / f"{name}.svg"
    sym_name = Path(symbol).stem
    out = {}
    for d in ("amazon", "shopify", "social", "print", "png"):
        (kit / d).mkdir(parents=True, exist_ok=True)
    # Amazon
    svg_to_png(symbol, kit / "amazon" / "brand-store-logo-400.png", size=400, bg="#ffffff", padding=0.14)
    svg_to_png(symbol, kit / "amazon" / "sponsored-brands-logo-400.png", size=400, bg="#ffffff", padding=0.14)
    svg_to_png(svg / f"{name}.svg", kit / "amazon" / "lockup-on-white-1200.png", width=1200, height=1200, bg="#ffffff", padding=0.12)
    hero_html = run / "mockups" / "amazon-store-header.html"
    if hero_html.exists():
        # The store hero at its real 3000 x 600: the same page, zoomed 2x, so nothing is upsampled.
        zoomed = run / "mockups" / "_hero-3000.html"
        zoomed.write_text(hero_html.read_text().replace("<body>", "<body style='zoom:2;margin:0'>", 1))
        screenshot_html(zoomed, kit / "amazon" / "brand-store-hero-3000x600.png", 3000, 600)
        zoomed.unlink()
    # Shopify / web
    svg_to_png(svg / f"{name}.svg", kit / "shopify" / "header-logo-800x200.png", width=800, height=200, padding=0.05)
    svg_to_png(svg / f"{name}-white.svg", kit / "shopify" / "header-logo-white-800x200.png", width=800, height=200, padding=0.05)
    shutil.copy2(svg / f"{name}.svg", kit / "shopify" / "logo.svg")
    svg_to_png(symbol, kit / "shopify" / "favicon-48.png", size=48, padding=0.04)
    run_py([base_script("render_png.py"), symbol, "--ico", kit / "shopify" / "favicon.ico", "--ico-sizes", 16, 32, 48])
    # Social
    svg_to_png(svg / f"{sym_name}-white.svg" if (svg / f"{sym_name}-white.svg").exists() else svg / f"{name}-white.svg",
               kit / "social" / "avatar-brand-1024.png", size=1024, bg=main, padding=0.22)
    svg_to_png(symbol, kit / "social" / "avatar-white-1024.png", size=1024, bg="#ffffff", padding=0.22)
    svg_to_png(svg / f"{name}.svg", kit / "social" / "cover-1500x500.png", width=1500, height=500, bg="#ffffff", padding=0.2)
    # Print
    for v in ("black", "white"):
        shutil.copy2(svg / f"{name}-{v}.svg", kit / "print" / f"{name}-{v}.svg")
    svg_to_png(svg / f"{name}-black.svg", kit / "print" / f"{name}-black-300dpi.png", width=3543, height=3543, padding=0.05)
    from PIL import Image as _I
    if (kit / "print" / f"{name}-black-300dpi.png").exists():
        _im = _I.open(kit / "print" / f"{name}-black-300dpi.png")
        _im.save(kit / "print" / f"{name}-black-300dpi.png", dpi=(300, 300))
    # Master PNGs: transparent, on white, on dark, on the brand color; lockup and symbol
    for src, base in ((svg / f"{name}.svg", name), (symbol, sym_name)):
        svg_to_png(src, kit / "png" / f"{base}-transparent-2048.png", width=2048, height=2048, padding=0.06)
        svg_to_png(src, kit / "png" / f"{base}-on-white-2048.png", width=2048, height=2048, padding=0.1, bg="#ffffff")
    white_lockup = svg / f"{name}-white.svg"
    white_symbol = svg / f"{sym_name}-white.svg" if (svg / f"{sym_name}-white.svg").exists() else white_lockup
    svg_to_png(white_lockup, kit / "png" / f"{name}-on-dark-2048.png", width=2048, height=2048, padding=0.1, bg="#111111")
    svg_to_png(white_symbol, kit / "png" / f"{sym_name}-on-dark-2048.png", width=2048, height=2048, padding=0.1, bg="#111111")
    svg_to_png(white_lockup, kit / "png" / f"{name}-on-brand-2048.png", width=2048, height=2048, padding=0.1, bg=main)
    svg_to_png(white_lockup, kit / "png" / f"{name}-white-transparent-2048.png", width=2048, height=2048, padding=0.06)
    for stale in (kit / "png" / f"{name}-color-2048.png", kit / "png" / f"{sym_name}-2048.png"):
        if stale.exists():
            stale.unlink()
    # Leftovers from the base exporter that a seller does not need by that name
    for f in list(svg.glob(f"{name}-mono-*.svg")) + list(svg.glob(f"{sym_name}-mono-*.svg")):
        f.unlink()
    onp = [m for m in (read_json(run / "mockups" / "on-product.json") or []) if m.get("ok")]
    for i, m in enumerate(onp, 1):
        src = run / m["file"]
        if src.exists():
            (kit / "png").mkdir(exist_ok=True)
            shutil.copy2(src, kit / "png" / f"on-product-{i}.png")
    symbol_note = ("The symbol file is the first letter of the wordmark, cut out as a monogram for the favicon, the avatar "
                   "and stamps." if fin.get("symbol_is_monogram") else
                   "The symbol file is the mark without the name, for the favicon, the avatar and stamps." if fin.get("symbol") else
                   "This mark has no separate symbol; the favicon and avatar use the whole lockup.")
    onp_note = (f"`png/on-product-1.png` to `png/on-product-{len(onp)}.png` show the mark on your product photos (renders, "
                "not photographs)." if onp else "No on-product render passed review for this run.")
    readme = README.format(brand=brief["brand"], main=main, palette=", ".join(fin["palette"]), name=name, sym=sym_name,
                           date=now(), symbol_note=symbol_note, onp_note=onp_note, fidelity=fin.get("fidelity", ""),
                           surfaces="\n".join(f"- {s['surface']}: {s['method']}, about {s.get('size_mm', '?')} mm"
                                               for s in brief.get("logo_surfaces", [])))
    (kit / "README.md").write_text(readme)
    log(f"kit written to {kit}")
    return kit


README = """# {brand} logo kit

Built {date}. Master files are the SVGs in `svg/`; everything else is exported from them.

## Colors
- Brand color: {main}
- Palette: {palette}
- One-color versions: `svg/{name}-black.svg` (print, engraving), `svg/{name}-white.svg` (dark backgrounds), `svg/{name}-brandcolor.svg`
- {symbol_note}
- The masters are traced from the approved artwork and checked against it (fidelity {fidelity} of 1.0). The letters are drawn shapes, not a font: there is nothing to license.

## Where each file goes
| File | Upload it in |
|---|---|
| `amazon/brand-store-logo-400.png` | Amazon Ads > Stores > Store settings > Brand logo (400 x 400 min, under 5 MB) |
| `amazon/sponsored-brands-logo-400.png` | Sponsored Brands campaign > Creative > Brand logo (same artwork, named for its upload; 400 x 400 min, under 1 MB) |
| `amazon/brand-store-hero-3000x600.png` | Store builder > Header image (3000 x 600) |
| `amazon/lockup-on-white-1200.png` | A+ brand story card, Brand Registry application |
| `shopify/logo.svg` and `shopify/header-logo-800x200.png` | Shopify theme editor > Header > Logo (set the width to about 160 to 200 px) |
| `shopify/favicon-48.png`, `shopify/favicon.ico` | Theme editor > Favicon; any website |
| `social/avatar-brand-1024.png` | Instagram, TikTok, Facebook, Pinterest profile |
| `social/cover-1500x500.png` | X / Facebook cover |
| `print/{name}-black.svg`, `print/{name}-black-300dpi.png` | packaging printer, label maker, embroidery, laser |
| `png/` | 2048 px PNGs: transparent, on white, on dark, on the brand color; lockup and symbol |

## On the product
{surfaces}

## Rules of use
- Clear space around the logo: at least the height of the symbol on every side.
- Minimum size: the horizontal logo 20 mm wide in print and 24 px tall on screen; the symbol alone 8 mm / 16 px.
- Backgrounds: white, the brand color (use the white version), kraft or dark (use the one-color version). Never on a photo without a solid plate behind it.
- Never stretch, rotate, recolor, add shadows, outlines or effects, or set the name in another font next to the mark.

## Before you print 10,000 boxes
- Trademark: search the name and the mark (USPTO TESS, EUIPO, your local registry, and a reverse image search). This kit does not clear trademarks.
- Amazon Brand Registry needs a trademark application or registration; it asks for photos of the product and the packaging with the brand on them. {onp_note} Shoot the real ones once the packaging exists.
- Print vendors who ask for EPS or PDF: open `svg/{name}-black.svg` in Illustrator, Inkscape or Affinity and export; the SVG is the master. Give the printer the hex codes and ask for a one-color proof on the real board.
"""


def board(run):
    """board.html after a pick; review.html before one. First screen: the picks and the verdict. Then why."""
    brief = read_json(run / "brief.json")
    prod = read_json(run / "product.json") or {}
    shelf = read_json(run / "shelf.json") or {}
    judge = read_json(run / "judge.json") or {}
    fin = read_json(run / "final.json") or {}
    opts = read_json(run / "options" / "options.json") or {}
    votes_note = f"""<p class="cost"><b>Buyers voted:</b> {esc(judge.get('votes', {}))}</p>""" if judge.get("votes") else ""
    trends = read_json(run / "trends.json") or {}
    checks = read_json(run / "checks.json") or {}
    system = read_json(run / "kit" / "brand-system" / "system.json") or {}
    onp = read_json(run / "mockups" / "on-product.json") or []
    kit = run / "kit" / "svg"
    name = Path(fin.get("master", "kit/svg/final.svg")).stem
    review = not fin
    rec = judge.get("recommend", "")
    picks = judge.get("picks", {})
    scores = {x["id"]: x for x in judge.get("scores", [])}
    import re as _re
    if judge.get("why"):
        judge["why"] = _re.sub(r"^(%s\s+because\s+)+" % _re.escape(rec), "", judge["why"]).strip() if rec else judge["why"]
        judge["why"] = judge["why"][:1].upper() + judge["why"][1:]
    dir_of = {d["key"]: d for d in brief.get("directions", [])}
    main = (fin.get("palette") or [dir_of.get(rec[:1] if rec else "A", {}).get("palette", ["#111"])[0]])[0]
    img = lambda p: file_data_uri(p) if Path(p).exists() else ""  # noqa: E731
    kind = brief.get("kind", "product")

    # --- pieces
    ranked = sorted((k for k in picks if picks.get(k)), key=lambda k: (-(scores.get(picks[k], {}).get("total", 0)), picks[k] != rec))
    rank_of = {k: i + 1 for i, k in enumerate(ranked)}
    if rec and rec in picks.values():
        rk = next(k for k, v in picks.items() if v == rec)
        if rank_of.get(rk) != 1:   # the recommendation is rank 1 by definition; the table shows the raw totals
            others = [k for k in ranked if k != rk]
            rank_of = {rk: 1, **{k: i + 2 for i, k in enumerate(others)}}
    cnames = {}
    for pr in (read_json(run / "prompts.json") or []):
        cnames[pr.get("id")] = pr.get("name", "")

    def pick_card(k):
        pid = picks.get(k)
        d = dir_of.get(k, {})
        if not pid:
            return ""
        sc = scores.get(pid, {})
        is_rec = pid == rec
        rk = rank_of.get(k, "")
        return f"""<div class="pick{' rec' if is_rec else ''}"><div class="ph"><span class="rank r{rk}">#{rk}</span><span class="k">{esc(k)}</span><span class="nm">{esc(cnames.get(pid) or d.get('name', ''))}</span>{'<span class="tag">recommended</span>' if is_rec else ''}</div>
        <img src="{img(run / 'concepts' / f'{pid}.png')}"><p class="idea">{esc(next((pr['concept'].get('idea', '') for pr in (read_json(run / 'prompts.json') or []) if pr.get('id') == pid and pr.get('concept')), d.get('idea', '')))}</p>
        <p class="why"><b>Score:</b> {sc.get('total', '')}/30 · {esc(sc.get('keep', ''))}</p>
        <p class="why"><b>Why here:</b> {esc(d.get('why_it_wins', ''))}</p><p class="why"><b>Risk:</b> {esc(d.get('risk', ''))}</p>
        <div class="pal">{''.join(f'<i style="background:{c}"></i>' for c in d.get('palette', []))}<span>{esc(' '.join(d.get('palette', [])))}</span></div></div>"""
    cols = ("idea_clarity", "distinct_on_shelf", "simplicity", "craft", "small_size", "fit")
    labels = ("Idea", "Distinct on the shelf", "Simplicity", "Craft", "Small size", "Fit")
    rows = "".join(f"<tr><td>{esc(k)} <small>{esc(picks.get(k, ''))}</small></td>" + "".join(f"<td>{scores.get(picks.get(k), {}).get(c, '')}</td>" for c in cols) + f"<td><b>{scores.get(picks.get(k), {}).get('total', '')}</b></td></tr>" for k in sorted(picks))
    score_table = f"""<table class="sc"><tr><th>Option</th>{''.join(f'<th>{l}</th>' for l in labels)}<th>Total /30</th></tr>{rows}</table>"""
    verdict = f"""<div class="verdict"><div class="vh">Recommendation: {esc(rec)}{(' · ' + esc(dir_of.get(rec[:1], {}).get('name', ''))) if rec else ''}</div>
      <p>{esc(judge.get('why', ''))}</p>{votes_note}{('<p class="cost"><b>The cost of choosing it:</b> ' + esc(judge.get('cost', '')) + '</p>') if judge.get('cost') else ''}
      {('<p class="cost"><b>Today:</b> ' + esc(brief.get('current_mark', '')) + '</p>') if brief.get('current_mark') else ''}</div>"""
    how = """<div class="how"><b>How to choose:</b> say A, B or C (or any tile id from the full sheet below). Want another round first? Answer these four and say "another round":
      1) what you like in each option, 2) what bothers you, 3) which color world, 4) safer or bolder. Twelve new concepts come back steered by that, with these three kept for comparison.
      The final files are built only after that choice: vector masters, one-color and reversed versions, PNGs on transparent, white, dark and brand backgrounds,
      the mark on your product photos, the listing, the Brand Store, the ad, Shopify, packaging and social mockups, and the upload-ready kit.</div>"""

    tiles = "".join(f"<div class='t'><img src='{img(run / t['local'])}'><span>{esc(t['title'][:38])}</span></div>" for t in shelf.get("tiles", [])[:8] if t.get("local"))
    logos = "".join((f"<div class='t lg'><img src='{img(run / t['logo'])}'><span>{esc(t.get('brand', ''))}</span></div>" if t.get("logo")
                     else f"<div class='t lg name'><b>{esc(t.get('brand', '') or t.get('title', '')[:16])}</b><span>{esc(t.get('logo_style', ''))}</span></div>")
                    for t in shelf.get("tiles", [])[:12] if (t.get("logo") or (t.get("brand") and t.get("brand", "").lower() not in ("unknown", "not clear", ""))))
    cen = shelf.get("census", {})
    rd = shelf.get("read", {})
    shelf_section = f"""<section><h2>The shelf: "{esc(shelf.get('keyword', ''))}"</h2>
      <p class="lead">The competitors' marks{' (cut from their own product photos; a name alone means no mark is printed on the product)' if kind != 'business' else ''}:</p><div class="shelf">{logos}</div>
      {('<p class="lead" style="margin-top:14px">The products as the buyer sees them:</p><div class="shelf">' + tiles + '</div>') if tiles and kind != 'business' else ''}
      <div class="two" style="margin-top:14px"><div class="c"><b>Colors already on this shelf:</b> {esc(', '.join(cen.get('owned', [])) or 'none dominant')} &nbsp; <b>free:</b> {esc(', '.join(cen.get('free', [])))}
        <p class="muted">Measured on the competitors' tiles as a buyer sees them: product and packaging colors together.</p><b>Type habits:</b> {esc(rd.get('type_habits', ''))}<ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('visual_habits', []))}</ul></div>
      <div class="c"><b>Whitespace we took</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('whitespace', []))}</ul><b>What would make us disappear</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('avoid', []))}</ul></div></div></section>""" if shelf else ""

    def option_block(key):
        o = opts.get(key)
        if not o:
            return ""
        f = run / o["folder"]
        cells = []
        biz = kind == "business"
        for fn, cap in (("page-one", "page one of Amazon, with us on it"), ("packaging", "box, card, tag, stickers"), ("label-and-box", "label and box"),
                        ("amazon-listing", "listing page"), ("amazon-store-header", "website banner" if biz else "Brand Store header"), ("shopify-home", "website home" if biz else "Shopify home")):
            if (f / f"{fn}.png").exists():
                cells.append(f"<figure><img src='{img(f / (fn + '.png'))}'><figcaption>{cap}</figcaption></figure>")
        if o.get("slide_use") and (run / o["slide_use"]).exists():
            cells.append(f"<figure><img src='{img(run / o['slide_use'])}'><figcaption>in use</figcaption></figure>")
        if o.get("on_product") and (run / o["on_product"]).exists():
            cells.append(f"<figure><img src='{img(run / o['on_product'])}'><figcaption>on the product (render)</figcaption></figure>")
        return f"<div class='optgrid'>{''.join(cells)}</div>"
    option_sections = "".join(f"""<section><h2>Option {esc(k)} in the world: {esc(dir_of.get(k, {}).get('name', ''))}{' · recommended' if opts.get(k, {}).get('id') == rec else ''}</h2>{option_block(k)}</section>"""
                              for k in ("A", "B", "C") if opts.get(k)) if review else ""
    tr = trends.get("read") or {}
    trend_imgs = "".join(f"<div class='t'><img src='{img(run / g['file'])}'></div>" for g in trends.get("sources", [])[:12] if (run / g["file"]).exists())
    trends_section = f"""<section><h2>Where the category's design is going</h2>
      <p class="lead">Measured on {len(trends.get('sources', []))} recent brand identities in "{esc(trends.get('category', ''))}" found on the web, not remembered.</p>
      <div class="verdict" style="margin:0 0 14px"><div class="vh">In one line</div><p>{esc(tr.get('one_line', ''))}</p></div>
      <div class="cards"><div class="c"><b>New brands are moving to</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('moving_to', []))}</ul></div>
      <div class="c"><b>They dropped</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('moving_away_from', []))}</ul><b>Already overused in the new wave</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('overused_now', []))}</ul></div>
      <div class="c"><b>The gap to own</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('gap', []))}</ul></div></div>
      <div class="shelf" style="margin-top:14px;grid-template-columns:repeat(12,1fr)">{trend_imgs}</div></section>""" if tr else ""

    v = checks.get("verdict") or {}
    risk = v.get("risk", "")
    rc = {"low": "#2e8b57", "medium": "#d4a017", "high": "#c0392b"}.get(risk, "#888")
    dom = "".join(f"<li>{esc(d['host'])}: <b style='color:{'#c0392b' if d['taken'] else '#2e8b57'}'>{'taken' if d['taken'] else 'free'}</b></li>" for d in checks.get("domains", []))
    coll = "".join(f"<li>{esc(x)}</li>" for x in v.get("collisions", [])) or "<li>none found</li>"
    tmr = "".join(f"<li>{esc(t.get('mark', ''))}: {esc(t.get('owner', ''))}, {esc(t.get('goods', ''))}, {esc(t.get('status', ''))} ({esc(t.get('office', ''))})</li>" for t in (checks.get("trademark") or {}).get("results", [])) or "<li>no record found in the search (not proof of absence)</li>"
    tml = checks.get("trademark") or {}
    checks_section = f"""<section><h2>Is the name free enough to print?</h2>
      <div class="verdict" style="background:{rc};margin:0 0 14px"><div class="vh" style="color:#fff">Name risk: {esc(risk or '?')}</div><p>{esc(v.get('do_first', ''))}</p></div>
      <div class="cards"><div class="c"><b>Domains</b><ul>{dom}</ul>{('<b>A logo already online under this name</b><br><img src="' + img(run / checks['existing_logo']) + '" style="max-height:80px;margin-top:6px;border:1px solid #eee;border-radius:6px">') if checks.get('existing_logo') else ''}</div>
      <div class="c"><b>Who else uses the name</b><ul>{coll}</ul></div>
      <div class="c"><b>Trademark records</b><ul>{tmr}</ul><p style="font-size:12px;color:#666">Open and verify: <a href="{esc(tml.get('uspto', '#'))}">USPTO</a> · <a href="{esc(tml.get('euipo', '#'))}">EUIPO</a> · <a href="{esc(tml.get('wipo', '#'))}">WIPO</a> · <a href="{esc(tml.get('il', '#'))}">Israel</a>. This is a search, not legal clearance.</p></div></div></section>""" if checks else ""

    bs = run / "kit" / "brand-system"
    sys_imgs = "".join(f"<figure><img src='{img(bs / (n + '.png'))}'><figcaption>{cap}</figcaption></figure>" for n, cap in (
        ("palette", "Color system"), ("type", "Type and voice"), ("listing-01-aplus", "A+ header template"), ("listing-02-benefits", "Benefits infographic template"),
        ("listing-03-lifestyle", "Lifestyle frame with the brand badge"), ("listing-04-whyus", "Why-us comparison template"), ("brand-story", "Brand Story module")) if (bs / f"{n}.png").exists())
    fonts = system.get("fonts", {})
    system_section = f"""<section><h2>The brand system</h2><p class="lead">Fonts: {esc(fonts.get('headline', ''))} for headlines, {esc(fonts.get('body', ''))} for body (Google Fonts, free for commercial use). Templates carry the mark and the real product photo; swap the words, keep the structure.</p>
      <div class="mocks">{sys_imgs}</div></section>""" if sys_imgs else ""

    tp = run / "options" / "test-pack"
    test_section = f"""<section><h2>Before you decide: ask 50 real buyers (optional)</h2><div class="c"><p style="margin:0 0 8px">The three options are packed as neutral tiles in <code>options/test-pack/</code> with a five-question survey (trust, what it sells, memory after 5 seconds, looks expensive, bothers you).
      Run it on PickFu or Prolific (about $50) or on your own customers, write the counts into <code>votes.json</code>, and the review re-ranks on real answers.</p>
      <div class="shelf" style="grid-template-columns:repeat(3,1fr);max-width:720px">{''.join(f"<div class='t'><img src='{img(tp / ('option-' + k + '.png'))}'><span>option {k}</span></div>" for k in ('A', 'B', 'C') if (tp / f'option-{k}.png').exists())}</div></div></section>""" if tp.exists() and review else ""

    brief_section = f"""<section><h2>The brief, read off the {'business' if kind == 'business' else 'product'}</h2><div class="cards">
      <div class="c"><b>Category</b><br>{esc(brief.get('category', ''))} · {esc(brief.get('price_tier', ''))} tier<br><br><b>Adjectives</b><br>{esc(', '.join(brief.get('adjectives', [])))}<br><br><b>Audience</b><br>{esc(brief.get('audience', ''))}</div>
      <div class="c"><b>Where the mark lives</b><ul>{''.join(f"<li>{esc(s['surface'])}: {esc(s['method'])}, ~{esc(s.get('size_mm', '?'))} mm</li>" for s in brief.get('logo_surfaces', []))}</ul></div>
      <div class="c"><b>Cliches we refused</b><ul>{''.join(f'<li>{esc(x)}</li>' for x in brief.get('cliches', [])[:6])}</ul></div></div></section>"""
    sheet_section = f"""<section><h2>All twelve concepts, scored</h2><figure><img src="{img(run / 'concepts.png')}"><figcaption>Four layouts per direction. Gold frame = the recommendation; red "spelling" = disqualified.</figcaption></figure></section>"""

    # --- final (after the pick)
    onp_html = "".join(f"<figure><img src='{img(run / m['file'])}'><figcaption>{esc(m['surface'])} · {esc(m['method'])} (render)</figcaption></figure>" for m in onp if m.get("ok"))
    today = img(run / "originals" / prod["images"][0]) if prod.get("images") else ""
    if onp_html and today:
        onp_html = f"<figure><img src='{today}'><figcaption>today</figcaption></figure>" + onp_html
    mocks = "".join(f"<figure><img src='{img(run / 'mockups' / f'{n}.png')}'><figcaption>{esc(c)}</figcaption></figure>" for n, c in (
        ("page-one", "Page one of Amazon with the brand in it"), ("amazon-store-header", "Website banner" if kind == "business" else "Amazon Brand Store header"), ("amazon-listing", "Listing page with brand byline and brand story card"),
        ("amazon-sponsored-brands", "Sponsored Brands ad"), ("label-and-box", "Label and box"), ("packaging", "Shipping box, thank-you card, hang tag, stickers"),
        ("shopify-home", "Website home" if kind == "business" else "Shopify home"), ("social-avatar", "Profile avatars")) if (run / "mockups" / f"{n}.png").exists())
    files = sorted(str(p.relative_to(run)) for p in (run / "kit").rglob("*") if p.is_file()) if (run / "kit").exists() else []
    chosen = scores.get(fin.get("concept"), {})
    fid = fin.get("fidelity")
    final_sections = "" if review else f"""
    <section><h2>The chosen mark: {esc(fin.get('concept', ''))} · {esc(dir_of.get(str(fin.get('concept', ''))[:1], {}).get('name', ''))}</h2><div class="final">
      <div class="c"><img src="{img(kit / f'{name}.svg')}" style="max-height:420px;object-fit:contain"><div class="sw">{''.join(f'<i style="background:{c}"></i>' for c in fin.get('palette', []))} <span>{esc(' '.join(fin.get('palette', [])))}</span></div></div>
      <div class="c"><b>Why</b><p>{esc(judge.get('why', ''))}</p>{('<b>The cost</b><p>' + esc(judge.get('cost', '')) + '</p>') if judge.get('cost') else ''}<b>What the judge kept</b><p>{esc(chosen.get('keep', ''))}</p><b>Known flaw</b><p>{esc(chosen.get('flaw', ''))}</p>
        <b>Vector master</b><p>Traced from the approved artwork and checked against it: fidelity {esc(fid if fid is not None else '?')} of 1.0{(' · readiness ' + esc(fin.get('audit_score')) + '/100') if fin.get('audit_score') is not None else ''}.</p>
        <div class="two"><figure><img src="{img(kit / f'{name}-black.svg')}" style="background:#fff;padding:14px"><figcaption>one color</figcaption></figure><figure style="background:{main}"><img src="{img(kit / f'{name}-white.svg')}" style="padding:14px"><figcaption style="color:#fff">reversed</figcaption></figure></div></div>
    </div></section>
    {checks_section}{system_section}
    <section><h2>Does it survive the places it has to live?</h2><figure><img src="{img(run / 'mockups' / 'tests.png')}"></figure></section>
    {('<section><h2>On the product</h2><div class="onp">' + onp_html + '</div></section>') if onp_html else ''}
    <section><h2>In the store, in the ad, on the box</h2><div class="mocks">{mocks}</div></section>
    <section><h2>The kit ({len(files)} files; kit/README.md says where each one goes)</h2><div class="c"><ul class="kitlist">{''.join(f'<li>{esc(f)}</li>' for f in files)}</ul></div></section>
    <section><h2>Next steps</h2><div class="c"><ul>
      <li>Trademark search on the name and the mark before anything is printed. This kit does not clear trademarks.</li>
      <li>Amazon Brand Registry: file the trademark, then upload product and packaging photos with the brand visible.</li>
      <li>Packaging: send print/{esc(name)}-black.svg to the printer with the hex codes; ask for a one-color proof on the actual board.</li>
      <li>Keep this folder. The SVG masters are the source; every PNG was exported from them.</li></ul></div></section>"""

    header_logo = f'<img src="{img(kit / f"{name}-white.svg")}">' if not review else ""
    first_screen = "" if not review else f"""<section class="first"><div class="picks">{''.join(pick_card(k) for k in ("A", "B", "C"))}</div>{verdict}{how}</section>
    <section><h2>How the three compare</h2>{score_table}</section>"""
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(brief['brand'])} brand mark</title><style>
    *{{box-sizing:border-box}} body{{margin:0;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;background:#f4f3f0;color:#151515;line-height:1.45}}
    header{{background:{main};color:#fff;padding:46px 56px;display:flex;align-items:center;gap:50px}} header img{{height:150px;max-width:460px}}
    header h1{{margin:0;font-size:32px}} header p{{margin:6px 0 0;opacity:.9;font-size:16px;max-width:680px}}
    main{{padding:34px 56px;max-width:1500px;margin:0 auto}} section{{margin-bottom:44px}}
    h2{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#777;margin:0 0 14px;padding-bottom:8px;border-bottom:1px solid #ddd}}
    .lead{{font-size:13px;color:#666;margin:0 0 8px}} .muted{{font-size:12px;color:#888;margin:4px 0 10px}}
    .cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}} .c{{background:#fff;border-radius:12px;padding:18px;box-shadow:0 1px 2px rgba(0,0,0,.05);font-size:14px}}
    .picks{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}} .pick{{background:#fff;border-radius:14px;padding:16px;border:2px solid transparent;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
    .pick.rec{{border-color:#d4a017;background:#fffdf5}} .pick img{{width:100%;border-radius:8px;border:1px solid #eee;display:block}}
    .ph{{display:flex;align-items:center;gap:10px;margin-bottom:10px}} .rank{{font-size:12px;font-weight:800;color:#fff;background:#999;border-radius:6px;padding:3px 7px}} .rank.r1{{background:#d4a017}} .rank.r2{{background:#8a8a8a}} .rank.r3{{background:#b08968}} .ph .k{{font-size:28px;font-weight:800;color:#bbb}} .ph .nm{{font-size:17px;font-weight:700}} .ph .tag{{margin-left:auto;background:#d4a017;color:#fff;font-size:11px;padding:3px 8px;border-radius:12px;letter-spacing:.04em}}
    .pick .idea{{font-size:14px;margin:10px 0 6px}} .pick .why{{font-size:12.5px;color:#555;margin:0 0 4px}} .pal{{margin-top:8px;font-size:11px;color:#777;display:flex;gap:4px;align-items:center}} .pal i{{display:inline-block;width:14px;height:14px;border-radius:50%;border:1px solid #ddd}}
    .verdict{{margin-top:18px;background:#111;color:#fff;border-radius:12px;padding:18px 22px;font-size:15px}} .verdict .vh{{color:#f3c969;font-weight:700;margin-bottom:6px}} .verdict p{{margin:4px 0}} .verdict .cost{{color:#ccc;font-size:14px}}
    .how{{margin-top:12px;background:#fff;border-radius:12px;padding:14px 18px;font-size:14px;color:#333}}
    .sc{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;font-size:13px}} .sc th,.sc td{{padding:9px 12px;text-align:center;border-bottom:1px solid #eee}} .sc th{{background:#fafafa;font-weight:600;color:#555}} .sc td:first-child,.sc th:first-child{{text-align:left}} .sc small{{color:#999}}
    .shelf{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}} .t{{background:#fff;border-radius:8px;padding:8px;font-size:10px;color:#555;text-align:center}} .t img{{width:100%;height:110px;object-fit:contain}}
    .t.lg{{height:120px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px}} .t.lg img{{max-height:70px;height:auto;object-fit:contain}} .t.lg.name b{{font-size:14px;color:#222}}
    .two{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} ul{{margin:6px 0;padding-left:18px;font-size:14px}}
    figure{{margin:0;background:#fff;border-radius:12px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,.05)}} figure img{{width:100%;border-radius:6px;display:block}} figcaption{{font-size:12px;color:#666;margin-top:8px}}
    .mocks{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .onp{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}} .optgrid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}
    .final{{display:grid;grid-template-columns:1.2fr 1fr;gap:16px}} .final .c img{{width:100%}} .sw{{display:flex;gap:10px;margin-top:10px;align-items:center;font-size:13px;color:#666}} .sw i{{width:34px;height:34px;border-radius:50%;border:1px solid #ddd;display:inline-block}}
    .kitlist{{columns:3;font-size:12px;color:#444}} .kitlist li{{break-inside:avoid}} .meta{{font-size:12px;color:#888;margin-top:30px}}
    </style></head><body>
    <header>{header_logo}<div><h1>{esc(brief['brand'])}{' · three directions for review' if review else ' · brand mark'}</h1><p>{esc(brief.get('product', ''))}</p></div></header>
    <main>
    {first_screen}{final_sections}{brief_section}{shelf_section}{trends_section}{sheet_section if review else ''}{option_sections}{test_section}
    <div class="meta">Built {esc(now())}{(' · source ' + esc(prod.get('source', ''))) if prod.get('source') else ''} · generation spend about ${total_cost(run):.2f}</div>
    </main></body></html>"""
    out = run / ("review.html" if review else "board.html")
    out.write_text(html)
    log(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n, fn in (("kit", lambda a: kit_files(Path(a.run))), ("board", lambda a: board(Path(a.run)))):
        p = sub.add_parser(n)
        p.add_argument("run")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
