# CLI reference

Set a stable script path from the repository root:

```powershell
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
python $imageGen doctor
python $imageGen models
```

## Generate

```powershell
python $imageGen generate `
  --prompt "A weathered brass compass on an explorer's desk" `
  --use-case product-mockup `
  --size 1024x1024 `
  --seed 42 `
  --out output/open-imagegen/compass.png
```

## Compose a new scene from references

Use `compose` when none of the inputs is an edit target. Assign one concise role
to every input so identity, layout, geometry, style, and lighting do not compete:

```powershell
python $imageGen compose `
  --image character-sheet.png `
  --image style-anchor.png `
  --image-role "absolute character identity and clothing" `
  --image-role "supporting brush handling only; never palette or composition" `
  --prompt "Create a new scene in a quiet fantasy bakery ..." `
  --size 944x1680 `
  --out output/open-imagegen/bakery.png
```

For a final-quality scene containing people, run the same command from the
SenseNova environment and select the registered Q8 profile:

```powershell
$python = ".local\venvs\open-imagegen-sensenova\Scripts\python.exe"
& $python $imageGen compose `
  --model sensenova-u1.5-q8 `
  --local-files-only `
  --image character-sheet.png `
  --image style-anchor.png `
  --image-role "absolute character identity and clothing" `
  --image-role "supporting rendering style only" `
  --prompt "Create a new coherent scene in a quiet fantasy bakery ..." `
  --size 896x1600 `
  --steps 50 `
  --out output/open-imagegen/bakery-final.png
```

SenseNova output edges must be multiples of 32. `--input-max-pixels 1048576`
is the tested per-reference budget on 12 GB VRAM. Use `--gguf-checkpoint` only
to override the registered cached Q8 file.

## Edit with references

```powershell
python $imageGen edit `
  --image portrait.png `
  --image jacket-reference.png `
  --image-role "edit target and absolute composition authority" `
  --image-role "jacket design authority only" `
  --prompt "Image 1 is the edit target. Replace only its jacket with the jacket from Image 2; preserve identity, pose, framing, lighting, and background." `
  --out output/open-imagegen/portrait-jacket.png
```

## Transparent output

```powershell
python $imageGen generate `
  --prompt "A clean painted game inventory icon of a round shield, isolated subject" `
  --transparent `
  --output-format png `
  --out output/open-imagegen/shield.png
```

This loads `ZhengPeng7/BiRefNet-matting` after generation. Its upstream model
uses trusted remote Python code on first load. The output contains a real alpha
channel, not a checkerboard or white backdrop. The pinned model code runs in
FP32 because its torchvision deformable-convolution operator has no BF16 CUDA
kernel on the validated Windows runtime.

For an existing image, avoid a generative pass:

```powershell
python $imageGen remove-background `
  --image source.png `
  --out output/open-imagegen/source-cutout.png
```

## Masked edit

```powershell
python $imageGen edit `
  --image room.png `
  --mask chairs-mask.png `
  --prompt "Replace only the masked chairs with dark oak chairs; preserve everything else." `
  --mask-feather 2 `
  --out output/open-imagegen/room-edited.png
```

White mask pixels select the generated edit and black pixels preserve the source.
For an existing protection mask whose white pixels mark content that must remain
exactly unchanged, add `--mask-mode preserve-white`. A masked edit keeps its
full generated pass as `<name>.raw-edit.png` by default so the seam can be tuned
without paying for another inference:

```powershell
python $imageGen composite-mask `
  --base room.png `
  --edited output/open-imagegen/room-edited.raw-edit.png `
  --mask chairs-mask.png `
  --mask-mode edit-white `
  --mask-feather 6 `
  --out output/open-imagegen/room-edited-feather6.png
```

Use `--discard-raw-edit` only for disposable masked edits.

For multiple corrections, follow the accept/reject and candidate-lineage rules
in [iterative editing](iterative-editing.md). Run one `edit` per target rather
than expanding a prompt with unrelated fixes.

### Focus a small masked correction

Use `--focus-mask` when the requested object is small relative to the full
image. The first input remains the edit target. Any later input with exactly the
same pixel dimensions is treated as a spatially aligned reference and receives
the same crop; differently sized identity or style references remain full.

```powershell
python $imageGen edit `
  --image panel.png `
  --image aligned-geometry-reference.png `
  --image-role "edit target" `
  --image-role "aligned geometry authority only" `
  --mask small-object-mask.png `
  --focus-mask `
  --focus-padding 96 `
  --size 576x768 `
  --prompt "Restore only the small missing window" `
  --out output/open-imagegen/panel-window.png
```

The output retains the full target dimensions. Its `.raw-edit` sibling contains
the rendered crop. The sidecar records `focus_region` and mask metrics. To tune
the focused result without inference, pass that recorded region back as
`X,Y,WIDTH,HEIGHT`:

```powershell
python $imageGen composite-mask `
  --base panel.png `
  --edited output/open-imagegen/panel-window.raw-edit.png `
  --mask small-object-mask.png `
  --region 51,299,272,362 `
  --mask-feather 3 `
  --out output/open-imagegen/panel-window-feather3.png
```

## Batch

Input JSONL supports flat prompt fields and per-job overrides:

```json
{"prompt":"A mossy forest altar","out":"altar.png","seed":100,"use_case":"stylized-concept"}
{"prompt":"A brass compass product shot","out":"compass.png","seed":101,"use_case":"product-mockup"}
```

```powershell
python $imageGen generate-batch `
  --input prompts.jsonl `
  --out-dir output/open-imagegen/batch
```

Jobs run serially to fit one consumer GPU. Each image receives a sibling
`.<format>.json` provenance sidecar.

## Model management and reproducibility

```powershell
python $imageGen download --model flux2-klein-4b
& $python $imageGen download --model sensenova-u1.5-q8
python $imageGen generate --local-files-only --revision <commit> ...
```

- `--quality draft|standard|high` selects model-specific steps.
- `--offload auto|model|sequential|none` controls memory strategy.
- `--force` is required to overwrite both an image and its sidecar.
- `--dry-run` validates routing, prompt, paths, and sizes without importing a
  model or touching the network.
- `--n` makes variants of one prompt with consecutive seeds; use JSONL for
  distinct assets.
