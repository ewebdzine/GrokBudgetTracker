#!/usr/bin/env python3
"""Render GrokBudgetTracker bucket charts to PNG (white Grok theme, purple #8350f2 bars, amber at 90%+, red when over).
Input: JSON from templates/bucket_chart.sql (run through the Supabase connector; the `chart` column) or a file shaped like
templates/sample/buckets-example.json. No database keys are used.
Usage:
  python3 render_bucket_chart.py DATA.json --view summary [--out buckets.png]
  python3 render_bucket_chart.py DATA.json --view single --bucket Groceries [--out groceries.png]
Views: summary (all buckets, default), single (one bucket breakdown). Optional: card, pails.
Needs Google Chrome or Chromium (headless). Pillow, if installed, trims the transparent margin."""
import json, os, shutil, subprocess, sys, tempfile, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
a = sys.argv[1:]
def opt(k, d=None): return a[a.index(k) + 1] if k in a else d
data_path = next((x for x in a if x.endswith(".json")), os.path.join(HERE, "sample", "buckets-example.json"))
view, bucket = opt("--view", "summary"), opt("--bucket")
out = opt("--out", f"bucket-{view}{'-' + bucket.lower().replace(' ', '-') if bucket else ''}.png")
data = json.load(open(data_path))
data = data.get("chart", data) if isinstance(data, dict) else data[0].get("chart", data[0])  # accept a raw connector row
if view == "single":
    names = [b["name"].lower() for b in data["buckets"]]
    if not bucket or bucket.lower() not in names: sys.exit(f"--bucket must be one of: {', '.join(b['name'] for b in data['buckets'])}")
for b in data["buckets"]:  # numeric strings from Postgres -> numbers
    b["planned"], b["spent"] = float(b["planned"]), float(b["spent"])
    b["expenses"] = [[r[0], float(r[1])] + list(r[2:]) for r in b.get("expenses", b.get("recent", []))]
html = open(os.path.join(HERE, "bucket-chart.html")).read().replace("/*BUCKET_DATA*/", json.dumps(data).replace("</", "<\\/"))
chrome = os.environ.get("CHROME_PATH") or next((shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)
if not chrome: sys.exit("Chrome or Chromium not found (set CHROME_PATH)")
width = {"summary": 400, "single": 520, "card": 760, "pails": 1060}.get(view, 760)
with tempfile.TemporaryDirectory() as td:
    page = os.path.join(td, "chart.html"); open(page, "w").write(html)
    q = urllib.parse.urlencode({"view": view, **({"bucket": bucket} if bucket else {})})
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    "--default-background-color=00000000", f"--window-size={width},{1400 + 60 * max(len(b["expenses"]) for b in data["buckets"])}", f"--screenshot={os.path.abspath(out)}",
                    f"file://{page}?{q}"], check=True, capture_output=True)
try:
    from PIL import Image
    im = Image.open(out); bbox = im.getbbox()
    if bbox: im.crop(bbox).save(out)
except ImportError:
    pass
print(out)
