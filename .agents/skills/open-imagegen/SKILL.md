---
name: open-imagegen
description: Generate or edit raster images entirely on the local machine with open-source models. Use for photos, illustrations, game assets, mockups, image-to-image edits, multi-reference composition, masks, batches, and transparent cutouts when cloud image generation is unwanted or unavailable. Do not use for SVG/vector/code-native graphics or trivial deterministic image transforms.
---

# Open ImageGen

Generate and edit project-ready images locally. Use the bundled
`scripts/open_imagegen.py`; do not create one-off inference scripts.

## Workflow

1. Classify the request as generation, composition from references, or editing.
   Images supplied only for style, identity, geometry, lighting, product, or
   layout guidance are references; an image whose content must change is the
   edit target.
2. Read [model routing](references/model-routing.md) only when the default model
   is unsuitable or the user prioritizes typography, maximum quality, or a
   specialized edit.
3. Run `python scripts/open_imagegen.py doctor` before the first live inference
   in an environment. The default cache is the repo's `.local/huggingface/`.
4. Shape the prompt with [prompting guidance](references/prompting.md). Preserve
   specific user instructions; augment generic prompts only when useful.
5. Use `flux2-klein-4b` for interactive drafts on the validated RTX 3060 12 GB
   machine. Route final-quality scenes containing people, identity-sensitive
   multi-reference composition, and difficult successive edits to the tested
   `sensenova-u1.5-q8` profile. For a small masked target, try focused FLUX
   before a heavyweight full-frame pass. Reserve `qwen-image-edit-2511` for
   geometry or text failures that survive those paths; a Qwen draft can take
   20+ minutes.
6. Use one live CLI invocation per requested asset, or `generate-batch` for
   distinct generation jobs. The runtime serializes GPU work and records a JSON
   provenance sidecar beside every output.
7. Inspect every result visually. Check subject, composition, visible text,
   invariants, and unwanted artifacts. Iterate with one targeted change while
   repeating edit invariants. For partial results or more than one correction,
   read [iterative editing](references/iterative-editing.md) and advance only
   accepted candidates.
8. Keep final project assets in the current workspace. Never overwrite existing
   files unless the user explicitly requested replacement; otherwise choose a
   versioned sibling filename.
9. Report the final path, model alias, seed, effective prompt, and whether
   BiRefNet transparency post-processing was used.

## Commands

Use [CLI reference](references/cli.md) for exact flags and examples.

- Generate: `python scripts/open_imagegen.py generate --prompt "..." --out output/open-imagegen/name.png`
- Compose from references: `python scripts/open_imagegen.py compose --image identity.png --image style.png --image-role "absolute identity" --image-role "supporting style" --prompt "create a new scene ..." --out output/open-imagegen/scene.png`
- Edit: `python scripts/open_imagegen.py edit --image source.png --prompt "change only ..." --out output/open-imagegen/name-edit.png`
- Repeat `--image` and `--image-role` in matching semantic order. Keep layout,
  identity, geometry, style, and lighting authority separate when possible.
- Transparent cutout: add `--transparent` and use PNG or WebP. This runs the
  MIT-licensed BiRefNet matting model after generation and preserves real alpha.
- Existing-image cutout: use `remove-background --image source.png --out cutout.png`
  to avoid regenerating or visually drifting the source.
- Masked edit: pass `--mask mask.png`. White edits by default; add
  `--mask-mode preserve-white` for protection masks where white must remain
  byte-identical to the source. This is a deterministic final composite, not
  native masked diffusion.
- Masked edits retain a `.raw-edit` sibling by default. Use `composite-mask` to
  retune mask polarity or feathering without rerunning inference. Discard the raw
  pass only for disposable outputs.
- When the editable object is small in the full frame, add `--focus-mask`. The
  runtime crops a padded region, crops same-sized aligned references with it,
  renders at the requested model resolution, and restores the result into the
  full target. Use `--focus-padding` to retain enough scene context.

## Operational constraints

- All image inference is local after explicit model download. No hosted image
  API or API key is used.
- A first run may download many gigabytes from Hugging Face. Do not claim offline
  readiness until `doctor` reports the chosen model cached or a live run succeeds.
- SenseNova requires its isolated runtime from `scripts/setup-sensenova.ps1` and
  a 21.2 GB Q8 checkpoint. Its tested 896×1600 pass took about 3.3 minutes; it is
  a quality profile, not an interactive default.
- `--transparent` trusts the upstream BiRefNet model repository's Python code;
  disclose this before first use in a new environment.
- The default 1024px output is the reliable production baseline for 12 GB VRAM.
  Use larger sizes deliberately and inspect for memory pressure and quality.
- Prefer focused inference over repeated full-frame passes when a masked target
  would otherwise occupy too few model pixels.
- Treat optional model profiles as candidates until their field note says they
  were tested on this machine. Qwen-Image-Edit-2511 is locally validated but is
  not interactive on this GPU. Never present upstream benchmarks as local results.
