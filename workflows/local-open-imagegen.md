# Local Open ImageGen

## Purpose

Provide a Codex image-generation skill backed only by locally executed,
permissively licensed open-source checkpoints. The workflow covers generation,
instruction editing, multi-reference inputs, masks, batches, reproducibility,
and real transparent output without a hosted image API.

## Tested stack

| Component | Version or revision |
| --- | --- |
| Skill | [`.agents/skills/open-imagegen/`](../.agents/skills/open-imagegen/SKILL.md) |
| Default model | FLUX.2 [klein] 4B at `e7b7dc27f91deacad38e78976d1f2b499d76a294` |
| Final-quality unified model | SenseNova-U1.5-8B-MoT at `19bc874ef6ffc97fda9837b40fc1d1301806158a`, Q8_0 GGUF |
| Complex-edit specialist | Qwen-Image-Edit-2511 at `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9` |
| Alpha matting | BiRefNet Matting at `eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9` |
| Runtime | Python 3.12.13; PyTorch 2.6.0+cu124; Diffusers 0.39.0; Transformers 5.14.1; Accelerate 1.14.0 |
| Tests | Fifteen unit tests, skill-package validation, catalog validation, offline generation/edit artifacts, live FLUX and SenseNova multi-reference composition, successive editing, masked and focused-edit inference, live alpha-matting inference, and end-to-end transparent generation |

## Hardware

- Windows 11
- NVIDIA GeForce RTX 3060 with 12 GB VRAM
- Intel Core i7-13700K
- 127.75 GB system RAM

## Installation

Use a Python environment with a CUDA-enabled PyTorch and matching torchvision
build. From the repository root:

```powershell
pwsh -File .agents/skills/open-imagegen/scripts/setup.ps1 -InstallPythonPackages
python .agents/skills/open-imagegen/scripts/open_imagegen.py download --model flux2-klein-4b
```

The first command deliberately does not pin PyTorch or torchvision because their
builds must match the local CUDA environment. Model caches live in
`.local/huggingface/` by default and are excluded from Git.

SenseNova pins PyTorch 2.8 and uses a separate environment:

```powershell
pwsh -File .agents/skills/open-imagegen/scripts/setup-sensenova.ps1
$python = ".local\venvs\open-imagegen-sensenova\Scripts\python.exe"
& $python .agents/skills/open-imagegen/scripts/open_imagegen.py download --model sensenova-u1.5-q8
```

## Usage

```powershell
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
python $imageGen doctor
python $imageGen generate --prompt "A weathered brass compass on an explorer's desk" --out output/open-imagegen/compass.png
python $imageGen edit --image source.png --prompt "Change only the jacket to dark red; preserve identity, pose, framing, lighting, and background" --out output/open-imagegen/source-red.png
python $imageGen compose --image identity.png --image style.png --image-role "absolute character identity" --image-role "supporting rendering style only" --prompt "Create a new coherent scene" --out output/open-imagegen/new-scene.png
python $imageGen edit --image panel.png --image style.png --mask protection.png --mask-mode preserve-white --prompt "Change only the environment" --out output/open-imagegen/panel-environment.png
python $imageGen composite-mask --base panel.png --edited output/open-imagegen/panel-environment.raw-edit.png --mask protection.png --mask-mode preserve-white --out output/open-imagegen/panel-recomposed.png
python $imageGen remove-background --image source.png --out output/open-imagegen/source-cutout.png
```

See the skill's [CLI reference](../.agents/skills/open-imagegen/references/cli.md)
for reference-authority roles, mask polarity, raw-edit recomposition, variants,
batches, model selection, and offline revision pinning.

## Successive corrections

Treat every pass as a candidate, not an automatic improvement. Correct semantic
presence and geometry before style or seam blending. Feed only the latest
accepted composite into the next pass, keep rejected artifacts as evidence, and
change one variable per retry. Masked commands now record editable-region change
and protected-region exactness in `mask_metrics`; use 100% protected exactness as
the hard-mask production gate.

When the target is small, use `--focus-mask` before adding another full-frame
pass or escalating models. The A1 window occupied too few pixels at 512×1024:
successive FLUX and Qwen corrections both worsened it. Automatic focused FLUX
rendered a 272×362 source crop at 576×768 and produced the best local result in
32.831 seconds. `composite-mask --region` then compared hard, 3px, and 6px
recompositions without another inference.

The full decision procedure is in the skill's
[iterative-editing reference](../.agents/skills/open-imagegen/references/iterative-editing.md).

For a full-frame scene with a person and two visual authorities, SenseNova-U1.5
Q8 produced the stronger final-quality candidate: exactly two functional hands
and the requested bread-tasting action in 197.544 seconds. A second 191.411-second
pass removed its one floating-utensil artifact while retaining the anatomy and
action. FLUX remains the faster exploration model.

## Expected result

Every successful command writes an image and a sibling JSON provenance file.
The default 1024×1024 FLUX generation completed in 22.048 seconds of inference;
the tested instruction edit completed in 34.039 seconds. BiRefNet matting added
3.175 seconds of inference after model load. A separate integrated 512×512
`generate --transparent` smoke test completed in 25.715 seconds total, produced
RGBA extrema `0..255`, and returned alpha 0 at all four corners.

In the Isekai masked micro-repair, Qwen-Image-Edit-2511 completed 20 steps at
512×1024 in 1214.428 seconds. It generated better window geometry than FLUX but
remained oversized and needed a feathered deterministic recomposition to hide a
hard patch boundary. See the [benchmark](../examples/image-generation/isekai-benchmark/README.md)
and [Qwen field note](../models/image-generation/qwen-image-edit-2511.md).

## Known limitations

- FLUX.2 [klein] 4B, SenseNova-U1.5 Q8, Qwen-Image-Edit-2511, and BiRefNet have
  completed local field-note admission. ERNIE-Image, Z-Image, and Qwen-Image-2512 remain
  researched routing candidates rather than local benchmark claims.
- Qwen-Image-Edit-2511 does run through sequential CPU offload, but its 57.72 GB
  cache and 20+ minute draft latency make it a poor default on this GPU.
- Masked editing uses a deterministic composite after a full instruction edit;
  it is not native diffusion inpainting.
- Deterministic recomposition can prove pixel preservation, but it cannot make a
  semantically wrong or poorly blended generated patch correct. In the
  [Isekai benchmark](../examples/image-generation/isekai-benchmark/README.md),
  large protected-area revision passed while a tiny window restoration did not.
- Image quality remains prompt- and seed-dependent. Visual QA is mandatory.
