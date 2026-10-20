# Where the files go

Checked 18.10.2026 against the Amazon Ads help pages, the Shopify theme editor and several vendor guides.
The upload console is the final word; when a console refuses a file, its message names the size it wants.

## Amazon

| Asset | Size | Format | File in the kit |
|---|---|---|---|
| Brand Store logo (Store header, also the "home" button) | 400 x 400 px minimum, square | PNG or JPG, under 5 MB | `amazon/brand-store-logo-400.png` |
| Sponsored Brands brand logo | 400 x 400 px minimum, square; shown at about 40 to 60 px on mobile | PNG or JPG, under 1 MB | `amazon/sponsored-brands-logo-400.png` |
| Brand Store header / hero | 3000 x 600 px | PNG or JPG | `amazon/brand-store-hero-3000x600.png` |
| A+ brand story logo card, Brand Registry evidence | any, square-ish on white | PNG | `amazon/lockup-on-white-1200.png` |
| Posts, Brand Follow avatar | 400 x 400 | PNG | `amazon/brand-store-logo-400.png` |

Rules worth knowing: the logo must fill the square without being crowded (the kit uses 14% padding), no
extra text, no promotional claims inside the logo tile. Sponsored Brands rejects logos that are mostly
white space or contain a tagline.

**Brand Registry** needs a pending or registered trademark (text or image mark) and asks for images of
the product and the packaging with the brand name permanently affixed. The on-product renders show what
those photos should look like; the real photos must be of the real product.

## Shopify (and any website)

| Asset | Size | File |
|---|---|---|
| Header logo | SVG preferred; PNG 800 x 200 (themes display it at about 160 to 400 px wide; set the width in the theme editor) | `shopify/logo.svg`, `shopify/header-logo-800x200.png` |
| Header logo on dark theme | same, white | `shopify/header-logo-white-800x200.png` |
| Favicon | 48 x 48 PNG (Shopify) or favicon.ico 16/32/48 (any site) | `shopify/favicon-48.png`, `shopify/favicon.ico` |
| Checkout logo | same as header | `shopify/logo.svg` |

## Social

| Asset | Size | File |
|---|---|---|
| Profile avatar (Instagram, TikTok, Facebook, Pinterest, YouTube) | 1024 x 1024, shown in a circle | `social/avatar-brand-1024.png`, `social/avatar-white-1024.png` |
| Cover (X, Facebook, YouTube banner safe area) | 1500 x 500 | `social/cover-1500x500.png` |

Avatars are the symbol on the brand color with 22% padding; a lockup in a circle at 40 px is unreadable.

## Print and manufacturing

| Use | What the vendor wants | File |
|---|---|---|
| Box, sleeve, label printer | vector, one color or the hex codes, plus a 300 dpi PNG as a reference | `print/<name>-black.svg`, `print/<name>-black-300dpi.png` |
| Laser engraving, embossing die, debossing | one-color vector, no strokes thinner than about 0.3 mm at final size | `print/<name>-black.svg` |
| Embroidery, woven label | one-color vector; the mill simplifies details under about 1 mm | `svg/<name>-symbol-black.svg` for small sizes |
| Pad print on steel or plastic | one-color vector | `print/<name>-black.svg` |

Minimum sizes written into `kit/README.md`: lockup 24 mm in print and 100 px on screen; symbol alone 8 mm
and 24 px. A traced master may need the symbol-only file at the smallest sizes.

## Hex, RGB, CMYK

The kit gives hex. For a printer, convert with the printer's profile, not a web converter, and ask for a
one-color proof on the real board before the run.
