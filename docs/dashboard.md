# Cohort dashboard

The TSPIPE workflow's final step is a static HTML cohort dashboard
that links every sample's per-tab review report to a top-level
index, all self-contained under `${params.outdir}`. The dashboard
runs after `ORGANIZE_OUTPUT` has assembled each sample's
`clinical/` directory and produces no scratch files — every artefact
it emits is part of the deliverable.

## What gets produced

```
${params.outdir}/
├── cohort_index.html                # one row per sample
├── assets/                          # vendored Bootstrap, jQuery, DataTables, Chart.js
│   ├── css/
│   ├── js/
│   └── webfonts/
└── <sample>/
    └── clinical/
        ├── <sample>_report.html     # per-sample report (~1-2 MB)
        ├── <sample>_igv_report.html # patched in place to support hash-router deep links
        └── (everything ORGANIZE_OUTPUT already published)
```

`cohort_index.html` is the entry point. Each row links to the
per-sample report. Headline columns: mean coverage, % bases ≥100x,
fold-80 base penalty, % duplicates, # clinical variants, FLT3-ITD
status, QC pill, and an "Open" button.

The per-sample report is tabbed: **Overview**, **QC**, **Variants —
Clinical**, **Variants — All Filtered**, **FLT3**, **CNV**, **IGV**,
**Reporting**, **Files**. The IGV tab embeds the patched
`<sample>_igv_report.html` and supports `#row_<variant_id>` hash
fragments — clicking a variant in the Variants — Clinical table
deep-links the IGV view to that locus.

## How to view

The dashboard uses only relative paths and vendored assets, so it
works equally well over HTTP and over a `file://` URL. To open
locally:

```bash
# Option 1: serve over HTTP (recommended for the IGV tab)
cd ${params.outdir}
python3 -m http.server 8765
# then browse to http://localhost:8765/cohort_index.html

# Option 2: copy the run dir off the cluster and open directly
scp -r hemat@gandalf:${params.outdir} ./
# then open cohort_index.html in any browser
```

The IGV tab's hash-router relies on `window.postMessage` between
the parent report and the embedded IGV iframe. Both `http://` and
`file://` are supported because the messaging never crosses an
origin boundary in either mode.

## Module reference

`DASHBOARD` is a single cohort-level process defined in
`modules/local/dashboard.nf` and wired at the end of
`workflows/tspipe.nf`. Inputs:

| Name            | Type                | Source                              |
|---|---|---|
| `sample_ids`    | `val(list)`         | `ORGANIZE_OUTPUT.out.clinical` keys |
| `clinical_dirs` | `path(list)`        | `ORGANIZE_OUTPUT.out.clinical` dirs |

Outputs:

| Name              | Path                                           |
|---|---|
| `cohort_html`     | `cohort_index.html`                            |
| `assets`          | `assets/`                                      |
| `sample_reports`  | `*/clinical/*_report.html`                     |
| `versions`        | `versions.yml` (consumed by MultiQC if wired)  |

The process runs **on the host** via `executor='local'`, matching
the existing pattern used by `VARIANT_VALIDATOR`, `ONCOVI`, and
`FLT3_TO_VARIANTS`. It does not pull a container.

## Requirements

The dashboard runs in the same conda env the pipeline already uses
for the host-executed annotation modules. On gandalf this is
`/home/hemat/anaconda3/envs/targeted-seq/`. The env must have:

| Package        | Purpose                              |
|---|---|
| `python` ≥ 3.7 | Builder runtime (3.10 in production) |
| `jinja2`       | Template rendering                   |
| `pandas`       | Variants and CNV TSV parsing         |
| `beautifulsoup4` | IGV HTML patching                  |
| `lxml`         | bs4's preferred parser               |
| `requests`     | Imported by optional annotators (GeneBe, MobiDetails, OncoKB, CancerVar) at module scope; required even when those annotators are not enabled |

Install everything in one go:

```bash
conda install -n targeted-seq -c conda-forge \
    jinja2 pandas beautifulsoup4 lxml requests
```

Verify:

```bash
/home/hemat/anaconda3/envs/targeted-seq/bin/python -c \
    "import jinja2, pandas, bs4, lxml, requests; print('all imports OK')"
```

## Parameters

| Param                       | Default                            | Description |
|---|---|---|
| `params.legacy_python_env`  | `/home/hemat/anaconda3/envs/targeted-seq` | Env root for host-executed modules. Dashboard falls back to `${legacy_python_env}/bin/python` if no override is set. |
| `params.dashboard_python`   | `null`                             | Explicit path to the python interpreter the dashboard should use. Set this if you want the dashboard to use a different env from the other local-executor modules. |

To override on the CLI for a one-off run:

```bash
nextflow run . \
    --dashboard_python /path/to/some/other/env/bin/python \
    ...
```

## IGV hash-router patch

The dashboard_builder patches each `<sample>_igv_report.html` in
place, inserting an idempotent JavaScript block delimited by these
HTML comments:

```html
<!-- BEGIN tspipe-dashboard-builder hash-router -->
<script>...</script>
<!-- END tspipe-dashboard-builder hash-router -->
```

The patch is safe to apply repeatedly — re-runs detect the
sentinels and skip the patch instead of stacking duplicates. It
runs on a module-owned copy of the IGV report inside the work dir;
the file `ORGANIZE_OUTPUT` hardlinked into `<sample>/clinical/` is
not mutated until `publishDir` copies the patched version on top
of it during the dashboard's publish step.

To check whether a given IGV report has been patched:

```bash
grep -c 'tspipe-dashboard-builder hash-router' \
    ${params.outdir}/<sample>/clinical/<sample>_igv_report.html
```

A patched report returns `2` (start + end sentinels). An
unpatched report returns `0`.

## Disabling the dashboard

The DASHBOARD process honours `task.ext.when`. To disable it for
a run, add this to `conf/modules.config`:

```groovy
withName: 'DASHBOARD' {
    ext.when = false
}
```

When disabled, the rest of the pipeline runs unchanged;
`ORGANIZE_OUTPUT` still publishes each sample's `clinical/`
directory under `${params.outdir}/<sample>/clinical/`.

## Troubleshooting

### `ModuleNotFoundError: No module named '<name>'`

A dashboard_builder dependency is missing from the conda env. Run
the `conda install` command in the Requirements section. The
common ones are `jinja2`, `bs4` (`beautifulsoup4`), `lxml`, and
`requests`.

### Cohort row counts are zero, or specific tabs are empty

Open the per-sample report and check which tabs are empty. The
likely cause is a filename-convention mismatch between
`bin/organize_output.py` and the dashboard_builder's parsers.
dashboard_builder v0.4.6 recognises both production
(`<sample>_somaticseq_*.tsv`, underscores) and nf-core port
(`<sample>.somaticseq.*.tsv`, dots) conventions. If your pipeline
emits a third convention, the parser will silently fall through;
the fix is to extend the candidate list in
`bin/dashboard_builder/build.py` (`collect_sample_context`,
clinical and filtered TSV blocks).

### `assets/` is missing from `${params.outdir}` after a run

This was a publishDir bug in the pre-v0.4.6 module (a brittle
brace-glob pattern). The current source uses a `saveAs` callback
that publishes every declared output except `versions.yml`. If
you see `assets/` absent on a fresh checkout, re-pull
`modules/local/dashboard.nf` from origin.

### IGV report opens but Variants — Clinical hash-link doesn't navigate

The hash-router requires the IGV iframe to be reachable in the
same browsing context as the report. Some browsers block iframe
messaging on `file://` URLs that span sibling directories. If
this happens, serve the run dir over HTTP using
`python3 -m http.server`.

### DASHBOARD ran but reports a different `params.dashboard_python` than expected

The module's elvis chain is
`params.dashboard_python ?: "${params.legacy_python_env}/bin/python"`.
If `params.dashboard_python = null` in `nextflow.config` (the
default) and `params.legacy_python_env` is set, the fall-through
fires and the dashboard uses the legacy env's python. If both
are null, Nextflow will fail with an undefined-parameter error.


## GeneBe annotation (optional)

The dashboard can call the GeneBe API (https://genebe.net) per
clinical variant to add ACMG classification, ClinVar status, and
gnomAD population frequencies to the Variants — Clinical tab. This
is opt-in and requires credentials.

GeneBe's auth model is HTTP Basic with the user's account email and
an API key. Calls without credentials still work but are
rate-limited; with credentials, the throughput is high enough that
the per-variant calls finish in seconds for typical samples.
Responses are cached to `<sample>/clinical/<sample>_genebe_cache.json`
so re-runs of the dashboard hit the cache, not the API.

### Setup

Credentials live in a per-user file outside the repository, loaded
conditionally by `nextflow.config`. This keeps the API key out of
version control entirely.

```bash
mkdir -p ~/.config/nf-core-tspipe
chmod 700 ~/.config/nf-core-tspipe
touch ~/.config/nf-core-tspipe/credentials.config
chmod 600 ~/.config/nf-core-tspipe/credentials.config
```

Then populate the file (use an editor; do not commit it anywhere):

```groovy
// ~/.config/nf-core-tspipe/credentials.config
params {
    genebe_enabled = true
    genebe_user    = 'you@example.org'
    genebe_key     = 'ak-...'
}
```

### Verify

After the credentials file is in place, a one-off check:

```bash
ls -la ~/.config/nf-core-tspipe/credentials.config
# Expected: -rw------- 1 <user> <group> ... credentials.config
```

The next pipeline run will pass `--annotate-genebe --genebe-user
... --genebe-key ...` to the dashboard_builder. To confirm GeneBe
fired, look for the per-variant cache after a run:

```bash
ls <outdir>/<sample>/clinical/<sample>_genebe_cache.json
```

The cache contains a `chr:pos:ref:alt` → annotation map. If the file
is missing the annotation didn't run; if it exists but is `{}`, the
clinical TSV had no rows for the parser to query.

### Disabling for a single run

Override on the CLI:

```bash
nextflow run . --genebe_enabled false ...
```

Or disable globally by editing the credentials file:

```groovy
params { genebe_enabled = false }
```

The credentials remain on disk but the dashboard ignores them until
re-enabled. Cached annotations on disk continue to populate the
Variants tab from earlier runs.

### Rotating the key

If the API key is ever pasted into a chat, ticket, screenshot, or
otherwise leaves the credentials file:

1. Log in to GeneBe → Account → API keys → revoke the old key.
2. Generate a new one.
3. Update `~/.config/nf-core-tspipe/credentials.config` with the new
   value. No pipeline restart needed; the new key is picked up on
   the next run.


## OncoKB annotation (optional)

The dashboard can also call the OncoKB API
(https://www.oncokb.org) per clinical variant to add OncoKB's
oncogenicity and therapeutic-evidence annotations to the Variants -
Clinical tab. This is opt-in and requires a free academic API
token from https://www.oncokb.org/account/register.

OncoKB's auth model is HTTP Bearer with a single token. Cached
responses are written to
`<sample>/clinical/<sample>_oncokb_cache.json`, so re-runs of the
dashboard hit the cache, not the API.

### Setup

Append OncoKB credentials to the same per-user credentials file
already used for GeneBe (see the GeneBe section above):

```groovy
// ~/.config/nf-core-tspipe/credentials.config
params {
    genebe_enabled = true
    genebe_user    = 'you@example.org'
    genebe_key     = 'ak-...'

    oncokb_enabled = true
    oncokb_token   = '<your-oncokb-bearer-token>'
}
```

Confirm the file is mode 0600 (it should already be, from the
GeneBe setup):

```bash
ls -la ~/.config/nf-core-tspipe/credentials.config
```

### Verify

After the next run, the OncoKB cache should appear next to the
GeneBe cache:

```bash
ls <outdir>/<sample>/clinical/<sample>_oncokb_cache.json
```

If the file is missing, the parser did not run; if it exists but
is `{}`, the clinical TSV had no rows for the parser to query.

### Cache file publishing

Both GeneBe and OncoKB caches are now published alongside the
per-sample report under `<outdir>/<sample>/clinical/`. This means
they travel with the deliverable tree and can be inspected for
audit. They are also re-used on `-resume` runs of the dashboard,
so the API is only hit once per variant per sample.

### Rotating the OncoKB token

OncoKB tokens are tied to the user's account. To rotate:

1. Log in to OncoKB -> Account -> API tokens -> regenerate.
2. Update `~/.config/nf-core-tspipe/credentials.config` with the
   new value. No pipeline restart needed; the new token is picked
   up on the next run.
