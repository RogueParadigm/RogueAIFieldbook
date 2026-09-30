# FLUX.2 [klein] 4B

## Verdict

**Tested** through Open ImageGen on 2026-09-02. It is the current local default:
fast enough for an interactive workflow, capable of both generation and
instruction-based editing, and Apache-2.0 licensed.

## Identity

| Field | Value |
| --- | --- |
| Capability | Text-to-image, single-reference editing, multi-reference editing |
| Upstream | [black-forest-labs/flux2](https://github.com/black-forest-labs/flux2) and [model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) |
| Checkpoint and revision | `black-forest-labs/FLUX.2-klein-4B` at `e7b7dc27f91deacad38e78976d1f2b499d76a294` |
| License | Apache-2.0 |
| Rogue Paradigm context | Open ImageGen controlled evaluation |

## Test environment

| Field | Value |
| --- | --- |
| Runtime | Python 3.12.13; PyTorch 2.6.0+cu124; Diffusers 0.39.0; Transformers 5.14.1; Accelerate 1.14.0 |
| Operating system | Windows 11 |
| GPU and VRAM | NVIDIA GeForce RTX 3060, 12 GB, compute capability 8.6 |
| System RAM | 127.75 GB |
| Precision and memory strategy | BF16 with model CPU offload |

## What we tested

- A four-step 1024×1024 fantasy inventory-item generation at seed `260902`.
- A four-step single-image instruction edit at seed `260903`, changing only
  liquid and glow from green to blue while requesting preservation of geometry,
  materials, framing, background, and lighting.
- A two-reference 944×1680 Isekai scene composed from separate character
  identity and style authorities at seed `260905`.
- A source-resolution Isekai environment revision using an existing character
  protection mask at seed `260906`.
- Two 512×1024 attempts to restore one missing background window with broad and
  tight edit masks at seeds `260907` and `260908`.
- A rejected full-frame scale-correction pass at seed `260910` and an accepted
  automatic mask-focused repair at seed `260912`.
- Reloading the exact revision with `--local-files-only`.
- JSON provenance sidecars containing prompt, model revision, seed, runtime,
  hashes, timing, and memory strategy.

The benchmark now covers multi-reference composition and both edit-mask
polarities. Batches and alternative generation profiles remain structurally
tested but do not yet have separate visual field notes.

## Results

| Run | Resolution | Inference | Recorded pipeline stage | Observation |
| --- | ---: | ---: | ---: | --- |
| Generation | 1024×1024 | 22.048 s | 22.759 s | Clean centered silhouette, coherent glass/brass/parchment materials, correct blank label and no visible text or watermark |
| Instruction edit | 1024×1024 | 34.039 s | 34.785 s | Liquid and emitted glow became sapphire blue; bottle design, label, viewpoint, and neutral background remained strongly consistent |
| Two-reference scene | 944×1680 | 82.166 s | 83.036 s | Coherent bakery panel with strong identity/style transfer; incorrect utensil action and pseudo-text remained |
| Protected background edit | 1664×944 | 85.325 s | 89.267 s | Environment changed while every white-mask protection pixel was restored exactly |
| Tight local window repair | 512×1024 | 46.235 s | 49.046 s | Recognisable window, exact hard-mask locality, but visible rectangular seam |
| Focused local window repair | 576×768 crop, restored to 882×1784 | 32.831 s | 35.627 s | Best local A1 result: correct small-window semantics and plausible integration; 3px recomposition retained 99.797145% exact protected pixels |

The local Hugging Face cache occupied approximately 22.11 GiB after download,
counting the cache's blob and snapshot layout as reported by Windows file
enumeration. This is a disk observation, not a VRAM figure. For these initial
artifacts, the sidecar's `total_command_seconds` began after pipeline loading;
newer skill runs additionally record the whole command and a distinct
`generation_stage_seconds` value.

Artifacts:

- [Generated potion](../../examples/image-generation/flux2-klein-4b/generated-potion.png)
- [Edited blue variant](../../examples/image-generation/flux2-klein-4b/edited-potion-blue.png)
- [Isekai production-workflow benchmark](../../examples/image-generation/isekai-benchmark/README.md)
- Each PNG has a sibling `.png.json` provenance record.

## Known limitations

- Instruction editing is a generative redraw. The result preserved the requested
  structure well, but exact unchanged pixels require a supplied mask and the
  skill's deterministic final composite.
- Multi-reference identity is useful but not exact: the Isekai test retained the
  heroine's major identifiers while narrowing the face and missing one action.
- Hard-mask compositing guarantees pixel locality, not a visually seamless or
  geometrically correct patch. Full-frame FLUX failed the strict A1 micro-edit
  bar, while focused inference around the same mask passed the local visual gate.
- Visible typography, long batches, and native inpainting remain unevaluated.
- The distilled model is designed for four steps; selecting more steps is not a
  substitute for a larger specialist checkpoint.
- The cache is large even though inference fits the 12 GB GPU through offload.

## Reproduction

Run from the repository root after downloading the pinned revision:

```powershell
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
python $imageGen download --model flux2-klein-4b --revision e7b7dc27f91deacad38e78976d1f2b499d76a294
python $imageGen generate --model flux2-klein-4b --revision e7b7dc27f91deacad38e78976d1f2b499d76a294 --local-files-only --size 1024x1024 --seed 260902 --prompt "A single ornate alchemical potion bottle with a round glass body filled with luminous emerald liquid, an aged-brass stopper and filigree, and a blank parchment label; centered premium fantasy game inventory render on a neutral studio background; no text, logo, watermark, frame, or crop" --out examples/image-generation/flux2-klein-4b/generated-potion.png
python $imageGen edit --model flux2-klein-4b --revision e7b7dc27f91deacad38e78976d1f2b499d76a294 --local-files-only --image examples/image-generation/flux2-klein-4b/generated-potion.png --seed 260903 --prompt "Image 1 is the edit target. Change only the potion liquid and emitted glow from emerald green to deep luminous sapphire blue. Preserve the bottle silhouette, glass, brass, stopper, parchment label, camera, framing, background, and lighting." --out examples/image-generation/flux2-klein-4b/edited-potion-blue.png
```

The committed sidecars preserve the exact augmented prompts used for the
recorded outputs.
