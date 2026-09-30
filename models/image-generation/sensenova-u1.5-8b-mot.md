# SenseNova-U1.5-8B-MoT Q8

## Verdict

**Tested** through Open ImageGen on 2026-09-03. This is the preferred local
quality profile for people, identity-sensitive scene creation, and successive
instruction edits. It is materially slower than FLUX.2 [klein] 4B, but the
Isekai two-reference scene had coherent anatomy and the follow-up edit removed
an unwanted object while retaining the intended action.

## Identity

| Field | Value |
| --- | --- |
| Capability | Text-to-image, instruction editing, multi-reference scene composition |
| Upstream | [OpenSenseNova/SenseNova-U1](https://github.com/OpenSenseNova/SenseNova-U1) and [model card](https://huggingface.co/sensenova/SenseNova-U1.5-8B-MoT) |
| Model revision | `sensenova/SenseNova-U1.5-8B-MoT` at `19bc874ef6ffc97fda9837b40fc1d1301806158a` |
| Runtime revision | `OpenSenseNova/SenseNova-U1` at `f97964a6e54b0abf92aa2db849af4e942bb2ff08` |
| Quantization | Community Q8_0 GGUF, 21,174,689,152 bytes, SHA-256 `61b227f036b7e8094cceab888c23b17a3fffc32d6182b039836d7cb31d688fe2` |
| License | Apache-2.0 |
| Rogue Paradigm context | Open ImageGen / Isekai production-workflow benchmark |

The official BF16 checkpoint is approximately 35.1 GB. The tested Q8_0 file is
distributed by `realrebelai/SenseNova-U1.5-8B_GGUFs`, which the official
SenseNova repository links from its low-memory guidance. The Fieldbook does not
mirror either set of weights.

## Test environment

| Field | Value |
| --- | --- |
| Runtime | Python 3.12.13; PyTorch 2.8.0+cu128; Transformers 5.16.1; Diffusers 0.40.0; SenseNova-U1 0.1.0 |
| Operating system | Windows 11 |
| GPU and VRAM | NVIDIA GeForce RTX 3060, 12 GB |
| System RAM | 127.75 GB |
| Precision and memory strategy | Q8_0 weights, BF16 compute, SDPA attention, balanced layer offload |

## What we tested

- New 896×1600 color-manga bakery scene from separate character-identity and
  rendering-style references, 50 steps, seed `260905`.
- Successive 896×1600 edit of that generated scene, removing one floating
  spatula while preserving the heroine, action, composition, and lighting,
  50 steps, seed `260914`.
- Offline CLI integration with two references at 448×800 and one smoke-test
  step, proving the registered profile resolves local model resources and the
  explicit GGUF without network access.
- Offline pure text-to-image CLI smoke at 448×800, proving the same registered
  profile covers both generation and editing code paths.

## Results

| Run | Resolution | Inference | Observation |
| --- | ---: | ---: | --- |
| Two-reference scene | 896×1600 | 197.544 s | Correct two-arm/two-hand anatomy; bread and price card have distinct hands; strong identity, outfit, bag, palette, and bakery transfer; one floating spatula remained |
| Successive object removal | 896×1600 | 191.411 s | Floating spatula removed and wall/window reconstructed; two hands and intended action retained; the whole frame was subtly re-rendered |
| Integrated CLI smoke | 448×800 | 13.638 s | Offline two-reference path completed through `open_imagegen.py` |

The main scene run reserved 7.40 GiB at its measured generation peak and loaded
the model in 13.419 seconds. The integrated correction took 227.168 seconds for
the full command, including loading, inference, output, provenance, and hashing.

Artifacts:

- [First SenseNova bakery scene](../../examples/image-generation/isekai-benchmark/local-sensenova-u1.5-casual-bakery.png)
- [Accepted successive correction](../../examples/image-generation/isekai-benchmark/local-sensenova-u1.5-casual-bakery-v2.png)
- [Isekai benchmark](../../examples/image-generation/isekai-benchmark/README.md)

## Known limitations

- The first candidate still invented a floating utensil. Visual QA and targeted
  correction remain mandatory.
- A full-frame instruction edit preserves semantics well but is not pixel
  invariant. Use a mask and deterministic recomposition when approved pixels
  must remain byte-identical.
- The generated price card contains unreadable pseudo-writing. The prompt asked
  for no readable text, but blank-sign control was not achieved.
- Q8 GGUF loading in the tested upstream revision reads arithmetic dtype from
  byte-quantized weights in two flow-matching modules. Open ImageGen applies a
  narrowly scoped runtime compatibility patch that uses `compute_dtype`.
- The 21.2 GB Q8 checkpoint and roughly 30 GB observed process RAM are much
  heavier than the interactive FLUX profile.
- Upstream documentation itself notes that small faces, hands, and limbs can
  remain unstable. This successful sample does not make anatomy guaranteed.

## Reproduction

Use the isolated environment because SenseNova pins a different PyTorch stack
than the lightweight default profile:

```powershell
pwsh -File .agents/skills/open-imagegen/scripts/setup-sensenova.ps1
$python = ".local\venvs\open-imagegen-sensenova\Scripts\python.exe"
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
& $python $imageGen download --model sensenova-u1.5-q8
& $python $imageGen compose --model sensenova-u1.5-q8 --local-files-only --image identity.png --image style.png --image-role "absolute identity" --image-role "rendering style only" --prompt "Create a new coherent scene" --size 896x1600 --steps 50 --seed 260905 --out output/open-imagegen/scene.png
```
