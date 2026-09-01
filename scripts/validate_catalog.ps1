$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$catalogPath = Join-Path $repoRoot 'catalog.json'
$catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json

if ($catalog.catalog_version -ne 1) {
    throw 'Unsupported catalog_version. Expected 1.'
}

$ids = @{}
foreach ($entry in $catalog.entries) {
    if ($entry.status -ne 'tested') {
        throw "Entry '$($entry.id)' is not tested. Only tested entries are allowed."
    }
    if ($ids.ContainsKey($entry.id)) {
        throw "Duplicate entry id '$($entry.id)'."
    }
    $ids[$entry.id] = $true

    $notePath = Join-Path $repoRoot $entry.field_note
    if (-not (Test-Path -LiteralPath $notePath -PathType Leaf)) {
        throw "Missing field note for '$($entry.id)': $($entry.field_note)"
    }
    if (-not [Uri]::IsWellFormedUriString($entry.upstream, [UriKind]::Absolute)) {
        throw "Invalid upstream URL for '$($entry.id)'."
    }
    if ($entry.tested_with.Count -lt 1) {
        throw "Entry '$($entry.id)' needs at least one test context."
    }
}

Write-Output "Catalog valid: $($catalog.entries.Count) tested entries."
