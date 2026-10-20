# The brief, read off the product

A software brand gets a brief from a conversation. A product brand already has one: it is sitting in
the gallery photos and the bullets. `intake.py understand` reads it from there so the seller answers
nothing, and the designer argues from facts instead of taste.

## 1. What the vision pass extracts, and why

| Field | Why it matters for the logo |
|---|---|
| `product` | One sentence. Every later prompt says it, so the mark is relevant without drawing the product. |
| `category`, `price_tier` | A $12 ice tray and a $140 cast-iron pot want different voices. Tier comes from the price AND the materials in the photos. |
| `materials`, `product_colors` | The logo will sit on these. A mark that clashes with the product's own color is a mark that gets printed small and grey. |
| `logo_surfaces` | The three to five places the mark will physically live, with method (printed, embossed, laser, woven label, sticker, hang tag) and size in mm. This drives the tests and the on-product renders. |
| `adjectives` | Five words; the concepts and the judge both score against them. "Quality" and "premium" are banned as too generic. |
| `cliches` | The category's visual defaults. Every prompt forbids them by name. |
| `shelf_keyword` | The search a buyer types. The shelf step fetches exactly that. |
| `name_notes` | Initials, a letter with graphic potential, a pronunciation trap. Lettermarks come from here. |
| `directions` | Three, as different as possible, each with mark type, one-sentence idea, why it wins on this shelf, palette, type feel, and its honest risk. |

## 2. The surfaces table (defaults when the photos do not say)

| Product kind | Surfaces, in order | Method | Typical mm | Colors |
|---|---|---|---|---|
| Kitchen electrics (steel body) | front of base, box front, manual cover | printed / pad print | 40 to 60 | 1 |
| Cast iron, ceramics, glass | lid or base relief, box, hang tag | embossed / debossed | 15 to 30 | tone on tone |
| Wood boards, bamboo | corner of the board, box sleeve, care card | laser engraved | 20 to 35 | 1 |
| Textiles, pouches, bags | woven label, hang tag, care label | woven / printed | 25 to 40 | 1 to 2 |
| Bottles, jars, cosmetics | front label, cap top, carton | printed label / foil | 30 to 50 | full |
| Supplements, food | front panel, lid seal, shipper | printed | 50 to 90 | full |
| Pet, baby, toys | product face or tag, box front | printed / stitched | 20 to 60 | 1 to full |
| Tools, hardware | handle or body, blister card | pad print / laser | 15 to 40 | 1 |

The first surface is the one the one-color test and the first on-product render use. A direction that
cannot survive its first surface in one color is dropped before it is rendered.

## 3. Rules the directions obey

- At least one wordmark or lettermark: a seller needs a name that reads at 40 px in an ad tile.
- At most one direction depicts the product or its use, and it must do it through a twist (a negative
  space, a letter that becomes the thing), never as clip art.
- No direction leans on a cliche from the brief's own list.
- Palettes differ from each other, and after the shelf pass no main color is a hue the shelf owns.
- Every idea is one sentence a designer could build from. A sentence that could describe a competitor's
  logo is not an idea; the understand prompt says so.

## 4. When the brief is wrong

The brief is a hypothesis built from photos. Two signs it missed:

- The surfaces do not match the product you see (a "woven label" on a steel pot). Edit `brief.json`
  by hand and rerun from `prompts`.
- The brand name in the listing is not the brand (a reseller name, "Generic", "Visit the Store").
  Rerun intake with `--brand`.

## 5. Price tier cues the model uses

- Budget: multipacks, "4 Pack", plastic, prices under about $15, infographic-heavy galleries.
- Mid: single hero product, some lifestyle shots, $15 to $60, mixed materials.
- Premium: natural materials, gift box in the gallery, lifestyle photography, $60 and up, few bullets.
