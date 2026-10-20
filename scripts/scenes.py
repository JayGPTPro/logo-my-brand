"""Photoreal mockups: the mark in three real-looking scenes, the same three for every option.

  scenes <run> --logo <png> --out <dir> [--prefix scene]

Product brands get: a kraft mailer box, a thank-you card with a hang tag on tissue paper, a paper shopping bag.
Businesses get: a storefront sign, takeaway packaging, a business card on a counter.
Each scene is one gpt-image-2 edit with the logo as the only input, one attempt. Then ONE vision pass looks at
all of them and marks each ok or not (logo present, spelled right, not redrawn); scenes.json records it, and
only ok scenes are shown anywhere.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import IMAGE_COST, QUALITY, append_cost, client, edit_image, log, read_json, vision_cost, vision_json, write_json  # noqa: E402

KEEP = ("The reference image is the brand's finished logo. Reproduce it EXACTLY as given: same shapes, same letters, same "
        "spelling \"{brand}\", same colors and proportions. Never redraw, restyle or add to it. ")

PRODUCT = [
    ("box", "The retail box this {category} product ships in, standing on a table in the room where it is used, soft natural light. "
            "The logo is printed large on the front panel of the box in the brand colors, crisp and centered; the box is a plain premium "
            "printed carton with no other text and no product picture. Three-quarter view, shallow depth of field, editorial product photography."),
    ("card", "A flat lay on a soft linen surface: a thick matte thank-you card and a small hang tag with a cotton string, on folded white "
             "tissue paper, a sprig of greenery at the edge. The logo is printed on the card and on the tag. Top-down, soft shadows, "
             "warm natural light, premium stationery photography, no other text."),
    ("mailer", "A matte shipping mailer box with the lid open on a pale oak table, branded tissue paper inside, the logo printed in one "
               "color on the inside of the lid. Soft morning daylight, from slightly above, premium unboxing photography, no other text."),
]
BUSINESS = [
    ("sign", "The street front of a small neighborhood shop at dusk: the logo on a flat painted fascia sign above the door, warm "
             "interior light spilling out, a few passers-by blurred. Eye-level photograph, realistic, no other signage text."),
    ("pack", "Takeaway packaging on a wooden counter: a kraft box and a paper cup, the logo printed on both, a little steam, warm light, "
             "close product photograph, no other text."),
    ("card", "Two business cards on a slate counter next to a ceramic cup, one face up showing the logo large, one showing the back "
             "in the brand color. Soft light, shallow depth of field, premium print photography, no other text."),
]

QA = """These {n} images are mockups that should show the logo of the brand "{brand}" placed into a scene.
For each, in order, return {{"i": index from 1, "ok": true/false, "reads": the brand text you can read on the mockup,
"issue": the main problem in under 10 words or ""}}. ok is false when the logo is missing, misspelled, redrawn into
a different design, distorted, or when extra text was invented. Return JSON {{"scenes": [...]}} only."""


def render(run, logo, out, prefix="scene", n=3):
    run = Path(run)
    brief = read_json(run / "brief.json") or {}
    brand = brief.get("brand", "Brand")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / f"{prefix}s.json"
    if manifest_path.exists():
        return read_json(manifest_path)
    scenes = (BUSINESS if brief.get("kind") == "business" else PRODUCT)[:n]
    c = client()

    def one(sc):
        key, text = sc
        dest = out / f"{prefix}-{key}.png"
        r = edit_image(c, KEEP.format(brand=brand) + text.format(category=(brief.get("category", "") or "").split(":")[-1].strip() or "consumer"),
                       [logo], dest, size="1536x1024")
        if r:
            append_cost(run, f"{prefix} {key}", IMAGE_COST.get(QUALITY, 0.02) * 1.5)
        return key, bool(r)
    with ThreadPoolExecutor(3) as ex:
        made = [k for k, ok in ex.map(one, scenes) if ok]
    files = [out / f"{prefix}-{k}.png" for k in made]
    verdict = {}
    if files:
        res, usage = vision_json(c, QA.format(n=len(files), brand=brand), files, max_px=768)
        append_cost(run, f"{prefix} qa", vision_cost(usage))
        verdict = {x.get("i"): x for x in (res or {}).get("scenes", [])}
    manifest = []
    for i, k in enumerate(made, 1):
        v = verdict.get(i, {})
        manifest.append({"key": k, "file": str((out / f"{prefix}-{k}.png").relative_to(run)), "ok": bool(v.get("ok")),
                         "reads": v.get("reads", ""), "issue": v.get("issue", "")})
        log(f"  {prefix}-{k}: {'ok' if v.get('ok') else 'REJECTED ' + v.get('issue', '')}")
    write_json(manifest_path, manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--logo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="scene")
    a = ap.parse_args()
    render(Path(a.run).resolve(), a.logo, Path(a.out).resolve(), a.prefix)


if __name__ == "__main__":
    main()
