# BArtstyle REv3 + Counterfeit V3

## Verdict

**Tested** locally on 2026-09-03. BArtstyle is useful as a fast, low-strength
style-consolidation pass after a stronger model has already solved composition,
identity, and anatomy. It is not a replacement for SenseNova as the primary
scene composer: from scratch, this older SD1.5 version produces convincing
flat-color anime rendering but drops important narrative constraints.

The tested combination is the openly downloadable 2023 `REv3-CounterfeitV3`
version, not the current Krea2-V2 release. The current release and its Krea 2
base both require authenticated access and acceptance of additional terms.

## Identity

| Field | Value |
| --- | --- |
| Capability | SD1.5 style LoRA for text-to-image and img2img |
| LoRA upstream | [BArtstyle on Civitai](https://civitai.com/models/29215/bartstyle-or-blue-archive-art-style-lora-or-anime-flat-color-or-or) |
| Tested LoRA version | `REv3-LoRA-CounterFeitV3`, model version `177313`, 151,147,032 bytes |
| LoRA SHA-256 | `DB117FB8CAA5E8E6F66F7C79DABEADC8524585D30D30DD42F77B4BC169AF0F27` |
| Base checkpoint | [gsdf/Counterfeit-V3.0](https://huggingface.co/gsdf/Counterfeit-V3.0), `Counterfeit-V3.0_fix_fp16.safetensors`, 2,132,651,162 bytes |
| Base SHA-256 | `A54C944E4C04E9D9CA43468EF5B90EA0408BB6264829A4980DE79A768DF7179F` |
| License | Counterfeit V3: CreativeML Open RAIL-M; LoRA: Civitai model permissions, requiring a separate shipping review |
| Rogue Paradigm context | Isekai style-retention and from-scratch benchmark |

The Fieldbook does not mirror either weight file. Civitai's model permissions
should be reviewed before product use; the listing does not grant unrestricted
commercial use under the same terms as an Apache-2.0 checkpoint.

## Test environment

| Field | Value |
| --- | --- |
| Runtime | Python 3.12.13; PyTorch 2.8.0+cu128; Diffusers 0.40.0; Transformers 5.16.1; PEFT 0.20.0 |
| Operating system | Windows 11 |
| GPU and VRAM | NVIDIA GeForce RTX 3060, 12 GB |
| Precision | FP16 |
| Scheduler | DPM-Solver++ with Karras sigmas |

## Results

| Run | Settings | Inference | Observation |
| --- | --- | ---: | --- |
| Low-strength img2img | 576×1024, denoise `0.22`, LoRA `0.60`, 30 requested steps, seed `260917` | 6.095 s | Preserved the two-hand action, glasses, ponytail, clothing, bag, lighting split, and bakery composition while making the rendering cleaner and flatter |
| Medium-strength img2img | 576×1024, denoise `0.32`, LoRA `0.60`, 30 requested steps, seed `260918` | 6.130 s | Stronger stylization with two hands still present, but more face and hair reinterpretation |
| From scratch A | 576×1024, LoRA `0.65`, 30 steps, seed `260919` | 18.793 s | Strong flat-color style and plausible visible hand; replaced the price card with a menu-like booklet and simplified the bakery into a café interior |
| From scratch B | 576×1024, LoRA `0.65`, 30 steps, seed `260920` | 17.643 s | Strong flat-color style and no extra limb, but omitted the price-card interaction and most bakery storytelling |

The img2img tests used the accepted SenseNova scene with its corrected left
background as the source. Both runs redrew the full frame; this is semantic
style retention, not pixel invariance.

Artifacts:

- [Low-strength img2img](../../examples/image-generation/isekai-benchmark/local-bartstyle-rev3-bakery-low.png)
- [Medium-strength img2img](../../examples/image-generation/isekai-benchmark/local-bartstyle-rev3-bakery-medium.png)
- [From-scratch seed 260919](../../examples/image-generation/isekai-benchmark/local-bartstyle-rev3-bakery-t2i-seed-260919.png)
- [From-scratch seed 260920](../../examples/image-generation/isekai-benchmark/local-bartstyle-rev3-bakery-t2i-seed-260920.png)

## Known limitations

- This is an old SD1.5 LoRA. Scene understanding and constraint following are
  materially weaker than the modern instruction-editing models in the catalog.
- With the current Diffusers/Transformers combination, the legacy Kohya text-
  encoder block fails adapter conversion. The benchmark therefore loaded the
  UNet portion only. The visual style transfers, but this is not a complete
  reproduction of the creator's original inference stack.
- Low denoise preserves identity semantically, not exactly. For approved pixels,
  keep using masks and deterministic recomposition.
- The from-scratch samples avoided extra hands by omitting or cropping the second
  hand. They do not prove reliable two-hand interaction.
- The current Krea2-V2 variant remains a separate candidate. It cannot be loaded
  into Counterfeit, FLUX, or SenseNova because LoRA architecture must match its
  base model.

## Recommended role

Use BArtstyle after scene construction, not before it:

1. Compose and correct the scene with SenseNova or another reference-aware
   instruction model.
2. Apply BArtstyle img2img at denoise `0.20-0.30` and LoRA weight `0.55-0.65`.
3. Reject any candidate that changes hand count, action roles, face identity, or
   protected props.
4. Recompose protected regions when byte-exact preservation is required.
