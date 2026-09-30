# Qwen-Image-Edit-2511

## Verdict

**Tested** through Open ImageGen on 2026-09-02 for a two-reference, masked
semantic micro-repair from the Isekai production workflow.

Qwen produced substantially better window geometry than the initial full-frame
FLUX.2 [klein] 4B attempt, but it did not match the scale or integration of the
hosted Isekai correction. A later mask-focused FLUX run produced a better result
in a fraction of the time. Qwen remains a slow fallback, not the default.

## Identity

| Field | Value |
| --- | --- |
| Capability | Instruction editing and multi-reference composition |
| Upstream | [Qwen/Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) |
| Checkpoint and revision | `Qwen/Qwen-Image-Edit-2511` at `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9` |
| Parameters | 20B |
| License | Apache-2.0 |
| Rogue Paradigm context | Open ImageGen Isekai production-workflow benchmark |

## Test environment

| Field | Value |
| --- | --- |
| Runtime | Python 3.12.13; PyTorch 2.6.0+cu124; Diffusers 0.39.0; Transformers 5.14.1; Accelerate 1.14.0 |
| Operating system | Windows 11 |
| GPU and VRAM | NVIDIA GeForce RTX 3060, 12 GB |
| System RAM | 127.75 GB |
| Precision and memory strategy | BF16 with sequential CPU offload |

## What we tested

The edit target was an 882×1784 painted manga panel with one missing window. A
second panel supplied the window's intended geometry and placement. Their roles
were stated separately, and a 78×170 hard edit mask limited the final composite.
Qwen generated at 512×1024 for 20 steps with true CFG 4.0 and seed `260909`.

The private source panels are not copied here. Their SHA-256 hashes are retained
in the output sidecar, while the generated raw edit, mask, hard composite, and
feathered recomposition are available in the public benchmark directory.

## Results

- The run completed locally without an out-of-memory failure.
- Inference took 1214.428 seconds (20m14s); the full command took 1236.377
  seconds (20m36s). The equivalent four-step FLUX attempt took 46.235 seconds.
- The cache occupied 57.72 GB under the Hugging Face snapshot layout.
- Qwen generated a recognisable narrow vertical window with a dark frame,
  crossbar, sill, and plausible wall perspective. FLUX's broad attempt confused
  it with a door; its tight attempt had weaker geometry.
- The window was still too large and dark compared with the Isekai hosted
  correction. A hard composite exposed a rectangular colour boundary.
- The hard composite kept 100% of pixels outside the mask byte-identical and
  changed 99.992459% inside it. A 12-pixel feather made the boundary much less
  visible; 99.246713% of pixels outside the original binary mask then remained
  identical, with a mean absolute channel delta of only 0.030182 there.
- A second 20-step Qwen pass asked only to shrink the accepted window. It took
  1067.893 seconds and instead produced a larger projecting bay-window form, so
  the candidate was rejected and never promoted in the lineage.
- Rendering a padded crop around the same mask let four-step FLUX solve the
  small-window geometry in 32.831 seconds. This became the accepted local route.

Artifacts:

- [Hard-mask result](../../examples/image-generation/isekai-benchmark/local-qwen-A1-window-restoration.png)
- [Full raw edit](../../examples/image-generation/isekai-benchmark/local-qwen-A1-window-restoration.raw-edit.png)
- [Feathered recomposition](../../examples/image-generation/isekai-benchmark/local-qwen-A1-window-restoration-feathered.png)
- [Complete benchmark and comparison](../../examples/image-generation/isekai-benchmark/README.md)
- [Rejected successive Qwen correction](../../examples/image-generation/isekai-benchmark/local-successive-A1-qwen-pass2-window-scale.png)

## Known limitations

- This was one demanding semantic repair at draft quality, not a broad suite of
  identity, typography, multi-person, or industrial-design tests.
- The upstream recipe uses 40 steps. The locally measured 20-step draft already
  required more than 20 minutes, so a full-quality run remains unmeasured.
- The pipeline performs a full generative redraw. Open ImageGen's mask is a
  deterministic post-composite; Qwen does not receive it as a native inpainting
  condition.
- Sequential CPU offload makes the model fit 12 GB VRAM but prevents an
  interactive correction loop. Try focused FLUX inference before escalating.

## Reproduction

```powershell
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
python $imageGen download --model qwen-image-edit-2511 --revision 6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9
python $imageGen edit --model qwen-image-edit-2511 --revision 6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9 --local-files-only --image <edit-target.png> --image <geometry-reference.png> --image-role "edit target and absolute authority outside the repair" --image-role "repair geometry and placement only" --mask <edit-mask.png> --mask-mode edit-white --mask-feather 0 --size 512x1024 --steps 20 --seed 260909 --prompt "Restore only the missing object; match the target rendering and keep everything else unchanged" --out output/open-imagegen/qwen-repair.png
python $imageGen composite-mask --base <edit-target.png> --edited output/open-imagegen/qwen-repair.raw-edit.png --mask <edit-mask.png> --mask-mode edit-white --mask-feather 12 --out output/open-imagegen/qwen-repair-feathered.png
```
