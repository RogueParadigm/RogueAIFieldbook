# ACE-Step 1.5

## Verdict

**Tested** in ProdIA-MAX and retained in the Rogue Paradigm catalog.

## Identity

| Field | Value |
| --- | --- |
| Capability | Text-to-music generation and music editing |
| Upstream | [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5) |
| License | MIT |
| Rogue Paradigm context | ProdIA-MAX |

## What we tested

ACE-Step 1.5 was run successfully through **ProdIA-MAX**, the music-generation application used as its host software. This real-world use is the validation required for inclusion in the Fieldbook; a separate benchmark is not an admission requirement.

The exact DiT and language-model checkpoints, workflow, hardware, prompt set and timing were not recorded for this initial note. They may be added later if useful, but the entry is already considered tested.

## Optional future documentation

- Exact ACE-Step 1.5 checkpoint and revision
- Language-model checkpoint, if used
- Runtime or ComfyUI nodes and versions
- GPU, VRAM and system RAM
- Prompt, seed and generation parameters
- Duration, generation time and peak VRAM
- Audio artifacts and known failure cases

## Upstream capabilities to evaluate

The upstream model card describes text-to-music generation, reference audio, covers and repainting across several checkpoint variants. The Fieldbook can document which of these ProdIA-MAX exposes as they are used, without requiring a formal benchmark.
