"""Step 7: prove the logo works where an e-commerce brand actually lives.

  tests      <run>            tests.html + tests.png: sizes a seller meets (56 px ad tile, 100 px thumb, 20 mm label),
                              one color on kraft, white on brand color, embossed, blurred, mirrored
  composites <run>            HTML mockups rendered with Chrome: Brand Store header, listing page, Sponsored Brands
                              ad, Shopify home, shipping box, thank-you card, hang tag, social avatar
  on-product <run> [--n 3]    gpt-image-2 places the logo ON the real product photo, on the surfaces the brief named
                              (printed on the base, embossed on the lid, on the box front...). One attempt each.

Everything lands in <run>/mockups/. The composites are deterministic (same input, same pixels); the
on-product shots are generated and the SKILL tells the designer to look at each one before showing it.
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (IMAGE_COST, QUALITY, api_size_for, append_cost, client, edit_image, esc, file_data_uri,  # noqa: E402
                    log, read_json, screenshot_html, svg_to_png)


def assets(run, kit_dir=None):
    """Everything the mockups need. kit_dir points at an options/<pick> folder for the checkpoint sheets."""
    fin = read_json((Path(kit_dir) / "final.json") if kit_dir else (run / "final.json"))
    if not fin:
        sys.exit("no final.json; run vectorize first")
    kit = (Path(kit_dir) if kit_dir else run / "kit") / "svg"
    brief = read_json(run / "brief.json")
    name = Path(fin["master"]).stem
    a = {
        "brand": brief["brand"], "brief": brief, "palette": fin["palette"], "main": fin["palette"][0],
        "color": file_data_uri(kit / f"{name}.svg"),
        "black": file_data_uri(kit / f"{name}-black.svg"),
        "white": file_data_uri(kit / f"{name}-white.svg"),
        "symbol": file_data_uri(kit / f"{name}-symbol.svg") if fin.get("symbol") and (kit / f"{name}-symbol.svg").exists() else None,
        "symbol_white": file_data_uri(kit / f"{name}-symbol-white.svg") if fin.get("symbol") and (kit / f"{name}-symbol-white.svg").exists() else None,
        "png": (run / fin["png2048"]) if not kit_dir else Path(fin["png2048"]),
        "fin": fin,
    }
    prod = read_json(run / "product.json") or {}
    a["product_imgs"] = [run / "originals" / n for n in prod.get("images", []) if (run / "originals" / n).exists()]
    good = [run / m["file"] for m in (read_json(run / "mockups" / "on-product.json") or []) if m.get("ok") and (run / m["file"]).exists()]
    a["hero_imgs"] = good + a["product_imgs"]   # the product already wearing the new mark, when a render passed review
    a["product"] = prod
    a["shelf"] = read_json(run / "shelf.json") or {}
    return a


CSS = """
*{box-sizing:border-box} body{margin:0;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;background:#f4f3f0;color:#111}
.wrap{padding:30px 36px} h1{font-size:24px;margin:0 0 4px} .sub{color:#666;font-size:13px;margin-bottom:22px}
.row{display:grid;gap:16px;margin-bottom:18px} .card{background:#fff;border-radius:12px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.card h3{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#888;margin:0 0 10px;font-weight:600}
.lad{display:flex;align-items:flex-end;gap:22px;flex-wrap:wrap} .lad div{text-align:center;font-size:10px;color:#999} .lad img{display:block;margin:0 auto 4px;max-width:360px}
.sw{height:150px;display:flex;align-items:center;justify-content:center;border-radius:8px} .sw img{max-width:70%;max-height:70%}
.kraft{background:#b9966b url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><filter id='n'><feTurbulence baseFrequency='.9' numOctaves='2'/><feColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .08 0'/></filter><rect width='80' height='80' filter='url(%23n)'/></svg>")}
.kraft img{mix-blend-mode:multiply;opacity:.85}
.emboss{background:#e8e3dc} .emboss img{filter:grayscale(1) brightness(1.35) contrast(.6) drop-shadow(-1px -1px 0 rgba(255,255,255,.95)) drop-shadow(1px 1px 1px rgba(0,0,0,.35));opacity:.55}
.deboss{background:#2b2b2b} .deboss img{filter:grayscale(1) brightness(.35) drop-shadow(1px 1px 0 rgba(255,255,255,.18)) drop-shadow(-1px -1px 1px rgba(0,0,0,.9));opacity:.9}
.blur img{filter:blur(4px)} .mirror img{transform:scaleX(-1)}
.phone{width:360px;border:10px solid #111;border-radius:34px;background:#fff;overflow:hidden;margin:0 auto}
.phone .bar{background:#232f3e;color:#fff;padding:10px 12px;font-size:12px;display:flex;align-items:center;gap:8px}
.phone .bar .q{flex:1;background:#fff;border-radius:6px;height:26px}
.ad{background:#fff;border-bottom:1px solid #ddd;padding:10px;display:flex;gap:10px;align-items:center}
.ad .tile{width:56px;height:56px;border:1px solid #e3e3e3;border-radius:6px;display:flex;align-items:center;justify-content:center;flex:none}
.ad .tile img{max-width:46px;max-height:46px} .ad .hl{font-size:12px;line-height:1.3} .ad .hl b{display:block;font-size:13px}
.ad .sp{font-size:9px;color:#777;margin-bottom:2px}
.res{display:flex;gap:10px;padding:10px;border-bottom:1px solid #eee} .res img{width:96px;height:96px;object-fit:contain}
.res .t{font-size:12px;line-height:1.3} .res .t small{color:#007185;display:block;margin-top:2px;font-size:11px}
.label{width:236px;height:118px;background:#fff;border:1px dashed #bbb;display:flex;align-items:center;justify-content:center;margin:0 auto}
.label img{max-width:200px;max-height:90px} .cap{font-size:10px;color:#999;text-align:center;margin-top:6px}
"""


def tests_html(a):
    L = a["color"]
    ladder = "".join(f"<div><img src='{L}' style='height:{h}px'>{h}px</div>" for h in (16, 24, 32, 48, 64, 100, 160))
    shelf = a["shelf"].get("tiles", [])[:3]
    comp = "".join(f"<div class='res'><img src='{file_data_uri(Path(a['run']) / t['local'])}'><div class='t'>{esc(t['title'][:70])}<small>{esc(t.get('price', ''))}</small></div></div>" for t in shelf if t.get("local"))
    prod = a["product_imgs"][0] if a["product_imgs"] else None
    ours = f"<div class='res' style='background:#fffbe8'><img src='{file_data_uri(prod)}'><div class='t'>{esc(a['product'].get('title', a['brand'])[:70])}<small>Visit the {esc(a['brand'])} Store</small></div></div>" if prod else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(a['brand'])} tests</title><style>{CSS}</style></head><body><div class="wrap">
    <h1>{esc(a['brand'])}: the mark at every size and surface</h1>
    <div class="sub">Rendered from the vector master. Every test below is a real size or a real surface.</div>
    <div class="row" style="grid-template-columns:3fr 1fr">
      <div class="card"><h3>Size ladder, from favicon to header</h3><div class="lad">{ladder}</div></div>
      <div class="card"><h3>20 mm label at 300 dpi (236 px)</h3><div class="label"><img src="{L}"></div><div class="cap">a sticker, a woven label, a base plate</div></div>
    </div>
    <div class="row" style="grid-template-columns:repeat(6,1fr)">
      <div class="card"><h3>One color black</h3><div class="sw" style="background:#fff"><img src="{a['black']}"></div></div>
      <div class="card"><h3>White on brand color</h3><div class="sw" style="background:{a['main']}"><img src="{a['white']}"></div></div>
      <div class="card"><h3>One color on kraft</h3><div class="sw kraft"><img src="{a['black']}"></div></div>
      <div class="card"><h3>Embossed</h3><div class="sw emboss"><img src="{a['black']}"></div></div>
      <div class="card"><h3>Debossed in dark</h3><div class="sw deboss"><img src="{a['white']}"></div></div>
      <div class="card"><h3>Squint test</h3><div class="sw blur" style="background:#fff"><img src="{L}"></div></div>
    </div>
    <div class="row" style="grid-template-columns:1fr 1fr 1fr">
      <div class="card"><h3>{'Search ad on a phone' if a['brief'].get('kind') == 'business' else 'Sponsored Brands ad on a phone'} (logo tile at 56 px)</h3>
        <div class="phone"><div class="bar">☰ <div class="q"></div></div>
        <div class="ad"><div class="tile"><img src="{a['symbol'] or L}"></div><div class="hl"><div class="sp">Sponsored</div><b>{esc(a['brand'])}</b>{esc(copy_of(a)['ad'])}</div></div>
        {ours}{comp}</div></div>
      <div class="card"><h3>Mirror and 180° (unintended shapes?)</h3><div class="sw mirror" style="background:#fff"><img src="{L}"></div><div class="sw" style="background:#fff"><img src="{L}" style="transform:rotate(180deg)"></div></div>
      <div class="card"><h3>Symbol alone (favicon, avatar, stamp)</h3><div class="sw" style="background:#fff"><img src="{a['symbol'] or L}"></div>
        <div class="lad" style="justify-content:center"><div><img src="{a['symbol'] or L}" style="height:16px">16</div><div><img src="{a['symbol'] or L}" style="height:32px">32</div><div><img src="{a['symbol'] or L}" style="height:64px">64</div></div></div>
    </div></div></body></html>"""


def cmd_tests(args):
    run = Path(args.run)
    a = assets(run)
    a["run"] = run
    out = run / "mockups"
    out.mkdir(exist_ok=True)
    (out / "tests.html").write_text(tests_html(a))
    screenshot_html(out / "tests.html", out / "tests.png", 1600, 1250)
    log(f"wrote {out / 'tests.png'}")


# ------------------------------------------------------------------ composites
def copy_of(a):
    """The short lines the mockups print: from brief.copy when the brief has it, else safe fallbacks. Never a slice."""
    brief, brand = a["brief"], a["brand"]
    c = brief.get("copy") or {}
    prod = brief.get("product", "")
    short = prod if len(prod) <= 90 else prod[:prod.rfind(" ", 0, 90)] + "."
    return {"tagline": c.get("tagline") or brief.get("category", "").split(":")[-1].strip().capitalize(),
            "card": c.get("card_line") or f"Thank you for choosing {brand}.",
            "ad": c.get("ad_headline") or (c.get("tagline") or brief.get("category", "").split(":")[-1].strip().capitalize()),
            "store": c.get("store_line") or short}


def price_of(a):
    """The listing price when it is a dollar price; Amazon shows the viewer's currency, so a non-dollar
    scrape is dropped rather than shown as ILS on a US listing mockup."""
    p = a["product"].get("price", "")
    return p if p.startswith("$") else ""


def comp_pages(a):
    L, W, B, main = a["color"], a["white"], a["black"], a["main"]
    cp = copy_of(a)
    price = price_of(a)
    sym = a["symbol"] or L
    symw = a["symbol_white"] or W
    hero = a.get("hero_imgs") or a["product_imgs"]
    prod = file_data_uri(hero[0]) if hero else ""
    prod2 = file_data_uri(hero[1]) if len(hero) > 1 else prod
    prod_img = lambda style: (f'<img src="{prod}" style="{style}">' if prod else "")  # noqa: E731
    brand, brief = a["brand"], a["brief"]
    title = a["product"].get("title", brand)
    fin = a["fin"]
    tag = cp["tagline"]
    base = f"<style>*{{box-sizing:border-box}}body{{margin:0;font-family:-apple-system,'Helvetica Neue',Arial,sans-serif;background:#fff}}</style>"
    pages = {}
    # 1. Amazon Brand Store header 3000x600 (rendered at 1500x300)
    pages["amazon-store-header"] = (1500, 300, base + f"""
    <div style="width:1500px;height:300px;background:{main};display:grid;grid-template-columns:520px 1fr 420px;align-items:center;padding:0 70px;gap:40px;overflow:hidden">
      <img src="{W}" style="max-height:150px;max-width:480px;justify-self:start">
      <div style="color:#fff;font-size:28px;line-height:1.3;opacity:.94">{esc(cp['store'])}</div>
      <div style="height:300px;display:flex;align-items:center;justify-content:center;overflow:hidden">{prod_img("max-height:270px;max-width:400px;filter:drop-shadow(0 20px 30px rgba(0,0,0,.25))")}</div>
    </div>""")
    # 2. Listing page, desktop (brand byline + brand story card)
    pages["amazon-listing"] = (1400, 760, base + f"""
    <div style="width:1400px;height:760px;background:#fff;padding:0">
      <div style="background:#131921;height:60px;display:flex;align-items:center;padding:0 24px;gap:18px;color:#fff;font-size:14px"><b style="font-size:18px">amazon</b><div style="flex:1;height:38px;background:#fff;border-radius:6px"></div><span>Hello, sign in</span><span>Returns &amp; Orders</span><span>🛒</span></div>
      <div style="background:#232f3e;height:36px;color:#fff;font-size:13px;display:flex;align-items:center;gap:22px;padding:0 24px"><span>☰ All</span><span>Today's Deals</span><span>Customer Service</span><span>Registry</span><span>Gift Cards</span></div>
      <div style="display:flex;gap:40px;padding:30px 40px">
        <img src="{prod}" style="width:460px;height:460px;object-fit:contain">
        <div style="flex:1">
          <div style="color:#007185;font-size:14px;display:flex;align-items:center;gap:10px"><img src="{sym}" style="height:22px">Visit the {esc(brand)} Store</div>
          <div style="font-size:24px;line-height:1.3;margin:6px 0">{esc(title)}</div>
          <div style="color:#ffa41c;font-size:16px">★★★★★ <span style="color:#007185;font-size:14px">ratings</span></div>
          <div style="font-size:28px;margin:14px 0">{esc(price)}</div>
          <div style="border:1px solid #ddd;border-radius:8px;padding:18px;margin-top:10px;display:flex;gap:18px;align-items:center;background:#fafafa">
            <div style="width:120px;height:120px;background:{main};border-radius:8px;display:flex;align-items:center;justify-content:center;flex:none"><img src="{symw}" style="max-width:84px;max-height:84px"></div>
            <div><div style="font-size:12px;letter-spacing:.08em;color:#888;text-transform:uppercase">From the brand</div><img src="{L}" style="height:40px;margin:6px 0"><div style="font-size:13px;color:#444;max-width:420px">{esc(brief.get('audience', ''))}</div></div>
          </div>
        </div>
        <div style="width:240px;border:1px solid #ddd;border-radius:8px;padding:16px;font-size:13px;height:230px"><div style="font-size:24px">{esc(price)}</div><div style="color:#007600;margin:8px 0">In Stock</div><div style="background:#ffd814;border-radius:20px;padding:9px;text-align:center;margin:8px 0">Add to Cart</div><div style="background:#ffa41c;border-radius:20px;padding:9px;text-align:center">Buy Now</div></div>
      </div></div>""")
    # 3. Sponsored Brands banner (desktop)
    shelf = [t for t in a["shelf"].get("tiles", []) if t.get("local")][:3]
    others = "".join(f"<div style='text-align:center;font-size:12px;width:150px'><img src='{file_data_uri(Path(a['run']) / t['local'])}' style='height:110px'><div style='color:#0f1111;height:32px;overflow:hidden;margin-top:6px'>{esc(t['title'][:40])}</div></div>" for t in shelf)
    pages["amazon-sponsored-brands"] = (1400, 240, base + f"""
    <div style="width:1400px;height:240px;background:#fff;border:1px solid #ddd;display:flex;align-items:center;gap:36px;padding:0 36px">
      <div style="width:150px;height:150px;border:1px solid #e3e3e3;display:flex;align-items:center;justify-content:center;flex:none"><img src="{sym}" style="max-width:120px;max-height:120px"></div>
      <div style="width:330px"><div style="font-size:11px;color:#777">Sponsored</div><div style="font-size:20px;line-height:1.3;color:#0f1111;font-weight:600">{esc(cp['ad'])}</div><div style="color:#007185;font-size:13px;margin-top:8px">Shop {esc(brand)} ›</div></div>
      <div style="text-align:center;font-size:12px;width:150px"><img src="{prod}" style="height:110px"><div style="color:#0f1111;height:32px;overflow:hidden;margin-top:6px">{esc(title[:40])}</div></div>
      {others}
    </div>""")
    # 4. Shopify home
    pages["shopify-home"] = (1400, 820, base + f"""
    <div style="width:1400px;height:820px;background:#fff">
      <div style="height:84px;display:flex;align-items:center;justify-content:space-between;padding:0 60px;border-bottom:1px solid #eee"><img src="{L}" style="height:44px;max-width:260px"><div style="font-size:14px;display:flex;gap:28px;color:#333"><span>Shop</span><span>Our story</span><span>Reviews</span><span>FAQ</span></div><div style="font-size:14px">🔍 &nbsp; 👤 &nbsp; 🛍</div></div>
      <div style="display:flex;height:736px"><div style="flex:1;padding:120px 60px 0 80px"><div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:{main}">{esc(tag)}</div><div style="font-size:52px;line-height:1.08;font-weight:700;margin:16px 0 20px;max-width:520px">{esc(cp['ad'] if len(cp['ad']) < 60 else cp['tagline'])}</div><div style="font-size:17px;color:#555;max-width:460px;line-height:1.5">{esc(brief.get('audience', ''))}</div><div style="display:inline-block;background:{main};color:#fff;padding:16px 34px;border-radius:4px;margin-top:30px;font-size:15px">Shop now</div></div>
      <div style="width:640px;background:{main}22;display:flex;align-items:center;justify-content:center">{prod_img("max-width:520px;max-height:600px") or f'<img src="{sym}" style="width:260px;opacity:.9">'}</div></div>
    </div>""")
    # 5. Shipping box (kraft) + thank-you card + hang tag + sticker
    pages["packaging"] = (1400, 700, base + f"""
    <div style="width:1400px;height:700px;background:#ecebe7;display:flex;align-items:center;justify-content:center;gap:50px">
      <div style="width:520px;height:400px;background:#b9966b;border-radius:6px;box-shadow:inset 0 0 0 2px rgba(0,0,0,.08),0 30px 50px rgba(0,0,0,.18);display:flex;align-items:center;justify-content:center;position:relative"><div style="position:absolute;top:0;left:0;right:0;height:14px;background:rgba(0,0,0,.08)"></div><img src="{B}" style="max-width:300px;max-height:200px;mix-blend-mode:multiply;opacity:.85"></div>
      <div style="display:flex;flex-direction:column;gap:30px">
        <div style="width:360px;height:220px;background:{main};border-radius:4px;box-shadow:0 16px 30px rgba(0,0,0,.18);padding:28px;color:#fff;display:flex;flex-direction:column;justify-content:space-between"><img src="{W}" style="height:52px;align-self:flex-start;max-width:220px"><div style="font-size:15px;line-height:1.4;opacity:.92">{esc(cp['card'])}</div></div>
        <div style="display:flex;gap:30px;align-items:center">
          <div style="width:120px;height:200px;background:#fff;border-radius:6px;box-shadow:0 12px 24px rgba(0,0,0,.15);display:flex;flex-direction:column;align-items:center;padding-top:22px;gap:30px"><div style="width:10px;height:10px;border-radius:50%;border:2px solid #999"></div><img src="{sym}" style="width:80px"></div>
          <div style="width:150px;height:150px;border-radius:50%;background:{main};box-shadow:0 12px 24px rgba(0,0,0,.18);display:flex;align-items:center;justify-content:center"><img src="{symw}" style="width:96px"></div>
          <div style="width:150px;height:150px;border-radius:50%;background:#fff;box-shadow:0 12px 24px rgba(0,0,0,.12);display:flex;align-items:center;justify-content:center"><img src="{sym}" style="width:96px"></div>
        </div></div>
    </div>""")
    # 5b. A flat label and a box face: the two print surfaces every packaged product has
    pages["label-and-box"] = (1400, 620, base + f"""
    <div style="width:1400px;height:620px;background:#ecebe7;display:flex;align-items:center;justify-content:center;gap:60px">
      <div style="width:560px;height:360px;background:#fff;border-radius:18px;box-shadow:0 20px 40px rgba(0,0,0,.14);border:1px solid #ddd;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;padding:30px">
        <img src="{L}" style="max-height:150px;max-width:440px"><div style="font-size:15px;letter-spacing:.14em;text-transform:uppercase;color:#444">{esc(cp['tagline'])}</div>
        <div style="font-size:12px;color:#888">{esc(title[:70])}</div></div>
      <div style="width:400px;height:460px;background:{main};border-radius:8px;box-shadow:0 30px 50px rgba(0,0,0,.22);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px;padding:40px;position:relative">
        <div style="position:absolute;top:0;left:0;right:0;height:18px;background:rgba(0,0,0,.14)"></div>
        <img src="{W}" style="max-height:140px;max-width:300px"><div style="color:#fff;font-size:14px;opacity:.9;text-align:center;line-height:1.4">{esc(cp['store'])}</div></div>
    </div>""")
    # The real page one with our product in it: the one proof a seller asks for
    grid_tiles = [t for t in a["shelf"].get("tiles", []) if t.get("local")][:7]
    if prod and grid_tiles:
        ours = f"""<div class="pt" style="background:#fffbea"><img src="{prod}"><div class="b"><img src="{sym}" style="height:16px;vertical-align:middle;margin-right:6px">{esc(brand)}</div><div class="tt">{esc(title[:62])}</div><div class="pr">{esc(price or '')}</div></div>"""
        tiles_html = "".join(f"""<div class="pt"><img src="{file_data_uri(Path(a['run']) / t['local'])}"><div class="b">{esc(t.get('brand', '') or '')}</div><div class="tt">{esc(t['title'][:62])}</div><div class="pr">{esc(t.get('price', ''))}</div></div>""" for t in grid_tiles)
        parts = tiles_html.split('<div class="pt">')
        inserted = '<div class="pt">'.join(parts[:4]) + ours + '<div class="pt">' + '<div class="pt">'.join(parts[4:]) if len(parts) > 4 else tiles_html + ours
        pages["page-one"] = (1400, 760, base + f"""
        <style>.pt{{background:#fff;border:1px solid #e3e3e3;border-radius:8px;padding:12px;font-size:12px;display:flex;flex-direction:column;gap:6px}} .pt img{{height:170px;object-fit:contain}} .pt .b{{color:#565959;font-size:11px}} .pt .tt{{color:#0f1111;line-height:1.3;height:32px;overflow:hidden}} .pt .pr{{font-weight:700;font-size:15px}}</style>
        <div style="width:1400px;height:760px;background:#fff;padding:0 24px">
          <div style="height:46px;display:flex;align-items:center;gap:14px;border-bottom:1px solid #eee;font-size:13px;color:#565959;margin-bottom:14px">Results for <b style="color:#c45500">{esc(a['shelf'].get('keyword', ''))}</b></div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px">{inserted}</div></div>""")
    # 6. Social avatars (IG/TikTok profile)
    pages["social-avatar"] = (1000, 340, base + f"""
    <div style="width:1000px;height:340px;background:#fff;display:flex;align-items:center;gap:60px;padding:0 70px">
      <div style="width:200px;height:200px;flex:none;border-radius:50%;background:{main};display:flex;align-items:center;justify-content:center;border:4px solid #fff;box-shadow:0 0 0 2px #e1306c"><img src="{symw}" style="width:120px"></div>
      <div><div style="font-size:26px;font-weight:600">{esc(brand.lower().replace(' ', ''))}</div><div style="color:#555;font-size:15px;margin:6px 0 14px;max-width:460px">{esc(cp['store'])}</div><div style="display:flex;gap:30px;font-size:15px;color:#777"><span>posts</span><span>followers</span><span>following</span></div></div>
      <div style="margin-left:auto;display:flex;gap:16px"><div style="width:64px;height:64px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center"><img src="{symw}" style="width:40px"></div><div style="width:64px;height:64px;border-radius:14px;background:{main};display:flex;align-items:center;justify-content:center"><img src="{symw}" style="width:40px"></div><div style="width:64px;height:64px;border-radius:50%;background:#fff;border:1px solid #ddd;display:flex;align-items:center;justify-content:center"><img src="{sym}" style="width:40px"></div></div>
    </div>""")
    return pages


NEEDS_PHOTO = ("amazon-listing", "amazon-sponsored-brands", "page-one")


def cmd_composites(args):
    run = Path(args.run)
    a = assets(run)
    a["run"] = run
    out = run / "mockups"
    out.mkdir(exist_ok=True)
    for name, (w, h, html) in comp_pages(a).items():
        if name in NEEDS_PHOTO and not a["product_imgs"] and name != "shopify-home":
            continue
        (out / f"{name}.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'></head><body>{html}</body></html>")
        screenshot_html(out / f"{name}.html", out / f"{name}.png", w, h)
        log(f"  {name}.png  {w}x{h}")
    log(f"composites in {out}")


# ------------------------------------------------------------------ on-product (generated)
PLACE = """Two images are given. The first is a product photo. The second is the exact brand logo artwork of "{brand}":
copy it faithfully, same shapes, same letterforms, same proportions, nothing redrawn or simplified. {describe}
Apply the logo to the product in the first image: on the {surface}, {method}, clearly visible, about {size} wide
(roughly {frac} of the product's width), in the position a real brand mark sits on this kind of product. If that
surface is not visible, put it where a brand mark naturally sits on the visible product. {finish}
Any brand name, logo or label text already on the product is removed and replaced by this logo; nothing else is added.
Keep everything else in the photo exactly as it is: the product, its colors, the props, the background, the framing.
The logo stays sharp, undistorted, correctly spelled "{brand}"."""

FINISH = {
    "laser": "Render it as a laser engraving: dark burnt lines into the material, crisp edges, the grain visible through it.",
    "engraved": "Render it as an engraving cut into the material, with real depth and a shadow inside the cut.",
    "embossed": "Render it raised in the product's own material, tone on tone, catching light on its top edges.",
    "debossed": "Render it pressed into the product's own material, tone on tone, with soft shadow inside.",
    "printed": "Render it printed flat on the surface, following the surface's curve and lighting.",
    "foil": "Render it as metallic foil, flat, with the foil's soft specular highlight.",
    "sticker": "Render it as a printed label applied flat to the surface.",
    "hang tag": "Render it printed on a paper hang tag attached to the product.",
    "woven label": "Render it as a woven textile label stitched to the product.",
}


def cmd_on_product(args):
    run = Path(args.run)
    place_on_product(run, assets(run), run / "mockups", args.n)


def place_on_product(run, a, out, n=3, prefix="on-product"):
    out.mkdir(parents=True, exist_ok=True)
    if (out / f"{prefix}.json").exists():
        log(f"{prefix} renders exist (delete {out / (prefix + '.json')} to redo them)")
        return
    surfaces = a["brief"].get("logo_surfaces", [])[:n]
    if not a["product_imgs"] or not surfaces:
        log("no product photos: skipping the on-product renders")
        (out / f"{prefix}.json").write_text("[]")
        return
    from PIL import Image
    c = client()
    logo_color = a["png"]
    master = Path(a["fin"]["master"])
    kit = (run / master).parent if not master.is_absolute() else master.parent
    name = master.stem
    logo_black = out / f"_{prefix}-logo-black.png"
    logo_white = out / f"_{prefix}-logo-white.png"
    svg_to_png(kit / f"{name}-black.svg", logo_black, width=1024, height=1024, padding=0.1)
    svg_to_png(kit / f"{name}-white.svg", logo_white, width=1024, height=1024, padding=0.1, bg="#000000")
    roles = a["brief"].get("photo_roles", [])
    usable = [p for p, r in zip(a["product_imgs"], roles) if r in ("packshot", "packaging")] or \
        [p for p, r in zip(a["product_imgs"], roles) if r == "lifestyle"] or a["product_imgs"][:1]
    jobs = []
    for i, s in enumerate(surfaces, 1):
        surf = s.get("surface", "front").lower()
        if any(k in surf for k in ("box", "pack", "carton", "sleeve", "bag", "pouch")):
            pk = [p for p, r in zip(a["product_imgs"], roles) if r == "packaging"]
            photo = pk[0] if pk else usable[0]
        else:
            photo = usable[(i - 1) % len(usable)]
        method = str(s.get("method", "printed")).lower()
        colors = s.get("colors_available", "full")
        if method in ("embossed", "debossed", "engraved", "laser"):
            logo = logo_black
        elif colors == 1 or method in ("woven label",):
            logo = logo_black
        else:
            logo = logo_color
        finish = next((v for k, v in FINISH.items() if k in method), FINISH["printed"])
        if logo is logo_black and method not in ("embossed", "debossed", "engraved", "laser"):
            finish += " Print it in ONE color: the logo's main color, or white when the surface is dark."
        with Image.open(photo) as im:
            size = api_size_for(*im.size)
        mm = s.get("size_mm") or 40
        try:
            frac = f"{max(15, min(45, int(100 * float(mm) / 200)))}%"
        except (TypeError, ValueError):
            frac = "20%"
        fin = a["fin"]
        idea = next((d.get("idea", "") for d in a["brief"].get("directions", []) if str(fin.get("concept", "")).lstrip("P").startswith(d.get("key", "?"))), "")
        describe = f"The logo is: {idea}" if idea else ""
        prompt = PLACE.format(brand=a["brand"], surface=s.get("surface", "front"), method=method, size=f"{mm} mm", frac=frac,
                              finish=finish, describe=describe)
        jobs.append((i, s, photo, logo, prompt, size))
    log(f"Placing the logo on {len(jobs)} surfaces (about ${len(jobs) * IMAGE_COST.get(QUALITY, 0.02) * 1.5:.2f})")

    def one(j):
        i, s, photo, logo, prompt, size = j
        dest = out / f"{prefix}-{i}.png"
        r = edit_image(c, prompt, [photo, logo], dest, size=size)
        if r:
            append_cost(run, f"{prefix} {i}", IMAGE_COST.get(QUALITY, 0.02) * 1.5, s.get("surface", ""))
        return i, s, bool(r)

    manifest = []
    with ThreadPoolExecutor(3) as ex:
        made = list(ex.map(one, jobs))
    # One look decides what may be shown: the NEW mark present and readable, the old mark gone, the product intact.
    from common import vision_cost, vision_json
    renders = [(i, s, out / f"{prefix}-{i}.png", photo) for (i, s, photo, *_), (_, _, ok) in zip(jobs, made) if ok]
    verdict = {}
    if renders:
        imgs = [a["png"]] + [x for _, _, f, ph in renders for x in (ph, f)]
        q = (f'Image 1 is the NEW logo of "{a["brand"]}". Then come {len(renders)} pairs: an ORIGINAL product photo followed by an EDITED '
             'version that should carry the new logo. For each pair, in order, return {"i": pair number from 1, "ok": true/false, "issue": "under 10 words or empty"}. '
             'ok only when the edited image clearly shows the NEW logo (not the old mark, not a redrawn variant), the product is otherwise unchanged '
             '(shape, lights, colors, parts all intact), and no extra text was added. Return JSON {"pairs": [...]}.')
        res, usage = vision_json(c, q, imgs, max_px=640)
        append_cost(run, f"{prefix} qa", vision_cost(usage))
        verdict = {x.get("i"): x for x in (res or {}).get("pairs", [])}
    k = 0
    for (i, s, photo, *_), (_, _, ok) in zip(jobs, made):
        issue = ""
        if ok:
            k += 1
            v = verdict.get(k, {})
            ok = bool(v.get("ok"))
            issue = v.get("issue", "")
        log(f"  {prefix}-{i}.png  {s.get('surface')} ({s.get('method')})  {'ok' if ok else 'REJECTED ' + issue}")
        manifest.append({"file": str((out / f"{prefix}-{i}.png").relative_to(run)), "surface": s.get("surface"), "method": s.get("method"),
                         "ok": ok, "issue": issue, "source": str(Path(photo).relative_to(run)) if str(photo).startswith(str(run)) else str(photo)})
    (out / f"{prefix}.json").write_text(json.dumps(manifest, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("tests", cmd_tests), ("composites", cmd_composites)):
        p = sub.add_parser(name)
        p.add_argument("run")
        p.set_defaults(fn=fn)
    p = sub.add_parser("on-product")
    p.add_argument("run")
    p.add_argument("--n", type=int, default=3)
    p.set_defaults(fn=cmd_on_product)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
