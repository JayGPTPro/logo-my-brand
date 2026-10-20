"""The one page per brand: <run>/brand.html (+ assets/), in two states.

  page <run>

choose     before a pick: hero with the three marks, the recommendation, the three options in ranked order with
           identical frames, side by side at real sizes, how to choose or ask for another round, then the brief,
           the shelf, the trend read and every concept in an appendix.
delivered  after a pick (final.json exists): the chosen mark, the name check, the system, stress tests, the mark in
           the world, the listing templates, the kit as download tiles with a zip, next steps, and the appendix with
           everything that led here.

Images are written once to assets/ as JPEG (photos, mockups) or copied SVG (marks), lazy-loaded, so the page is a
few MB instead of 20. The same file is rewritten in place when the state changes; nothing else is ever produced.
"""
import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import esc, log, now, read_json, total_cost  # noqa: E402


class Assets:
    def __init__(self, run):
        self.run = Path(run)
        self.dir = self.run / "assets"
        if self.dir.exists():
            shutil.rmtree(self.dir)   # every build writes only what the page uses
        self.dir.mkdir()

    def __call__(self, p, w=1600):
        """Relative URL of a web copy of p (JPEG for raster, the file itself for SVG). '' when p is missing."""
        p = Path(p)
        if not p.is_absolute():
            p = self.run / p
        if not p.exists():
            return ""
        h = hashlib.sha1(f"{p}:{p.stat().st_mtime}:{w}".encode()).hexdigest()[:12]
        if p.suffix.lower() == ".svg":
            dest = self.dir / f"{h}.svg"
            if not dest.exists():
                shutil.copy2(p, dest)
            return f"assets/{dest.name}"
        from PIL import Image
        try:
            im = Image.open(p)
            alpha = im.mode in ("RGBA", "LA", "P") and im.convert("RGBA").split()[3].getextrema()[0] < 250
        except Exception:
            return ""
        dest = self.dir / f"{h}.{'png' if alpha else 'jpg'}"
        if not dest.exists():
            try:
                im.thumbnail((w, w))
                if alpha:   # transparent art stays transparent (a white logo must not become a white box)
                    im.convert("RGBA").save(dest, "PNG", optimize=True)
                else:
                    im.convert("RGB").save(dest, "JPEG", quality=84, optimize=True, progressive=True)
            except Exception:
                return ""
        return f"assets/{dest.name}"


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cmyk(h):
    r, g, b = (x / 255 for x in rgb(h))
    k = 1 - max(r, g, b)
    if k >= 1:
        return (0, 0, 0, 100)
    return tuple(round(100 * x) for x in ((1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k))


def ink_on(h):
    r, g, b = rgb(h)
    return "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 160 else "#ffffff"


CSS = """
:root{--paper:#fafaf8;--ink:#111;--mute:#6b6b6b;--line:#e6e4df;--soft:#f1efea}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,system-ui,-apple-system,sans-serif;font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
img{max-width:100%;display:block}a{color:inherit}
.nav{position:sticky;top:0;z-index:20;background:rgba(250,250,248,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav .in{max-width:1440px;margin:0 auto;padding:0 32px;height:56px;display:flex;align-items:center;gap:28px}
.nav .bn{font-family:'Inter Tight',Inter,sans-serif;font-weight:700;letter-spacing:-.01em;margin-right:auto;display:flex;align-items:center;gap:10px}
.nav .bn img{height:22px;width:auto}
.nav a.l{font-size:14px;color:var(--mute);text-decoration:none;white-space:nowrap}.nav a.l:hover{color:var(--ink)}
.wrap{max-width:1440px;margin:0 auto;padding-left:32px;padding-right:32px}
section,section.wrap{padding-top:120px}
.eyebrow{font-size:13px;color:var(--mute);letter-spacing:.02em;margin-bottom:14px}
h1,h2,h3{font-family:'Inter Tight',Inter,sans-serif;letter-spacing:-.025em;line-height:1.05;margin:0}
h1{font-size:clamp(44px,6vw,96px);font-weight:700}
h2{font-size:clamp(32px,3.6vw,52px);font-weight:700;margin-bottom:22px}
h3{font-size:24px;font-weight:650;letter-spacing:-.015em;margin-bottom:8px}
.lede{font-size:20px;line-height:1.5;max-width:65ch;color:#2a2a2a}
.txt{max-width:65ch}
.hero{padding-top:72px}
.hero .marks{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:48px}
.hero .mk{background:#fff;border:1px solid var(--line);aspect-ratio:4/3;display:flex;align-items:center;justify-content:center;padding:9%;position:relative}
.hero .mk img{max-height:100%;object-fit:contain}
.hero .mk .tag{position:absolute;left:14px;top:12px;font-size:13px;color:var(--mute)}
.hero .mk.rec{outline:2px solid var(--ink);outline-offset:-2px}
.band{background:var(--ink);color:#fff;padding:56px 0;margin-top:96px}
.band .in{max-width:1440px;margin:0 auto;padding:0 32px;display:grid;grid-template-columns:1.1fr 1fr;gap:56px;align-items:start}
.band h2{color:#fff;margin-bottom:10px}.band p{color:#d8d8d8;max-width:60ch;margin:0 0 12px}.band b{color:#fff}
.chips{display:flex;gap:10px;flex-wrap:wrap}.chip{border:1px solid #444;border-radius:999px;padding:6px 14px;font-size:14px;color:#ddd}
.chip.on{background:#fff;color:#111;border-color:#fff}
.opt{padding-top:96px;border-top:1px solid var(--line);margin-top:96px}
.opt .head{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;margin-bottom:26px}
.opt .rank{font-size:14px;font-weight:700;background:var(--ink);color:#fff;border-radius:999px;padding:4px 12px}
.opt .score{color:var(--mute);font-size:15px}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.field{aspect-ratio:3/2;display:flex;align-items:center;justify-content:center;padding:12%}
.field img{max-height:100%;object-fit:contain}
.tri{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:20px}
.tri img,.duo img.ph{width:100%;aspect-ratio:3/2;object-fit:cover}
.meta{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:40px;margin-top:30px}
.meta p{margin:0 0 6px;color:#333}.meta .k{font-size:13px;color:var(--mute);margin-bottom:6px}
.sw{display:flex;gap:8px;margin-top:4px}.sw i{width:40px;height:40px;border-radius:50%;border:1px solid var(--line);display:inline-block}
.cap{font-size:13px;color:var(--mute);margin-top:8px}
table.cmp{width:100%;border-collapse:collapse;margin-top:10px}
table.cmp th{font-weight:600;text-align:left;font-size:14px;color:var(--mute);padding:10px 12px;border-bottom:1px solid var(--line)}
table.cmp td{padding:16px 12px;border-bottom:1px solid var(--line);vertical-align:middle}
table.cmp td.lab{font-size:14px;color:var(--mute);width:180px}
.cell{display:flex;align-items:center;gap:14px;min-height:40px}
.ask{background:#fff;border:1px solid var(--line);padding:36px;margin-top:24px}
.ask ol{margin:12px 0 0;padding-left:20px}.ask li{margin-bottom:6px}
.grid6{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}
.lg{background:#fff;border:1px solid var(--line);aspect-ratio:3/2;display:flex;align-items:center;justify-content:center;padding:14%}
.lg img{max-height:100%;object-fit:contain}
.prod{background:#fff;border:1px solid var(--line);aspect-ratio:1;display:flex;align-items:center;justify-content:center;padding:8%}
.prod img{max-height:100%;object-fit:contain}
.cols3{display:grid;grid-template-columns:repeat(3,1fr);gap:40px}
.cols3 ul{margin:8px 0 0;padding-left:18px}.cols3 li{margin-bottom:6px;color:#333}
details{border-top:1px solid var(--line);padding:26px 0}details summary{cursor:pointer;font-family:'Inter Tight',Inter,sans-serif;font-size:22px;font-weight:650;list-style:none}
details summary::after{content:' +';color:var(--mute)}details[open] summary::after{content:' −'}
.full{width:100%;margin-top:20px}
.color{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:0}
.color .c{aspect-ratio:1;padding:18px;display:flex;flex-direction:column;justify-content:flex-end;font-size:13px}
.color .c b{font-size:16px;margin-bottom:6px}
.kit{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.tile{background:#fff;border:1px solid var(--line);padding:14px;text-decoration:none;display:flex;flex-direction:column;gap:10px}
.tile .pv{aspect-ratio:4/3;background:var(--soft);display:flex;align-items:center;justify-content:center;padding:12%}
.tile .pv img{max-height:100%;object-fit:contain}.tile b{font-size:14px}.tile span{font-size:12px;color:var(--mute)}
.btn{display:inline-block;background:var(--ink);color:#fff;text-decoration:none;padding:14px 26px;font-weight:600;margin-top:10px}
.grouph{font-size:13px;color:var(--mute);margin:30px 0 12px}
.risk{display:inline-block;padding:6px 14px;border-radius:999px;color:#fff;font-weight:600;font-size:14px}
footer{padding:96px 0 64px;color:var(--mute);font-size:13px}
@media (max-width:900px){.wrap,.nav .in,.band .in{padding-left:16px;padding-right:16px}.hero .marks,.tri,.duo,.meta,.cols3,.band .in{grid-template-columns:1fr}
.grid6{grid-template-columns:repeat(3,1fr)}.kit{grid-template-columns:repeat(2,1fr)}.nav a.l{display:none}section,section.wrap{padding-top:72px}.opt{margin-top:64px;padding-top:64px}}
"""


def guidelines(run, brand, fin, system, A, mark_line):
    """A dedicated landscape guidelines document, one topic per page: the PDF in the kit."""
    kit = run / "kit" / "svg"
    nm = Path(fin.get("master", "kit/svg/final.svg")).stem
    pal = fin.get("palette") or ["#111111"]
    main = pal[0]
    f = fin.get("font") or {}
    sym = run / fin["symbol"] if fin.get("symbol") else kit / f"{nm}.svg"
    sp = system.get("palette") or {}
    colors = [("Brand", main)] + [("Ink", (sp.get("neutrals") or {}).get("ink", "#151515")), ("Paper", (sp.get("neutrals") or {}).get("paper", "#f6f3ee"))] + \
             [("Accent", x.get("hex") if isinstance(x, dict) else x) for x in (sp.get("accents") or [])]
    fonts = system.get("fonts") or {}
    pg = lambda inner: f'<section class="pg">{inner}<div class="ft">{esc(brand)} · Brand guidelines</div></section>'  # noqa: E731
    lock = A(kit / f"{nm}.svg")
    pages = [
        pg(f'<div style="background:{main};position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:80px"><img src="{A(kit / (nm + "-white.svg")) if ink_on(main) == "#ffffff" else lock}" style="max-width:640px"><p style="color:{ink_on(main)};font-size:20px;max-width:640px;margin-top:40px">{esc(mark_line)}</p><div style="color:{ink_on(main)};opacity:.7;margin-top:30px">Brand guidelines</div></div>'),
        pg(f'<h2>The mark</h2><div class="g2"><div class="bx"><img src="{lock}"></div><div class="bx"><img src="{A(kit / (nm + "-stacked.svg")) or lock}"></div><div class="bx"><img src="{A(sym)}"></div><div class="bx"><img src="{A(kit / (nm + "-wordmark.svg")) or lock}"></div></div><p class="c">Horizontal is the default. Stacked for square spaces. The symbol alone for favicons, avatars and stamps.</p>'),
        pg(f'<h2>Clear space and minimum size</h2><div class="g2"><div class="bx" style="padding:0"><div style="border:2px dashed #c33;padding:9%;display:inline-block;background:#fff"><img src="{lock}" style="max-width:420px"></div></div><div><p class="c" style="font-size:16px">Keep empty space around the logo equal to the height of the symbol on every side. Nothing enters that area: no text, no edges, no other marks.</p><div style="display:flex;gap:30px;align-items:flex-end;margin-top:30px"><div><img src="{lock}" style="height:24px;width:auto"><p class="c">24 px on screen</p></div><div><img src="{A(sym)}" style="height:16px;width:auto"><p class="c">symbol: 16 px</p></div></div><p class="c">In print: the horizontal logo at least 20 mm wide.</p></div></div>'),
        pg('<h2>Color</h2><div class="cl">' + "".join(f'<div style="background:{h};color:{ink_on(h)}"><b>{esc(n)}</b><span>{esc(h)}<br>RGB {",".join(str(x) for x in rgb(h))}<br>CMYK {"/".join(str(x) for x in cmyk(h))}</span></div>' for n, h in colors if h and str(h).startswith("#")) + '</div><p class="c">CMYK values are a starting point; ask the printer for a proof on the real material.</p>'),
        pg(f'<h2>Typography</h2><div class="g2"><div><div class="c">Headlines and logo</div><div style="font-size:44px;font-weight:700">{esc(fonts.get("headline") or f.get("family") or "")}</div><div class="c" style="margin-top:20px">Body</div><div style="font-size:30px">{esc(fonts.get("body", ""))}</div><p class="c" style="margin-top:20px">Both are on Google Fonts and free for commercial use.</p></div><div><img src="{A(kit / (nm + "-wordmark.svg")) or lock}"></div></div>'),
        pg(f'<h2>On backgrounds</h2><div class="g3"><div class="bx"><img src="{lock}"></div><div class="bx" style="background:{main}"><img src="{A(kit / (nm + "-white.svg"))}"></div><div class="bx" style="background:#111"><img src="{A(kit / (nm + "-white.svg"))}"></div><div class="bx"><img src="{A(kit / (nm + "-black.svg"))}"></div><div class="bx" style="background:#b9966b"><img src="{A(kit / (nm + "-black.svg"))}"></div><div class="bx" style="background:{main}"><img src="{A(kit / (nm + "-black.svg"))}" style="opacity:.0"></div></div><p class="c">Full color on white; white on the brand color or on dark; one color black on kraft and in print.</p>'),
        pg(f'<h2>Do not</h2><div class="g3">' + "".join(f'<div class="bx" style="position:relative"><img src="{lock}" style="{st}"><span class="x">{cap}</span></div>' for st, cap in (("transform:scaleX(1.5)", "stretch it"), ("transform:rotate(-12deg)", "rotate it"), ("filter:drop-shadow(6px 6px 4px rgba(0,0,0,.6))", "add shadows or effects"), ("filter:hue-rotate(120deg)", "recolor it"), ("opacity:.35", "fade it"), ("outline:3px solid #000;outline-offset:6px", "box or outline it"))) + '</div>'),
    ]
    css = """@page{size:A4 landscape;margin:0}*{box-sizing:border-box}body{margin:0;font-family:Inter,sans-serif;color:#111}
    .pg{width:297mm;height:210mm;position:relative;padding:22mm 24mm;page-break-after:always;overflow:hidden;background:#fff}
    h2{font-family:'Inter Tight',Inter,sans-serif;font-size:34px;letter-spacing:-.02em;margin:0 0 18px}.ft{position:absolute;left:24mm;bottom:10mm;font-size:10px;color:#888}
    .g2{display:grid;grid-template-columns:1fr 1fr;gap:14px}.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    .bx{border:1px solid #e6e4df;height:55mm;display:flex;align-items:center;justify-content:center;padding:8%}.bx img{max-height:100%;max-width:100%}
    .g2 .bx{height:62mm}.c{font-size:12px;color:#666;margin:10px 0 0}.x{position:absolute;bottom:6px;left:10px;font-size:11px;color:#b3261e;font-weight:600}
    .cl{display:grid;grid-template-columns:repeat(auto-fit,minmax(40mm,1fr));height:110mm}.cl div{padding:12px;display:flex;flex-direction:column;justify-content:flex-end;font-size:11px}.cl b{font-size:15px;margin-bottom:6px}"""
    return f'<!doctype html><html><head><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Inter+Tight:wght@700&display=swap" rel="stylesheet"><style>{css}</style></head><body>{"".join(pages)}</body></html>'


def build(run):
    run = Path(run)
    A = Assets(run)
    brief = read_json(run / "brief.json") or {}
    prod = read_json(run / "product.json") or {}
    shelf = read_json(run / "shelf.json") or {}
    trends = read_json(run / "trends.json") or {}
    judge = read_json(run / "judge.json") or {}
    prompts = {p["id"]: p for p in (read_json(run / "prompts.json") or [])}
    opts = read_json(run / "options" / "options.json") or {}
    fin = read_json(run / "final.json") or {}
    checks = read_json(run / "checks.json") or {}
    system = read_json(run / "kit" / "brand-system" / "system.json") or {}
    brand = brief.get("brand") or prod.get("brand", "Brand")
    delivered = bool(fin)
    picks = judge.get("picks", {})
    rec = judge.get("recommend", "")
    scores = {x["id"]: x for x in judge.get("scores", [])}
    dir_of = {d["key"]: d for d in brief.get("directions", [])}

    def key_of(pid):
        return (pid or "").lstrip("P")[:1]

    order = sorted(picks, key=lambda k: (picks[k] != rec, -(scores.get(picks[k], {}).get("total", 0))))
    rank = {k: i + 1 for i, k in enumerate(order)}

    def mark_of(k, white=False):
        o = opts.get(k) or {}
        f = run / o.get("folder", "") / "svg" / ("logo-white.svg" if white else "logo.svg")
        if f.exists():
            return A(f)
        return A(run / "concepts" / f"{picks.get(k)}.png", 1200)

    def palette_of(k):
        o = opts.get(k) or {}
        pr = prompts.get(picks.get(k), {})
        return (o.get("palette") or pr.get("concept", {}).get("palette") or dir_of.get(k, {}).get("palette") or ["#111111"])

    def idea_of(pid):
        pr = prompts.get(pid, {})
        return pr.get("concept", {}).get("idea") or dir_of.get(key_of(pid), {}).get("idea", "")

    def name_of(pid):
        pr = prompts.get(pid, {})
        n = pr.get("name") or dir_of.get(key_of(pid), {}).get("name", pid)
        return re.sub(r"\s+(refined|bolder|\((craft|bolder)\))$", "", n)   # the evolve pass is process, not a name

    def font_of(pid):
        f = prompts.get(pid, {}).get("font") or {}
        return f"{f.get('family')} {f.get('weight', '')}".strip() if f.get("family") else "custom lettering"

    nav_links = []
    body = []
    head_mark = A(run / fin["master"]) if delivered and fin.get("master") else (mark_of(order[0]) if order else "")

    # ------------------------------------------------------------------ choose state
    if not delivered:
        nav_links = [("options", "Options"), ("compare", "Side by side"), ("choose", "How to choose"), ("brief", "Brief"), ("shelf", "Shelf"), ("trends", "Trends"), ("concepts", "All concepts")]
        marks = "".join(f'<div class="mk{" rec" if picks[k] == rec else ""}"><span class="tag">#{rank[k]} · {esc(k)}</span><img src="{mark_of(k)}" alt="option {esc(k)}"></div>' for k in order)
        rk = order[0] if order else ""
        body.append(f"""<div class="wrap hero"><div class="eyebrow">{esc(brief.get('category', ''))}</div>
          <h1>Three directions<br>for {esc(brand)}.</h1><p class="lede" style="margin-top:22px">{esc(brief.get('product', ''))} We recommend <b>{esc(rk)} · {esc(name_of(picks.get(rk)))}</b>.</p>
          <div class="marks">{marks}</div></div>""")
        chips = "".join(f'<span class="chip{" on" if picks[k] == rec else ""}">#{rank[k]} {esc(k)} · {scores.get(picks[k], {}).get("total", "")}/30</span>' for k in order)
        body.append(f"""<div class="band"><div class="in"><div><div class="eyebrow" style="color:#aaa">The recommendation</div><h2>{esc(rk)} · {esc(name_of(rec))}</h2>
          <p>{esc(judge.get('why', ''))}</p>{('<p><b>What it costs:</b> ' + esc(judge.get('cost', '')) + '</p>') if judge.get('cost') else ''}
          {('<p><b>Buyers voted:</b> ' + esc(judge.get('votes')) + '</p>') if judge.get('votes') else ''}</div>
          <div><div class="chips">{chips}</div>{('<p style="margin-top:22px"><b>Today:</b> ' + esc(brief.get('current_mark', '')) + '</p>') if brief.get('current_mark') else ''}</div></div></div>""")
        # options, identical frames
        blocks = []
        for k in order:
            pid = picks[k]
            o = opts.get(k) or {}
            sc = scores.get(pid, {})
            pal = palette_of(k)
            main = pal[0]
            folder = run / o.get("folder", "_none")
            scs = [m for m in o.get("scenes", []) if m.get("ok")][:3]
            imgs3 = "".join(f'<figure style="margin:0"><img loading="lazy" src="{A(run / m["file"], 1400)}" alt=""><div class="cap">{esc(m["key"])}</div></figure>' for m in scs)
            if len(scs) < 3:
                for fn, cap in (("packaging", "packaging"), ("label-and-box", "label and box"), ("amazon-store-header", "store header")):
                    if len(scs) >= 3:
                        break
                    if (folder / f"{fn}.png").exists():
                        imgs3 += f'<figure style="margin:0"><img loading="lazy" src="{A(folder / (fn + ".png"), 1400)}" alt=""><div class="cap">{cap}</div></figure>'
                        scs.append({})
            onp = A(run / o["on_product"], 1400) if o.get("on_product") else ""
            p1 = A(folder / "page-one.png", 1600) if (folder / "page-one.png").exists() else ""
            listing = A(folder / "amazon-listing.png", 1600) if (folder / "amazon-listing.png").exists() else ""
            extra = "".join(f'<figure style="margin:0"><img loading="lazy" class="ph" src="{u}" alt="" style="aspect-ratio:auto;object-fit:contain;background:#fff"><div class="cap">{c}</div></figure>'
                            for u, c in ((onp, "on the product (render)"), (p1 or listing, "page one of Amazon" if p1 else "listing page")) if u)
            d = dir_of.get(k, {})
            blocks.append(f"""<div class="opt" id="opt-{esc(k)}"><div class="head"><span class="rank">#{rank[k]}</span><h2 style="margin:0">{esc(k)} · {esc(name_of(pid))}</h2>
              <span class="score">{sc.get('total', '')}/30 · {esc(prompts.get(pid, {}).get('style_world', ''))}</span></div>
              <p class="lede">{esc(idea_of(pid))}</p>
              <div class="duo" style="margin-top:30px"><div class="field" style="background:#fff;border:1px solid var(--line)"><img loading="lazy" src="{mark_of(k)}" alt=""></div>
              <div class="field" style="background:{main}"><img loading="lazy" src="{mark_of(k, True)}" alt=""></div></div>
              <div class="tri">{imgs3}</div>{('<div class="duo" style="margin-top:20px">' + extra + '</div>') if extra else ''}
              <div class="meta"><div><div class="k">Why it fits this shelf</div><p>{esc(d.get('why_it_wins', ''))}</p><div class="k" style="margin-top:14px">Risk</div><p>{esc(d.get('risk', ''))}</p></div>
              <div><div class="k">Colors</div><div class="sw">{''.join(f'<i style="background:{c}"></i>' for c in pal)}</div><p class="cap">{esc(' '.join(pal))}</p></div>
              <div><div class="k">Type</div><p>{esc(font_of(pid))}</p><div class="k" style="margin-top:14px">The judge kept</div><p>{esc(sc.get('keep', ''))}</p></div></div></div>""")
        body.append(f'<section class="wrap" id="options" style="padding-top:40px">{"".join(blocks)}</section>')
        # side by side
        rows = []
        rows.append("<tr><td class='lab'>At real sizes</td>" + "".join(
            f"<td><div class='cell'>{''.join(f'<img src={chr(34)}{mark_of(k)}{chr(34)} style={chr(34)}height:{h}px;width:auto{chr(34)}>' for h in (16, 28, 48))}</div></td>" for k in order) + "</tr>")
        rows.append("<tr><td class='lab'>Reversed</td>" + "".join(
            f"<td><div class='cell' style='background:{palette_of(k)[0]};padding:14px 18px'><img src='{mark_of(k, True)}' style='height:40px;width:auto'></div></td>" for k in order) + "</tr>")
        rows.append("<tr><td class='lab'>On the product</td>" + "".join(
            f"<td>{('<img loading=lazy src=' + chr(34) + A(run / opts[k]['on_product'], 600) + chr(34) + ' style=' + chr(34) + 'height:160px;width:auto' + chr(34) + '>') if (opts.get(k) or {}).get('on_product') else '<span class=cap>no product photo</span>'}</td>" for k in order) + "</tr>")
        rows.append("<tr><td class='lab'>Score</td>" + "".join(
            f"<td><b>{scores.get(picks[k], {}).get('total', '')}/30</b> <span class='cap'>idea {scores.get(picks[k], {}).get('idea_clarity', '')} · shelf {scores.get(picks[k], {}).get('distinct_on_shelf', '')} · small {scores.get(picks[k], {}).get('small_size', '')} · craft {scores.get(picks[k], {}).get('craft', '')}</span></td>" for k in order) + "</tr>")
        body.append(f"""<section class="wrap" id="compare"><div class="eyebrow">Side by side</div><h2>The same tests for all three.</h2>
          <table class="cmp"><tr><th></th>{''.join(f'<th>#{rank[k]} · {esc(k)} · {esc(name_of(picks[k]))}</th>' for k in order)}</tr>{''.join(rows)}</table></section>""")
        tp = run / "options" / "test-pack"
        body.append(f"""<section class="wrap" id="choose"><div class="eyebrow">How to choose</div><h2>Say A, B or C.</h2>
          <p class="lede">The final files are built only after you choose: vector masters, every color version, the mark on your product and packaging, the store and ad assets, the color and type system, listing templates and a zip.</p>
          <div class="ask"><h3>Or ask for another round</h3><p class="txt">Answer four questions and twelve new concepts come back steered by your answers, with these three kept for comparison.</p>
          <ol><li>What do you like in each option?</li><li>What bothers you?</li><li>Which color world feels right?</li><li>Safer or bolder?</li></ol></div>
          {('<div class="ask"><h3>Not sure? Ask 50 buyers</h3><p class="txt">The three options are packed as neutral tiles with a five-question survey in <code>options/test-pack/</code>. Run it on PickFu or Prolific (about $50) or with your own customers; the counts go back in and the ranking follows the buyers.</p></div>') if tp.exists() else ''}</section>""")

    # ------------------------------------------------------------------ delivered state
    else:
        nav_links = [("mark", "The mark"), ("name", "Name check"), ("system", "System"), ("world", "In the world"), ("templates", "Templates"), ("kit", "Files"), ("next", "Next steps"), ("story", "How we got here")]
        kit = run / "kit"
        svgd = kit / "svg"
        nm = Path(fin.get("master", "kit/svg/final.svg")).stem
        pal = fin.get("palette") or ["#111111"]
        main = pal[0]
        pid = fin.get("concept", "")
        body.append(f"""<div style="background:{main};color:{ink_on(main)};padding:120px 0 110px"><div class="wrap">
          <div class="eyebrow" style="color:inherit;opacity:.7">{esc(brand)} · brand mark</div>
          <div style="max-width:900px;margin:40px 0 46px"><img src="{A(svgd / (nm + '-white.svg')) if ink_on(main) == '#ffffff' else A(svgd / (nm + '.svg'))}" alt="{esc(brand)} logo" fetchpriority="high"></div>
          <p class="lede" style="color:inherit;opacity:.9">{esc(system.get('mark_line') or idea_of(pid))}</p></div></div>""")
        stacked = svgd / f"{nm}-stacked.svg"
        sym = run / fin["symbol"] if fin.get("symbol") else None
        word = svgd / f"{nm}-wordmark.svg"
        lock_tiles = "".join(f'<figure style="margin:0"><div class="field" style="background:#fff;border:1px solid var(--line)"><img loading="lazy" src="{A(f)}" alt=""></div><div class="cap">{c}</div></figure>'
                             for f, c in ((svgd / f"{nm}.svg", "horizontal"), (stacked, "stacked"), (sym, "symbol"), (word, "wordmark")) if f and Path(f).exists())
        f = fin.get("font") or prompts.get(pid, {}).get("font") or {}
        body.append(f"""<section class="wrap" id="mark"><div class="eyebrow">01 · The mark</div><h2>{esc(name_of(pid))}</h2>
          <p class="lede">{esc(re.sub(r"^On this shelf,?\s*", "", judge.get('why', '')).capitalize() if judge.get('why') else '')}</p>
          <div class="duo" style="margin-top:34px">{lock_tiles}</div>
          <div class="meta"><div><div class="k">Typeface</div><p>{esc((f.get('family') or 'custom lettering') + (' ' + str(f.get('weight')) if f.get('weight') else ''))}{' · Google Fonts, free for commercial use' if f.get('family') else ''}</p></div>
          <div><div class="k">Files</div><p>Vector masters in SVG, traced from the approved artwork and checked against it, with every PNG exported from them.</p></div>
          <div><div class="k">Use it</div><p>Clear space: the height of the symbol on every side. Smallest: 24 px on screen, 20 mm wide in print.</p></div></div></section>""")
        v = checks.get("verdict") or {}
        if checks:
            rc = {"low": "#2e7d4f", "medium": "#b8860b", "high": "#b3261e"}.get(v.get("risk", ""), "#666")
            yours = "".join(f"<li>{esc(x.get('name') or x.get('mark') or x) if isinstance(x, dict) else esc(x)}</li>" for x in v.get("probably_yours", []))
            dom = "".join(f"<li>{esc(d['host'])}: <b>{'taken' if d['taken'] else 'free'}</b></li>" for d in checks.get("domains", []))
            def _item(x):
                if isinstance(x, dict):
                    nm = x.get("name") or x.get("mark") or x.get("brand") or ""
                    fld = x.get("field") or x.get("goods") or x.get("what") or ""
                    return f"{nm} ({fld})" if fld else nm
                return str(x)
            coll = "".join(f"<li>{esc(_item(x))}</li>" for x in v.get("collisions", [])) or "<li>none found</li>"
            tm = "".join(f"<li>{esc(t.get('mark', ''))}, {esc(t.get('owner', ''))}: {esc(t.get('goods', ''))} ({esc(t.get('status', ''))}, {esc(t.get('office', ''))})</li>" for t in (checks.get("trademark") or {}).get("results", [])) or "<li>no record found (a search, not proof)</li>"
            tl = checks.get("trademark") or {}
            body.append(f"""<section class="wrap" id="name"><div class="eyebrow">02 · Name check</div><h2>Is the name free to print?</h2>
              <p><span class="risk" style="background:{rc}">Risk from others: {esc(v.get('risk', '?'))}</span></p><p class="lede" style="margin-top:14px">{esc(v.get('do_first', ''))}</p>
              {('<div class="ask" style="margin-top:20px"><h3>Probably yours</h3><p class="txt">You already sell under this name, so these records most likely belong to you. Confirm the owner matches your company.</p><ul>' + yours + '</ul></div>') if yours else ''}
              <div class="cols3" style="margin-top:34px"><div><h3>Domains</h3><ul>{dom}</ul></div><div><h3>Who else uses the name</h3><ul>{coll}</ul></div>
              <div><h3>Trademark records</h3><ul>{tm}</ul><p class="cap">Verify: <a href="{esc(tl.get('uspto', '#'))}">USPTO</a> · <a href="{esc(tl.get('euipo', '#'))}">EUIPO</a> · <a href="{esc(tl.get('wipo', '#'))}">WIPO</a>. This is a search, not legal clearance.</p></div></div></section>""")
        # system
        sp = system.get("palette") or {}
        colors = [("Brand", main)] + [(f"Tint {n}", h) for n, h in (sp.get("tints") or [])[:2]] + [(f"Shade {n}", h) for n, h in (sp.get("tints") or [])[3:5]] + \
                 [("Accent", (x.get("hex") if isinstance(x, dict) else x)) for x in (sp.get("accents") or [])] + [("Paper", (sp.get("neutrals") or {}).get("paper", "#f6f3ee")), ("Ink", (sp.get("neutrals") or {}).get("ink", "#151515"))]
        cblocks = "".join(f'<div class="c" style="background:{h};color:{ink_on(h)}"><b>{esc(n)}</b>{esc(h)}<br>RGB {",".join(str(x) for x in rgb(h))}<br>CMYK {"/".join(str(x) for x in cmyk(h))}</div>' for n, h in colors if h and h.startswith("#"))
        fonts = system.get("fonts") or {}
        voice = system.get("voice") or {}
        bs = kit / "brand-system"
        body.append(f"""<section class="wrap" id="system"><div class="eyebrow">03 · System</div><h2>Color, type, voice.</h2>
          <div class="color" style="margin-top:20px">{cblocks}</div><p class="cap">CMYK values are a starting point; ask your printer for a proof on the real board.</p>
          <div class="cols3" style="margin-top:44px"><div><h3>Headlines</h3><p>{esc(fonts.get('headline', ''))} {esc(fonts.get('headline_weight', ''))}</p><h3 style="margin-top:20px">Body</h3><p>{esc(fonts.get('body', ''))}</p><p class="cap">{esc(fonts.get('why', ''))}</p></div>
          <div><h3>Voice</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in voice.get('rules', [])[:5])}</ul></div>
          <div><h3>Lines it would write</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in voice.get('samples', [])[:3])}</ul></div></div>
          {('<img loading="lazy" class="full" src="' + A(run / 'mockups' / 'tests.png', 2000) + '" alt="stress tests"><div class="cap">Stress tests: real sizes, one color, kraft, embossed, debossed, squint, the ad tile on a phone.</div>') if (run / 'mockups' / 'tests.png').exists() else ''}</section>""")
        # world
        chosen_key = key_of(pid)
        o = opts.get(chosen_key) or {}
        scs = [m for m in o.get("scenes", []) if m.get("ok")]
        onp = [m for m in (read_json(run / "mockups" / "on-product.json") or []) if m.get("ok")]
        world = ""
        if scs:
            world += f'<img loading="lazy" class="full" src="{A(run / scs[0]["file"], 2200)}" alt="">'
            if len(scs) > 1:
                world += '<div class="duo" style="margin-top:20px">' + "".join(f'<img loading="lazy" class="ph" src="{A(run / m["file"], 1400)}" alt="">' for m in scs[1:3]) + "</div>"
        if onp:
            today = A(run / "originals" / prod["images"][0], 1200) if prod.get("images") else ""
            world += '<div class="tri" style="margin-top:20px">' + (f'<figure style="margin:0"><img loading="lazy" src="{today}" style="aspect-ratio:1;object-fit:contain;background:#fff"><div class="cap">today</div></figure>' if today else "") + \
                     "".join(f'<figure style="margin:0"><img loading="lazy" src="{A(run / m["file"], 1200)}" style="aspect-ratio:1;object-fit:contain;background:#fff"><div class="cap">{esc(m["surface"])} (render)</div></figure>' for m in onp[:2]) + "</div>"
        comps = [(n, c) for n, c in (("page-one", "Page one of Amazon, with the brand in it"), ("amazon-listing", "The listing"), ("amazon-store-header", "Store header"),
                                     ("amazon-sponsored-brands", "Sponsored Brands ad"), ("packaging", "Box, card, tag, stickers"), ("label-and-box", "Label and box"),
                                     ("shopify-home", "Website home"), ("social-avatar", "Profile avatars")) if (run / "mockups" / f"{n}.png").exists()]
        world += '<div class="duo" style="margin-top:20px">' + "".join(f'<figure style="margin:0"><img loading="lazy" src="{A(run / "mockups" / (n + ".png"), 1600)}" alt="" style="background:#fff;border:1px solid var(--line)"><div class="cap">{c}</div></figure>' for n, c in comps) + "</div>"
        body.append(f'<section class="wrap" id="world"><div class="eyebrow">04 · In the world</div><h2>Where it will live.</h2>{world}</section>')
        tpl = [(n, c) for n, c in (("listing-01-aplus", "A+ header"), ("listing-02-benefits", "Benefits"), ("listing-03-lifestyle", "Lifestyle with badge"),
                                   ("listing-04-whyus", "Why us"), ("brand-story", "Brand Story module")) if (bs / f"{n}.png").exists()]
        if tpl:
            body.append(f'<section class="wrap" id="templates"><div class="eyebrow">05 · Templates</div><h2>Your next five listing images.</h2><p class="lede">They already carry the mark, the colors, the fonts and your product. Swap the words, keep the structure.</p>'
                        f'<div class="duo" style="margin-top:28px">' + "".join(f'<figure style="margin:0"><img loading="lazy" src="{A(bs / (n + ".png"), 1600)}" alt="" style="border:1px solid var(--line)"><div class="cap">{c}</div></figure>' for n, c in tpl) + "</div></section>")
        # kit
        groups = [("Amazon", "amazon"), ("Shopify and web", "shopify"), ("Social", "social"), ("Print", "print"), ("Brand system", "brand-system"), ("Masters (PNG)", "png"), ("Masters (SVG)", "svg")]
        kt = ""
        for title, sub in groups:
            fs = sorted(x for x in (kit / sub).glob("*") if x.is_file() and not x.name.startswith("_") and x.suffix.lower() in (".png", ".svg", ".ico", ".md", ".json", ".pdf")) if (kit / sub).exists() else []
            if not fs:
                continue
            tiles = ""
            for x in fs[:16]:
                src = x if x.suffix.lower() in (".png", ".svg") else (x.with_name("favicon-48.png") if x.suffix.lower() == ".ico" else None)
                pv = A(src, 600) if src and src.exists() else ""
                st = x.stem.lower()
                dark = (st.endswith("-white") or "white-transparent" in st or "-white-" in st) and "on-white" not in st
                tiles += f'<a class="tile" href="kit/{sub}/{esc(x.name)}" download><div class="pv"{" style=" + chr(39) + "background:#222" + chr(39) if dark else ""}>{("<img loading=lazy src=" + chr(34) + pv + chr(34) + ">") if pv else "<span>" + esc(x.suffix.upper().lstrip(".")) + "</span>"}</div><b>{esc(x.stem)}</b><span>{esc(x.suffix.lstrip(".").upper())}</span></a>'
            kt += f'<div class="grouph">{esc(title)}</div><div class="kit">{tiles}</div>'
        zipf = run / "logo-kit.zip"
        pdf = run / "brand-guidelines.pdf"
        body.append(f"""<section class="wrap" id="kit"><div class="eyebrow">06 · Files</div><h2>Everything, sized and named.</h2>
          <p class="lede">kit/README.md says where each file is uploaded. The SVG masters are the source; every PNG was exported from them.</p>
          <a class="btn" href="logo-kit.zip" download>Download all (zip)</a> {('<a class="btn" style="background:#fff;color:#111;border:1px solid #111" href="brand-guidelines.pdf" download>Brand guidelines (PDF)</a>') if pdf.exists() else ''}
          {kt}</section>""")
        body.append(f"""<section class="wrap" id="next"><div class="eyebrow">07 · Next steps</div><h2>Before you print.</h2><ol class="lede">
          <li>Run a trademark search on the name and the mark. {esc(v.get('do_first', ''))}</li>
          <li>Amazon Brand Registry: file the trademark, then upload real product and packaging photos with the brand on them.</li>
          <li>Send <code>kit/print/{esc(nm)}-black.svg</code> and the color codes to your printer; ask for a one-color proof on the real board.</li>
          <li>Upload the Brand Store logo, the Sponsored Brands logo and the Shopify header from the kit.</li></ol></section>""")
        nav_links_story = True

    # ------------------------------------------------------------------ research (both states)
    tiles = [t for t in shelf.get("tiles", [])]
    logos = "".join(f'<figure style="margin:0"><div class="lg">{("<img loading=lazy src=" + chr(34) + A(run / t["logo"], 500) + chr(34) + ">") if t.get("logo") else "<b>" + esc(t.get("brand", "")) + "</b>"}</div><div class="cap">{esc(t.get("brand", ""))}</div></figure>'
                    for t in tiles if t.get("logo") or (t.get("brand") and t.get("brand", "").lower() not in ("unknown", "not clear")))
    prods = "".join(f'<div class="prod"><img loading="lazy" src="{A(run / t["local"], 500)}" alt=""></div>' for t in tiles[:6] if t.get("local"))
    cen = shelf.get("census", {})
    rd = shelf.get("read", {})
    tr = trends.get("read") or {}
    research = f"""<section class="wrap" id="brief"><div class="eyebrow">{'The brief' if not delivered else 'How we got here · the brief'}</div><h2>What we read off the {'business' if brief.get('kind') == 'business' else 'product'}.</h2>
      <div class="cols3"><div><h3>Who buys it</h3><p>{esc(brief.get('audience', ''))}</p><p class="cap">{esc(brief.get('category', ''))} · {esc(brief.get('price_tier', ''))} tier · {esc(', '.join(brief.get('adjectives', [])))}</p></div>
      <div><h3>Where the mark lives</h3><ul>{''.join(f"<li>{esc(s['surface'])}: {esc(s['method'])}, about {esc(s.get('size_mm', '?'))} mm</li>" for s in brief.get('logo_surfaces', []))}</ul></div>
      <div><h3>Cliches we refused</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in brief.get('cliches', [])[:6])}</ul></div></div></section>"""
    if shelf:
        research += f"""<section class="wrap" id="shelf"><div class="eyebrow">The shelf</div><h2>Who it stands next to.</h2>
          <p class="lede">The competitors for "{esc(shelf.get('keyword', ''))}". Colors already taken: <b>{esc(', '.join(cen.get('owned', [])) or 'none dominant')}</b>; free: {esc(', '.join(cen.get('free', [])))}.</p>
          <div class="grid6" style="margin-top:26px">{logos}</div>{('<div class="grid6" style="margin-top:14px">' + prods + '</div>') if prods else ''}
          <div class="cols3" style="margin-top:34px"><div><h3>What the shelf does</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('visual_habits', [])[:5])}</ul></div>
          <div><h3>The whitespace</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('whitespace', []))}</ul></div><div><h3>What would make us disappear</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in rd.get('avoid', []))}</ul></div></div></section>"""
    if tr:
        srcs = "".join(f'<div class="lg" style="aspect-ratio:1;padding:6%"><img loading="lazy" src="{A(run / g["file"], 400)}" alt=""></div>' for g in trends.get("sources", [])[:12] if (run / g["file"]).exists())
        research += f"""<section class="wrap" id="trends"><div class="eyebrow">Where the category is going</div><h2>{esc(tr.get('one_line', ''))}</h2>
          <p class="cap">Read from {len(trends.get('sources', []))} recent brand identities in the category found on the web.</p>
          <div class="grid6" style="margin-top:24px">{srcs}</div>
          <div class="cols3" style="margin-top:34px"><div><h3>New brands moved to</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('moving_to', [])[:5])}</ul></div>
          <div><h3>Already overused</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('overused_now', []))}</ul></div><div><h3>The gap we aimed at</h3><ul>{''.join(f'<li>{esc(x)}</li>' for x in tr.get('gap', []))}</ul></div></div></section>"""
    sheet = A(run / "concepts.png", 2200) if (run / "concepts.png").exists() else ""
    research += f"""<section class="wrap" id="concepts"><details><summary>All {len(prompts)} concepts, scored</summary>{('<img loading="lazy" class="full" src="' + sheet + '" alt="concept sheet">') if sheet else ''}
      <p class="cap">Every concept started from its own idea, technique and style. The strongest of each direction went forward.</p></details></section>"""
    if delivered:
        others = [k for k in order if picks.get(k) != fin.get("concept")]
        research = (f'<section class="wrap" id="story"><div class="eyebrow">08 · How we got here</div><h2>The options you did not pick.</h2><div class="duo">' +
                    "".join(f'<figure style="margin:0"><div class="field" style="background:#fff;border:1px solid var(--line)"><img loading="lazy" src="{mark_of(k)}" alt=""></div><div class="cap">{esc(k)} · {esc(name_of(picks[k]))}</div></figure>' for k in others) +
                    "</div></section>" + research)
    body.append(research)

    links = "".join(f'<a class="l" href="#{h}">{esc(t)}</a>' for h, t in nav_links)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(brand)} · {'brand mark' if delivered else 'three directions'}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Inter+Tight:wght@600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body data-state="{'delivered' if delivered else 'choose'}">
<nav class="nav"><div class="in"><span class="bn">{('<img src="' + head_mark + '" alt="">') if head_mark and delivered else esc(brand)}</span>{links}</div></nav>
{''.join(body)}
<footer class="wrap">{esc(brand)} · {esc(now()[:10])}</footer>
</body></html>"""
    (run / "brand.html").write_text(html)
    if delivered:
        import zipfile
        with zipfile.ZipFile(run / "logo-kit.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted((run / "kit").rglob("*")):
                if f.is_file() and not f.name.startswith("_"):
                    z.write(f, f"{brand}-logo-kit/" + str(f.relative_to(run / "kit")))
        try:
            import subprocess
            from render_png import find_chrome   # base skill
        except Exception:
            find_chrome = None
        if find_chrome is None:
            sys.path.insert(0, str(Path(__import__("common").base_script("render_png.py")).parent))
            from render_png import find_chrome
        chrome = find_chrome()
        if chrome:
            import subprocess
            g = guidelines(run, brand, fin, system, A, idea_of(pid) if False else (system.get("mark_line") or ""))
            gp = run / "_guidelines.html"
            gp.write_text(g)
            subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={run / 'brand-guidelines.pdf'}",
                            "--virtual-time-budget=8000", "file://" + str(gp)], capture_output=True, timeout=120)
            gp.unlink(missing_ok=True)
        if (run / "brand-guidelines.pdf").exists() and "brand-guidelines.pdf" not in html:
            html = html.replace('<a class="btn" href="logo-kit.zip" download>Download all (zip)</a> ',
                                '<a class="btn" href="logo-kit.zip" download>Download all (zip)</a> <a class="btn" style="background:#fff;color:#111;border:1px solid #111" href="brand-guidelines.pdf" download>Brand guidelines (PDF)</a>')
            (run / "brand.html").write_text(html)
    for stale in ("review.html", "board.html"):
        if (run / stale).exists():
            (run / stale).unlink()
    size = sum(f.stat().st_size for f in (run / "assets").glob("*")) + (run / "brand.html").stat().st_size
    log(f"wrote {run / 'brand.html'} ({'delivered' if delivered else 'choose'} state, {size / 1e6:.1f} MB with assets)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    a = ap.parse_args()
    build(Path(a.run).resolve())


if __name__ == "__main__":
    main()
