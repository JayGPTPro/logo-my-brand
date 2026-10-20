"""Step 4 and 5: generate the concepts, judge them, pick three.

  prompts  <run>                         write prompts.json (4 prompts per direction) from brief + shelf
  generate <run> [--only A B] [--n 4]    render every prompt with gpt-image-2 (parallel, one attempt each)
  judge    <run>                         vision pass: spelling read-back + scores; picks one per direction
  sheet    <run>                         concepts.html + concepts.png: the checkpoint image the user sees

The prompt recipe lives in references/logo-prompt-recipes.md; keep the two in step.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (IMAGE_COST, QUALITY, WORKERS, append_cost, client, edit_image, esc, file_data_uri, generate_image,  # noqa: E402
                    log, read_json, screenshot_html, vision_cost, vision_json, write_json)

VARIANTS = [
    ("symbol-led", "The symbol is the hero, large above the wordmark; the wordmark small and quiet underneath."),
    ("wordmark-led", "The wordmark is the hero, set large and wide; the symbol is small and tucked beside or above the first letter."),
    ("emblem", "Symbol and wordmark unified into one compact badge-like unit with a single clean outer silhouette, no fine inner lines."),
    ("mono-minimal", "The most reduced version possible: one color, maximum two shapes, the idea stripped to its essence."),
]

RECIPE = """Professional brand logo for the e-commerce brand "{brand}". {product_line}
Mark type: {mark_type}. Idea: {idea}
Layout: {layout}
Typography: {type_feel}. The brand name is set as a custom logotype, letterforms drawn for this brand, consistent stroke weight, generous letterspacing, no default-looking font.
Colors: exactly these solid colors and nothing else: {palette}. {color_note}
Style: flat vector, solid filled shapes, clean geometry, exact angles, optical balance; the kind of mark that still reads when printed 20 mm wide in one color on {surface}.
Must avoid: {cliches}. Also avoid: gradients, shadows, 3D, bevels, glow, textures, mockups, backgrounds, scenes, borders, taglines, any text other than the brand name.
Composition: the logo alone, centered, with generous empty margin on every side, on a pure flat white background. The brand name must be spelled exactly "{brand}" and nothing else may be written."""


IDEATE = """You are the creative director of a top identity studio (think Pentagram, Collins, DesignStudio) writing the
concept sheet for the brand "{brand}". Brief: {product}. Audience: {audience}. Tier: {tier}. Adjectives: {adjectives}.
Name notes: {name_notes}. Surfaces: {surfaces}. Cliches banned: {cliches}. Shelf facts: {shelf}.
{trends}
{steer}

The three strategic directions are fixed:
{directions}

Write FIVE concepts per direction, fifteen in all, each a genuinely different idea (not the same idea in another
layout). Spread the visual devices across the sheet; no device twice in one direction:
negative space that hides a second image · a ligature or shared stroke between two letters · a counter-form (the hole
in a letter becomes the symbol) · one modified letter that carries the idea · a geometric construction from circles
and squares on a grid · a continuous single line (monoline) · a pictorial twist (the thing drawn from an unexpected
angle or combined with a letter) · a pattern or repetition that becomes a mark · a badge or seal with ONE unexpected
cut · an abstract form built from the product's silhouette · typographic play with scale or rotation · a
hand-drawn or sign-painted letterform (custom, not a font).
Give each concept a style world (e.g. Swiss modernism, 1930s sign painting, Bauhaus geometry, Japanese minimalism,
Memphis color blocking, Art Deco, Scandinavian craft, contemporary editorial serif, vintage apothecary, sports
heritage) that fits the direction, and vary the worlds across the twelve.

Every concept is on one of two tracks:
- "symbol": a drawn symbol (pictorial, abstract, monogram letter-shape, emblem) PLUS the brand name set in a real
  typeface you choose from Google Fonts. The image model draws ONLY the symbol, never letters of the name; code sets
  the name. At least eight of the twelve are on this track (exact spelling, real typography, clean vector).
- "lettering": the name itself is the logo with custom-drawn letters (a modified letter, a ligature, a hand-drawn
  sign-painted word). The image model draws the whole word. Two to four of the twelve.

For each concept return: {{"direction": "A"|"B"|"C", "track": "symbol"|"lettering", "name": 2-3 words, "device": the device from the list,
"style_world": ..., "mark_type": wordmark|lettermark|monogram|pictorial|abstract|emblem|combination,
"idea": TWO sentences a designer can draw from, naming exactly what the symbol is and what the letters do,
"composition": how symbol and name sit (one line), "type": the typographic voice in 6 to 10 words (weight, width,
case, terminals, spacing), "palette": 1 to 3 hex colors from the direction's palette (one-color concepts are welcome),
"ownable_detail": the one detail nobody else on the shelf has, in a few words,
"symbol_brief": for the symbol track, exactly what to draw in 2 sentences with NO words or letters except a single
monogram letter when the device is a monogram (shapes, construction, what the negative space shows),
"font": for the symbol track {{"family": an existing Google Fonts family that fits the style world (e.g. Space
Grotesk, Syne, Fraunces, DM Serif Display, Archivo, Unbounded, Outfit, Manrope, Bricolage Grotesque, Instrument
Serif, Young Serif, Familjen Grotesk, Sora, Big Shoulders Display, Playfair Display, Cormorant Garamond, Righteous,
Lexend, Epilogue, Chivo, Red Hat Display), "weight": 300-900, "case": "upper"|"lower"|"title"|"as-is", "tracking":
-0.02 to 0.2 (letter spacing as a fraction of the size)}}, "symbol_color": hex, "name_color": hex}}.
Rules: the idea must be drawable in flat vector; nothing literal from the cliche list; between two and four of the
twelve are one color (and a one-color concept uses the direction's MAIN color, not black, unless the direction is
black) and the rest use the direction's palette with intent; the direction's main color appears in at least two of its
four concepts (a colored symbol against a dark name, a
two-tone letter, a colored counter); at least two have no separate symbol at all; no two concepts share both device
and composition.
Return JSON: {{"concepts": [ ...15... ]}}"""

RECIPE2 = """Professional brand logo for the brand "{brand}". {product_line}
Concept "{name}" in the spirit of {style_world}. Mark type: {mark_type}.
The idea: {idea}
Visual device: {device}. The ownable detail: {ownable_detail}.
Composition: {composition}
Typography: {type}. The brand name is a custom logotype drawn for this brand: consistent stroke logic, optical spacing,
deliberate terminals; it must not look like a default font.
Colors: exactly these solid colors and nothing else: {palette}. {color_note}
Craft: flat vector, solid filled shapes, clean resolved geometry, optical balance, confident negative space; the kind of
mark a senior identity designer would present, that still reads printed 20 mm wide in one color on {surface}.
Must avoid: {cliches}. Also avoid: gradients, shadows, 3D, bevels, glow, textures, mockups, backgrounds, scenes,
borders, taglines, any text other than the brand name.
Composition on the canvas: the logo alone, centered, generous empty margin on every side, pure flat white background.
The brand name must be spelled exactly "{brand}" and nothing else may be written."""


SYMBOL_RECIPE = """A professional brand symbol (logo mark only, no wordmark) for the brand "{brand}". {product_line}
Concept "{name}" in the spirit of {style_world}. Device: {device}.
Draw exactly this: {symbol_brief}
The ownable detail: {ownable_detail}.
Constraints: at most 3 shapes; flat solid color {symbol_color}{second}; built on a clear geometric grid with consistent
stroke weights and exact curves; confident negative space; it must read as one clear silhouette at 16 px and work in a
single color. Avoid: {cliches}; gradients, shadows, 3D, outlines around the mark, textures, mockups.
NO letters, NO words, NO numbers anywhere{letter_rule}.
Composition: the symbol alone, centered, filling about 60 percent of the canvas, pure flat white background."""

ANCHOR_NOTE = """

The reference image shows {n} professional logos from other companies as a benchmark for craft level, finish and
simplicity ONLY. Do not copy their shapes, subjects, letters or layouts; the new symbol must look nothing like them."""

DEVICE_TECH = [("negative", "negative-space"), ("ligature", "ligature"), ("counter", "negative-space"), ("monoline", "line-monoline"),
               ("single line", "line-monoline"), ("grid", "geometric-construction"), ("geometric", "geometric-construction"),
               ("pattern", "modular-repetition"), ("repetition", "modular-repetition"), ("badge", "containment"), ("seal", "containment"),
               ("silhouette", "hidden-meaning"), ("pictorial", "hidden-meaning"), ("letter", "letter-substitution"),
               ("type", "letter-substitution"), ("hand", "hand-drawn"), ("sign", "hand-drawn"), ("mirror", "mirror-symmetry"),
               ("radial", "radial-symmetry"), ("overlap", "overlap-transparency")]


def anchor_sheet(run, device, seed, out):
    """Two exemplary library marks that use the concept's technique, side by side on white. Returns the PNG or None."""
    import random
    from common import base_skill, svg_to_png
    from PIL import Image
    lib = base_skill()
    if not lib:
        return None
    cat = read_json(lib / "assets" / "library" / "catalog.json") or []
    tech = next((t for k, t in DEVICE_TECH if k in (device or "").lower()), "geometric-construction")
    pool = [e for e in cat if tech in (e.get("techniques") or []) and e.get("exemplary") and not e.get("gradients") and e.get("n_colors", 9) <= 2]
    pool = pool or [e for e in cat if tech in (e.get("techniques") or []) and not e.get("gradients")]
    if len(pool) < 2:
        return None
    rnd = random.Random(seed)
    picks = rnd.sample(pool, 2)
    tiles = []
    for i, e in enumerate(picks):
        png = Path(out).with_name(f"{Path(out).stem}-a{i}.png")
        if svg_to_png(lib / "assets" / "library" / "svg" / e["file"], png, size=512, bg="#ffffff", padding=0.14):
            tiles.append(Image.open(png).convert("RGB"))
            png.unlink()
    if len(tiles) < 2:
        return None
    sheet = Image.new("RGB", (1024, 512), "white")
    sheet.paste(tiles[0], (0, 0))
    sheet.paste(tiles[1], (512, 0))
    sheet.save(out)
    return Path(out)


def ideate(run, brief, shelf, steer="", fresh=False):
    """Twelve concept briefs from the creative-director pass. Written to concepts.json; reused when it exists.
    steer: the user's feedback for another round (what they liked, what to drop)."""
    existing = read_json(run / "concepts.json")
    if existing and len(existing.get("concepts", [])) >= 12 and not fresh:
        return existing["concepts"]
    from intake import shelf_facts
    from trends import trend_facts
    trends = trend_facts(read_json(run / "trends.json"))
    c = client()
    dirs = "\n".join(f"{d['key']}: {d['name']} ({d['mark_type']}): {d['idea']} Why it wins: {d.get('why_it_wins', '')} "
                      f"Palette: {' '.join(d.get('palette', []))}. Type feel: {d.get('type_feel', '')}" for d in brief["directions"])
    prompt = IDEATE.format(brand=brief["brand"], product=brief.get("product", ""), audience=brief.get("audience", ""),
                           tier=brief.get("price_tier", ""), adjectives=", ".join(brief.get("adjectives", [])),
                           name_notes=brief.get("name_notes", ""),
                           surfaces="; ".join(f"{x['surface']} ({x['method']})" for x in brief.get("logo_surfaces", [])[:4]),
                           cliches="; ".join(brief.get("cliches", []) + shelf.get("read", {}).get("avoid", [])),
                           shelf=shelf_facts(shelf) or "no shelf measured", directions=dirs, trends=trends,
                           steer=("The client reviewed a first round and said: \"" + steer + "\". This round answers that: keep what "
                                  "they liked, drop what they rejected, and still offer range inside those bounds. Do not repeat the "
                                  "first round's concepts.") if steer else "")
    log("Creative-director pass: twelve distinct concepts..." + (" (steered by the client's feedback)" if steer else ""))
    res, usage = vision_json(c, prompt, [])
    append_cost(run, "ideate", vision_cost(usage))
    concepts = (res or {}).get("concepts", [])
    if len(concepts) < 12:
        sys.exit("the ideation pass returned too few concepts; run prompts again")
    write_json(run / "concepts.json", {"concepts": concepts})
    return concepts


def build_prompts(run):
    brief = read_json(run / "brief.json")
    shelf = read_json(run / "shelf.json") or {}
    brand = brief["brand"]
    cliches = brief.get("cliches", []) + shelf.get("read", {}).get("avoid", [])
    surface = (brief.get("logo_surfaces") or [{"surface": "kraft packaging"}])[0]["surface"]
    concepts = ideate(run, brief, shelf)
    prompts = []
    counts = {}
    for cpt in concepts:
        key = str(cpt.get("direction", "A"))[:1].upper()
        if key not in ("A", "B", "C") or counts.get(key, 0) >= 5:
            continue
        counts[key] = counts.get(key, 0) + 1
        pal = cpt.get("palette") or next((d.get("palette", ["#111111"]) for d in brief["directions"] if d["key"] == key), ["#111111"])
        track = "symbol" if cpt.get("track", "symbol") == "symbol" and cpt.get("symbol_brief") else "lettering"
        sym_color = cpt.get("symbol_color") or pal[0]
        entry = {
            "id": f"{key}{counts[key]}", "direction": key, "variant": cpt.get("device", ""), "track": track,
            "name": cpt.get("name", ""), "style_world": cpt.get("style_world", ""), "concept": cpt}
        if track == "symbol":
            mono = "monogram" in (cpt.get("device", "") + cpt.get("mark_type", "")).lower()
            entry["prompt"] = SYMBOL_RECIPE.format(
                brand=brand, product_line=f"The brand sells: {brief.get('product', '')}", name=cpt.get("name", ""),
                style_world=cpt.get("style_world", "contemporary identity design"), device=cpt.get("device", ""),
                symbol_brief=cpt.get("symbol_brief", ""), ownable_detail=cpt.get("ownable_detail", ""), symbol_color=sym_color,
                second=(f" with {pal[1]} as a small accent" if len(pal) > 1 and pal[1] != sym_color else ""),
                cliches="; ".join(cliches[:8]) or "category cliches",
                letter_rule=(f" except the single letter {brand.strip()[:1].upper()} drawn as a shape" if mono else ""))
            entry["font"] = cpt.get("font") or {"family": "Inter", "weight": 700, "case": "upper", "tracking": 0.04}
            entry["name_color"] = cpt.get("name_color") or "#151515"
            entry["symbol_color"] = sym_color
            prompts.append(entry)
            continue
        prompts.append({**entry,
            "prompt": RECIPE2.format(
                brand=brand, product_line=f"The brand sells: {brief.get('product', '')}",
                name=cpt.get("name", ""), style_world=cpt.get("style_world", "contemporary identity design"),
                mark_type=cpt.get("mark_type", "combination"), idea=cpt.get("idea", ""), device=cpt.get("device", ""),
                ownable_detail=cpt.get("ownable_detail", ""), composition=cpt.get("composition", ""),
                type=cpt.get("type", "clean geometric sans"), palette=", ".join(pal),
                color_note="One color only." if len(pal) == 1 else "Use the first color for the main shapes; the others only as small accents.",
                surface=surface, cliches="; ".join(cliches[:8]) or "category cliches")})
    write_json(run / "prompts.json", prompts)
    return prompts


def build_prompts_v1(run):
    brief = read_json(run / "brief.json")
    shelf = read_json(run / "shelf.json") or {}
    brand = brief["brand"]
    cliches = brief.get("cliches", []) + shelf.get("read", {}).get("avoid", [])
    surface = (brief.get("logo_surfaces") or [{"surface": "kraft packaging"}])[0]["surface"]
    prompts = []
    for d in brief["directions"]:
        pal = d.get("palette", ["#111111"])
        for vkey, layout in VARIANTS:
            palette = pal if vkey != "mono-minimal" else pal[:1]
            if d["mark_type"] in ("wordmark", "lettermark") and vkey == "symbol-led":
                layout = "The logotype itself carries the idea; one letter is modified to express it. No separate symbol."
            prompts.append({
                "id": f"{d['key']}{len([p for p in prompts if p['direction'] == d['key']]) + 1}",
                "direction": d["key"], "variant": vkey,
                "prompt": RECIPE.format(
                    brand=brand,
                    product_line=f"The brand sells: {brief.get('product', '')}",
                    mark_type=d["mark_type"], idea=d["idea"], layout=layout,
                    type_feel=d.get("type_feel", "clean geometric sans"),
                    palette=", ".join(palette),
                    color_note="One color only." if len(palette) == 1 else "Use the first color for the main shapes; the others only as small accents.",
                    surface=surface,
                    cliches="; ".join(cliches[:8]) or "category cliches")})
    write_json(run / "prompts.json", prompts)
    return prompts


def cmd_prompts(a):
    ps = build_prompts(Path(a.run))
    log(f"{len(ps)} prompts -> prompts.json")


def cmd_round(a):
    """Another round of twelve, steered by feedback (or just more range). The previous round is archived under
    rounds/<n>/ and its picks stay on the sheet as 'previous round' for comparison."""
    import shutil
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    shelf = read_json(run / "shelf.json") or {}
    judge = read_json(run / "judge.json") or {}
    n = len(list((run / "rounds").glob("*"))) + 1 if (run / "rounds").exists() else 1
    arch = run / "rounds" / f"{n}"
    arch.mkdir(parents=True, exist_ok=True)
    for f in ("concepts.json", "prompts.json", "judge.json", "concepts.png"):
        if (run / f).exists():
            shutil.move(str(run / f), str(arch / f))
    if (run / "concepts").exists():
        shutil.move(str(run / "concepts"), str(arch / "concepts"))
    (run / "concepts").mkdir()
    # the previous picks come along, so the client sees old vs new side by side
    keep = []
    for key, pid in judge.get("picks", {}).items():
        src = arch / "concepts" / f"{pid}.png"
        if src.exists():
            shutil.copy2(src, run / "concepts" / f"P{pid}.png")
            keep.append((key, pid))
    if (run / "options").exists():
        shutil.rmtree(run / "options")
    ideate(run, brief, shelf, steer=a.feedback or "", fresh=True)
    prompts = build_prompts(run)
    old_prompts = read_json(arch / "prompts.json") or []
    for key, pid in keep:
        base = next((p for p in old_prompts if p["id"] == pid), {})
        prompts.append({**base, "id": f"P{pid}", "direction": key, "variant": "previous round pick", "name": f"{base.get('name', pid)} (round {n})"})
    write_json(run / "prompts.json", prompts)
    log(f"round {n + 1}: {len(prompts) - len(keep)} new concepts to generate; previous picks kept as P{', P'.join(p for _, p in keep)}")


def compose(run, p, symbol_png, dest):
    """Symbol PNG -> quick vector -> lockup with the concept's real font -> the PNG the judge sees."""
    import subprocess
    from lockup import FALLBACK_FONTS, build, font_file
    from common import svg_to_png
    tmp = Path(run) / "concepts" / "_vec" / p["id"]
    r = subprocess.run([sys.executable, "-W", "ignore", str(Path(__file__).parent / "vectorize.py"), str(Path(run).resolve()), str(symbol_png),
                        "--out-dir", str(tmp), "--name", "sym", "--no-audit", "--colors", "2", "--symbol-only"], capture_output=True, text=True)
    sym_svg = tmp / "svg" / "sym.svg"
    if not sym_svg.exists():
        log(f"  {p['id']}: symbol vector failed: {r.stderr[-200:]}")
        return None
    f = p.get("font") or {}
    ttf = None
    for fam in [f.get("family", "Inter")] + FALLBACK_FONTS:
        ttf = font_file(fam, int(f.get("weight", 700) or 700))
        if ttf:
            p.setdefault("font_used", fam)
            break
    brand = (read_json(Path(run) / "brief.json") or {}).get("brand", "Brand")
    files = build(sym_svg, brand, ttf, tmp / "lockup", "logo", f.get("case", "as-is"), float(f.get("tracking", 0.03) or 0.03),
                  p.get("name_color", "#151515"))
    if not svg_to_png(files["horizontal"], dest, width=1024, height=1024, bg="#ffffff", padding=0.1):
        return None
    return Path(dest)


def cmd_generate(a):
    run = Path(a.run)
    prompts = read_json(run / "prompts.json") or build_prompts(run)
    if a.only:
        prompts = [p for p in prompts if p["direction"] in a.only or p["id"] in a.only]
    out = run / "concepts"
    out.mkdir(exist_ok=True)
    c = client()
    todo = [p for p in prompts if not (out / f"{p['id']}.png").exists()]
    log(f"Generating {len(todo)} concepts with {QUALITY} quality, {WORKERS} in parallel "
        f"(about ${len(todo) * IMAGE_COST.get(QUALITY, 0.02):.2f})")

    def make(p):
        if p.get("track") == "symbol":
            sym = out / f"{p['id']}-symbol.png"
            if not sym.exists():
                anchors = anchor_sheet(run, p.get("variant", ""), p["id"], out / f"_{p['id']}-anchors.png")
                if anchors:
                    r = edit_image(c, p["prompt"] + ANCHOR_NOTE.format(n=2), [anchors], sym)
                else:
                    r = generate_image(c, p["prompt"], sym)
                if not r:
                    return None
            return compose(run, p, sym, out / f"{p['id']}.png")
        return generate_image(c, p["prompt"], out / f"{p['id']}.png")

    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {ex.submit(make, p): p for p in todo}
        for f in as_completed(futs):
            p = futs[f]
            r = f.result()
            if r:
                append_cost(run, f"concept {p['id']}", IMAGE_COST.get(QUALITY, 0.02))
            log(f"  {p['id']}  {'ok' if r else 'FAILED'}")
    have = sorted(x.name for x in out.glob("*.png"))
    log(f"{len(have)} concept images in {out}")


JUDGE = """You are the creative director judging logo concepts for the e-commerce brand "{brand}".
Brief: {product}. Audience: {audience}. Adjectives: {adjectives}.
The shelf it sits on already owns these colors: {owned}; shared habits: {habits}.

You see {n} concept images, numbered in order: {ids}.
Each image should show ONLY the brand name "{brand}" (exact spelling) plus a mark.

For EVERY image return an entry:
{{"id": "...", "reads": the exact text you can read in the image, "spelled_right": true/false (compare LETTERS only:
  uppercase, lowercase or mixed case all count as spelled right; a missing, extra or swapped letter does not, and a
  letter drawn mirrored or reversed (like a backwards E), upside down, or replaced by a symbol so that a shopper would
  misread it is NOT spelled right),
  "extra_text": true if anything beyond the brand name is written,
  "idea_clarity": 1-5, "distinct_on_shelf": 1-5, "simplicity": 1-5, "craft": 1-5 (letterforms, spacing, balance),
  "small_size": 1-5 (would it survive 40 px on a phone), "fit": 1-5 (brand adjectives and price tier),
  "flaw": the single biggest flaw in under 12 words, "keep": what is worth keeping in under 12 words,
  "looks_like_existing": the name of a well-known logo it resembles, or ""}}
An image that looks like an existing well-known logo can never be a pick.
Then: "picks": one id per direction letter {dirs}: the best of that direction (a misspelled or extra-text image can never be
a pick). Then "recommend": the single id you would put on the box tomorrow. Ties on total are broken by distinct_on_shelf,
then small_size. "why": one sentence that starts with "On this shelf" and does not repeat the id; "cost": one sentence, the honest price of choosing it
(what the other picks do better). "today": one sentence on the brand mark currently printed on the product photos, if any
was described to you: {today}.
Return JSON: {{"scores": [...], "picks": {{"A": "...", "B": "...", "C": "..."}}, "recommend": "...", "why": "...", "cost": "..."}}"""


def cmd_judge(a):
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    shelf = read_json(run / "shelf.json") or {}
    prompts = read_json(run / "prompts.json")
    seen = set()
    imgs = []
    for p in prompts:
        if p["id"] in seen or not (run / "concepts" / f"{p['id']}.png").exists():
            continue
        seen.add(p["id"])
        imgs.append((p["id"], run / "concepts" / f"{p['id']}.png"))
    per_dir = {k: sum(1 for i, _ in imgs if i.lstrip("P").startswith(k)) for k in {p["direction"] for p in prompts}}
    if any(n < 2 for n in per_dir.values()):
        sys.exit(f"some directions have fewer than 2 concepts ({per_dir}); run generate again before judging")
    if len(imgs) < max(6, len(prompts) // 2):
        sys.exit(f"only {len(imgs)} of {len(prompts)} concepts exist; run generate again before judging (a judge on a thin sheet picks badly)")
    c = client()
    dirs = sorted({p["direction"] for p in prompts})
    prompt = JUDGE.format(brand=brief["brand"], product=brief.get("product", ""), audience=brief.get("audience", ""),
                          adjectives=", ".join(brief.get("adjectives", [])),
                          owned=", ".join(shelf.get("census", {}).get("owned", [])) or "nothing dominant",
                          habits="; ".join(shelf.get("read", {}).get("visual_habits", [])[:4]),
                          n=len(imgs), ids=", ".join(i for i, _ in imgs), dirs="/".join(dirs),
                          today=brief.get("current_mark") or "none described")
    log(f"Judging {len(imgs)} concepts (spelling read-back + 6 scores each)...")
    res, usage = vision_json(c, prompt, [p for _, p in imgs], max_px=640)
    append_cost(run, "judge", vision_cost(usage))
    if not res or "scores" not in res:
        sys.exit("judge returned nothing usable; run judge again")
    def to_int(v):
        try:
            return int(str(v).split("/")[0])
        except (TypeError, ValueError):
            return 0
    for s in res["scores"]:
        for k in ("idea_clarity", "distinct_on_shelf", "simplicity", "craft", "small_size", "fit"):
            s[k] = to_int(s.get(k))
        s["total"] = sum(s[k] for k in ("idea_clarity", "distinct_on_shelf", "simplicity", "craft", "small_size", "fit"))
    # A direction the judge left without a pick gets its best eligible concept (spelled right, no extra text, no look-alike).
    picks = res.setdefault("picks", {})
    for key in sorted({p["direction"] for p in prompts}):
        if picks.get(key) and any(x["id"] == picks[key] for x in res["scores"]):
            continue
        ok = [x for x in res["scores"] if str(x.get("id", "")).lstrip("P").startswith(key) and x.get("spelled_right", True)
              and not x.get("extra_text") and str(x.get("looks_like_existing") or "").strip().lower() in ("", "none", "no", "n/a", "null", "false")]
        if ok:
            picks[key] = max(ok, key=lambda x: x["total"])["id"]
    if not res.get("recommend") or res["recommend"] not in picks.values():
        res["recommend"] = max((x for x in res["scores"] if x["id"] in picks.values()), key=lambda x: x["total"])["id"]
    write_json(run / "judge.json", res)
    bad = [s["id"] for s in res["scores"] if not s.get("spelled_right", True) or s.get("extra_text")]
    log(f"Spelling or extra text failed: {', '.join(bad) or 'none'}")
    for k, v in res.get("picks", {}).items():
        s = next((x for x in res["scores"] if x["id"] == v), {})
        log(f"  pick {k}: {v}  ({s.get('total', '?')}/30)  keep: {s.get('keep', '')}")
    log(f"Recommend: {res.get('recommend')}  because {res.get('why')}")


def cmd_sheet(a):
    run = Path(run_ := a.run)
    brief = read_json(run / "brief.json")
    judge = read_json(run / "judge.json") or {}
    prompts = read_json(run / "prompts.json")
    picks = judge.get("picks", {})
    rec = judge.get("recommend")
    scores = {s["id"]: s for s in judge.get("scores", [])}
    cols = []
    for d in brief["directions"]:
        pid = picks.get(d["key"])
        tiles = []
        seen_ids = set()
        for p in [x for x in prompts if x["direction"] == d["key"] and not (x["id"] in seen_ids or seen_ids.add(x["id"]))]:
            f = run / "concepts" / f"{p['id']}.png"
            if not f.exists():
                continue
            s = scores.get(p["id"], {})
            cls = "pick" if p["id"] == pid else ""
            cls += " ev" if p.get("evolved_from") else ""
            cls += " prev" if p["id"].startswith("P") else ""
            cls += " rec" if p["id"] == rec else ""
            bad = (not s.get("spelled_right", True)) or s.get("extra_text")
            tiles.append(f"""<div class="c {cls}"><img src="{file_data_uri(f)}">
              <div class="m"><b>{p['id']}</b> {esc(p.get('name', ''))} · {esc(p['variant'])} · {s.get('total', '')}{'/30' if s else ''}{' · <b style=color:#c00>spelling</b>' if bad else ''}</div>
              <div class="k">{esc(s.get('keep', ''))}</div></div>""")
        pick_img = (run / "concepts" / f"{pid}.png") if pid else None
        hero = f"""<div class="hero"><img src="{file_data_uri(pick_img)}"></div>
                   <div class="ladder">{''.join(f'<img src="{file_data_uri(pick_img)}" style="width:{w}px;height:{w}px">' for w in (100, 50, 32))}</div>""" if pick_img and pick_img.exists() else ""
        cols.append(f"""<section class="dir"><div class="h"><span class="key">{d['key']}</span><div><h2>{esc(d['name'])} <small>{esc(d['mark_type'])}</small></h2>
          <p class="idea">{esc(d['idea'])}</p><p class="why">{esc(d.get('why_it_wins', ''))}</p>
          <p class="pal">{''.join(f'<i style="background:{c}"></i>' for c in d.get('palette', []))} {' '.join(d.get('palette', []))}</p></div></div>
          {hero}<div class="grid">{''.join(tiles)}</div><p class="risk">Risk: {esc(d.get('risk', ''))}</p></section>""")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{esc(brief['brand'])} logo concepts</title><style>
    body{{font-family:-apple-system,Inter,Arial,sans-serif;margin:0;background:#f4f3f0;color:#111}}
    .wrap{{padding:34px 40px}} h1{{font-size:28px;margin:0}} .sub{{color:#666;margin:6px 0 22px;font-size:14px}}
    .dirs{{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}}
    .dir{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 1px 2px rgba(0,0,0,.06)}}
    .h{{display:flex;gap:12px;align-items:flex-start;min-height:150px}} .key{{font-size:34px;font-weight:800;color:#bbb;line-height:1}}
    h2{{font-size:18px;margin:0}} h2 small{{font-weight:400;color:#888;font-size:12px;margin-left:6px}}
    .idea{{font-size:13px;margin:6px 0 4px;line-height:1.4}} .why{{font-size:12px;color:#555;margin:0 0 6px}} .pal{{font-size:11px;color:#777;margin:0}}
    .pal i{{display:inline-block;width:14px;height:14px;border-radius:50%;vertical-align:middle;margin-right:2px;border:1px solid #ddd}}
    .hero{{background:#fff;border:1px solid #eee;border-radius:10px;margin:12px 0 8px;display:flex;justify-content:center}} .hero img{{width:100%;max-width:420px}}
    .ladder{{display:flex;gap:14px;align-items:flex-end;justify-content:center;margin:4px 0 12px;background:#fafafa;padding:8px;border-radius:8px}}
    .grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}} .c.ev{{background:#f3f7ff}} .c.prev{{background:#f7f3ea}}
    .c{{border:2px solid transparent;border-radius:8px;padding:4px;font-size:10px;color:#666}} .c img{{width:100%;border-radius:4px;display:block}}
    .c.pick{{border-color:#111}} .c.rec{{border-color:#d4a017;background:#fff8e1}} .m{{margin-top:3px}} .k{{color:#999;min-height:24px}}
    .risk{{font-size:12px;color:#a33;margin:12px 0 0}}
    .rc{{margin-top:22px;background:#111;color:#fff;border-radius:12px;padding:16px 20px;font-size:14px}} .rc b{{color:#f3c969}}
    </style></head><body><div class="wrap">
    <h1>{esc(brief['brand'])}: three directions</h1>
    <div class="sub">{esc(brief.get('product', ''))} · for {esc(brief.get('audience', ''))}</div>
    <div class="dirs">{''.join(cols)}</div>
    <div class="rc"><b>Recommendation: {esc(rec or '')}</b> &nbsp; {esc(judge.get('why', ''))}</div>
    </div></body></html>"""
    (run / "concepts.html").write_text(html)
    screenshot_html(run / "concepts.html", run / "concepts.png", 1600, 1700)
    # trim the empty page below the sheet
    from PIL import Image, ImageChops
    im = Image.open(run / "concepts.png").convert("RGB")
    bg = Image.new("RGB", im.size, im.getpixel((5, im.size[1] - 5)))
    bbox = ImageChops.difference(im, bg).getbbox()
    if bbox:
        im.crop((0, 0, im.size[0], min(im.size[1], bbox[3] + 30))).save(run / "concepts.png")
    log(f"wrote {run / 'concepts.png'}")


REFINE = """Reproduce this exact logo as a clean master: same brand name "{brand}" spelled exactly, same mark, same layout,
same proportions, same colors ({palette}). Perfectly crisp vector-sharp edges, mathematically smooth curves, even stroke
weights, exact letterspacing, solid flat fills with no anti-aliasing noise, no gradients, no shadows, no texture.
Every stroke and serif at least 1/80 of the logo's height thick (no hairlines: this master gets printed small).
Pure flat white background, the logo centered with generous margins. Nothing added, nothing removed."""


EVOLVE = [
    ("craft", """Keep this exact logo idea for "{brand}" and raise the craft to the level of a senior identity designer: refine every
letterform so the logotype reads as custom-drawn (consistent stroke logic, optical spacing, resolved joins), tighten the
symbol's geometry (clean curves, exact angles, balanced weights), strengthen the ownable detail ({detail}), and use the
palette with intent ({palette}). Same name, same idea, same composition; flat vector, solid colors, no gradients or
shadows, pure white background, the logo alone, spelled exactly "{brand}"."""),
    ("bolder", """A bolder, more confident interpretation of this exact logo idea for "{brand}": larger, simpler shapes, one strong
silhouette that reads at thumbnail size, fewer details, the idea pushed further ({detail}) without becoming literal.
Keep the palette ({palette}) and the name; flat vector, solid colors, no gradients or shadows, pure white background,
the logo alone, spelled exactly "{brand}"."""),
]


def cmd_evolve(a):
    """Two edits on every pick (craft pass, bolder pass), judged again with the originals: the round where a good
    idea becomes a good logo. New ids: B3e1, B3e2."""
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    judge = read_json(run / "judge.json") or {}
    prompts = read_json(run / "prompts.json") or []
    picks = judge.get("picks", {})
    if not picks:
        sys.exit("no picks; run judge first")
    from common import edit_image
    c = client()
    out = run / "concepts"
    jobs = []
    for key, pid in picks.items():
        if "e" in pid:
            continue   # already an evolution
        pr = next((p for p in prompts if p["id"] == pid), {})
        cpt = pr.get("concept", {})
        pal = ", ".join(cpt.get("palette") or next((d.get("palette", []) for d in brief["directions"] if d["key"] == key), []))
        for n, (kind, tpl) in enumerate(EVOLVE, 1):
            nid = f"{pid}e{n}"
            if (out / f"{nid}.png").exists():
                continue
            jobs.append((nid, pid, key, kind, tpl.format(brand=brief["brand"], detail=cpt.get("ownable_detail", "the idea"), palette=pal or "the shown colors")))
    log(f"Evolving {len(picks)} picks x {len(EVOLVE)} = {len(jobs)} edits (about ${len(jobs) * IMAGE_COST.get(QUALITY, 0.02) * 1.5:.2f})")

    def one(j):
        nid, pid, key, kind, prompt = j
        base = next((p for p in prompts if p["id"] == pid), {})
        if base.get("track") == "symbol" and (out / f"{pid}-symbol.png").exists():
            prompt = prompt.replace("this exact logo idea", "this exact symbol").replace("letterform so the logotype reads as custom-drawn (consistent stroke logic, optical spacing, resolved joins), tighten the\nsymbol's geometry", "tighten the symbol's geometry")
            prompt += " The symbol alone, no letters or words."
            r = edit_image(c, prompt, [out / f"{pid}-symbol.png"], out / f"{nid}-symbol.png")
            if r:
                r = compose(run, {**base, "id": nid}, out / f"{nid}-symbol.png", out / f"{nid}.png")
        else:
            r = edit_image(c, prompt, [out / f"{pid}.png"], out / f"{nid}.png")
        if r:
            append_cost(run, f"evolve {nid}", IMAGE_COST.get(QUALITY, 0.02) * 1.5, kind)
        return nid, kind, bool(r)
    with ThreadPoolExecutor(WORKERS) as ex:
        for nid, kind, ok in ex.map(one, jobs):
            log(f"  {nid} ({kind})  {'ok' if ok else 'FAILED'}")
            if ok:
                base = next((p for p in prompts if p["id"] == nid.split("e")[0]), {})
                prompts.append({**base, "id": nid, "variant": f"{base.get('variant', '')} · {kind} pass", "name": f"{base.get('name', '')} {'refined' if kind == 'craft' else 'bolder'}",
                                "evolved_from": nid.split("e")[0]})
    write_json(run / "prompts.json", prompts)


def cmd_refine(a):
    """Re-render a pick at 2048 px as a clean master for tracing (one edit call, one attempt)."""
    from common import edit_image
    run = Path(a.run)
    brief = read_json(run / "brief.json")
    out = run / "concepts" / f"{a.concept}-2048.png"
    if out.exists() and not a.force:
        log(f"{out.name} exists")
        return
    pal = next((d.get("palette", []) for d in brief["directions"] if a.concept.lstrip("P").startswith(d["key"])), [])
    if not (run / "concepts" / f"{a.concept}.png").exists():
        sys.exit(f"no concept image for {a.concept} (ids are like B2, upper case)")
    pr = next((p for p in (read_json(run / "prompts.json") or []) if p["id"] == a.concept), {})
    if pr.get("track") == "symbol" and (run / "concepts" / f"{a.concept}-symbol.png").exists():
        out = run / "concepts" / f"{a.concept}-symbol-2048.png"
        if out.exists() and not a.force:
            log(f"{out.name} exists")
            return
        c = client()
        r = edit_image(c, "Reproduce this exact symbol as a clean master: same shapes, same proportions, same colors. Perfectly crisp vector-sharp "
                          "edges, mathematically smooth curves, even stroke weights, solid flat fills, no texture, no letters. Pure flat white "
                          "background, centered, generous margin. Nothing added, nothing removed.",
                       [run / "concepts" / f"{a.concept}-symbol.png"], out, size="2048x2048")
        if r:
            append_cost(run, f"refine {a.concept}", IMAGE_COST.get(QUALITY, 0.02) * 4, "2048 px symbol")
            log(f"wrote {out}")
        return
    c = client()
    log(f"Refining {a.concept} to a 2048 px master...")
    r = edit_image(c, REFINE.format(brand=brief["brand"], palette=", ".join(pal) or "as shown"),
                   [run / "concepts" / f"{a.concept}.png"], out, size="2048x2048")
    if r:
        append_cost(run, f"refine {a.concept}", IMAGE_COST.get(QUALITY, 0.02) * 4, "2048 px")
        log(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("round")
    p.add_argument("run")
    p.add_argument("--feedback", help="what the client said about the previous round")
    p.set_defaults(fn=cmd_round)
    for name, fn in (("prompts", cmd_prompts), ("judge", cmd_judge), ("sheet", cmd_sheet), ("evolve", cmd_evolve)):
        p = sub.add_parser(name)
        p.add_argument("run")
        p.set_defaults(fn=fn)
    p = sub.add_parser("refine")
    p.add_argument("run")
    p.add_argument("concept")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_refine)
    p = sub.add_parser("generate")
    p.add_argument("run")
    p.add_argument("--only", nargs="*")
    p.set_defaults(fn=cmd_generate)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
