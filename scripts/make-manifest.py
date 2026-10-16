#!/usr/bin/env python3
"""Build manifest/<scan>/images.csv, checksums.sha256 and summary.json from an image directory.

Usage:  scripts/make-manifest.py <images_dir> <scan> [--interior <list>] [--edited <list>] [--repo <root>]

Columns: filename, session, interior, edited, bytes, sha256, width, height, datetime, lat, lon,
         alt_m, rel_alt_m, gimbal_pitch, gps_valid

  session     battery session, numbered from 1 in capture order. A new session starts when two
              consecutive frames are more than 120 s apart.
  interior    the interior spot (1, 2, 3...) for a frame shot inside the building, else empty.
              Taken from --interior: a text file with one filename per line; a line starting
              '# spot' begins the next spot, any other '#' line is a comment. The list is made by
              eye, not computed.
  edited      empty for a camera original; otherwise what was changed, from --edited (a text file,
              "<filename>  <what>" per line, '#' lines are comments).
  gps_valid   false for null-island (0,0) fixes and for missing coordinates.

Checksum paths are '<scan>/images/<name>', the same paths the files have on Hugging Face, so
scripts/verify.sh can check a download without rewriting anything.
"""
import argparse, csv, hashlib, json, os, re, subprocess, sys
from datetime import datetime

ap = argparse.ArgumentParser()
ap.add_argument("images_dir")
ap.add_argument("scan")
ap.add_argument("--interior")
ap.add_argument("--edited")
ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
a = ap.parse_args()

img_dir = os.path.abspath(a.images_dir)
out = os.path.join(a.repo, "manifest", a.scan)
os.makedirs(out, exist_ok=True)

files = sorted(f for f in os.listdir(img_dir) if f.lower().endswith(".jpg"))
if not files:
    sys.exit(f"no .jpg found in {img_dir}")
print(f"{len(files)} images in {img_dir}")

interior = {}
if a.interior:
    spot = 0
    for line in open(a.interior):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if re.match(r"#\s*spot\b", line):
                spot += 1
            continue
        name = os.path.basename(line)
        if name not in files:
            sys.exit(f"--interior names {name}, which is not in {img_dir}")
        interior[name] = spot

edited = {}
if a.edited:
    for line in open(a.edited):
        line = line.strip()
        if line and not line.startswith("#"):
            name, what = line.split(None, 1)
            if name not in files:
                sys.exit(f"--edited names {name}, which is not in {img_dir}")
            edited[name] = what

print("reading EXIF ...")
proc = subprocess.run(
    ["exiftool", "-q", "-q", "-m", "-n", "-json",
     "-FileName", "-ImageWidth", "-ImageHeight", "-DateTimeOriginal",
     "-GPSLatitude", "-GPSLongitude", "-GPSAltitude",
     "-GPSLatitudeRef", "-GPSLongitudeRef", "-RelativeAltitude", "-GimbalPitchDegree", img_dir],
    capture_output=True, text=True)
meta = {r.get("FileName", ""): r for r in json.loads(proc.stdout or "[]")}


def signed(val, ref, negative_ref):
    """exiftool -n returns an UNSIGNED magnitude; the hemisphere lives in a separate Ref tag.
    Without this, every western longitude comes out positive."""
    if val in (None, ""):
        return ""
    v = abs(float(val))
    if str(ref).strip().upper().startswith(negative_ref):
        v = -v
    return v


rows, sums, last_t, session = [], [], None, 0
for i, name in enumerate(files, 1):
    path = os.path.join(img_dir, name)
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    m = meta.get(name, {})
    t = datetime.strptime(m["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
    if last_t is None or (t - last_t).total_seconds() > 120:
        session += 1
    last_t = t
    lat = signed(m.get("GPSLatitude"), m.get("GPSLatitudeRef"), "S")
    lon = signed(m.get("GPSLongitude"), m.get("GPSLongitudeRef"), "W")
    valid = lat != "" and lon != "" and float(lat) != 0.0 and float(lon) != 0.0
    rows.append({
        "filename": name, "session": session, "interior": interior.get(name, ""),
        "edited": edited.get(name, ""),
        "bytes": os.path.getsize(path), "sha256": h.hexdigest(),
        "width": m.get("ImageWidth", ""), "height": m.get("ImageHeight", ""),
        "datetime": m.get("DateTimeOriginal", ""), "lat": lat, "lon": lon,
        "alt_m": m.get("GPSAltitude", ""), "rel_alt_m": m.get("RelativeAltitude", ""),
        "gimbal_pitch": m.get("GimbalPitchDegree", ""),
        "gps_valid": "true" if valid else "false",
    })
    sums.append(f"{h.hexdigest()}  {a.scan}/images/{name}")
    if i % 250 == 0 or i == len(files):
        print(f"  hashed {i}/{len(files)}")

cols = list(rows[0].keys())
with open(os.path.join(out, "images.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)
with open(os.path.join(out, "checksums.sha256"), "w") as fh:
    fh.write("\n".join(sums) + "\n")

total = sum(r["bytes"] for r in rows)
sessions = {}
for r in rows:
    s = sessions.setdefault(str(r["session"]), {"images": 0, "first": r["datetime"]})
    s["images"] += 1
    s["last"] = r["datetime"]
spots = {}
for r in rows:
    if r["interior"] != "":
        spots[str(r["interior"])] = spots.get(str(r["interior"]), 0) + 1
summary = {
    "images": len(rows), "bytes": total, "gb": round(total / 1e9, 2),
    "gps_invalid": sum(1 for r in rows if r["gps_valid"] == "false"),
    "interior_images": sum(spots.values()), "interior_spots": spots,
    "edited_images": len(edited), "camera_originals": len(rows) - len(edited),
    "sessions": sessions,
}
with open(os.path.join(out, "summary.json"), "w") as fh:
    json.dump(summary, fh, indent=2)
    fh.write("\n")
print(json.dumps(summary, indent=2))
