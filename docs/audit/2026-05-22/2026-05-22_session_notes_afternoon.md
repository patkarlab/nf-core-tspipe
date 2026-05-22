# Session audit (afternoon) — 2026-05-22

**Subject:** Opt-in GeneBe + OncoKB annotation wired into the cohort
dashboard via untracked credentials file. Cache JSONs now publish
alongside per-sample reports.

**Repos touched:** patkarlab/nf-core-tspipe at /goast/hemat_data/nf-core-tspipe/

**Server:** gandalf

**HEAD at start of session:** 0a09ef1 (on origin/main, from the morning
dashboard integration session)

**HEAD at end of session:** _to be filled in after commits land_

---

## Outcome

The cohort dashboard can now optionally call GeneBe and OncoKB to
add ACMG / oncogenicity / therapeutic-evidence annotations to the
Variants — Clinical tab. Both annotators are opt-in, controlled by
params declared with safe defaults in `nextflow.config` and
overridden at runtime from an untracked credentials file at
`~/.config/nf-core-tspipe/credentials.config` (mode 0600). The
credentials file is never tracked in git.

Validated end-to-end on 26CGH775-MYCNV:

| Annotator | Variants | Cache size | Errors |
|---|---|---|---|
| GeneBe   | 14 | 8.2 KB | 0 |
| OncoKB   | 14 | 8.2 KB | 0 |

Both cache files now appear under
`<outdir>/<sample>/clinical/<sample>_*_cache.json` and are picked
up on `-resume` runs so the APIs are hit only once per variant per
sample.

---

## Commits landed (2 planned)

To land on patkarlab/nf-core-tspipe origin/main:

| Hash | Subject |
|---|---|
| TBD | `feat(dashboard): opt-in GeneBe + OncoKB annotation via untracked credentials file` |
| TBD | `docs: 2026-05-22 annotator session audit (GeneBe + OncoKB)` |

---

## Scope of work delivered

### 1. Credentials file pattern

Both annotators authenticate via the same per-user file:

```
~/.config/nf-core-tspipe/credentials.config   (mode 0600)
```

Contents:

```groovy
params {
    genebe_enabled = true
    genebe_user    = 'you@example.org'
    genebe_key     = 'ak-...'

    oncokb_enabled = true
    oncokb_token   = '<bearer-token>'
}
```

Loaded conditionally by `nextflow.config` at end-of-file:

```groovy
if (new File("${System.getProperty('user.home')}/.config/nf-core-tspipe/credentials.config").exists()) {
    includeConfig "${System.getProperty('user.home')}/.config/nf-core-tspipe/credentials.config"
}
```

Six new params declared with safe defaults in the `params { ... }`
block (`genebe_enabled = false`, `genebe_user = null`,
`genebe_key = null`, `oncokb_enabled = false`, `oncokb_token = null`)
so the pipeline runs cleanly with no credentials file present.

### 2. DASHBOARD process script extensions

`modules/local/dashboard.nf` now passes credentials through to
`build.py` via Groovy ternaries that resolve at task time:

```groovy
${py} ${builder_dir}/build.py \\
    dashboard_view \\
    --subdir clinical \\
    ${ params.genebe_enabled ? "--annotate-genebe" : "" } \\
    ${ params.genebe_enabled && params.genebe_user ? "--genebe-user '" + params.genebe_user + "'" : "" } \\
    ${ params.genebe_enabled && params.genebe_key  ? "--genebe-key '"  + params.genebe_key  + "'" : "" } \\
    ${ params.oncokb_enabled ? "--annotate-oncokb" : "" } \\
    ${ params.oncokb_enabled && params.oncokb_token ? "--oncokb-token '" + params.oncokb_token + "'" : "" } \\
    ${task.ext.args ?: ''}
```

When both annotators are disabled, the ternaries render as empty
strings and the invocation collapses to the original
`--subdir clinical` form.

### 3. Cache file publishing

Added a new output declaration to `dashboard.nf`:

```groovy
path "*/clinical/*_cache.json",   emit: caches,   optional: true
```

Both `<sample>_genebe_cache.json` and `<sample>_oncokb_cache.json`
match the glob. The `optional: true` keeps the process valid when
neither annotator is enabled. The saveAs callback already filters
`versions.yml` out of publishing; cache files are not affected.

### 4. Documentation

`docs/dashboard.md` extended with two new sections (`## GeneBe
annotation (optional)` and `## OncoKB annotation (optional)`)
covering setup, verification, cache file publishing, and token
rotation.

---

## Key findings during the session

### Two-stage debug of the GeneBe wiring

First attempt: params declared correctly in `nextflow.config` but
`genebe_enabled` resolved to `false` at task time. Root cause: the
original apply script's sentinel check for the `includeConfig`
block falsely matched a comment inside the params block that
mentioned `credentials.config`. The append-to-EOF therefore never
fired, so the credentials file was never loaded. Fixed by manually
appending a clean idiomatic block:

```groovy
if (new File("${System.getProperty('user.home')}/.config/nf-core-tspipe/credentials.config").exists()) {
    includeConfig "${System.getProperty('user.home')}/.config/nf-core-tspipe/credentials.config"
}
```

`nextflow config -profile gandalf` then resolved
`genebe_enabled = true` and the file picked up correctly.

### Cache files were written but not published

The first successful GeneBe run wrote
`<sample>_genebe_cache.json` into the work dir but the file did
not appear in the published `clinical/` tree. Root cause: the
DASHBOARD process declared `*/clinical/*_report.html` and
`*/clinical/*_igv_report.html` as outputs but not the cache JSONs.
publishDir copied only declared outputs. Fixed by adding
`path "*/clinical/*_cache.json", emit: caches, optional: true` to
the output block.

This means GeneBe was working correctly all along — it had run,
hit the API, and written 14 cache entries — they were just stuck
in the work dir. After the publish fix, the same cache files
appear under `<outdir>/<sample>/clinical/` and are reused on
`-resume`.

### Free OncoKB tokens have known rate limits

OncoKB free academic tokens are subject to per-day request quotas
(typically around 1000/day). 14 variants per sample is well within
budget for normal use, but a multi-sample run on thousands of
variants would need careful sequencing. Cache reuse on `-resume`
makes this mostly a non-issue once a cohort has been annotated
once.

### Credentials hygiene — two near-misses this session

The GeneBe API key and OncoKB token were both pasted into the chat
transcript at different points (the GeneBe key directly; the
OncoKB token indirectly via a `nextflow config` output that
included the resolved value). Both credentials are considered
compromised the moment they appear in chat. Both have been
rotated.

The hardening lesson: never `cat`, `nextflow config`, or otherwise
dump anything that could contain credentials into the conversation.
For verification, use a redacting filter such as:

```bash
nextflow config -profile gandalf 2>/dev/null | \
    grep -E "(genebe|oncokb)_(enabled|user|key|token)" | \
    sed -E "s/=\\s*'(.{3}).*'/= '\\1...[REDACTED]'/"
```

That shows only the first three characters of any quoted value, so
the structure is visible but the secret isn't.

---

## What's still open

Carrying forward from the morning session:

1. **`ch_bed` is a queue channel** — flagged 2026-05-16. Multi-sample
   safety.
2. **Multi-sample dashboard not yet exercised.** Both annotators
   demonstrably work on N=1; cohort layout / API rate-limit
   behaviour on N>>1 untested.
3. **Female PoN age mismatch** — flagged 2026-05-16.
4. **CDKN2A/B whitelist** — pending from 2026-05-14.
5. **`PANEL_GENE_CHROMS` configurability** for non-myeloid panels.
6. **dashboard_builder filename-fallback silence** — when neither
   underscore nor dot form of a variants TSV exists, the parser
   silently skips the tab.
7. **`docs/output.md`** does not yet reference the dashboard or
   annotator artefacts.
8. **Repo work tree noise** — multiple untracked files
   (`samp.dat`, `test_samples.dat`, `samplesheet.csv`, `script.log`,
   etc.) need a `.gitignore` pass.

New from this afternoon:

9. **MobiDetails and CancerVar parsers are vendored but not wired.**
   `bin/dashboard_builder/parsers/` contains `mobidetails.py` and
   `cancervar.py`. If those become useful for any clinical
   workflow, the same credentials-file pattern would apply (new
   params under `params { ... }`, new ternaries in `dashboard.nf`).
10. **OncoKB rate-limit handling** — the parser does not currently
    back off on 429 responses. Acceptable at 14 variants × 1 sample;
    worth revisiting if a cohort run is rate-limited.

---

## Conda environment

`targeted-seq` env unchanged from the morning session. No new
Python packages added today. `requests` (already present) is the
only new module-level import exercised by enabling GeneBe and
OncoKB.

---

## Git references

- Production: `bb2d2ee` (unchanged today)
- nf-core: `0a09ef1` at start of this session; HEAD after today's
  two annotator commits to be recorded once they land.

Apply scripts transferred through `~/inbox/from_claude/`:

- `apply_genebe_wiring.py` (initial; the includeConfig block in
  this version did not land due to a sentinel false-positive; the
  fix was applied manually)
- `apply_oncokb_and_cache_fix.py` (OncoKB params + ternaries +
  cache output declaration; applied cleanly)

The credentials file at `~/.config/nf-core-tspipe/credentials.config`
is git-ignored and is not part of any commit; it lives only on
this host's filesystem under the deploying user's home dir, with
mode 0600.
