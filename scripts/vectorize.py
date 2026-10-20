"""Step 6: from a chosen concept PNG to production vector files.

  vectorize <run> <concept-id | png> [--colors 3] [--name final]

What it does, in order:
  1. Cuts the white studio background away (flood fill from the edges, so cream shapes inside the logo survive).
  2. Crops to the artwork with a 6% margin and writes <name>-2048.png (transparent, for anything raster).
  3. Quantizes the artwork to at most --colors solid colors (the brief's palette snaps them to exact hex).
  4. Traces every color layer with potrace (vtracer when potrace is missing) and merges the layers into
     ONE clean SVG with one <path> per color, viewBox 0 0 1024 1024, a <title>, no rasters, no gradients.
  5. Runs the base skill's svg_audit on it and writes audit.txt, then export_variants for black / white /
     mono / square / favicon files into kit/svg/.

The SVG is traced, not drawn: curves carry more anchors than a hand-built mark. The audit says so, and
SKILL.md tells the designer when to rebuild the symbol by hand from references/svg-construction.md.
"""
import argparse
import colorsys
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import base_script, log, read_json, run_py, svg_to_png, write_json  # noqa: E402


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(c):
    return "#%02x%02x%02x" % tuple(int(x) for x in c[:3])


def cut_background(im, tol=26, counter_tol=12):
    """Paper becomes transparent: the studio background reachable from the edges (near-white, flood fill), and
    the pure-white counters inside letters. Off-whites inside the mark (cream, ivory) stay: they are ink."""
    from PIL import Image, ImageChops, ImageFilter
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    lo = 255 - tol
    outside = Image.new("L", (w, h), 0)
    op = outside.load()
    stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or op[x, y]:
            continue
        r, g, b = px[x, y]
        if r < lo or g < lo or b < lo:
            continue
        op[x, y] = 255
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    r, g, b = rgb.split()
    lo2 = 255 - counter_tol
    pure = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v >= lo2 else 0), g.point(lambda v: 255 if v >= lo2 else 0)),
                               b.point(lambda v: 255 if v >= lo2 else 0))
    paper = ImageChops.lighter(outside, pure)
    alpha = paper.point(lambda v: 255 - v).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    return out


def crop_margin(im, margin=0.06):
    """Crop to the artwork plus a margin; the aspect follows the mark (a lockup stays wide)."""
    from PIL import Image
    bbox = im.split()[3].point(lambda v: 255 if v > 40 else 0).getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    pad = int(max(r - l, b - t) * margin)
    canvas = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    canvas.paste(im.crop(bbox), (pad, pad), im.crop(bbox))
    return canvas


def palette_of(im, k, snap=()):
    """The k most used opaque colors, merged when closer than a threshold, snapped to the brief's hex when near."""
    small = im.copy()
    small.thumbnail((256, 256))
    opaque = [(r, g, b) for r, g, b, a in list(small.getdata()) if a > 200]
    if not opaque:
        return [(0, 0, 0)]
    from PIL import Image
    tmp = Image.new("RGB", (len(opaque), 1))
    tmp.putdata(opaque)
    q = tmp.quantize(colors=max(k * 3, 8), method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[:3 * (k * 3)]
    counts = sorted(q.getcolors(), reverse=True)
    cols = []
    for n, idx in counts:
        c = tuple(pal[3 * idx:3 * idx + 3])
        if not any(sum((a - b) ** 2 for a, b in zip(c, o)) < 60 ** 2 for o in cols):
            cols.append(c)
        if len(cols) >= k:
            break
    snapped = []
    for c in cols:
        best = min(((sum((a - b) ** 2 for a, b in zip(c, hex_to_rgb(s))), s) for s in snap), default=(1e9, None))
        c = hex_to_rgb(best[1]) if best[0] < 90 ** 2 else c
        if c not in snapped:
            snapped.append(c)
    # A declared brand color that the mark really uses stays, however small its area (an accent in an ampersand).
    total = max(1, len(opaque))
    for h in snap:
        rgb = hex_to_rgb(h)
        if rgb in snapped:
            continue
        near = sum(1 for px_ in opaque if sum((a - b) ** 2 for a, b in zip(px_, rgb)) < 55 ** 2)
        if near / total >= 0.004:
            snapped.append(rgb)
    # Primary color = the ink: darkest or most saturated, so the one-color variants are never cream on white.
    def ink(c):
        h, l, s_ = colorsys.rgb_to_hls(*(x / 255 for x in c))
        return (1 - l) + s_ * 0.6
    snapped.sort(key=ink, reverse=True)
    return snapped


def layer_masks(im, palette):
    """Assign every opaque pixel to its nearest palette color; one 1-bit mask per color."""
    from PIL import Image
    w, h = im.size
    data = list(im.getdata())
    masks = [bytearray(w * h) for _ in palette]
    for i, (r, g, b, a) in enumerate(data):
        if a < 128:
            continue
        j = min(range(len(palette)), key=lambda t: (r - palette[t][0]) ** 2 + (g - palette[t][1]) ** 2 + (b - palette[t][2]) ** 2)
        masks[j][i] = 255
    return [Image.frombytes("L", (w, h), bytes(m)) for m in masks]


BLUR_USED = [2.0]   # set after the master trace, so the one-color files match it
BLUR = 2.0   # module default; trace_layers() tries finer settings when the result drifts from the ink


def trace_mask(mask, tmp, idx, blur=None):
    """potrace -> path data. Returns the d string (may be several subpaths)."""
    blur = BLUR if blur is None else blur
    pbm = tmp / f"l{idx}.pbm"
    svg = tmp / f"l{idx}.svg"
    # Blur then re-threshold: the pixel stair-steps of the raster become smooth edges before tracing.
    # A big blur smooths wobble but eats hairlines; the caller measures and picks.
    from PIL import ImageFilter
    smooth = mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: 255 if v > 128 else 0) if blur > 0 else mask
    smooth.point(lambda v: 0 if v > 128 else 255).convert("1").save(pbm)
    turd = "40" if blur >= 2 else "12"
    alpha = "1.2" if blur >= 2 else "1.0"
    opt = "0.5" if blur >= 2 else "0.2"
    if shutil.which("potrace"):
        subprocess.run(["potrace", pbm, "-s", "-o", svg, "--flat", "-t", turd, "-a", alpha, "-O", opt, "-u", "10"],
                       check=True, capture_output=True)
        text = svg.read_text()
        tr = re.search(r'<g transform="translate\(([-\d.]+),([-\d.]+)\) scale\(([-\d.]+),([-\d.]+)\)"', text)
        d = " ".join(re.findall(r'<path d="([^"]+)"', text, re.S))
        return d, (tr.groups() if tr else None), text
    sys.exit("potrace is required (brew install potrace); run scripts/check-env.sh")


def first_letter(work, pal):
    """The leftmost letter of a wordmark, cut out as a monogram: the connected ink components whose x-range
    overlaps the leftmost component (so an i keeps its dot). None when the mark is one blob."""
    from PIL import Image
    alpha = work.split()[3].point(lambda v: 255 if v > 60 else 0)
    small = alpha.copy()
    scale = 400 / max(alpha.size)
    small = small.resize((max(1, int(alpha.size[0] * scale)), max(1, int(alpha.size[1] * scale))), Image.NEAREST)
    w, h = small.size
    px = small.load()
    seen = bytearray(w * h)
    comps = []
    for y in range(h):
        for x in range(w):
            if px[x, y] and not seen[y * w + x]:
                stack = [(x, y)]
                seen[y * w + x] = 1
                xs, ys, n = [x], [y], 0
                while stack:
                    cx, cy = stack.pop()
                    n += 1
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h and px[nx, ny] and not seen[ny * w + nx]:
                            seen[ny * w + nx] = 1
                            stack.append((nx, ny))
                            xs.append(nx)
                            ys.append(ny)
                if n > 12:
                    comps.append((min(xs), max(xs), min(ys), max(ys), n))
    if len(comps) < 3:
        return None
    comps.sort()
    first = comps[0]
    group = [c for c in comps if c[0] <= first[1] and c[1] >= first[0]]
    # one line of text only: every part of the "first letter" must share the first part's vertical band
    # (a stacked lockup would otherwise give the first letters of two rows, cut mid-word)
    if any(c[3] < first[2] or c[2] > first[3] for c in group if c is not first and c[4] > first[4] * 0.2):
        return None
    ys = [c for c in comps if not (c[3] < first[2] or c[2] > first[3])]
    if len(ys) < len(comps) * 0.6:   # most of the ink sits on other rows: a stacked mark, no monogram
        return None
    x0, x1 = min(c[0] for c in group), max(c[1] for c in group)
    y0, y1 = min(c[2] for c in group), max(c[3] for c in group)
    if (x1 - x0) > 0.45 * w:      # the "first letter" is most of the mark: no monogram
        return None
    box = (int(x0 / scale) - 2, int(y0 / scale) - 2, int((x1 + 1) / scale) + 2, int((y1 + 1) / scale) + 2)
    return crop_margin(work.crop((max(0, box[0]), max(0, box[1]), min(work.size[0], box[2]), min(work.size[1], box[3]))), 0.1)


def split_symbol(alpha):
    """Find the symbol in a lockup: the biggest gap in the alpha projection (rows for a stacked lockup,
    columns for a horizontal one). Returns ("rows"|"cols", cut, which_side_is_symbol) or None."""
    w, h = alpha.size
    px = alpha.load()
    best = None
    for axis in ("rows", "cols"):
        n = h if axis == "rows" else w
        prof = []
        for i in range(n):
            line = (px[x, i] for x in range(w)) if axis == "rows" else (px[i, y] for y in range(h))
            prof.append(sum(1 for v in line if v > 60))
        ink = [i for i, v in enumerate(prof) if v > 0]
        if not ink:
            continue
        lo, hi = ink[0], ink[-1]
        gaps, start = [], None
        for i in range(lo, hi + 1):
            if prof[i] == 0 and start is None:
                start = i
            if prof[i] > 0 and start is not None:
                gaps.append((i - start, start, i))
                start = None
        if not gaps:
            continue
        g = max(gaps)
        if g[0] < (hi - lo) * 0.03:
            continue
        a_side, b_side = g[1] - lo, hi - g[2]
        small, big = min(a_side, b_side), max(a_side, b_side)
        if small < (hi - lo) * 0.12:
            continue
        # the symbol is the part whose bounding box is closer to square
        def squareness(i0, i1):
            cols = [x for x in range(w) if any(px[x, y] > 60 for y in range(i0, i1 + 1))] if axis == "rows" else None
            rows = [y for y in range(h) if any(px[x, y] > 60 for x in range(i0, i1 + 1))] if axis == "cols" else None
            if axis == "rows":
                bw, bh = (cols[-1] - cols[0] + 1) if cols else 1, i1 - i0 + 1
            else:
                bw, bh = i1 - i0 + 1, (rows[-1] - rows[0] + 1) if rows else 1
            return min(bw, bh) / max(bw, bh)
        sa, sb = squareness(lo, g[1] - 1), squareness(g[2], hi)
        cand = (g[0] / (hi - lo), axis, (g[1] + g[2]) // 2, "a" if sa >= sb else "b")
        if best is None or cand[0] > best[0]:
            best = cand
    return best[1:] if best else None


def lum(c):
    return (0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]) / 255


def ink_layers(pal, masks):
    """Which color layers are 'ink' for a one-color version. A mark with a dark plate and light letters
    keeps the plate and knocks the letters out (so the letters stay readable in one color); a mark whose
    colors are all mid or light is ink everywhere."""
    if len(pal) < 2:
        return list(range(len(pal)))
    ls = [lum(c) for c in pal]
    if max(ls) - min(ls) > 0.45:
        return [i for i, l in enumerate(ls) if l < (min(ls) + max(ls)) / 2]
    return list(range(len(pal)))


def one_color_svgs(pal, masks, size, out_dir, base, title, tmp_root, main_hex):
    from PIL import ImageChops
    idx = ink_layers(pal, masks)
    ink = None
    for i in idx:
        ink = masks[i] if ink is None else ImageChops.lighter(ink, masks[i])
    if ink is None or ink.getbbox() is None:
        return
    with tempfile.TemporaryDirectory() as t:
        d, tr, _ = trace_mask(ink, Path(t), 99, blur=BLUR_USED[0])
    for suffix, fill in (("black", "#000000"), ("white", "#ffffff"), ("brandcolor", main_hex)):
        (out_dir / f"{base}-{suffix}.svg").write_text(merge_svg([(hex_to_rgb(fill), d, tr)], size, f"{title} ({suffix})"))


def fidelity(svg_text, masks, size, tmp):
    """IoU between the traced SVG (rendered back) and the ink it was traced from. 1.0 = identical."""
    from PIL import Image, ImageChops
    vw, vh = size
    f = tmp / "fid.svg"
    f.write_text(svg_text)
    png = tmp / "fid.png"
    if not svg_to_png(f, png, width=vw, height=vh):
        return None
    rendered = Image.open(png).convert("RGBA").split()[3].point(lambda v: 255 if v > 128 else 0)
    ink = None
    for m in masks:
        ink = m if ink is None else ImageChops.lighter(ink, m)
    ink = ink.point(lambda v: 255 if v > 128 else 0)
    inter = ImageChops.multiply(rendered, ink).histogram()[255]
    union = ImageChops.lighter(rendered, ink).histogram()[255]
    return inter / union if union else 0.0


def trace_layers(pal, masks, size, title, log_name="mark"):
    """Trace every color layer at a few smoothing levels and keep the most faithful result that is still
    smooth: the first level whose IoU against the ink is 0.93 or better, else the best one."""
    best = None
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        for blur in (2.0, 1.0, 0.4):
            layers = []
            for i, (c, m) in enumerate(zip(pal, masks)):
                if m.getbbox() is None:
                    continue
                d, tr, _ = trace_mask(m, tmp, i, blur=blur)
                layers.append((c, d, tr))
            text = merge_svg(layers, size, title)
            iou = fidelity(text, masks, size, tmp)
            if best is None or (iou or 0) > best[0]:
                best = (iou or 0, blur, layers, text)
            if iou is not None and iou >= 0.93:
                break
    log(f"  {log_name}: fidelity {best[0]:.3f} at blur {best[1]}")
    return best


def merge_svg(layers, size, title):
    import html as _html
    title = _html.escape(title, quote=True)
    vw, vh = size
    parts = []
    for color, d, tr in layers:
        if not d.strip():
            continue
        g = f' transform="translate({tr[0]},{tr[1]}) scale({tr[2]},{tr[3]})"' if tr else ""
        parts.append(f'  <g fill="{rgb_to_hex(color)}" fill-rule="evenodd"{g}><path d="{d}"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
            f'role="img" aria-labelledby="title">\n  <title id="title">{title}</title>\n' + "\n".join(parts) + "\n</svg>\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("concept", help="concept id (e.g. B2) or a PNG path")
    ap.add_argument("--colors", type=int, default=3)
    ap.add_argument("--name", default="final")
    ap.add_argument("--out-dir", help="where svg/ and png/ go (default <run>/kit); final.json is written only for the default")
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--symbol-only", action="store_true", help="trace the master and stop (used to compose concepts)")
    a = ap.parse_args()
    from PIL import Image
    run = Path(a.run).resolve()
    brief = read_json(run / "brief.json") or {}
    src = Path(a.concept) if a.concept.lower().endswith(".png") else run / "concepts" / f"{a.concept}.png"
    entry = {}
    if not a.concept.lower().endswith(".png"):
        entry = next((p for p in (read_json(run / "prompts.json") or []) if p["id"] == a.concept), {})
    composed = entry.get("track") == "symbol" and (run / "concepts" / f"{a.concept}-symbol.png").exists()
    if composed:
        src = run / "concepts" / f"{a.concept}-symbol-2048.png"
        if not src.exists():
            src = run / "concepts" / f"{a.concept}-symbol.png"
    else:
        refined = run / "concepts" / f"{Path(a.concept).stem}-2048.png"
        if not a.concept.lower().endswith(".png") and refined.exists():
            src = refined  # the clean 2048 re-render from `concepts refine`
    if not src.exists():
        sys.exit(f"{src} not found")
    kit = Path(a.out_dir).resolve() if a.out_dir else run / "kit"
    if (kit / "svg").exists():
        shutil.rmtree(kit / "svg")   # a previous pick's symbol files must never leak into this one
    (kit / "svg").mkdir(parents=True, exist_ok=True)
    (kit / "png").mkdir(parents=True, exist_ok=True)

    im = Image.open(src).convert("RGBA")
    log(f"Cutting the background from {src.name}...")
    art = crop_margin(cut_background(im))

    snap = []
    cid = Path(a.concept).stem if not a.concept.lower().endswith(".png") else src.stem
    for d in brief.get("directions", []):
        if cid.lstrip("P").startswith(d["key"]):
            snap = d.get("palette", [])
    if entry.get("concept", {}).get("palette"):
        snap = entry["concept"]["palette"]
    if composed and entry.get("symbol_color"):
        snap = [entry["symbol_color"]] + [c for c in snap if c != entry["symbol_color"]]
    pal = palette_of(art, a.colors, snap)
    if snap and hex_to_rgb(snap[0]) in pal:
        pal.remove(hex_to_rgb(snap[0]))
        pal.insert(0, hex_to_rgb(snap[0]))   # the direction's declared brand color leads
    log(f"Palette: {' '.join(rgb_to_hex(c) for c in pal)}")
    mono = rgb_to_hex(pal[0])

    W, H = art.size
    long_side = 2048
    vw, vh = int(round(W * long_side / max(W, H))), int(round(H * long_side / max(W, H)))
    work = art.resize((vw, vh), Image.LANCZOS)
    work.save(kit / "png" / f"{a.name}-2048.png")
    masks = layer_masks(work, pal)
    fid, blur_used, layers, svg_text = trace_layers(pal, masks, (vw, vh), f"{brief.get('brand', 'Brand')} logo", "lockup")
    BLUR_USED[0] = blur_used
    master = kit / "svg" / f"{a.name}.svg"
    master.write_text(svg_text)
    log(f"wrote {master} ({len(layers)} color layers, {len(svg_text) // 1024} KB)")
    if a.symbol_only:
        return

    parts = {}
    if composed:
        # The traced art is the symbol; the name is set in the concept's real font; the lockups are built in code.
        from lockup import FALLBACK_FONTS, build, font_file
        sym = kit / "svg" / f"{a.name}-symbol.svg"
        master.rename(sym)
        one_color_svgs(pal, masks, (vw, vh), kit / "svg", f"{a.name}-symbol", f"{brief.get('brand', 'Brand')} symbol", None, mono)
        f = entry.get("font") or {}
        ttf = None
        for fam in [f.get("family", "Inter")] + FALLBACK_FONTS:
            ttf = font_file(fam, int(f.get("weight", 700) or 700))
            if ttf:
                entry["font_used"] = fam
                break
        name_color = entry.get("name_color", "#151515")
        files = build(sym, brief.get("brand", "Brand"), ttf, kit / "svg", a.name, f.get("case", "as-is"), float(f.get("tracking", 0.03) or 0.03), name_color)
        for kind in ("", "-stacked", "-wordmark"):
            src_svg = kit / "svg" / f"{a.name}{kind}.svg"
            if not src_svg.exists():
                continue
            t = src_svg.read_text()
            for suffix, fill in (("black", "#000000"), ("white", "#ffffff"), ("brandcolor", mono)):
                (kit / "svg" / f"{a.name}{kind}-{suffix}.svg").write_text(re.sub(r'fill="#[0-9a-fA-F]{3,6}"', f'fill="{fill}"', t))
        svg_to_png(master, kit / "png" / f"{a.name}-2048.png", width=2048, height=1024, padding=0.04)
        parts = {"symbol": str(sym.relative_to(run)) if not a.out_dir else str(sym),
                 "wordmark": str((kit / "svg" / f"{a.name}-wordmark.svg").relative_to(run)) if not a.out_dir else str(kit / "svg" / f"{a.name}-wordmark.svg"),
                 "stacked": str((kit / "svg" / f"{a.name}-stacked.svg").relative_to(run)) if not a.out_dir else str(kit / "svg" / f"{a.name}-stacked.svg"),
                 "font": {**f, "family": entry.get("font_used", f.get("family"))}}
        if hex_to_rgb(name_color) not in pal:
            pal.append(hex_to_rgb(name_color))
        log(f"composed lockups with {parts['font']['family']} {f.get('weight', 700)}: horizontal, stacked, wordmark, symbol")
        run_py([base_script("export_variants.py"), sym, "--out-dir", kit / "svg", "--name", f"{a.name}-symbol",
                "--title", f"{brief.get('brand', 'Brand')} symbol", "--mono", mono, "--icon-bg", mono, "--only", "favicon", "app-icon"])
        run_py([base_script("export_variants.py"), master, "--out-dir", kit / "svg", "--name", a.name,
                "--title", f"{brief.get('brand', 'Brand')} logo", "--mono", mono, "--icon-bg", mono, "--only", "square"])
        score = None
        if not a.no_audit:
            code, out, err = run_py([base_script("svg_audit.py"), sym])
            (kit / "audit.txt").write_text(out + err)
            if not a.out_dir:
                (run / "audit.txt").write_text(out + err)
            score = re.search(r"score:\s*(\d+)/100", out)
            log(f"svg_audit (symbol): {score.group(1) + '/100' if score else 'see audit.txt'}")
        write_json((kit / "final.json") if a.out_dir else (run / "final.json"), {
            "concept": cid, "master": str(master.relative_to(run)) if not a.out_dir else str(master), "palette": [rgb_to_hex(c) for c in pal],
            "png2048": (f"kit/png/{a.name}-2048.png" if not a.out_dir else str(kit / "png" / f"{a.name}-2048.png")),
            "audit_score": int(score.group(1)) if score else None, "fidelity": round(fid, 3), "composed": True, **parts})
        log(f"variants in {kit / 'svg'}: " + ", ".join(sorted(p.name for p in (kit / 'svg').glob('*.svg'))))
        return

    # Symbol and wordmark as their own files, when the lockup has a visible gap between them.
    split = split_symbol(work.split()[3])
    if split:
        axis, cut, side = split
        for part in ("symbol", "wordmark"):
            take_a = (part == "symbol") == (side == "a")
            box = (0, 0, vw, cut) if (axis == "rows" and take_a) else (0, cut, vw, vh) if axis == "rows" else \
                  (0, 0, cut, vh) if take_a else (cut, 0, vw, vh)
            piece = crop_margin(work.crop(box), 0.04)
            pw, ph = piece.size
            _, _, lay, text = trace_layers(pal, layer_masks(piece, pal), (pw, ph), f"{brief.get('brand', 'Brand')} {part}", part)
            f = kit / "svg" / f"{a.name}-{part}.svg"
            f.write_text(text)
            parts[part] = str(f.relative_to(run)) if not a.out_dir else str(f)
            if part == "symbol":
                one_color_svgs(pal, layer_masks(piece, pal), (pw, ph), kit / "svg", f"{a.name}-symbol",
                               f"{brief.get('brand', 'Brand')} symbol", None, mono)
        log(f"split into symbol + wordmark ({axis}); symbol = {parts.get('symbol')}")
    else:
        mono_piece = first_letter(work, pal)
        if mono_piece is not None:
            pw, ph = mono_piece.size
            _, _, lay, text = trace_layers(pal, layer_masks(mono_piece, pal), (pw, ph), f"{brief.get('brand', 'Brand')} monogram", "monogram")
            f = kit / "svg" / f"{a.name}-symbol.svg"
            f.write_text(text)
            parts["symbol"] = str(f.relative_to(run)) if not a.out_dir else str(f)
            parts["symbol_is_monogram"] = True
            one_color_svgs(pal, layer_masks(mono_piece, pal), (pw, ph), kit / "svg", f"{a.name}-symbol",
                           f"{brief.get('brand', 'Brand')} monogram", None, mono)
            log("no symbol in the lockup: the first letter is the monogram (favicon, avatar, stamp)")
        else:
            log("no clear symbol/wordmark gap: the whole mark is the symbol")

    score = None
    if not a.no_audit:
        code, out, err = run_py([base_script("svg_audit.py"), master])
        (kit / "audit.txt").write_text(out + err)
        if not a.out_dir:
            (run / "audit.txt").write_text(out + err)
        score = re.search(r"score:\s*(\d+)/100", out)
        log(f"svg_audit: {score.group(1) + '/100' if score else 'see audit.txt'}")
    run_py([base_script("export_variants.py"), master, "--out-dir", kit / "svg", "--name", a.name,
            "--title", f"{brief.get('brand', 'Brand')} logo", "--mono", mono, "--icon-bg", mono, "--only", "square", "favicon", "app-icon"])
    one_color_svgs(pal, masks, (vw, vh), kit / "svg", a.name, f"{brief.get('brand', 'Brand')} logo", None, mono)
    if parts.get("symbol"):
        run_py([base_script("export_variants.py"), run / parts["symbol"], "--out-dir", kit / "svg", "--name", f"{a.name}-symbol",
                "--title", f"{brief.get('brand', 'Brand')} symbol", "--mono", mono, "--icon-bg", mono, "--only", "favicon", "app-icon"])
    write_json((kit / "final.json") if a.out_dir else (run / "final.json"), {"concept": cid, "master": str(master.relative_to(run)) if not a.out_dir else str(master), "palette": [rgb_to_hex(c) for c in pal],
                                    "png2048": (f"kit/png/{a.name}-2048.png" if not a.out_dir else str(kit / "png" / f"{a.name}-2048.png")), "audit_score": int(score.group(1)) if score else None,
                                    "symbol": parts.get("symbol"), "wordmark": parts.get("wordmark"),
                                    "symbol_is_monogram": bool(parts.get("symbol_is_monogram")), "fidelity": round(fid, 3)})
    log(f"variants in {kit / 'svg'}: " + ", ".join(sorted(p.name for p in (kit / 'svg').glob('*.svg'))))


if __name__ == "__main__":
    main()
