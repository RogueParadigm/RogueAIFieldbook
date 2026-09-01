# Qwen3-TTS

## Verdict

**Tested** in VoiceBox and retained in the Rogue Paradigm catalog.

## Identity

| Field | Value |
| --- | --- |
| Capability | Text-to-speech, voice design and voice cloning |
| Upstream | [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) |
| License | Apache-2.0 |
| Rogue Paradigm context | VoiceBox and Voice Clone Studio |

## What we tested

Qwen3-TTS was run successfully through **VoiceBox**, the local voice synthesis studio used as its host application. This real-world use is the validation required for inclusion in the Fieldbook; a separate benchmark is not an admission requirement.

### Original voice creation with VoiceDesign

The intended Rogue Paradigm use case was validated through **Voice Clone Studio** on 2026-09-01 with `Qwen3-TTS-12Hz-1.7B-VoiceDesign`. This mode creates an original timbre from a natural-language description and does not use a preset speaker.

Voice description:

> Create an original French female voice in her mid-thirties. She has a warm, clear, slightly husky timbre and the confident personality of an experienced tavern keeper. Her delivery is lively and welcoming, with a brisk natural pace, a smile in the voice, expressive emphasis, and absolutely no slow or sleepy delivery.

The test produced 5.44 seconds of mono French speech at 24 kHz on an NVIDIA GeForce RTX 3060 12 GB with PyTorch 2.9.1/CUDA 12.8. The first run, including download, model load and generation, took approximately 52 seconds.

### Preset-voice comparison

Earlier smoke tests used CustomVoice, which selects a voice supplied by Qwen rather than creating a new one. They are retained here to make the distinction explicit:

| Checkpoint | Style instruction | Output | First-run total |
| --- | --- | --- | --- |
| `Qwen3-TTS-12Hz-0.6B-CustomVoice` | None | 6.24 s at 24 kHz | ~63 s |
| `Qwen3-TTS-12Hz-1.7B-CustomVoice` | Energetic, brisk French tavern keeper | 5.76 s at 24 kHz | ~61 s |

Both runs used an NVIDIA GeForce RTX 3060 12 GB with PyTorch 2.9.1/CUDA 12.8. The 1.7B instruction was:

> Speak in energetic, brisk French, with a warm tavern-keeper personality. Keep a lively pace, use natural emphasis, and avoid slow or sleepy delivery.

For this sentence and seed, the instructed 1.7B CustomVoice output was 0.48 seconds, or about 7.7%, shorter than the uninstructed 0.6B output. This timing is descriptive rather than a general performance benchmark; delivery quality remains a listening judgment.

### Mode guide

| Goal | Qwen3-TTS mode |
| --- | --- |
| Create a new voice from a written description | VoiceDesign 1.7B |
| Clone a specific recorded voice | Base 0.6B or 1.7B with reference audio and transcript |
| Use and style a voice supplied by Qwen | CustomVoice 0.6B or 1.7B |

The exact VoiceBox checkpoint and environment were not recorded for the initial note. They may be added later if useful, but the entry is already considered tested.

## Optional future documentation

- Exact checkpoint and revision
- Runtime and dependency versions
- GPU, VRAM and system RAM
- French and English sample prompts
- Time to first audio and total generation time
- Voice cloning or voice design mode used
- Known failure cases

## Upstream capabilities to evaluate

The upstream project publishes 0.6B and 1.7B variants for custom voices, voice design and voice cloning, with streaming support. These details can help identify the exact VoiceBox configuration later; they are not additional acceptance criteria.
