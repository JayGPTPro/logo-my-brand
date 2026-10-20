---
name: logo-my-brand
description: >-
  A brand logo for an e-commerce product, built from the product itself. One Amazon link or ASIN in
  (or a folder of product photos, or just a brand name): the skill reads the product and its photos,
  measures the competitor shelf on Amazon, writes three strategic directions, renders twelve concepts
  with gpt-image-2, judges them, traces the pick into clean vector masters, proves it at every size a
  seller meets (56 px ad tile, 20 mm label, one color on kraft, embossed), places it ON the real product
  photos, mocks up the Brand Store, the listing, a Sponsored Brands ad, Shopify, the shipping box and the
  socials, and ships a kit with Amazon, Shopify, social and print files plus a usage guide, all on one
  brand.html. Stops once, at the concept checkpoint (brand.html in the choose state: three ranked options shown on the product, the box and page one, with the brief, the shelf and the trends) and builds the final files only after a pick, unless told to run on autopilot. Use whenever a seller or
  any business wants a logo, brand mark, wordmark, rebrand, "a logo for my Amazon brand", "branding for my
  product", "my logo looks cheap", a logo for Brand Registry or a Brand Store, or pastes an ASIN with the
  word logo or brand. Also for ANY business or brand that is not on Amazon: a pizza place, a clinic, a
  Shopify or DTC brand, a local service (then the competitors come from the web, with their real logos), for
  a logo critique of an existing brand, and for turning an existing logo PNG into the kit.
---

# logo-my-brand

A seller's logo is judged in three places: a 56 px tile in a Sponsored Brands ad on a phone, a one-color
print on a box, and next to eleven competitors on page one. This skill designs for those three places
first and builds everything else from there. It stands on top of kaankiziltug's `logo-design` skill (the
craft: SVG audit, size ladder, variants, renderer) and adds what a product brand needs: the product, the
shelf, the surfaces, the uploads.

One line in: `/logo-my-brand B0C2YXMXCR`. Out: ONE page, `logo/<ASIN>/brand.html` (with `assets/`), in the choose
state at the checkpoint; after the pick the same file is rewritten in the delivered state, next to `kit/`,
`logo-kit.zip` and `brand-guidelines.pdf`. There is never a second html per brand. A business: `/logo-my-brand "Tony's Slice"`
plus a line about what it is and where (see Other modes).

Engine: `gpt-image-2` for every image and `gpt-5.4` for every look, on OpenAI direct. When OpenAI answers
`insufficient_quota` the run moves by itself to the same gpt-image-2 hosted on kie.ai (`KIE_API_KEY`) and to
Gemini 3.1 Pro for vision and web search (`GEMINI_API_KEY`), and says so in one log line. Force a route with
`LMB_IMAGE_PROVIDER=kie` and `LMB_VISION_PROVIDER=gemini`. No other image model, ever. A full run costs about $0.30 to $0.60 at the
default `low` quality (12 concepts, 1 refine, 3 on-product edits, 4 vision calls). Do not raise
`LMB_QUALITY` unless the user asks.

## Files

```
SKILL.md                      this file
install.sh                    installs the logo-design base skill beside this one, checks tools
scripts/check-env.sh          OK / MISSING with the fix line for each
scripts/lmb.py                the whole run: run | continue | status
scripts/intake.py             intake (ASIN, URL, folder, saved page, brand name) · understand (brief.json)
scripts/shelf.py              competitor shelf: tiles, color census, habits, whitespace (shelf.json, shelf.html)
scripts/trends.py             where the category's design is going, measured on recent identities found on the web (trends.json)
scripts/concepts.py           prompts (creative-director pass) · generate (12) · judge · evolve · round · sheet · refine (2048 master)
scripts/lockup.py             the name set in a real Google Font as vector paths; horizontal, stacked and wordmark lockups in code
scripts/scenes.py             three photoreal scenes per option (box, card and tag, bag; or sign, takeaway, card for a business), QA'd
scripts/options.py            the three picks made imaginable before the choice: vector, composites, scenes, one on-product render each
scripts/page.py               brand.html: the one page per brand, choose or delivered state, assets/ folder, zip and PDF
scripts/vectorize.py          background cut, palette snap, potrace per color, symbol/wordmark split, audit, variants
scripts/mockups.py            tests (tests.png) · composites (store, listing, ad, Shopify, box, socials) · on-product
scripts/checks.py             name risk: domains, who else uses the name (real web search), trademark records, a logo already online
scripts/system.py             the brand system after the pick: palette with tints, type pairing, 4 listing templates, Brand Story, voice
scripts/pack.py               kit (amazon/ shopify/ social/ print/ png/ brand-system/ README.md) (page.py writes the html)
references/ecom-brief.md      how the brief is read off a product, the surfaces table, price tiers
references/shelf-analysis.md  what the census measures, how to read owned vs free hues, when to override
references/logo-prompt-recipes.md   the gpt-image-2 recipe, the four layouts, what breaks it
references/judging-rubric.md  the six scores, the spelling gate, when to overrule the judge
references/platform-specs.md  Amazon, Shopify, social and print sizes with where each file is uploaded
references/on-product.md      placing a logo on a real product photo: surfaces, methods, what to check
references/hebrew-brands.md   brands with Hebrew or bilingual names
evals/evals.json              trigger and behavior checks
```

`S=~/.claude/skills/logo-my-brand/scripts`. Run from the user's working directory; a run lands in
`<cwd>/logo/<slug>/` (the ASIN, or the brand name).

## Step 0: environment (first run on a machine, or after an error)

```
bash $S/check-env.sh
```

Needs python3, `openai`, Pillow, curl, potrace (`brew install potrace`; vtracer is the fallback), a
Chromium browser for the HTML renders, `OPENAI_API_KEY`, and the `logo-design` base skill (install.sh
puts it in `~/.claude/skills/logo-design`). If anything prints MISSING, show the fix lines and stop.

## Step 1: the run, to the checkpoint

```
python3 $S/lmb.py run <ASIN | Amazon URL | folder | "Brand name"> [--brand NAME] [--about "..."]
```

What happens, and what to tell the user while it runs (one line per step, in their language):

1. **intake**: the listing page and up to 7 gallery photos (one attempt; a captcha stops the run with the
   three ways around it: a saved HTML page, a folder of photos, or a brand name plus `--about`).
   The brand name comes from the listing. No brand name is a stop: the name is the seller's decision.
   When the user gives a brand name and no product, `--about` carries what the product is.
2. **understand**: gpt-5.4 reads the photos and the copy and writes `brief.json`: what the product is,
   who buys it, the price tier, the materials, the **surfaces the logo physically lives on** (base,
   lid, box front, woven label, hang tag, with method and size in mm), the category's cliches, the shelf
   keyword, and three directions.
3. **shelf**: page one of Amazon for the shelf keyword. Twelve tiles, a **color census** (which hues the
   shelf owns, which are free), the brands and logo habits read off the tiles, the whitespace, and what
   would make the brand disappear. Every named competitor's **real logo** is then fetched from the web
   (an image search for "<brand> logo", up to six candidates, the vision model picks the one that is
   the brand's mark); brands with no web presence get their mark cut from their own product photo, and a
   name alone when nothing is printed. `shelf.html` shows the shelf as a buyer sees it. When Amazon
   blocks the search fetch, open the search in the browser pane, read the tiles with the JS snippet in
   `references/shelf-analysis.md` §4, save them as `competitors.json` and rerun `shelf.py --competitors`;
   logo URLs you find yourself (Bing or Google Images in the browser pane) go in `--logo-urls logos.json`.
3b. **trends**: three image searches for recent brand identities in the category (new DTC brands, showcases,
   recent packaging), the vision model keeps the real ones and reads them as a trend analyst: where new
   brands are moving, what they dropped, what is already overused in the new wave, and the gap between the
   shelf and the new wave. `trends.json`; the brief and the creative-director pass both receive it.
4. **understand, second pass**: the directions are rewritten against the measured shelf and the trend facts. No direction's
   main color may be a hue the shelf owns; one direction takes a whitespace opportunity literally.
5. **prompts**: a creative-director pass (gpt-5.4) writes twelve concept briefs, four per direction, each
   with its own visual device (negative space, ligature, counter-form, one modified letter, grid
   construction, monoline, pictorial twist, pattern, cut badge, silhouette abstraction, type play,
   sign-painted letterform), a style world (Swiss modernism, 1930s sign painting, Bauhaus, Japanese
   minimalism...), composition, palette and the ownable detail; fifteen in all, five per direction. Most are on
   the **symbol track**: the image model draws ONLY the symbol (no letters), anchored on two exemplary marks
   from the logo-design library that use the same technique (craft benchmark, never copied), and the name is set
   in code in the Google Font the concept names (`lockup.py`): exact spelling, real kerning, a font the seller
   can name. A few are on the **lettering track** (custom-drawn words), drawn whole. Then **generate**.
6. **judge**: gpt-5.4 reads every image back (spelling gate: a misspelled or extra-text image can never
   be a pick), scores six things, picks one per direction, recommends one, says why in terms of the shelf
   and what the choice costs. Then **evolve**: two edits on each pick (a craft pass that refines letterforms
   and geometry, a bolder pass that simplifies and pushes the idea), judged again together with the
   originals; the evolved tiles sit under their parents on the sheet with ids like B3e2.
7. **sheet**: `concepts.png`: three columns, the pick large with a 100/50/32 px ladder, the four tiles
   scored, the risk line, the recommendation.
8. **options**: each pick gets a quick vector (free), the e-commerce composites (page one of Amazon with
   our tile in it, box and card and tag, label and box, listing, Store header, Shopify), one slide of the
   base skill's deck on the surfaces of this kind of brand, and one gpt-image-2 render on the product
   photo. `brand.html` is then written in the choose state: first screen = the three picks with idea, why-here, risk and
   palette, the recommendation with its reason and its cost, and how to choose; then the score table, the
   brief, the shelf (competitor marks first), the twelve-tile sheet, and one "in the world" strip per option.

   The options folder also holds `test-pack/`: the three options as neutral tiles and a five-question
   consumer survey (PickFu, Prolific, or the seller's own customers); `lmb.py votes <run> votes.json`
   re-ranks the review on real answers.

**Another round instead of a pick:** when the user answers the four questions on the review (what they
like in each, what bothers them, which color world, safer or bolder) or just wants more range, run
`lmb.py round <run> --feedback "<their words>"`: twelve new concepts steered by the feedback, the previous
three picks kept on the sheet as P-tiles for comparison, judged, evolved, and the review rebuilt. The
previous round is archived under `rounds/`.

**Look at brand.html (and concepts.png) yourself before showing it.** Open it with the image tool. Check: every brand
name spelled right, no stray text, the picks really are the strongest tile in each column, nothing that
looks like an existing logo. If a column is weak (all four tiles generic, or the judge's pick has a flaw
you can see), regenerate that direction: `concepts.py generate <run> --only A` after deleting its PNGs,
then `judge` and `sheet` again. One regeneration round, not three.

### The checkpoint message

Open `brand.html` for the user, then in the user's language,
ALWAYS three options with their rank (#1 is the recommendation, then by total score):

```
### #1 · A · <name> · <mark type> · <total>/30
**Idea:** <one sentence>  **Why here:** <the shelf fact it answers>  **Risk:** <the honest one>
### B … ### C …
**Recommendation:** <id>. <the judge's why, in your words, mentioning the shelf>.
Pick a direction (or say what you like in each) and I build the kit: vector masters, one-color and
reversed versions, the logo on your product photos, Brand Store header, listing, Sponsored Brands ad,
Shopify header, box, socials, favicon, and the files sized for every upload.
```

Then wait. Skip the wait only when the user said "autopilot", "don't ask", "just deliver" or ran with
`--autopilot`: then the recommendation is the pick and the run continues to the board.

## Step 2: the kit

```
python3 $S/lmb.py continue <run> --pick B2
```

1. **refine**: one `images.edit` call re-renders the pick at 2048 px as a clean master (crisp edges, same
   mark, same spelling). This is what gets traced, not the 1024 concept.
2. **vectorize**: paper becomes transparent (the background reachable from the edges, and the pure-white
   counters; cream and ivory stay), crop to the mark, palette locked to the direction's hex codes (a
   declared accent survives even when small), one potrace layer per color traced at three smoothing levels
   and **measured against the ink** (IoU; the first level at 0.93 or better wins), merged into one SVG with
   a `<title>`. The lockup is split into `-symbol.svg` and `-wordmark.svg` when there is a visible gap;
   a plain wordmark gets its first letter cut out as the monogram for favicon, avatar and stamps. One-color
   versions keep the knockout (a dark plate with light letters stays readable). Then the base skill's
   `svg_audit` (score in `audit.txt`) and the square, favicon and app-icon variants. The fidelity number
   is on the board; a master under 0.9 is reported, not shipped quietly. **A traced master carries more
   anchors than a drawn one.** When the symbol is simple geometry (a ring, a monogram of straight strokes, a badge), rebuild it
   by hand from `logo-design/references/svg-construction.md` with the traced file as the guide, run the
   audit again, and keep the better score. Tell the user which one shipped.
2b. **checks**: is the name free enough to print? DNS on six domains, a real web search for who else
   uses the name, trademark records (USPTO, EUIPO, WIPO), the Amazon search for the name, and whether a
   logo already exists online under it. A paralegal-style verdict (low / medium / high) with the one thing
   to do before printing. On the board; never called legal clearance.
2c. **system**: the brand system in `kit/brand-system/`: palette with tints and shades, two Google Fonts
   (headline and body) with the reason, voice rules, and five templates that already carry the mark and
   the real product photo: A+ header, benefits infographic, lifestyle frame with the badge, why-us
   comparison, Brand Story module. These are the seller's next five listing images.
3. **tests**: `mockups/tests.png`: size ladder 16 to 160 px, 20 mm label at 300 dpi, one color black,
   white on the brand color, one color on kraft, embossed, debossed, squint, a Sponsored Brands ad on a
   phone with the logo tile at 56 px next to the real competitors, mirror and 180°, the symbol alone at
   16/32/64. **Look at it.** The 16 px tile and the kraft print are where traced marks fail.
4. **composites**: deterministic HTML mockups rendered with Chrome: Brand Store header (3000 x 600),
   the listing page with "Visit the Store" and the brand story card, a Sponsored Brands banner with two
   real competitors beside the product, a Shopify home, a kraft shipping box with thank-you card, hang tag
   and stickers, and profile avatars.
5. **on-product**: gpt-image-2 places the logo on the real product photos, on the surfaces the brief
   named (printed on the base, laser on the lid, on the box front), one attempt each. Existing brand
   marks on the product are replaced. **Look at every one before it goes on the board**; a bad one is
   deleted from `mockups/on-product.json` (set `ok` to false), never shown. Read `references/on-product.md`.
6. **kit**: `kit/amazon` (Brand Store logo 400, Sponsored Brands logo 400, hero 3000 x 600, lockup on
   white), `kit/shopify` (logo.svg, header 800 x 200 color and white, favicon 48 and .ico), `kit/social`
   (avatars on brand and on white, cover), `kit/print` (black and white SVG, 300 dpi black PNG),
   `kit/png` (2048 masters), `kit/svg` (all masters), `kit/README.md` (hex codes, where each file is
   uploaded, clear space, minimum sizes, misuse, trademark and Brand Registry notes).
7. **page**: `brand.html` rewritten in the delivered state: the chosen mark on its color, the lockups and type,
   the name check, the color system with HEX/RGB/CMYK, type and voice, stress tests, the photoreal scenes and
   the mark on the product, page one, the listing, the store, the five listing templates, the kit as download
   tiles with one zip and the PDF, next steps, and an appendix with the options not picked, the brief, the
   shelf, the trend read and every concept.

### The delivery message

Open `brand.html` for the user (or give the path). Then, in their language, five lines at most: the
chosen mark in one sentence, the one shelf fact it answers, where the kit is and the three files they
will upload first (Brand Store logo, Sponsored Brands logo, Shopify header), the one thing to do before
printing (trademark search), and the spend. No process talk.

## Other modes

- **A business, or a product that is not on Amazon** (pizza place, clinic, DTC brand, local service):
  `lmb.py run "Brand name" --kind business --about "what it is, for whom" --city X [--website ...]`.
  There is no Amazon shelf, so YOU research the competitors before the run or right after intake: 8 to 12
  of them from the web, Maps, delivery apps or their own sites, and write `competitors.json`:
  `[{"brand": "...", "domain": "their-site.com", "title": "one line", "image": "optional photo url"}]`.
  The shelf step fetches each competitor's real logo from its site (the header logo, else og:image, else
  a favicon of at least 64 px) and reads the shelf from those. Then `lmb.py run ... --competitors
  competitors.json` (the run resumes; nothing is refetched). No product photos means no on-product
  renders and no listing mockups; the surfaces come from the brief (sign, box, menu, card, apron) and the
  deck shows signage, cards, bags and cups. A folder of the business's own photos (`run ./photos --brand
  "Name" --kind business`) turns the on-product renders back on.
- **Critique an existing e-commerce logo**: `intake` the product (its photos carry the current logo),
  `understand`, `shelf`, then put the current logo PNG through `vectorize <run> <png>` and `mockups tests`.
  Report against the tests and the shelf (`references/judging-rubric.md` §4), then offer the full run.
- **Kit from an existing logo**: `vectorize <run> <logo.png>` then `continue --pick` is not needed;
  run `mockups tests`, `mockups composites`, `mockups on-product`, `pack kit`, `pack board`.
- **Brand with no listing yet**: `lmb.py run "Brand name" --about "what the product is"`, plus a folder
  of product photos when they exist (`lmb.py run ./photos --brand "Name"`). The shelf still comes from
  the brief's keyword.
- **Hebrew or bilingual brand names**: read `references/hebrew-brands.md` before `prompts`.

## Rules that do not bend

- One attempt per generation, per fetch, per edit. A failure is reported, not retried in a loop.
- The brand name is never invented or "improved". Spelling is read back on every image.
- Nothing on the board is shown unseen: concepts.png, tests.png and every on-product render are opened
  and looked at before the user sees them.
- The library inside logo-design and the competitor tiles are for learning and comparison. Never trace
  or imitate a competitor's mark; if a concept resembles one, it is dropped, whatever its score.
- No trademark claims. The kit README and the board say so; the delivery message says so once.
- No version numbers, engine names or prompt text in anything the user's customer could see.
