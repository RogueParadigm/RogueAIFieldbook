# MMAudio

## Verdict

**Tested** through Voice Clone Studio on 2026-09-01 and retained in the Rogue Paradigm catalog.

## Identity

| Field | Value |
| --- | --- |
| Capability | Text-to-audio and synchronized video-to-audio generation |
| Upstream | [hkchengrex/MMAudio](https://github.com/hkchengrex/MMAudio) |
| License | MIT for the source code; see the pretrained-weight caution below |
| Rogue Paradigm context | Voice Clone Studio |

## Test environment

| Field | Value |
| --- | --- |
| Host application | Voice Clone Studio at commit `fe0b40458c5adcd03bff9df5ae668d9138e369a2` |
| Integration | Voice Clone Studio `FoleyManager` and its vendored MMAudio module |
| Model | Medium 44 kHz (`mmaudio_medium_44k.pth`) |
| Operating system | Windows |
| GPU | NVIDIA GeForce RTX 3060 12 GB |
| Runtime | Python 3.12, PyTorch 2.9.1 with CUDA 12.8 |

## What we tested

A text-to-audio generation was run through Voice Clone Studio's MMAudio manager with:

- Prompt: `A heavy wooden tavern door opens, iron hinges creak, then it closes with a deep thud.`
- Negative prompt: `music, speech, voices`
- Seed: `20260901`
- Duration: 4 seconds
- Steps: 15
- CFG strength: 4.5

## Result

The run completed successfully and produced 4.017 seconds of mono audio at 44.1 kHz. After the initial model load and downloads, generation took approximately 5.26 seconds on the test GPU.

This validates text-to-audio through Voice Clone Studio. Video-to-audio conditioning has not yet been exercised in this test record.

## Licensing caution

The upstream source code is MIT licensed. The upstream project states that its pretrained models were trained with multiple third-party datasets and does not guarantee that the weights are suitable for commercial use. Commercial deployment therefore needs a separate dataset and weight-usage review; the MIT code license alone is not sufficient evidence.

## Local evidence

The generated WAV and JSON run record are kept in the ignored local evaluation directory and are not committed with model weights or caches.
