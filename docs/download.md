# Downloading

Images, the ZIP and the tie points are hosted on Hugging Face, not GitHub — this repo holds
documentation, manifests, checksums and the small pose files.

**→ https://huggingface.co/datasets/Matt1up/abandoned-graffiti-mill-photogrammetry**

```
mill/images/        1,896 images                       18.85 GB
zip/                the same 1,896, one file           18.85 GB
mill/poses/         poses, tie points, control points   0.43 GB
```

## Two ways to take the images

**One ZIP.** Simplest if your connection is good. Stored, not compressed: the JPEGs inside are
the original files, byte for byte, in sorted (capture) order under one folder,
`abandoned-graffiti-mill-images/`.

```bash
curl -LO https://huggingface.co/datasets/Matt1up/abandoned-graffiti-mill-photogrammetry/resolve/main/zip/abandoned-graffiti-mill-images.zip
sha256sum abandoned-graffiti-mill-images.zip      # must print the line below
unzip abandoned-graffiti-mill-images.zip
```

```
4bb2ed0f616fbb8f97b3cbf0f53dc8ea73a104ad3e94c901ef6245f92623662a  abandoned-graffiti-mill-images.zip
18,851,082,050 bytes
```

If it stops part-way, `curl -C - -LO <same URL>` resumes. To check every image after
unzipping:

```bash
./scripts/verify.sh --unzipped abandoned-graffiti-mill-images
```

**File by file.** Better on a flaky connection: each file is resumable and checksummed on its
own, and you can take part of the set.

```bash
pip install -U huggingface_hub

./scripts/download.sh --images   # 18.85 GB
./scripts/download.sh --zip      # 18.85 GB
./scripts/download.sh --poses    # poses, tie points, control points, 0.43 GB
./scripts/download.sh --all      # everything, 38.14 GB — the images twice, loose and zipped
./scripts/verify.sh
```

Raw CLI, without the wrapper. Run it again if it stops — finished files are skipped.

```bash
hf download Matt1up/abandoned-graffiti-mill-photogrammetry --repo-type dataset --local-dir ./data --include 'mill/images/*'
```

## What's where

```
mill/images/                 source JPEGs, original aircraft filenames, EXIF intact
                             (33 have faces or plates blurred — manifest/mill/blurred.txt)
mill/poses/colmap/           cameras.txt, images.txt, points3D.txt (the 5,710,910 tie points)
mill/poses/xmp/              RealityScan XMP sidecars, one per posed image, named after it
mill/poses/controlpoints.txt AprilTag control points — the scale reference
mill/poses/*.txt             unaligned.txt, suspect_cameras.txt
zip/                         all images in one stored ZIP
preview/                     renders of the reconstructed model
```

Everything in `mill/poses/` except `points3D.txt` is also committed to this repo under
`poses/mill/`, so you can read the camera parameters without downloading anything.
`points3D.txt` is on Hugging Face only: at 0.43 GB it is over GitHub's 100 MB file limit.

## Verifying

```bash
./scripts/verify.sh
```

Checks SHA-256 for every file you actually have and ignores the rest, so partial downloads
verify cleanly. The lists are `manifest/mill/checksums.sha256` (per image),
`manifest/mill/poses.sha256` and `manifest/zip.sha256`.

`manifest/mill/images.csv` carries filename, battery session, interior spot, size, SHA-256,
dimensions, capture time, GPS, height above takeoff and gimbal pitch for every image.
