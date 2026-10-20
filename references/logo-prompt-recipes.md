# The gpt-image-2 logo recipe

`concepts.py` builds every prompt from one template (RECIPE in the script). This file says why each
line is there, so a change to one is a change to both.

## 1. The template, line by line

```
Professional brand logo for the e-commerce brand "{brand}". The brand sells: {product}.
```
The product line makes the mark relevant without asking for the product to be drawn.

```
Mark type: {mark_type}. Idea: {idea}
```
The direction's one-sentence idea, verbatim. The model follows a sentence far better than a list of
adjectives.

```
Layout: {layout}
```
One of four, so the twelve tiles differ in structure and not only in rendering noise:
- symbol-led: symbol large above a quiet wordmark (for wordmark directions this becomes "one letter
  carries the idea, no separate symbol").
- wordmark-led: the name large and wide, the symbol small beside the first letter.
- emblem: symbol and name in one compact badge with a single clean outer silhouette.
- mono-minimal: one color, two shapes at most, the idea stripped to its essence.

```
Typography: {type_feel}. The brand name is set as a custom logotype, letterforms drawn for this brand,
consistent stroke weight, generous letterspacing, no default-looking font.
```
Without this line the model sets the name in something that looks like a system font.

```
Colors: exactly these solid colors and nothing else: {palette}. One color only. | Use the first color
for the main shapes; the others only as small accents.
```
Hex codes work. "Exactly" and "nothing else" stop the model adding a gradient or a third tone.

```
Style: flat vector, solid filled shapes, clean geometry, exact angles, optical balance; the kind of mark
that still reads when printed 20 mm wide in one color on {surface}.
```
Naming the first surface from the brief changes the output: a mark "for a laser-engraved bamboo corner"
comes back bolder than a mark "for an app".

```
Must avoid: {cliches}. Also avoid: gradients, shadows, 3D, bevels, glow, textures, mockups,
backgrounds, scenes, borders, taglines, any text other than the brand name.
```
The brief's cliches plus the shelf's "avoid" list, by name.

```
Composition: the logo alone, centered, with generous empty margin on every side, on a pure flat white
background. The brand name must be spelled exactly "{brand}" and nothing else may be written.
```
Pure white is load-bearing: `vectorize.py` makes pure white transparent. A cream or grey background
would survive the cut and become part of the mark. Spelling is demanded here and read back by the judge.

## 2. What breaks it

- **Transparent background requests.** gpt-image-2 refuses `background=transparent` (tested 18.10.2026).
  White, then cut.
- **Long brand names in emblems.** Over about 12 characters the emblem layout squeezes the name; the
  judge's `small_size` score catches it. Prefer wordmark-led and mono-minimal for long names.
- **Names that are words.** "Nostalgia", "Harvest": the model wants to illustrate the word. The idea line
  must say what the symbol is, so the word does not get drawn.
- **Two-word names.** Say which word is dominant in `type_feel` or the model stacks them equally.
- **Numbers and ampersands.** Spell out "and"; the model misreads "&" as decoration.

## 3. The refine prompt (2048 master)

```
Reproduce this exact logo as a clean master: same brand name "{brand}" spelled exactly, same mark, same
layout, same proportions, same colors ({palette}). Perfectly crisp vector-sharp edges, mathematically
smooth curves, even stroke weights, exact letterspacing, solid flat fills with no anti-aliasing noise,
no gradients, no shadows, no texture. Pure flat white background, the logo centered with generous
margins. Nothing added, nothing removed.
```
One `images.edit` on the 1024 concept, output 2048 x 2048. This is what gets traced. Compare it to the
concept before tracing: if the model "improved" the mark (a different N, a new accent), run refine again
with `--force` once, then trace the 1024 concept instead.

## 4. Quality

`LMB_QUALITY` defaults to `low`. For flat logos on white the difference to `medium` is not visible after
tracing; the 2048 refine is where sharpness comes from. Raise quality only when the user asks.
