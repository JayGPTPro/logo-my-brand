# The competitor shelf

Page one of Amazon for the brief's keyword is the only shelf that matters: the buyer never sees the
brand anywhere else first. `shelf.py` measures it instead of describing it.

## 1. What is measured

**Tiles.** Up to twelve organic and sponsored results: ASIN, title, price, main image. The product's own
ASIN is excluded. Thumbnails are downloaded once; a blocked CDN gives a 9-byte file and the tile is
dropped, never retried.

**Color census.** Every tile is shrunk to 120 px and each saturated pixel (HLS saturation over 0.25,
lightness between 0.12 and 0.93) is binned into one of eight hue families: red, orange, yellow, green,
cyan, blue, purple, pink. White and black are counted apart and do not vote.

- `owned`: families with 18% or more of the saturated pixels. The shelf already speaks this color.
- `free`: families with 4% or less. Nobody on page one uses it.

The census counts product photos, not logos, on purpose: a buyer scanning the grid sees products, and a
brand color that matches the dominant product color vanishes into the grid. A mark in a free hue is a
mark that reads as a different thing on the page.

**Read.** gpt-5.4 looks at the twelve tiles as a shopper would and returns the brand names it can read,
each visible logo's style, the shelf's shared visual habits, its type habits, three whitespace
opportunities and three ways to disappear. This is the qualitative half; the census is the quantitative
half, and the brief's second pass gets both.

## 2. How the directions use it

The second `understand` pass receives the shelf facts and must obey: no direction's main color in an
owned family; at least one direction takes a whitespace opportunity literally (a type voice, a symbol
language, a tone). The judge also receives the owned colors and the habits, and scores
`distinct_on_shelf` against them.

## 3. When to override

- **A free hue that is wrong for the category.** Purple is free on most kitchen shelves because it
  reads as cosmetics. Free is an opportunity, not an order. The brief's adjectives decide.
- **An owned hue that is the brand's equity.** A rebrand of a product people already know by its color
  keeps the color and differentiates with shape and type instead. Say so in the brief's `name_notes`.
- **A shelf with no dominant color** (`owned` empty). Then distinction comes from type and symbol
  language; the read's `type_habits` line becomes the main constraint.
- **A keyword that pulled the wrong shelf.** Check `shelf.html`. If the tiles are not the product's
  real competitors, rerun with `--keyword`.

## 3b. The competitors' real logos

For every brand the read names, `shelf.py` runs an image search for "<brand> logo" (Bing's async endpoint
answers plain requests; Google and DuckDuckGo do not), downloads up to six candidates, and asks the vision
model which ones are the brand's actual mark. The best is saved as `shelf/logo-NN.png`, flattened on
white, with `logo_source: "web"` in shelf.json. Brands the search cannot find fall back to the crop pass
(a labelled 10 x 10 grid on their product photo, a zoom pass, a read-back). Tiles whose brand is "unknown"
show nothing: a wrong logo is worse than none.

To hand the script better candidates, collect URLs in the browser pane and pass `--logo-urls logos.json`
(`{"Brand": ["https://...png"]}`). On Bing Images this returns the result URLs for the open page:

```js
Array.from(document.querySelectorAll('a.iusc')).slice(0,8).map(a=>JSON.parse(a.getAttribute('m')).murl)
```

## 4. When Amazon blocks the fetch

Search results can be read straight from the browser pane when curl is bot-checked. On the Amazon results
page, this returns the tiles as `competitors.json` wants them:

```js
JSON.stringify(Array.from(document.querySelectorAll('[data-component-type="s-search-result"]')).slice(0,14).map(el=>{const img=el.querySelector('img.s-image');const p=el.querySelector('.a-price .a-offscreen');return {asin:el.getAttribute('data-asin'),title:(img?.alt||'').replace(/^Sponsored Ad - /,'').slice(0,120),image:(img?.src||'').replace(/\._[A-Z0-9_,]+_(\.[a-z]+)$/,'$1'),price:p?p.textContent.trim():''}}))
```

## 4b. The older ways around a block

After a few searches in a short time Amazon answers with a captcha page. The run says so and continues
without a shelf. Three ways to add it later, then rerun `understand` and `prompts`:

- Save the search results page from a browser as HTML: `shelf.py <run> --competitors page.html`.
- A folder of competitor images: `shelf.py <run> --competitors ./competitors/`.
- A JSON list: `[{"brand": "...", "title": "...", "image": "url or path", "price": "..."}]`.

## 5. What the shelf is not for

The tiles are a measurement and a comparison target. Never trace, imitate or "improve" a competitor's
mark. A concept that resembles a tile's logo is dropped at the checkpoint, whatever its score.
