"""Real type for the name, real lockups: the symbol is drawn by the model, the name is set by code.

  lockup <run> <symbol.svg> --font "Space Grotesk" --weight 700 [--case upper|lower|title|as-is]
         [--tracking 0.04] [--color #hex] [--symbol-color #hex] --out <dir> [--name logo]

Writes <name>.svg (horizontal), <name>-stacked.svg, <name>-wordmark.svg into <out>, all true vector
(the font's glyph outlines become paths: no font file is needed to open them), plus PNG previews.

Fonts come from Google Fonts (free for commercial use, OFL): the CSS API is asked with a plain user agent,
which makes it answer with a TTF URL; the file is cached in ~/.cache/logo-my-brand/fonts.
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import curl, download, log, svg_to_png  # noqa: E402

CACHE = Path.home() / ".cache" / "logo-my-brand" / "fonts"
FALLBACK_FONTS = ["Inter", "Manrope", "Space Grotesk", "DM Sans", "Outfit"]


def font_file(family, weight=700):
    """A TTF for a Google Font family at a weight. Returns a path or None."""
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "-", family).strip("-")
    dest = CACHE / f"{safe}-{weight}.ttf"
    if dest.exists() and dest.stat().st_size > 10000:
        return dest
    import subprocess

    def css_for(q):   # a plain user agent makes Google Fonts answer with TTF urls instead of woff2
        r = subprocess.run(["curl", "-sL", "--max-time", "20", "-A", "Wget/1.21", f"https://fonts.googleapis.com/css2?family={q}"], capture_output=True)
        return r.stdout.decode("utf-8", "ignore")
    fam = family.replace(" ", "+")
    css = css_for(f"{fam}:wght@{weight}")
    m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css or "")
    if not m:
        css = css_for(fam)
        m = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css or "")
    if not m or not download(m.group(1), dest, min_bytes=10000):
        return None
    return dest


def text_path(text, ttf, size=200, tracking=0.0):
    """SVG path data for a line of text, baseline at y=0 (y down), and its advance width.
    tracking is a fraction of the font size added between letters."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    f = TTFont(str(ttf))
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm
    scale = size / upm
    hmtx = f["hmtx"]
    kern = {}
    if "kern" in f:
        try:
            for t in f["kern"].kernTables:
                kern.update(t.kernTable)
        except Exception:
            pass
    pen = SVGPathPen(gs)
    x = 0.0
    prev = None
    for ch in text:
        g = cmap.get(ord(ch))
        if g is None:
            g = cmap.get(ord("?"))
        if prev and (prev, g) in kern:
            x += kern[(prev, g)] * scale
        tp = TransformPen(pen, (scale, 0, 0, -scale, x, 0))
        gs[g].draw(tp)
        x += hmtx[g][0] * scale + (tracking * size if ch != " " else 0)
        prev = g
    width = x - (tracking * size if text else 0)
    asc = f["OS/2"].sCapHeight * scale if getattr(f["OS/2"], "sCapHeight", 0) else f["hhea"].ascent * scale * 0.7
    desc = -f["hhea"].descent * scale
    return pen.getCommands(), width, asc, desc


def symbol_body(svg_text):
    """Inner markup and viewBox of a symbol SVG."""
    vb = re.search(r'viewBox="([-\d.\s]+)"', svg_text)
    x, y, w, h = [float(v) for v in vb.group(1).split()] if vb else (0, 0, 1024, 1024)
    inner = re.sub(r"^.*?<svg[^>]*>", "", svg_text, flags=re.S)
    inner = re.sub(r"</svg>\s*$", "", inner, flags=re.S)
    inner = re.sub(r"<title[^>]*>.*?</title>", "", inner, flags=re.S)
    return inner, (x, y, w, h)


def recolor(inner, color):
    return re.sub(r'fill="#[0-9a-fA-F]{3,6}"', f'fill="{color}"', inner)


def apply_case(name, case):
    return {"upper": name.upper(), "lower": name.lower(), "title": name.title()}.get(case, name)


def build(symbol_svg, name, ttf, out, base="logo", case="as-is", tracking=0.02, color="#111111",
          symbol_color=None, title=None):
    """Horizontal, stacked and wordmark-only lockups. Returns {kind: path}."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    text = apply_case(name, case)
    size = 200
    d, tw, cap, desc = text_path(text, ttf, size, tracking)
    import html as _h
    title = _h.escape(title or f"{name} logo", quote=True)
    try:   # a name color too light to read on white falls back to near-black
        r_, g_, b_ = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        if 0.299 * r_ + 0.587 * g_ + 0.114 * b_ > 175:
            color = "#151515"
    except Exception:
        color = "#151515"
    files = {}
    # wordmark only
    pad = size * 0.12
    wvb = (-pad, -cap - pad, tw + 2 * pad, cap + desc + 2 * pad)
    word = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{wvb[0]:.1f} {wvb[1]:.1f} {wvb[2]:.1f} {wvb[3]:.1f}" role="img">'
            f'<title>{title}</title><path fill="{color}" d="{d}"/></svg>')
    (out / f"{base}-wordmark.svg").write_text(word)
    files["wordmark"] = out / f"{base}-wordmark.svg"
    if symbol_svg and Path(symbol_svg).exists():
        inner, (sx, sy, sw, sh) = symbol_body(Path(symbol_svg).read_text())
        if symbol_color:
            inner = recolor(inner, symbol_color)
        # horizontal: symbol height = 1.55 x cap height, gap = 0.45 x cap
        k = 1.9 if sw <= sh * 1.4 else 1.5        # a wide symbol sits a little smaller
        hs = cap * k / sh
        gap = cap * 0.55
        sym_w = sw * hs
        total_w = sym_w + gap + tw
        top = -cap / 2 - cap * k / 2             # symbol centered on the cap height
        bottom = max(top + cap * k, desc)
        vb = (-pad, top - pad, total_w + 2 * pad, bottom - top + 2 * pad)
        hor = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]:.1f} {vb[1]:.1f} {vb[2]:.1f} {vb[3]:.1f}" role="img"><title>{title}</title>'
               f'<g transform="translate({-sx * hs:.2f},{top - sy * hs:.2f}) scale({hs:.4f})">{inner}</g>'
               f'<path fill="{color}" transform="translate({sym_w + gap:.2f},0)" d="{d}"/></svg>')
        (out / f"{base}.svg").write_text(hor)
        files["horizontal"] = out / f"{base}.svg"
        # stacked: symbol width = 0.62 x name width (or height 2.4 cap), centered, name below
        ss = min(tw * 0.62 / sw, cap * 2.6 / sh)
        sym_w2, sym_h2 = sw * ss, sh * ss
        gap2 = cap * 0.55
        W = max(tw, sym_w2)
        st = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.1f} {-pad:.1f} {W + 2 * pad:.1f} {sym_h2 + gap2 + cap + desc + 2 * pad:.1f}" role="img"><title>{title}</title>'
              f'<g transform="translate({(W - sym_w2) / 2 - sx * ss:.2f},{-sy * ss:.2f}) scale({ss:.4f})">{inner}</g>'
              f'<path fill="{color}" transform="translate({(W - tw) / 2:.2f},{sym_h2 + gap2 + cap:.2f})" d="{d}"/></svg>')
        (out / f"{base}-stacked.svg").write_text(st)
        files["stacked"] = out / f"{base}-stacked.svg"
    else:
        (out / f"{base}.svg").write_text(word)
        files["horizontal"] = out / f"{base}.svg"
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("symbol")
    ap.add_argument("--font", default="Inter")
    ap.add_argument("--weight", type=int, default=700)
    ap.add_argument("--case", default="as-is")
    ap.add_argument("--tracking", type=float, default=0.02)
    ap.add_argument("--color", default="#111111")
    ap.add_argument("--symbol-color")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="logo")
    a = ap.parse_args()
    from common import read_json
    brief = read_json(Path(a.run) / "brief.json") or {}
    ttf = None
    for fam in [a.font] + FALLBACK_FONTS:
        ttf = font_file(fam, a.weight)
        if ttf:
            if fam != a.font:
                log(f"font {a.font} not found; used {fam}")
            break
    files = build(a.symbol, brief.get("brand", "Brand"), ttf, a.out, a.name, a.case, a.tracking, a.color, a.symbol_color)
    for k, f in files.items():
        svg_to_png(f, Path(f).with_suffix(".png"), width=1600, height=1000 if k != "stacked" else 1400, bg="#ffffff", padding=0.08)
        log(f"  {k}: {f}")


if __name__ == "__main__":
    main()
