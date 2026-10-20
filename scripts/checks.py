"""Step 6b: is the name free enough to print? Checked, not assumed.

  checks <run> [--symbol kit/svg/final-symbol.svg]

Runs the checks a seller can do in an afternoon, in seconds, and writes checks.json plus a section on the
board. None of it is legal clearance; all of it catches the expensive surprises early:
  domains        DNS for brand.com / .co / .shop / .store / .io and brandname+category.com
  web presence   a web search for the exact name: who already uses it, and whether a brand with this name
                 already shows a logo online (the strongest "someone is here" signal)
  trademark      web results for "<name> trademark" and the USPTO / EUIPO / WIPO search links to open
  amazon         the Amazon search link for the name as a brand (fetched once when not blocked)
  marketplaces   Etsy / Shopify / Instagram handle links (handles are not probed: the sites answer 200 for
                 missing pages; the links are for the seller to click)
The board shows green / amber / red per line with the evidence, and the one sentence that matters: whether
to file before printing.
"""
import argparse
import re
import socket
import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import append_cost, client, curl, log, read_json, slugify, vision_cost, vision_json, web_search_json, write_json  # noqa: E402
from intake import blocked  # noqa: E402
from shelf import bing_image_urls, logo_from_web  # noqa: E402


def dns(host):
    try:
        socket.gethostbyname(host)
        return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    a = ap.parse_args()
    run = Path(a.run).resolve()
    brief = read_json(run / "brief.json") or {}
    prod = read_json(run / "product.json") or {}
    brand = brief.get("brand") or prod.get("brand", "")
    cat = (brief.get("category", "") or "").split(":")[-1].strip()
    slug = re.sub(r"[^a-z0-9]", "", brand.lower())
    out = {"brand": brand, "domains": [], "web": [], "trademark": {}, "amazon": {}, "links": {}, "verdict": {}}

    # 1. domains
    for host in (f"{slug}.com", f"{slug}.co", f"{slug}.shop", f"{slug}.store", f"{slug}.io", f"{slug}{(re.findall(r'[a-z]+', cat.lower()) or ['shop'])[0]}.com"):
        taken = dns(host)
        out["domains"].append({"host": host, "taken": taken})
    log("domains: " + ", ".join(f"{d['host']} {'taken' if d['taken'] else 'free'}" for d in out["domains"]))

    # 2. web presence for the exact name
    c = client()
    found = web_search_json(c, f'Which businesses, brands or products use the name "{brand}" (exact or near-identical spelling)? '
                               f'Look beyond the first page; include Amazon brands, Shopify stores, Instagram shops, registered companies.',
                            '{"items": [{"name": "...", "field": "what they sell or do", "url": "...", "same_name": true/false}]}')
    exact = found.get("items", []) if isinstance(found, dict) else []
    out["web"] = exact
    append_cost(run, "checks web search", 0.02)
    (run / "checks").mkdir(exist_ok=True)
    existing_logo = logo_from_web(brand, run / "checks" / "existing-logo.png", c, run)
    out["existing_logo"] = "checks/existing-logo.png" if existing_logo else None
    log(f"web: {len(exact)} results for the exact name; a logo under this name online: {'YES' if existing_logo else 'no'}")

    # 3. trademark signals
    tmf = web_search_json(c, f'Is there a registered or pending trademark for "{brand}" (USPTO, EUIPO, WIPO, UK IPO, Israel)? '
                             f'Search trademark databases and news. Name the owner, the classes or goods, and the status when you find one.',
                          '{"items": [{"mark": "...", "owner": "...", "goods": "...", "status": "...", "office": "...", "url": "..."}]}')
    tm = tmf.get("items", []) if isinstance(tmf, dict) else []
    append_cost(run, "checks trademark search", 0.02)
    out["trademark"] = {
        "results": tm,
        "uspto": f"https://tmsearch.uspto.gov/search/search-information?searchText={quote_plus(brand)}",
        "euipo": f"https://euipo.europa.eu/eSearch/#basic/1+1+1+1/100+100+100+100/{quote_plus(brand)}",
        "wipo": f"https://branddb.wipo.int/en/quicksearch?by=brandName&v={quote_plus(brand)}",
        "il": "https://trademarks.justice.gov.il/TradeMarksWebSiteUI/TrademarksSearch/TrademarksSearch.aspx",
    }

    # 4. amazon: the name as a brand
    host = prod.get("host", "www.amazon.com")
    url = f"https://{host}/s?k={quote_plus(brand)}"
    page = curl(url)
    if page and not blocked(page):
        hits = len(re.findall(r'data-component-type="s-search-result"', page))
        byline = len(re.findall(re.escape(brand), page, re.I))
        out["amazon"] = {"url": url, "fetched": True, "results": hits, "name_mentions": byline}
    else:
        out["amazon"] = {"url": url, "fetched": False}
    out["links"] = {"etsy": f"https://www.etsy.com/search?q={quote_plus(brand)}",
                    "instagram": f"https://www.instagram.com/{slug}/", "tiktok": f"https://www.tiktok.com/@{slug}",
                    "shopify_like": f"https://{slug}.myshopify.com/"}

    # 5. the verdict, by the model, from the evidence only
    own = bool(prod.get("asin")) and (prod.get("brand", "").lower() == brand.lower())
    own_line = (f'IMPORTANT: "{brand}" is the brand this seller ALREADY sells this product under on Amazon. A trademark or listing for '
                f'"{brand}" in this category most likely belongs to the seller (they are rebranding their own name). Treat such records as '
                f'"probably yours": say so, and judge risk only by OTHER owners or other fields. ') if own else ""
    prompt = f"""You are a brand-protection paralegal (not a lawyer). Brand name: "{brand}", category: "{cat}". {own_line}
Evidence:
- domains: {out['domains']}
- businesses found using the name: {exact}
- a logo under this name already online: {bool(existing_logo)}
- trademark records found: {tm}
- amazon: {out['amazon']}
Return JSON: {{"risk": "low|medium|high", "probably_yours": [records that look like the seller's own filings or listings],
"collisions": [names of businesses that appear to use this or a near-identical name, with their field],
"same_field": true/false (does any collision sell in the same category), "do_first": the one thing to do before printing packaging, in one sentence,
"notes": up to 3 short facts from the evidence}}. Say nothing the evidence does not show."""
    res, usage = vision_json(c, prompt, [])
    append_cost(run, "checks", vision_cost(usage))
    out["verdict"] = res or {}
    out["own_brand"] = own
    write_json(run / "checks.json", out)
    log(f"name risk: {out['verdict'].get('risk', '?')}; do first: {out['verdict'].get('do_first', '')}")


if __name__ == "__main__":
    main()
