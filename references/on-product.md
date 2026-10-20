# The logo on the real product

`mockups.py on-product` sends two images to gpt-image-2 `images.edit`: the product photo as the canvas
and the logo as the second image, with a prompt built from one row of the brief's `logo_surfaces`. One
attempt per surface, three surfaces by default. These are the renders a seller shows a partner, puts in
a deck, or uses to brief the packaging printer. They are also the ones most likely to be wrong.

## 1. How the prompt is built

- Surface and method come from the brief row: "on the front of the brushed steel base, printed, about
  55 mm wide".
- The logo file depends on the method: embossed, debossed, engraved and laser get the black version and
  a "tone-on-tone relief in the product's own material" rule; a one-color surface gets the black version
  and "print it in one color"; a full-color surface gets the color master.
- Existing brand marks on the product are replaced (the prompt says so). Without that line the model
  keeps the old print and ignores the new logo; measured on the first run (a steel base that kept its
  old name).
- If the named surface is not in the photo (a "box front" when the gallery has no box), the prompt lets
  the model place the mark where a brand mark naturally sits on the visible product. The manifest still
  carries the brief's surface name; rename the caption on the board when that happened.
- The output size follows the photo's aspect (`api_size_for`), so nothing is cropped.

## 2. What to check on every render, before the board

1. **Spelling.** Zoom in. The edit model respells names more often than the generate model.
2. **Only the logo changed.** Compare to the original: product shape, color, props, background. An
   edit that "cleaned up" the strawberries is a failed edit.
3. **Scale.** 55 mm on a 180 mm base is a third of the width. Too small reads as a sticker, too large
   reads as a mockup.
4. **Material.** Printed looks printed (flat, follows the curve); engraved shows depth; embossed catches
   light on the top edges. A flat decal on a cast-iron lid is wrong even when the logo is right.
5. **The old mark is gone.** Half-removed previous branding is the most common failure after spelling.

A render that fails any of these is set to `"ok": false` in `mockups/on-product.json` and the board
skips it. One rerun of that surface is allowed (`on-product` again after deleting the PNG); a second
failure means the surface is shown as a flat composite instead.

## 3. Choosing the photo

Surface 1 uses the main image (the product on white, where the brand mark is easiest to judge). Later
surfaces use later gallery photos in order, except packaging surfaces, which go back to the main image
because the gallery rarely shows the box. A user with their own packaging photo can put it in
`originals/` and name the surface in `brief.json`.

## 4. What these renders are not

They are not product photography and not proof of manufacturability. The board labels them as renders;
the Brand Registry note says the real photos must be of the real product. Do not let a client print from
them: the printer gets `print/<name>-black.svg`.
