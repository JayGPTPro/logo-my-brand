"""Shared plumbing for logo-my-brand: paths, keys, OpenAI clients, curl, images, the base skill.

Everything here is boring on purpose. The interesting parts live in the step scripts.
"""
import base64
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent

IMAGE_MODEL = os.getenv("LMB_IMAGE_MODEL", "gpt-image-2")
VISION_MODEL = os.getenv("LMB_VISION_MODEL", "gpt-5.4")
QUALITY = os.getenv("LMB_QUALITY", "low")          # low by default: one run costs under a dollar
WORKERS = int(os.getenv("LMB_WORKERS", "6"))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# gpt-image-2 prices (USD per image, 1024x1024). Updated 18.10.2026 from measured usage; they are
# estimates for the cost line on the board, not an invoice.
IMAGE_COST = {"low": 0.011, "medium": 0.042, "high": 0.167}


def log(msg):
    print(msg, flush=True)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ------------------------------------------------------------------ keys and clients
def load_key():
    """OPENAI_API_KEY from the environment, else the first .env that has it:
    ./.env, ~/.claude/.env, ~/.env, or the file named by LMB_ENV_FILE."""
    if os.getenv("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]
    for p in (Path.cwd() / ".env", Path.home() / ".claude" / ".env", Path.home() / ".env",
              Path(os.getenv("LMB_ENV_FILE", str(Path.home() / ".env")))):
        if p.exists():
            m = re.search(r"^OPENAI_API_KEY\s*=\s*[\"']?([^\"'\s]+)", p.read_text(), re.M)
            if m:
                os.environ["OPENAI_API_KEY"] = m.group(1)
                return m.group(1)
    return None


def client():
    if not load_key() and not (_env("KIE_API_KEY") and _env("GEMINI_API_KEY")):
        sys.exit("OPENAI_API_KEY not found. Put it in the environment or in ./.env (OPENAI_API_KEY=sk-...).")
    from openai import OpenAI
    return OpenAI()


# ------------------------------------------------------------------ run folder and state
def run_dir(slug, root=None):
    root = Path(root or os.getenv("LMB_ROOT") or (Path.cwd() / "logo"))
    d = root / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text())


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def append_cost(run, item, usd, note=""):
    with open(Path(run) / "cost.jsonl", "a") as fh:
        fh.write(json.dumps({"t": now(), "item": item, "usd": round(usd, 4), "note": note}) + "\n")


def total_cost(run):
    p = Path(run) / "cost.jsonl"
    if not p.exists():
        return 0.0
    return sum(json.loads(l)["usd"] for l in p.read_text().splitlines() if l.strip())


def slugify(text, fallback="brand"):
    """ASCII slug; a name with no ASCII letters (Hebrew, Arabic, CJK) gets a stable hash so two brands never
    share a folder."""
    import hashlib
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    if not s:
        s = fallback + "-" + hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:8]
    return s[:40]


# ------------------------------------------------------------------ curl
def curl(url, out=None, timeout=30):
    cmd = ["curl", "-sL", "--max-time", str(timeout), "-A", UA,
           "-H", "Accept-Language: en-US,en;q=0.9",
           "-H", "Accept: text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
           "--compressed", url]
    if out:
        r = subprocess.run(cmd + ["-o", str(out)], capture_output=True)
        return r.returncode == 0
    r = subprocess.run(cmd, capture_output=True)
    return r.stdout.decode("utf-8", "ignore") if r.returncode == 0 else ""


def download(url, dest, min_bytes=3000):
    """One attempt, never retried: a blocked CDN answers with a 9-byte file, and hammering it gets
    the IP blocked. Returns True when a real file landed."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > min_bytes:
        return True
    ok = curl(url, dest, timeout=60) and dest.exists() and dest.stat().st_size > min_bytes
    if not ok and dest.exists():
        dest.unlink()
    return ok


# ------------------------------------------------------------------ images
def img_b64(path, max_px=768, fmt="JPEG"):
    from PIL import Image
    with Image.open(path) as im:
        if fmt == "JPEG":
            im = im.convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = io.BytesIO()
        im.save(buf, fmt, quality=88)
    mime = "image/jpeg" if fmt == "JPEG" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def file_data_uri(path):
    p = Path(path)
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml",
            "webp": "image/webp"}.get(p.suffix.lower().lstrip("."), "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


# ------------------------------------------------------------------ providers
# Images: OpenAI direct, else kie.ai's hosted gpt-image-2 (the same model) when OpenAI is out of credit.
# Vision and web search: OpenAI gpt-5.4, else Gemini 3.1 Pro. LMB_IMAGE_PROVIDER / LMB_VISION_PROVIDER force one.
_DRY = {"openai": os.getenv("LMB_IMAGE_PROVIDER") == "kie" or os.getenv("LMB_VISION_PROVIDER") == "gemini"}
_DRY_IMG = {"v": os.getenv("LMB_IMAGE_PROVIDER") == "kie"}
_DRY_VIS = {"v": os.getenv("LMB_VISION_PROVIDER") == "gemini"}
GEMINI_MODEL = os.getenv("LMB_GEMINI_MODEL", "gemini-3.1-pro-preview")


def _env(name):
    if os.getenv(name):
        return os.environ[name]
    for p in (Path.cwd() / ".env", Path.home() / ".claude" / ".env", Path.home() / ".env", Path(os.getenv("LMB_ENV_FILE", str(Path.home() / ".env")))):
        if p.exists():
            m = re.search(r"^%s\s*=\s*[\"']?([^\"'\s]+)" % name, p.read_text(), re.M)
            if m:
                os.environ[name] = m.group(1)
                return m.group(1)
    return None


def _is_dry(exc):
    t = str(exc)
    return "insufficient_quota" in t or "credit_balance_exhausted" in t or "billing_hard_limit" in t


class Usage:
    def __init__(self, i=0, o=0):
        self.prompt_tokens, self.completion_tokens = i, o


def _gemini_json(prompt, images=(), max_px=1024, search=False):
    import json as _j
    from google import genai
    from google.genai import types
    g = genai.Client(api_key=_env("GEMINI_API_KEY"))
    parts = [prompt]
    from PIL import Image
    for p in images:
        im = Image.open(p).convert("RGB")
        im.thumbnail((max_px, max_px))
        parts.append(im)
    cfg = types.GenerateContentConfig(response_mime_type=None if search else "application/json",
                                      tools=[types.Tool(google_search=types.GoogleSearch())] if search else None)
    r = g.models.generate_content(model=GEMINI_MODEL, contents=parts, config=cfg)
    text = r.text or "{}"
    m = re.search(r"\{.*\}", text, re.S)
    um = getattr(r, "usage_metadata", None)
    u = Usage(getattr(um, "prompt_token_count", 0) or 0, getattr(um, "candidates_token_count", 0) or 0)
    try:
        return _j.loads(m.group(0) if m else text), u
    except Exception:
        return None, u


def vision_json(c, prompt, images=(), max_px=1024):
    """One look: text + images in, a JSON object out. Returns (dict or None, usage). OpenAI, else Gemini."""
    if not _DRY_VIS["v"]:
        content = [{"type": "text", "text": prompt}]
        for p in images:
            content.append({"type": "image_url", "image_url": {"url": img_b64(p, max_px), "detail": "high"}})
        try:
            r = c.chat.completions.create(model=VISION_MODEL, messages=[{"role": "user", "content": content}],
                                          response_format={"type": "json_object"})
            text = r.choices[0].message.content or "{}"
            try:
                return json.loads(text), r.usage
            except json.JSONDecodeError:
                return None, r.usage
        except Exception as exc:
            if not _is_dry(exc):
                raise
            _DRY_VIS["v"] = True
            log("  OpenAI is out of credit: vision moves to Gemini for the rest of the run")
    return _gemini_json(prompt, images, max_px)


def web_search_json(c, question, schema_hint):
    """A real web search answered as JSON: OpenAI web_search, else Gemini with Google Search grounding."""
    ask = f"{question}\nAnswer with JSON only, shaped like: {schema_hint}. Cite the URL you saw for each item; say [] when you find nothing."
    if not _DRY_VIS["v"]:
        try:
            r = c.responses.create(model=VISION_MODEL, tools=[{"type": "web_search"}], input=ask)
            m = re.search(r"\{.*\}", r.output_text or "{}", re.S)
            return json.loads(m.group(0)) if m else {}
        except Exception as exc:
            if not _is_dry(exc):
                log(f"  web search failed: {str(exc)[:140]}")
                return {}
            _DRY_VIS["v"] = True
    try:
        res, _ = _gemini_json(ask, search=True)
        return res or {}
    except Exception as exc:
        log(f"  web search failed: {str(exc)[:140]}")
        return {}


def vision_cost(usage):
    """gpt-5.4 list price (USD): $2.50 / 1M in, $15 / 1M out (Gemini 3.1 Pro is in the same range)."""
    if not usage:
        return 0.0
    return usage.prompt_tokens * 2.5e-6 + usage.completion_tokens * 15e-6


KIE = "https://api.kie.ai/api/v1/jobs"


def _kie_upload(path):
    import requests
    with open(path, "rb") as fh:
        r = requests.post("https://kieai.redpandaai.co/api/file-stream-upload", headers={"Authorization": f"Bearer {_env('KIE_API_KEY')}"},
                          files={"file": (Path(path).name, fh)}, data={"uploadPath": "logo-my-brand"}, timeout=120)
    d = r.json().get("data") or {}
    url = d.get("downloadUrl") or d.get("fileUrl")
    if not url:
        raise RuntimeError(f"kie upload: {r.text[:200]}")
    return url


def _kie_image(prompt, dest, size, images=()):
    """gpt-image-2 on kie.ai: text-to-image, or image-to-image with uploaded inputs. One attempt, polled."""
    import requests
    key = _env("KIE_API_KEY")
    if not key:
        raise RuntimeError("no KIE_API_KEY")
    w, h = (int(x) for x in size.split("x"))
    ar = "1:1" if abs(w - h) < 50 else ("3:2" if w > h else "2:3")
    inp = {"prompt": prompt[:3900], "aspect_ratio": ar}
    model = "gpt-image-2-text-to-image"
    if images:
        model = "gpt-image-2-image-to-image"
        inp["input_urls"] = [_kie_upload(p) for p in images][:16]
        inp["resolution"] = "2K" if max(w, h) >= 2000 else "1K"
    hd = {"Authorization": f"Bearer {key}"}
    d = requests.post(f"{KIE}/createTask", headers=hd, json={"model": model, "input": inp}, timeout=60).json()
    tid = (d.get("data") or {}).get("taskId")
    if not tid:
        raise RuntimeError(f"kie createTask: {json.dumps(d)[:200]}")
    for _ in range(80):
        time.sleep(5)
        q = requests.get(f"{KIE}/recordInfo", headers=hd, params={"taskId": tid}, timeout=60).json().get("data") or {}
        if q.get("state") == "success":
            url = json.loads(q["resultJson"])["resultUrls"][0]
            Path(dest).write_bytes(requests.get(url, timeout=120).content)
            from PIL import Image
            with Image.open(dest) as im:   # kie returns webp or odd sizes: normalise to a PNG at the asked size
                im = im.convert("RGB")
                if im.size != (w, h):
                    im = im.resize((w, h), Image.LANCZOS)
                im.save(dest, "PNG")
            return Path(dest)
        if q.get("state") == "fail":
            raise RuntimeError(f"kie fail: {q.get('failCode')} {q.get('failMsg')}")
    raise RuntimeError(f"kie timeout {tid}")


def generate_image(c, prompt, dest, size="1024x1024", quality=None):
    """One gpt-image-2 generation, one attempt. OpenAI direct, else kie. Returns the path or None."""
    quality = quality or QUALITY
    if not _DRY_IMG["v"]:
        try:
            r = c.images.generate(model=IMAGE_MODEL, prompt=prompt, size=size, quality=quality, n=1)
            Path(dest).write_bytes(base64.b64decode(r.data[0].b64_json))
            return Path(dest)
        except Exception as exc:
            if not _is_dry(exc):
                log(f"  generate failed: {str(exc)[:160]}")
                return None
            _DRY_IMG["v"] = True
            log("  OpenAI is out of credit: images move to kie.ai (same gpt-image-2) for the rest of the run")
    try:
        return _kie_image(prompt, dest, size)
    except Exception as exc:
        log(f"  generate failed (kie): {str(exc)[:160]}")
        return None


def edit_image(c, prompt, images, dest, size="1024x1024", quality=None):
    """gpt-image-2 edit with one or more input images (the first is the canvas). OpenAI direct, else kie."""
    quality = quality or QUALITY
    if not _DRY_IMG["v"]:
        handles = [open(p, "rb") for p in images]
        try:
            r = c.images.edit(model=IMAGE_MODEL, image=handles if len(handles) > 1 else handles[0],
                              prompt=prompt, size=size, quality=quality, n=1)
            Path(dest).write_bytes(base64.b64decode(r.data[0].b64_json))
            return Path(dest)
        except Exception as exc:
            if not _is_dry(exc):
                log(f"  edit failed: {str(exc)[:160]}")
                return None
            _DRY_IMG["v"] = True
            log("  OpenAI is out of credit: images move to kie.ai (same gpt-image-2) for the rest of the run")
        finally:
            for h in handles:
                h.close()
    try:
        return _kie_image(prompt, dest, size, images)
    except Exception as exc:
        log(f"  edit failed (kie): {str(exc)[:160]}")
        return None


def api_size_for(w, h):
    """The gpt-image size closest to an input's aspect: square, landscape or portrait."""
    r = w / max(h, 1)
    if r > 1.25:
        return "1536x1024"
    if r < 0.8:
        return "1024x1536"
    return "1024x1024"


# ------------------------------------------------------------------ the base skill (logo-design)
def base_skill():
    """Folder of kaankiziltug's logo-design skill. Its scripts do the SVG audit, the size ladder,
    the variants and the PNG rendering; we do not duplicate them."""
    cands = [os.getenv("LOGO_DESIGN_SKILL"),
             Path.home() / ".claude" / "skills" / "logo-design",
             Path.cwd() / ".claude" / "skills" / "logo-design",
             SKILL.parent / "logo-design",
             SKILL / "vendor" / "logo-design"]
    for c in cands:
        if c and (Path(c) / "scripts" / "render_png.py").exists():
            return Path(c)
    return None


def base_script(name):
    b = base_skill()
    if not b:
        sys.exit("The logo-design base skill is not installed. Run: bash " + str(SKILL / "install.sh"))
    return str(b / "scripts" / name)


def run_py(args, cwd=None, quiet=False):
    r = subprocess.run([sys.executable] + [str(a) for a in args], cwd=cwd, capture_output=True)
    out = r.stdout.decode("utf-8", "ignore")
    err = r.stderr.decode("utf-8", "ignore")
    if r.returncode != 0 and not quiet:
        log(f"  {Path(str(args[0])).name} exited {r.returncode}: {err.strip()[-300:]}")
    return r.returncode, out, err


def screenshot_html(html_path, png_path, w, h):
    """Headless Chrome screenshot via the base skill's renderer (it finds Chrome on every OS)."""
    sys.path.insert(0, str(Path(base_script("render_png.py")).parent))
    import render_png  # noqa
    render_png.screenshot_html(str(html_path), str(png_path), w, h)
    return Path(png_path)


def svg_to_png(svg, png, size=None, width=None, height=None, bg=None, padding=0.0):
    args = [base_script("render_png.py"), svg, "-o", png]
    if size:
        args += ["--size", size]
    if width:
        args += ["--width", width]
    if height:
        args += ["--height", height]
    if bg:
        args += ["--bg", bg]
    if padding:
        args += ["--padding", padding]
    code, _, _ = run_py(args)
    return Path(png) if code == 0 and Path(png).exists() else None


def esc(s):
    """HTML-escape, and turn the dashes the models love into plain punctuation."""
    import html
    t = str(s if s is not None else "").replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ").replace("\u2013", "-")
    return html.escape(t)
