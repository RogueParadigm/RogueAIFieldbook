# Model routing (reviewed 2026-09-03)

The runtime exposes only models with permissive Apache-2.0 weights. Upstream
quality claims are routing evidence, not Rogue Paradigm measurements.
`flux2-klein-4b`, `sensenova-u1.5-q8`, and `qwen-image-edit-2511` have local field
notes; the remaining profiles are unmeasured candidates.

| Need | Model alias | Why | RTX 3060 12 GB strategy |
| --- | --- | --- | --- |
| Interactive generation and editing | `flux2-klein-4b` | Unified 4-step generation, single/multi-reference editing, good prompt adherence | Model CPU offload; tested here |
| Final-quality people, identity, or multi-reference scene | `sensenova-u1.5-q8` | Unified generation/editing; stronger local anatomy, action, and reference transfer than FLUX on the bakery test | Q8_0, BF16 compute, balanced layer offload; tested at 896×1600 in 197.544s |
| Aesthetic text-to-image alternative | `z-image-turbo` | Strong photorealistic defaults and 8-step generation | Sequential CPU offload; optional |
| Posters, diagrams, dense visible text | `ernie-image-turbo` | Strong typography and structured layouts | Sequential CPU offload; optional and slow |
| Maximum open generation quality / visible text | `qwen-image-2512` | Strong realism, detail, and text rendering | Sequential CPU offload; tens of GB and very slow |
| Fallback geometry, identity, or text editing | `qwen-image-edit-2511` | Better than full-frame FLUX on the first A1 attempt; 1–3 image composition | Sequential CPU offload; focused FLUX later won; tested at 20 steps, 20m14s inference |

## Default decision

Use `flux2-klein-4b` while exploring. Use `sensenova-u1.5-q8` when a candidate
with people or multiple visual authorities is expected to survive final review.
SenseNova fixed FLUX's extra-hand/action failure in the Isekai bakery test, then
removed its own floating-utensil artifact in one successive edit. It still
re-rendered the frame, so use deterministic masked recomposition when exact
pixel preservation matters.

For a small semantic repair, try FLUX with `--focus-mask` and preserve its raw
crop. Escalate to Qwen only when focused FLUX still gets the geometry wrong. In
the Isekai A1 test, focused FLUX produced the best local window in 32.831 seconds;
the first full-frame Qwen pass was oversized and a second Qwen correction made
the geometry worse.

## Current research watchlist

- **Boogu-Image-0.1 Turbo / Edit-Turbo** (Apache-2.0, 10B): very recent unified
  family with promising photography, bilingual text, and editing. Official
  guidance supports 12 GB only through sequential offload or FP8 plus offload.
  It remains outside the runtime registry until its custom pipeline is stable in
  the installed Windows Diffusers environment.
- **FLUX.2 [klein] 9B**: higher quality than 4B but its weights use the FLUX
  non-commercial license, so it is deliberately excluded from this open-source,
  commercial-safe default stack.
- **Qwen-Image 2.0**: current public Qwen materials describe a hosted model; no
  matching open Diffusers checkpoint was available during this review. Do not
  confuse it with the Apache-2.0 `Qwen-Image-2512` checkpoint.

## Primary sources

- FLUX.2 official inference repository: https://github.com/black-forest-labs/flux2
- FLUX.2 Klein 4B model card: https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
- Qwen-Image official repository: https://github.com/QwenLM/Qwen-Image
- Qwen-Image-2512 model card: https://huggingface.co/Qwen/Qwen-Image-2512
- Qwen-Image-Edit-2511 model card: https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- ERNIE-Image official repository: https://github.com/baidu/ERNIE-Image
- Z-Image-Turbo model card: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- Boogu-Image official repository: https://github.com/boogu-project/Boogu-Image
- BiRefNet official repository: https://github.com/ZhengPeng7/BiRefNet
- SenseNova-U1.5 model card: https://huggingface.co/sensenova/SenseNova-U1.5-8B-MoT
- SenseNova-U1 official repository: https://github.com/OpenSenseNova/SenseNova-U1
