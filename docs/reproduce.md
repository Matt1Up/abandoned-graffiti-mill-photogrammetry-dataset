# Reproducing the reconstruction

The images are ordinary geotagged JPEGs, so any structure-from-motion tool reads them. Below is
what to expect from *this* capture before you spend hours on it.

The scan ships solved poses for the original photos in [`../poses/mill/`](../poses/mill/), so
you can skip alignment and go straight to meshing or splatting. Re-align only if you want to
compare.

---

## What to expect

| | |
|---|---|
| images | 1,896 |
| solved | **1,888 / 1,896**, one component |
| interior photos solved | 230 / 233 |
| solver | RealityScan 2.2 |

**The interior joins the exterior.** Each of the three interior spots was entered through an
open window bay, and in the published solve 230 of the 233 interior photos sit in the same
component as the exterior. The frames shot at the window openings see both inside and out. If
your solve puts a room in its own component, those are the frames to look at.

**Repeating metal cladding is the weak spot.** The cameras that solved badly here are close-ups
of the corrugated metal panels with louvers on the upper structure (around 15:33, frames
`…0778`–`…0793`): the same panels repeat, and the matcher cannot tell one from the next. They
are listed in [`../poses/mill/suspect_cameras.txt`](../poses/mill/suspect_cameras.txt) and
left out of the published poses. Expect the same there.

**8 images did not align**, listed in [`../poses/mill/unaligned.txt`](../poses/mill/unaligned.txt).

---

## COLMAP / GLOMAP

```bash
colmap feature_extractor \
  --database_path db.db --image_path images/ \
  --ImageReader.camera_model OPENCV

colmap exhaustive_matcher --database_path db.db   # or sequential_matcher: filenames are in capture order

# either COLMAP's mapper, or GLOMAP for a much faster global solve
colmap mapper --database_path db.db --image_path images/ --output_path sparse/
```

Every frame is 4096 × 3072 from the same lens at the same settings, so
`--ImageReader.single_camera 1` looks natural. Test it before relying on it: in the published
solve RealityScan gave each photo its own focal length and distortion, and holding all photos
to one shared camera fits those poses clearly worse — the bar tags reproject at about 8 px
instead of 1.4 px, and the bar comes out 34 mm long.

---

## Scale

The published solve is metrically scaled from a 1.996 m AprilTag bar used as control points —
see *Scale* in the [README](../README.md), including the tag-numbering trap: RealityScan's
labels are not the official 36h11 IDs a detector reports.

A fresh solve of your own comes out at arbitrary scale (or GPS scale, if your tool uses the
EXIF positions) unless you detect the tags and apply the 1.996 m constraint yourself. GPS is
not a measurement of size.

---

## Gaussian splatting

`poses/mill/colmap/` is a drop-in sparse reconstruction — `cameras.txt`, `images.txt` and
`points3D.txt` (the last hosted with the images). The cameras are `FULL_OPENCV`, one per photo,
for the original photos. A pipeline that reads OpenCV distortion trains on them directly; one
that accepts only pinhole cameras needs undistorted copies first:

```bash
colmap image_undistorter --image_path images/ --input_path colmap/ --output_path undistorted/
```

Downsample to ~1600 px wide before training — nothing trains at 4096 px, and the originals are
here so you can choose. The 6 cameras in `suspect_cameras.txt` are already left out.
