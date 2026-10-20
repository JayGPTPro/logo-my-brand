"""logo-my-brand, the whole run in one command.

  lmb.py run <ASIN | Amazon URL | folder | "Brand name"> [--brand NAME] [--about "..."] [--autopilot] [--pick B2]
  lmb.py continue <run> --pick B2          after the checkpoint: refine, vectorize, tests, mockups, kit, board
  lmb.py status <run>                      what exists, what it cost

Default flow stops at the concept checkpoint (concepts.png) and prints what to show the user.
--autopilot takes the judge's recommendation and runs to the board without stopping.
Every step is its own script and is resumable: a step whose output exists is skipped.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import log, read_json, total_cost  # noqa: E402


def step(script, *args, must=True):
    cmd = [sys.executable, "-W", "ignore", str(HERE / script)] + [str(a) for a in args]
    log(f"\n$ {script} {' '.join(str(a) for a in args)}")
    r = subprocess.run(cmd, text=True, capture_output=True)
    sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stdout.write(r.stderr[-1200:])
        if must:
            sys.exit(f"\n{script} failed (exit {r.returncode}). Fix the cause and run the same command again; finished steps are kept.")
    return r


def phase_concepts(run, competitors=None, keyword=None):
    if not (run / "brief.json").exists():
        step("intake.py", "understand", run)
    prod = read_json(run / "product.json") or {}
    if not (run / "shelf.json").exists() and prod.get("kind") == "business" and not competitors:
        log("Business brand: no Amazon shelf. Research 8 to 12 competitors (web, Maps, their sites), write competitors.json "
            "[{\"brand\", \"domain\", \"image\"(optional), \"title\"}] and run: lmb.py run ... --competitors competitors.json")
    if not (run / "trends.json").exists():
        step("trends.py", run, must=False)   # where the category's design is going, measured on recent brands
    if (run / "trends.json").exists() and not (run / "shelf.json").exists() and prod.get("kind") == "business" and not competitors \
            and not (run / "prompts.json").exists():
        step("intake.py", "understand", run)   # the brief learns the trend facts
    if not (run / "shelf.json").exists() and not (prod.get("kind") == "business" and not competitors):
        args = [run] + (["--competitors", competitors] if competitors else []) + (["--keyword", keyword] if keyword else [])
        r = step("shelf.py", *args, must=False)
        if r.returncode == 0 and not (run / "prompts.json").exists():
            step("intake.py", "understand", run)   # second pass: directions that answer the measured shelf (never once concepts exist)
        else:
            log("Continuing without a competitor shelf (rerun shelf.py with --competitors to add it later).")
    if not (run / "prompts.json").exists():
        step("concepts.py", "prompts", run)
    want = [p["id"] for p in (read_json(run / "prompts.json") or []) if not p["id"].startswith("P") and "e" not in p["id"][1:]]
    if any(not (run / "concepts" / f"{i}.png").exists() for i in want):
        step("concepts.py", "generate", run)
    if not (run / "judge.json").exists():
        step("concepts.py", "judge", run)
    if not any((run / "concepts").glob("*e1.png")) and os.getenv("LMB_SKIP_EVOLVE") != "1":
        step("concepts.py", "evolve", run, must=False)   # craft and bolder passes on the three picks
        step("concepts.py", "judge", run)                 # judged again with the originals
    step("concepts.py", "sheet", run)
    if not (run / "options" / "options.json").exists():
        step("options.py", run, must=False)   # each option on the box, the listing, the store and the product
    step("page.py", run)   # brand.html in the choose state


def phase_finish(run, pick):
    step("concepts.py", "refine", run, pick)
    step("vectorize.py", run, pick)
    if not (run / "checks.json").exists():
        step("checks.py", run, must=False)   # name, domains, collisions
    if not (run / "mockups" / "on-product.json").exists():
        step("mockups.py", "on-product", run, must=False)   # first: the composites and templates use the passing renders
    if not (run / "kit" / "brand-system" / "system.json").exists():
        step("system.py", run, must=False)   # palette, type, listing templates, brand story
    step("mockups.py", "tests", run)
    step("mockups.py", "composites", run)
    step("pack.py", "kit", run)
    step("page.py", run)   # the same brand.html, now in the delivered state, plus logo-kit.zip and brand-guidelines.pdf


def cmd_run(a):
    from intake import asin_from
    from common import slugify
    guess = Path(a.source).expanduser()
    slug = slugify(a.brand) if a.brand else (asin_from(a.source.strip()) or (slugify(guess.name) if guess.is_dir() else slugify(a.source)))
    existing = Path.cwd() / "logo" / slug / "product.json"
    if existing.exists():
        log(f"product.json exists for {slug}: skipping the fetch (delete it to refetch)")
        run = existing.parent
        phase_concepts(run, a.competitors, a.keyword)
        return finish_or_checkpoint(a, run)
    args = ["intake", a.source]
    if a.brand:
        args += ["--brand", a.brand]
    if a.about:
        args += ["--about", a.about]
    for flag in ("kind", "city", "website"):
        if getattr(a, flag):
            args += [f"--{flag}", getattr(a, flag)]
    r = step("intake.py", *args)
    run = Path(r.stdout.strip().splitlines()[-1])
    phase_concepts(run, a.competitors, a.keyword)
    finish_or_checkpoint(a, run)


def finish_or_checkpoint(a, run):
    judge = read_json(run / "judge.json") or {}
    pick = a.pick or judge.get("recommend")
    if pick and not (run / "concepts" / f"{pick}.png").exists():
        sys.exit(f"no concept image for pick {pick}")
    if a.autopilot or a.pick:
        phase_finish(run, pick)
        log(f"\nDone. Open {run / 'brand.html'}. Spend about ${total_cost(run):.2f}.")
    else:
        log(f"\nCHECKPOINT. Open {run / 'brand.html'} for the user; recommendation "
            f"({pick}). When they choose: lmb.py continue {run} --pick <id>. Spend so far about ${total_cost(run):.2f}.")


def cmd_continue(a):
    run = Path(a.run)
    pick = a.pick or (read_json(run / "judge.json") or {}).get("recommend")
    if not pick:
        sys.exit("no pick and no judge recommendation")
    phase_finish(run, pick)
    log(f"\nDone. Open {run / 'brand.html'}. Spend about ${total_cost(run):.2f}.")


def cmd_round(a):
    """Another round of twelve concepts, steered by the client's feedback, then judge, evolve, options, review."""
    run = Path(a.run)
    step("concepts.py", "round", run, *(["--feedback", a.feedback] if a.feedback else []))
    step("concepts.py", "generate", run)
    step("concepts.py", "judge", run)
    step("concepts.py", "evolve", run, must=False)
    step("concepts.py", "judge", run)
    step("concepts.py", "sheet", run)
    step("options.py", run, must=False)
    step("page.py", run)
    log(f"\nNew round on the page: {run / 'brand.html'}. Spend so far about ${total_cost(run):.2f}.")


def cmd_votes(a):
    """Re-rank the three options on consumer votes and rebuild the review."""
    run = Path(a.run)
    votes = read_json(a.votes) or {}
    judge = read_json(run / "judge.json") or {}
    picks = judge.get("picks", {})
    score = {k: sum(int(v or 0) for v in (votes.get(k) or {}).values()) for k in picks}
    if not any(score.values()):
        sys.exit("votes.json has no counts")
    best = max(score, key=score.get)
    judge["votes"] = votes
    judge["recommend_before_votes"] = judge.get("recommend")
    judge["recommend"] = picks[best]
    judge["why"] = f"{sum(score.values())} buyers voted; option {best} led on trust, memory and perceived value ({score})."
    from common import write_json
    write_json(run / "judge.json", judge)
    step("page.py", run)
    log(f"re-ranked on votes: {best} leads")


def cmd_status(a):
    run = Path(a.run)
    for f in ("product.json", "brief.json", "shelf.json", "prompts.json", "judge.json", "concepts.png", "final.json",
              "mockups/tests.png", "mockups/on-product.json", "kit/README.md", "brand.html"):
        print(f"  {'ok ' if (run / f).exists() else '.. '} {f}")
    print(f"  spend about ${total_cost(run):.2f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("source")
    p.add_argument("--brand")
    p.add_argument("--about")
    p.add_argument("--autopilot", action="store_true")
    p.add_argument("--pick")
    p.add_argument("--kind", choices=["product", "business"])
    p.add_argument("--city")
    p.add_argument("--website")
    p.add_argument("--competitors", help="competitors.json / saved results page / folder, for businesses and non-Amazon products")
    p.add_argument("--keyword", help="override the shelf search")
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("continue")
    p.add_argument("run")
    p.add_argument("--pick")
    p.set_defaults(fn=cmd_continue)
    p = sub.add_parser("round")
    p.add_argument("run")
    p.add_argument("--feedback", help="what the client said: what they liked in each option, what to drop, bolder or safer")
    p.set_defaults(fn=cmd_round)
    p = sub.add_parser("votes")
    p.add_argument("run")
    p.add_argument("votes")
    p.set_defaults(fn=cmd_votes)
    p = sub.add_parser("status")
    p.add_argument("run")
    p.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
