# Hebrew and bilingual brand names

Israeli sellers on Amazon sell in English, but many brands carry a Hebrew name at home, on the Shopify
store or on packaging for the local market. Three cases.

## 1. The Amazon brand is English, the home brand is Hebrew

Run the skill on the English name (that is what Brand Registry and the Store use). Then, for the
Hebrew version, do not generate: gpt-image-2 draws Hebrew letterforms with wrong shapes and joins often
enough that the spelling gate fails most tiles. Instead, set the Hebrew wordmark in a licensed Hebrew
typeface that matches the English type feel, as a second lockup beside the symbol. Suggested pairings
(license each before use):

| English type feel | Hebrew counterpart |
|---|---|
| geometric sans | Heebo, Assistant, Rubik |
| humanist sans | Open Sans Hebrew, Noto Sans Hebrew |
| modern serif | Frank Ruhl Libre, David Libre |
| wide display | Secular One, Karantina (display only) |

Build the lockup as SVG with the text converted to outlines (Inkscape: Path > Object to Path), then
run it through `vectorize.py` (it accepts a PNG) or straight into `mockups tests` as an SVG.

## 2. The brand name is a Hebrew word written in Latin letters

"Shemesh", "Tzuf", "Kesem". Treat it as an English brand for generation, but write the meaning into
`brief.json` `name_notes` so the directions can use it (a sun, nectar, magic) without the model drawing
the Hebrew. Pronunciation traps go there too: a US buyer reads "Tzuf" as "zoof"; the wordmark can help
with letterspacing or a diacritic-like detail, and the board should say so.

## 3. The brand is Hebrew only (local Shopify, no Amazon)

Skip `generate`. Use the brief and the shelf (the shelf keyword can be in Hebrew for amazon.com? No:
Amazon has no Hebrew marketplace; use a folder of local competitor images with `--competitors`). Write
three directions, set the wordmark in type as in §1, draw the symbol by hand from
`logo-design/references/svg-construction.md`, and run the rest of the pipeline from `vectorize` on.

## 4. Right-to-left in the mockups

The composites are left-to-right. For a Hebrew storefront mockup add `dir="rtl"` to the Shopify page
in `mockups.py comp_pages` for that run; nothing else changes.

## 5. What never changes

The spelling gate applies to Hebrew too: read every letter back at native resolution, and check final
forms (ך ם ן ף ץ) at word ends. A single wrong final form on a box is a reprint.
