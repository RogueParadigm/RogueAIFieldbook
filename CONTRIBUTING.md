# Contributing

Rogue AI Fieldbook accepts evidence-backed field notes, not speculative recommendations.

## Add a model

1. Run the model successfully in a named project or controlled evaluation.
2. Copy `templates/model-field-note.md` into the appropriate capability directory.
3. Record exact revisions and hardware whenever they are known.
4. Add the entry to `catalog.json` with `status` set to `tested`.
5. Run `pwsh -File scripts/validate_catalog.ps1`.

If a detail was not recorded, say so. Never copy an upstream benchmark into the Results section as if Rogue Paradigm measured it.

## Add a workflow

Use `templates/workflow-field-note.md`. Remove API keys, credentials, local absolute paths, private prompts and model weights before committing a workflow.

## Third-party licenses

Record the upstream license for every entry and re-check it for the exact checkpoint used. Do not commit third-party weights or code unless their license clearly permits redistribution and the repository genuinely needs them.
