"""Step 7b: from a logo to a brand system a seller can use tomorrow.

  system <run>

Written after the pick, into kit/brand-system/:
  system.json            the whole system as data
  palette.png            brand color with tints and shades, accents, neutrals, with hex and where each is used
  type.png               the type pairing (two licensed Google fonts: one for headlines, one for body) set as a spec
  listing-01..04.png     four listing-image templates that already carry the mark: A+ header, benefit infographic,
                         lifestyle frame with a brand badge, comparison / why-us; the real product photo inside
  brand-story.png        the Amazon Brand Story module (3 cards) with the logo, the one-line story and the palette
  voice.md               tone of voice: 5 rules, 5 words to use, 5 to avoid, 3 sample lines
The vision pass writes the words once (fonts, voice, headlines); the pages are deterministic HTML renders.
"""
import argparse
import colorsys
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_cost, client, esc, file_data_uri, log, read_json, screenshot_html, vision_cost, vision_json, write_json  # noqa: E402

SYSTEM_PROMPT = """You are a brand designer writing the system around a finished logo for "{brand}" ({product}; audience: {audience};
adjectives: {adjectives}; price tier: {tier}). The logo's colors: {palette}. The category's design direction: {trend}.
Return JSON:
- "fonts": {{"headline": the logo's own typeface {logo_font} when given, else a Google Font that matches the logo's voice, "headline_weight": e.g. 700, "body": a Google Font for body copy,
   "body_weight": e.g. 400, "why": one sentence}}  (Google Fonts only: they are free to use commercially)
- "accents": 1 or 2 hex colors that extend the palette for listing images and Store pages, each with "use" (one phrase). They must
   NOT be any color the brief refused ({refused}) and must sit calmly with the logo colors; prefer a muted or deep accent over neon.
- "neutrals": {{"paper": hex (a warm or cool off-white that fits), "ink": hex (a near-black that fits)}}
- "voice": {{"rules": 5 short rules, "use": 5 words, "avoid": 5 words, "samples": 3 lines the brand would write on a listing image}}
- "headlines": {{"aplus": under 7 words, "benefits": [3 benefit headlines under 5 words each], "lifestyle": under 8 words, "whyus": under 6 words,
   "story": [3 one-sentence cards for the Brand Story module: who we are, what we make, why it matters]}}
Plain, specific, no superlatives. Return JSON only."""


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(x)))) for x in c)


def tints(hexc):
    r, g, b = hex_to_rgb(hexc)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    out = []
    for name, ll in (("90", 0.92), ("70", 0.78), ("50", l), ("30", max(0.1, l * 0.65)), ("10", max(0.06, l * 0.38))):
        rr, gg, bb = colorsys.hls_to_rgb(h, ll, s)
        out.append((name, rgb_to_hex((rr * 255, gg * 255, bb * 255))))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    a = ap.parse_args()
    run = Path(a.run).resolve()
    brief = read_json(run / "brief.json")
    fin = read_json(run / "final.json")
    prod = read_json(run / "product.json") or {}
    trends = read_json(run / "trends.json") or {}
    if not fin:
        sys.exit("no final.json; vectorize first")
    out = run / "kit" / "brand-system"
    out.mkdir(parents=True, exist_ok=True)
    kit = run / "kit" / "svg"
    name = Path(fin["master"]).stem
    pal = fin["palette"]
    main_hex = pal[0]
    c = client()
    res, usage = vision_json(c, SYSTEM_PROMPT.format(
        brand=brief["brand"], product=brief.get("product", ""), audience=brief.get("audience", ""),
        adjectives=", ".join(brief.get("adjectives", [])), tier=brief.get("price_tier", ""), palette=", ".join(pal),
        trend=(trends.get("read") or {}).get("one_line", "not measured"), logo_font=(fin.get("font") or {}).get("family", ""),
        refused="; ".join(brief.get("cliches", []))), [])
    append_cost(run, "system", vision_cost(usage))
    sysd = res or {}
    fonts = sysd.get("fonts", {"headline": "Inter", "headline_weight": 700, "body": "Inter", "body_weight": 400})
    lf = fin.get("font") or {}
    if lf.get("family"):   # the logo's own typeface leads the system; the model only picks the body face
        fonts["headline"] = lf["family"]
        fonts["headline_weight"] = lf.get("weight", fonts.get("headline_weight", 700))
        fonts["why"] = f"{lf['family']} is the logo's typeface, so headlines and the mark speak with one voice; " + (fonts.get("why") or "")
    accents = sysd.get("accents", [])
    neutrals = sysd.get("neutrals", {"paper": "#f6f3ee", "ink": "#151515"})
    pal_all = fin.get("palette") or []
    dark = [h for h in pal_all if sum(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) < 200]
    if dark:
        neutrals["ink"] = dark[-1]   # the same near-black the logo files use
    # One sentence on what the finished mark actually shows, read off the final symbol (not the concept brief).
    sym_png = run / "kit" / "png" / "_mark-for-reading.png"
    from common import svg_to_png
    src_svg = run / (fin.get("symbol") or fin["master"])
    if svg_to_png(src_svg, sym_png, size=768, bg="#ffffff", padding=0.1):
        ml, u2 = vision_json(c, f'This is the finished symbol of the brand "{brief["brand"]}". In one plain sentence (under 30 words), say what it shows and the idea '
                                f'behind it, the way a designer would present it to the client. Describe only what is actually drawn. Return JSON {{"line": "..."}}.', [sym_png], max_px=768)
        append_cost(run, "mark line", vision_cost(u2))
        sysd["mark_line"] = (ml or {}).get("line", "")
        sym_png.unlink(missing_ok=True)
    heads = sysd.get("headlines", {})
    voice = sysd.get("voice", {})
    system = {"palette": {"main": main_hex, "logo": pal, "tints": tints(main_hex), "accents": accents, "neutrals": neutrals},
              "fonts": fonts, "voice": voice, "headlines": heads, "mark_line": sysd.get("mark_line", "")}
    write_json(out / "system.json", system)

    gf = lambda f: f"https://fonts.googleapis.com/css2?family={f.replace(' ', '+')}:wght@400;500;600;700;800&display=swap"  # noqa: E731
    head = f"""<link rel="stylesheet" href="{gf(fonts['headline'])}"><link rel="stylesheet" href="{gf(fonts['body'])}">
    <style>*{{box-sizing:border-box}}body{{margin:0;font-family:'{fonts['body']}',sans-serif;color:{neutrals.get('ink', '#151515')}}}
    h1,h2,h3,.h{{font-family:'{fonts['headline']}',sans-serif;font-weight:{fonts.get('headline_weight', 700)};letter-spacing:-.01em}}</style>"""
    logo = file_data_uri(kit / f"{name}.svg")
    logo_w = file_data_uri(kit / f"{name}-white.svg")
    sym = file_data_uri(kit / f"{name}-symbol.svg") if (kit / f"{name}-symbol.svg").exists() else logo
    sym_w = file_data_uri(kit / f"{name}-symbol-white.svg") if (kit / f"{name}-symbol-white.svg").exists() else logo_w
    imgs = [run / "originals" / n for n in prod.get("images", []) if (run / "originals" / n).exists()]
    roles = brief.get("photo_roles", [])
    good = [run / m["file"] for m in (read_json(run / "mockups" / "on-product.json") or []) if m.get("ok") and (run / m["file"]).exists()]
    clean = good + [p for p, r in zip(imgs, roles) if r == "packshot"] or imgs[:1]
    prod_img = file_data_uri(clean[0]) if clean else ""
    scenes_ok = []
    for o in (read_json(run / "options" / "options.json") or {}).values():
        if isinstance(o, dict) and str(fin.get("concept", "")) == o.get("id"):
            scenes_ok = [run / m["file"] for m in o.get("scenes", []) if m.get("ok")]
    life_img = file_data_uri(scenes_ok[0]) if scenes_ok else prod_img
    paper, ink = neutrals.get("paper", "#f6f3ee"), neutrals.get("ink", "#151515")
    tint = dict(system["palette"]["tints"])

    pages = {}
    # palette
    sw = "".join(f"<div class='sw' style='background:{h}'><b>{n}</b><span>{h}</span></div>" for n, h in system["palette"]["tints"])
    acc = "".join(f"<div class='sw' style='background:{x.get('hex', x) if isinstance(x, dict) else x}'><b>accent</b><span>{x.get('hex', x) if isinstance(x, dict) else x}</span><i>{esc(x.get('use', '')) if isinstance(x, dict) else ''}</i></div>" for x in accents)
    pages["palette"] = (1400, 620, head + f"""<style>.wrap{{padding:40px 48px;background:#fff;width:1400px;height:620px}}.row{{display:flex;gap:10px;margin:14px 0 26px}}
    .sw{{flex:1;height:120px;border-radius:10px;padding:10px;color:#fff;display:flex;flex-direction:column;justify-content:flex-end;font-size:12px;text-shadow:0 0 6px rgba(0,0,0,.4)}}.sw b{{font-size:13px}}.sw i{{font-style:normal;opacity:.9}}
    h2{{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:#777;margin:0}}</style><div class="wrap"><div style="display:flex;justify-content:space-between;align-items:center"><img src="{logo}" style="height:64px"><div class="h" style="font-size:26px">Color system</div></div>
    <h2>Brand color, tints and shades</h2><div class="row">{sw}</div><h2>Accents and neutrals</h2><div class="row">{acc}<div class='sw' style='background:{paper};color:{ink};text-shadow:none'><b>paper</b><span>{paper}</span></div><div class='sw' style='background:{ink}'><b>ink</b><span>{ink}</span></div></div>
    <p style="font-size:13px;color:#666;margin:0">Main color for the mark and primary buttons; tints 90/70 for backgrounds and cards; shades 30/10 for text on light tints; accents only for highlights and one badge per image.</p></div>""")
    # type
    pages["type"] = (1400, 620, head + f"""<style>.wrap{{padding:44px 48px;background:{paper};width:1400px;height:620px;display:grid;grid-template-columns:1.2fr 1fr;gap:40px}}
    .lab{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#888;margin-bottom:8px}}</style><div class="wrap"><div><div class="lab">Headlines · {esc(fonts['headline'])} {fonts.get('headline_weight', 700)}</div>
    <div class="h" style="font-size:56px;line-height:1.05;color:{ink}">{esc(heads.get('aplus', brief['brand']))}</div><div class="h" style="font-size:30px;margin-top:14px;color:{main_hex}">{esc((heads.get('benefits') or ['Made for every day'])[0])}</div>
    <div class="lab" style="margin-top:34px">Body · {esc(fonts['body'])} {fonts.get('body_weight', 400)}</div><p style="font-size:18px;line-height:1.55;max-width:620px;color:{ink}">{esc((voice.get('samples') or [brief.get('product', '')])[0])} {esc((voice.get('samples') or ['', ''])[1] if len(voice.get('samples', [])) > 1 else '')}</p>
    <p style="font-size:13px;color:#777">{esc(fonts.get('why', ''))} Both fonts are on Google Fonts and free for commercial use.</p></div>
    <div style="background:#fff;border-radius:14px;padding:26px"><img src="{logo}" style="height:70px"><div class="lab" style="margin-top:22px">Voice</div><ul style="font-size:14px;line-height:1.6;padding-left:18px;color:{ink}">{''.join(f'<li>{esc(r)}</li>' for r in voice.get('rules', [])[:5])}</ul>
    <div style="font-size:13px;color:#555"><b>Use:</b> {esc(', '.join(voice.get('use', [])))}<br><b>Avoid:</b> {esc(', '.join(voice.get('avoid', [])))}</div></div></div>""")
    # listing 01: A+ header
    pages["listing-01-aplus"] = (1464, 600, head + f"""<div style="width:1464px;height:600px;background:{main_hex};display:grid;grid-template-columns:1fr 1fr;align-items:center;padding:0 70px;gap:40px;overflow:hidden">
    <div><img src="{logo_w}" style="height:90px;max-width:420px"><div class="h" style="color:#fff;font-size:54px;line-height:1.05;margin-top:26px">{esc(heads.get('aplus', ''))}</div><p style="color:#fff;opacity:.9;font-size:20px;max-width:560px">{esc((voice.get('samples') or [''])[0])}</p></div>
    <div style="height:600px;display:flex;align-items:center;justify-content:center"><img src="{prod_img}" style="max-height:540px;max-width:620px;filter:drop-shadow(0 24px 40px rgba(0,0,0,.28))"></div></div>""")
    # listing 02: benefits infographic
    bens = (heads.get("benefits") or ["Easy to use", "Built to last", "Made for you"])[:3]
    pages["listing-02-benefits"] = (1200, 1200, head + f"""<div style="width:1200px;height:1200px;background:{tint.get('90', paper)};position:relative;padding:60px;overflow:hidden">
    <img src="{logo}" style="height:60px;position:absolute;top:44px;left:60px"><div class="h" style="font-size:46px;color:{ink};margin:90px 0 0;max-width:640px;line-height:1.08">{esc(heads.get('lifestyle', brief['brand']))}</div>
    <img src="{prod_img}" style="position:absolute;right:40px;top:200px;height:620px;max-width:560px;object-fit:contain">
    <div style="position:absolute;left:60px;bottom:70px;display:flex;gap:18px">{''.join(f'<div style="background:#fff;border-radius:14px;padding:18px 20px;width:330px;box-shadow:0 8px 24px rgba(0,0,0,.08)"><div style="width:30px;height:30px;border-radius:50%;background:{main_hex};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;margin-bottom:10px">{i+1}</div><div class="h" style="font-size:22px;color:{ink}">{esc(b)}</div></div>' for i, b in enumerate(bens))}</div></div>""")
    # listing 03: lifestyle frame with badge
    pages["listing-03-lifestyle"] = (1200, 1200, head + f"""<div style="width:1200px;height:1200px;position:relative;overflow:hidden;background:{ink}"><img src="{life_img}" style="width:1200px;height:1200px;object-fit:cover;display:block">
    <div style="position:absolute;left:0;right:0;bottom:0;height:300px;background:linear-gradient(transparent,rgba(0,0,0,.75))"></div>
    <div style="position:absolute;left:60px;bottom:60px;color:#fff"><div class="h" style="font-size:54px;line-height:1.05;max-width:760px">{esc(heads.get('lifestyle', ''))}</div></div>
    <div style="position:absolute;top:44px;right:44px;width:120px;height:120px;border-radius:50%;background:{main_hex};display:flex;align-items:center;justify-content:center;box-shadow:0 10px 30px rgba(0,0,0,.3)"><img src="{sym_w}" style="width:70px;max-height:70px"></div></div>""")
    # listing 04: why us
    pages["listing-04-whyus"] = (1200, 1200, head + f"""<div style="width:1200px;height:1200px;background:#fff;padding:60px;position:relative"><img src="{logo}" style="height:60px">
    <div class="h" style="font-size:44px;color:{ink};margin:40px 0 24px">{esc(heads.get('whyus', 'Why ' + brief['brand']))}</div>
    <table style="width:100%;border-collapse:collapse;font-size:22px"><tr style="background:{tint.get('90', paper)}"><th style="text-align:left;padding:18px"></th><th style="padding:18px;color:{main_hex}"><img src="{sym}" style="height:40px;vertical-align:middle"> {esc(brief['brand'])}</th><th style="padding:18px;color:#999">Others</th></tr>
    {''.join(f'<tr style="border-bottom:1px solid #eee"><td style="padding:22px 18px;color:{ink}">{esc(b)}</td><td style="text-align:center;color:{main_hex};font-size:30px">✓</td><td style="text-align:center;color:#ccc;font-size:30px">—</td></tr>' for b in bens + [heads.get('aplus', '')])}</table>
    <img src="{prod_img}" style="position:absolute;right:60px;bottom:40px;height:360px;max-width:420px;object-fit:contain"></div>""".replace("—", "·"))
    # brand story module
    story = (heads.get("story") or ["", "", ""])[:3]
    cards = "".join(f'<div style="flex:1;background:{"#fff" if i else main_hex};color:{ink if i else "#fff"};border-radius:12px;padding:28px;display:flex;flex-direction:column;justify-content:space-between;min-height:360px"><div><div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.7">{["Who we are", "What we make", "Why it matters"][i]}</div><div class="h" style="font-size:26px;line-height:1.2;margin-top:12px">{esc(t)}</div></div>{"<img src=\'" + (logo_w if not i else sym) + "\' style=\'height:48px;align-self:flex-start\'>"}</div>' for i, t in enumerate(story))
    pages["brand-story"] = (1464, 625, head + f"""<div style="width:1464px;height:625px;background:{tint.get('90', paper)};padding:40px;display:flex;gap:20px">{cards}</div>""")

    for n, (w, h, html) in pages.items():
        (out / f"{n}.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'>{html if html.startswith('<link') else ''}</head><body style='margin:0'>{html if not html.startswith('<link') else html.split('</style>', 1)[1] if '</style>' in html else html}</body></html>")
        screenshot_html(out / f"{n}.html", out / f"{n}.png", w, h)
        (out / f"{n}.html").unlink()
        log(f"  {n}.png")
    (out / "voice.md").write_text(f"# {brief['brand']} voice\n\n" + "\n".join(f"- {r}" for r in voice.get("rules", [])) +
                                  f"\n\nUse: {', '.join(voice.get('use', []))}\nAvoid: {', '.join(voice.get('avoid', []))}\n\n" +
                                  "\n".join(f"> {s}" for s in voice.get("samples", [])) +
                                  f"\n\nFonts: {fonts['headline']} {fonts.get('headline_weight', 700)} for headlines, {fonts['body']} for body (Google Fonts).\n")
    log(f"brand system in {out}")


if __name__ == "__main__":
    main()
