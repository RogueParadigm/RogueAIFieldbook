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

It was subsequently validated through **Voice Clone Studio** on 2026-09-01 using `Qwen3-TTS-12Hz-0.6B-CustomVoice`, the `Ryan` speaker and French text. The run produced 6.24 seconds of 24 kHz audio on an NVIDIA GeForce RTX 3060 12 GB with PyTorch 2.9.1/CUDA 12.8. The first run, including model download and load, completed in approximately 63 seconds.

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
