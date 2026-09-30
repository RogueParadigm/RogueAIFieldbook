# Local image prompting

## Structure

Order prompts as scene/backdrop, subject, material and visual details,
composition, lighting, then constraints. Include the intended asset use when it
changes layout or polish.

Use only useful labeled lines:

```text
Use case: <photorealistic-natural | product-mockup | ui-mockup |
  infographic-diagram | scientific-educational | ads-marketing |
  productivity-visual | logo-brand | illustration-story |
  stylized-concept | historical-scene>
Asset type: <where this will be used>
Primary request: <the user's request>
Input images: <Image 1: edit target; Image 2: style reference>
Scene/backdrop: <environment>
Subject: <main subject>
Style/medium: <photo, illustration, 3D, painted texture, etc.>
Composition/framing: <viewpoint, crop, placement, negative space>
Lighting/mood: <lighting and atmosphere>
Color palette: <only when requested or contextually required>
Materials/textures: <surface detail>
Text (verbatim): "<exact text>"
Constraints: <must preserve / must include>
Avoid: <negative constraints>
```

## Specificity

- Normalize a detailed prompt without inventing new creative requirements.
- For a generic prompt, add only composition, intended-use, material, or lighting
  detail that materially improves the result.
- Do not invent characters, props, brands, slogans, palettes, or narrative beats.
- For photorealism, request real texture and concrete camera/framing language.
- For visible text, quote it exactly, require it once, and spell unusual words
  letter-by-letter if accuracy matters. Inspect the final pixels; a prompt is not
  proof of correct typography.

## Editing and references

- Label every input by index and role.
- Use `compose` when all images are references for a new scene. Use `edit` only
  when Image 1 is an existing target whose scene must change.
- Express reference roles with repeated `--image-role` flags. Separate the five
  useful authorities: layout, identity, geometry, style, and lighting. State
  what each supporting reference must *not* control when conflicts are likely.
- Repeat `change only X; keep Y unchanged` on every edit iteration.
- Use the first `--image` as the edit target. Additional images are references.
- For identity preservation, explicitly lock face, proportions, hair, pose,
  expression, clothing elements that must remain, and background as applicable.
- For compositing, specify which subject moves into which base image and require
  matched scale, perspective, illumination, and shadow direction.
- Prefer a mask plus deterministic composite when unchanged pixels matter more
  than seamless global relighting.
- Use `--mask-mode preserve-white` for protection masks. This exactly restores
  the white region from Image 1 after inference; feather only when a soft seam is
  desired.

## FLUX.2 Klein specifics

- Front-load the subject because word order matters.
- Prefer 40–70 words of descriptive narrative for complex scenes.
- Describe lighting and atmosphere explicitly.
- Distilled Klein is a four-step model. Raising steps is not a reliable substitute
  for choosing a stronger specialist model.
