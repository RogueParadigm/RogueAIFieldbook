# BiRefNet Matting

## Verdict

**Tested** through Open ImageGen on 2026-09-02 as the transparent-output
post-processor for generated images and existing raster assets.

## Identity

| Field | Value |
| --- | --- |
| Capability | Foreground segmentation and alpha matting |
| Upstream | [ZhengPeng7/BiRefNet](https://github.com/ZhengPeng7/BiRefNet) |
| Checkpoint and revision | `ZhengPeng7/BiRefNet-matting` at `eccde0a8cbdce7ac5fecfeb06340fe7b949e85d9` |
| License | MIT |
| Rogue Paradigm context | Open ImageGen transparent cutout evaluation |

## Test environment

| Field | Value |
| --- | --- |
| Runtime | Python 3.12.13; PyTorch 2.6.0+cu124; Transformers 5.14.1; torchvision 0.21.0+cu124 |
| Operating system | Windows 11 |
| GPU and VRAM | NVIDIA GeForce RTX 3060, 12 GB |
| System RAM | 127.75 GB |
| Precision | FP32 |

## What we tested

The generated potion sample was passed through the pinned matting checkpoint at
1024×1024. Before execution, the checkpoint's required remote Python files were
inspected for process, network, and file-write behavior. Open ImageGen pins the
exact revision and uses `trust_remote_code=True` because Transformers requires it
for this architecture.

## Results

- Model inference took 3.175 seconds; the complete first loaded command took
  12.691 seconds.
- The resulting 1024×1024 PNG was RGBA, with alpha extrema `0..254` and all four
  corner pixels at alpha 0.
- Visual inspection retained the glass bottle's fine silhouette and glow while
  removing the neutral studio backdrop.
- The cached checkpoint occupied approximately 0.82 GiB under the Hugging Face
  cache layout.

Artifact: [transparent potion cutout](../../examples/image-generation/flux2-klein-4b/generated-potion-cutout.png).

## Known limitations

- The upstream custom model code is executed locally. The revision is pinned and
  was inspected for this evaluation, but updating it requires a fresh review.
- Torchvision's CUDA deformable-convolution implementation failed with BF16 in
  this Windows stack. FP32 is therefore intentional and fits the tested GPU.
- Transparent and reflective subjects can contain meaningful semi-transparent
  pixels. Final compositing should be inspected over both light and dark colors.

## Reproduction

```powershell
$imageGen = ".agents\skills\open-imagegen\scripts\open_imagegen.py"
python $imageGen remove-background --image examples/image-generation/flux2-klein-4b/generated-potion.png --out examples/image-generation/flux2-klein-4b/generated-potion-cutout.png
```
