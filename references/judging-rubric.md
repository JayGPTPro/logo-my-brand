# Judging the concepts

`concepts.py judge` sends all twelve images to gpt-5.4 in one call with the brief and the shelf facts.
The designer reads the result, then looks at the sheet. The judge proposes; the designer decides.

## 1. The spelling gate

Every image is read back: `reads`, `spelled_right`, `extra_text`. A misspelled name or any extra word
(a tagline, "EST. 2024", a category word) disqualifies the image from being a pick, whatever it scores.
This is the one rule the judge cannot bend. The sheet marks these tiles in red.

## 2. The six scores (1 to 5 each, 30 total)

| Score | Question |
|---|---|
| idea_clarity | Can the idea be said in one sentence after one look? |
| distinct_on_shelf | Next to the twelve tiles and the owned colors, is it a different thing? |
| simplicity | Few shapes, one detail that is ownable, nothing decorative. |
| craft | Letterforms, spacing, stroke consistency, optical balance. Where generated marks fail most. |
| small_size | Would it survive 40 px on a phone, in the Sponsored Brands tile? |
| fit | The brief's adjectives and price tier. A playful mark on a premium product scores low here. |

`flaw` and `keep` are one short line each; the sheet shows `keep` under every tile and the board shows
both for the chosen mark.

## 3. Picks and the recommendation

One pick per direction (the best of its four layouts) and one overall recommendation with a `why` that
must mention the shelf. The designer overrules when:

- the pick resembles an existing logo (a tile's, or one you know). Drop it, pick the next.
- the pick's `craft` flaw is visible at a glance (a lumpy curve, uneven letter widths). The refine pass
  fixes rendering noise, not design flaws.
- two picks share a palette or a structure. The checkpoint should offer three different things.
- the recommendation chooses a color the shelf owns. The judge is told the owned colors; if it still
  recommends one, the direction's palette was set before the shelf pass. Rerun `understand` and `prompts`.

## 4. Critique mode (an existing logo)

Score the current logo on the same six, then run it through `mockups tests` and look. Report in this
order: what works (one line), the three places it fails on the shelf or in the tests, and the one change
that would fix the most. Then offer the full run. Never open with the flaws.

## 5. What a 30/30 is not

The scores compare twelve generated options against a brief. They do not say the mark is trademarkable,
original in the legal sense, or better than a human designer's. The board says "scored", never "approved".
