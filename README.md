# logo-my-brand

A brand logo for an e-commerce product, built from the product itself.

One Amazon link in. Out: three strategic directions, twelve concepts scored, the pick traced into
clean vector masters, proof at every size a seller meets, the logo placed on the real product photos,
mockups of the Brand Store, the listing, a Sponsored Brands ad, Shopify, the shipping box and the
socials, and a kit with files sized for every upload. All of it on one page per brand, `brand.html`.

```
/logo-my-brand B0C2YXMXCR
```

A full run costs about $0.45 to $0.70 in OpenAI usage and takes about six minutes. Any business works too:
`/logo-my-brand "Tony's Slice"` with a line about the place; the competitors then come from the web with
their real logos.

## Why not a normal logo skill

A seller's logo is judged in three places a software logo never meets: a 56 px tile in a Sponsored
Brands ad on a phone, a one-color print on a kraft box, and page one of Amazon next to eleven
competitors. This skill designs for those first.

- **The brief comes from the product.** The skill reads the gallery photos and the bullets: what the
  thing is, who buys it, the price tier, the materials, and the surfaces where a mark will physically
  live (printed on the base, laser on the lid, on the box front), with sizes in millimetres.
- **The shelf is measured, not described.** Page one of Amazon for the product's keyword: a color
  census of what the shelf already owns, the brands and logo habits read off the tiles, the whitespace
  nobody uses. No direction may take an owned color.
- **Twelve concepts, one spelling gate, one judge.** gpt-image-2 renders four layouts per direction;
  gpt-5.4 reads every brand name back and scores six things against the brief and the shelf.
- **The logo on the product.** The pick is placed on the real product photos, on the surfaces the brief
  named, with the right finish (laser, emboss, print).
- **Files a seller uploads tomorrow.** Brand Store logo 400 x 400, Sponsored Brands logo, Store hero
  3000 x 600, Shopify header and favicon, social avatars, print-ready black SVG, and a README that says
  where each one goes.

## Install

```
git clone https://github.com/JayGPTPro/logo-my-brand.git ~/Downloads/logo-my-brand
bash ~/Downloads/logo-my-brand/install.sh
```

`install.sh` installs the [logo-design](https://github.com/kaankiziltug/logo-design-skill) base skill
(the craft layer this skill stands on: SVG audit, size ladder, variants, renderer), links this skill into
`~/.claude/skills/`, and runs the environment check. Needs Python 3.9+, `openai`, Pillow, curl, potrace
(`brew install potrace`), a Chromium browser, and `OPENAI_API_KEY`.

## What a run produces

```
logo/<ASIN>/
  brand.html            the one page: three ranked options before the pick, the full brand after it (+ assets/)
  logo-kit.zip          every file in one download
  brand-guidelines.pdf  the delivered page as a PDF
  concepts.png          the concept sheet alone, as one image
  shelf.html            page one of Amazon as a buyer sees it, with the color census
  mockups/              tests.png, on-product-*.png, amazon-store-header, amazon-listing, sponsored-brands, shopify, packaging, social
  kit/
    svg/                masters: color, black, white, one-color, symbol, wordmark, favicon, app icon
    amazon/             brand-store-logo-400, sponsored-brands-logo-400, brand-store-hero-3000x600, lockup-on-white-1200
    shopify/            logo.svg, header-logo-800x200 (color, white), favicon-48.png, favicon.ico
    social/             avatar on brand color, avatar on white, cover 1500x500
    print/              black and white SVG, 300 dpi black PNG
    README.md           hex codes, where each file goes, clear space, minimum sizes, misuse, trademark note
```

## The flow

1. `intake`: listing page and gallery photos (or a folder of photos, or a brand name plus a sentence).
2. `understand`: the brief, read off the product by gpt-5.4.
3. `shelf`: page one of Amazon, measured.
4. `understand` again, against the shelf.
5. `generate` twelve concepts, `judge`, `sheet`, then `options`: each pick on page one of Amazon, on the
   box, the label, the listing, the Store, Shopify, and on the product photo. **The run stops here and
   opens brand.html: three ranked picks, one recommendation with its reason and its cost, how to choose.**
6. `refine` the pick at 2048 px, `vectorize` (potrace per color, symbol split, audit), `tests`,
   `composites`, `on-product`, `kit`, `board`.

`--autopilot` skips the stop and takes the judge's recommendation.

## Honest limits

- The vector master is traced from a generated image, then audited. It is clean enough for print and
  web; a hand-drawn master has fewer anchors, and the skill says when to rebuild one by hand.
- The on-product renders are generated. They show the intent for the printer and for Brand Registry;
  the real photos must be of the real product.
- Nothing here clears a trademark. Search before you print.
- Amazon blocks scraping after a few fetches in a short time. The skill makes one attempt per page and
  tells you the three ways around a captcha.

## Credits

Built on [logo-design](https://github.com/kaankiziltug/logo-design-skill) by Kaan Kızıltuğ (MIT). The
discipline in that skill (identify, don't explain; 16 px and one color; the shelf test) is the backbone
here; this skill adds the product, the shelf, the surfaces and the uploads. MIT license.
