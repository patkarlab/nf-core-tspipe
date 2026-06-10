# Audit — 2026-06-10: repo review fixes (blacklist default, FLT3 sentinel, dead code)

**Repo:** `patkarlab/nf-core-tspipe`
**Scope:** code review of the full pipeline; fixes for Issues 1, 3, 4 (Issue 2 deferred by decision).
**Method:** anchor-based idempotent Python patchers, dry-run validated, applied with timestamped
rollback backups, committed in three conventional commits.

---

## Issues addressed

### Issue 1 — silent empty blacklist (HIGH, clinical)
`nextflow.config` set the `snv_blacklist` default to the legacy 4-column file
`references/blacklist_snvs_hg38.tsv` (Chr/Start/Ref/Alt). `bin/apply_blacklist.py` parses an
11-column schema (`chrom start end match_mode pos_exact ref_exact alt_exact gene reason evidence
date_added`) and skips any non-conforming line. `conf/gandalf.config` overrides the default to the
correct 11-column `references/blacklist_file.tsv`, so validated gandalf runs were unaffected — but any
run without that override silently applied an **empty** blacklist, letting known artefacts through into
the clinical TSV. `apply_blacklist.py` is used as a library by `bin/variant_filter.py`, and
`VARIANT_FILTER` is not `error_ignore`, so a hard failure there correctly fails the sample.

**Fix:**
- Repointed the `snv_blacklist` default to `references/blacklist_file.tsv` so the documented default
  matches the parser even without the gandalf override.
- Added a zero-entry guard in `load_blacklist`: if a supplied blacklist contains data lines but none
  parse as valid 11-column entries, it raises `ValueError` instead of returning `[]`. This is the
  load-bearing protection — a schema mismatch (e.g. feeding the legacy 4-column file) now fails
  `VARIANT_FILTER` loudly rather than quietly disabling artefact filtering. An all-comment /
  header-only / empty file (no data lines) is still allowed through as a legitimately empty blacklist.
- Repointed the three stale `blacklist_snvs_hg38.tsv` references in the docstrings/argparse help.

### Issue 3 — FLT3-ITD-negative specimens shown as failed tasks (MEDIUM)
`modules/local/flt3_itd_ext.nf` declared `vcf`/`summary` as non-optional outputs. `FLT3_ITD_EXT` exits
non-zero (`NO ITD CANDIDATE CLUSTERS GENERATED`) and writes no VCF on ITD-negative specimens, so output
collection failed and every negative sample (the majority) surfaced as a failed task in the execution
report; `FLT3_CONSENSUS` fell back to the join placeholder.

**Fix (sentinel output on no-ITD):** the script block now captures the tool exit code, treats the
benign no-cluster message as success, and writes a header-only sentinel VCF + empty summary when
absent so output collection succeeds and `FLT3_CONSENSUS` receives a parseable zero-record VCF. Any
**other** non-zero exit is propagated (`exit $rc`) so genuine breakage stays visible rather than being
masked by a blanket `|| true`. A non-empty real VCF (ITD-positive success) is never clobbered
(`[ ! -s "$vcf" ]` guard).

### Issue 4 — dead code and stale docstrings (LOW, cleanup)
- `workflows/tspipe.nf` imported `SV_CALLING` and `REPORTING` but never invoked them (SV's only call is
  commented out; final assembly is done directly via `IGV_REPORTS` + `ORGANIZE_OUTPUT`). The header DAG
  comment advertised `-> SV_CALLING` and `-> REPORTING` flows that do not run.
- `bin/annotate.py` `parse_vep_csq()` docstring still claimed VEP ran with `--pick` and was "bit-for-bit
  identical to production"; the 2026-06-09 flag_pick patch changed this to `--flag_pick` + severity
  selection via `_pick_csq`.
- `nextflow.config` declared a dead `skip_from = 0` param (README confirms no `--skip-from` in the port;
  nothing reads `params.skip_from`).

**Fix:** removed the two dead includes, corrected the header DAG comment (with a NOTE explaining
SV_CALLING/REPORTING are intentionally not wired), corrected the `parse_vep_csq` docstring, and removed
the dead `skip_from` param.

---

## Patch scripts (this session)

All under `tools/patches/2026-06-10/`. Dry-run by default; `--apply` to write; idempotent via MARKER
(`[skip]` on re-run); timestamped `.bak_<tag>_<ts>` backups. Python 3.6-safe.

| Script | Target file | Issue |
| --- | --- | --- |
| `patch_nextflow_config_blacklist_skipfrom.py` | `nextflow.config` | 1 (repoint) + 4 (skip_from) |
| `patch_apply_blacklist_guard.py` | `bin/apply_blacklist.py` | 1 (guard + path refs) |
| `patch_flt3_itd_ext_sentinel.py` | `modules/local/flt3_itd_ext.nf` | 3 |
| `patch_annotate_parse_csq_docstring.py` | `bin/annotate.py` | 4 |
| `patch_tspipe_deadcode.py` | `workflows/tspipe.nf` | 4 |

Rollback backups from this session carry the suffix `_20260610_060013`.

---

## Validation performed

Validated against a throwaway copy of the repo before delivery, and re-confirmed on the live checkout
via dry-run prior to `--apply`:

- **Anchors / dry-run:** all five reported `[patch] DRY-RUN ok` on the live files (no drift).
- **Apply + idempotency:** all five applied cleanly; re-running each reported `[skip]`.
- **Python syntax:** `python3 -m py_compile bin/apply_blacklist.py bin/annotate.py` passed.
- **FLT3 Groovy escaping:** verified byte-for-byte via `cat -A` and by reconstructing the post-GString
  `.command.sh` with a faithful escape transform; bash variables emit as `$rc`/`$vcf`, line
  continuations as single `\`, and `printf` escapes as `\n`/`\t`.
- **FLT3 sentinel logic (reconstructed .command.sh, fake shims):**
  - ITD-negative (tool exits non-zero with the benign message) -> exit 0, valid 3-line header-only VCF, summary created.
  - genuine failure (different error, non-zero) -> exit code propagated, no VCF.
  - ITD-positive (real VCF present) -> preserved intact, not clobbered.
  - 0-byte VCF present -> sentinel header written.
- **Blacklist guard (live `load_blacklist`):**
  - legacy 4-column file -> raises `ValueError` (correct).
  - valid 11-column file -> returns entries.
  - header-only file -> returns `[]` (no raise).
  - empty file -> returns `[]` (no raise).

---

## Commits

```
f0adf55  fix(blacklist): default to 11-col blacklist_file.tsv; fail loudly on schema mismatch
422b106  fix(flt3): emit sentinel outputs on ITD-negative; propagate real failures
14e7692  refactor(workflow): drop dead SV_CALLING/REPORTING includes; fix stale docstrings
```

Pushed to `origin/main` (`357e656..14e7692`). Files staged by name so the `.bak_*` rollbacks remained
untracked.

---

## Operational notes

- The next pipeline run re-executes `FLT3_ITD_EXT` on `-resume` (its script hash changed). Expected; no
  cache clear required (no container directive changed).

## Deliberately not changed

- **Issue 2** (`CNV_ANNOTATE.out.tsv` emitted by `cnv_calling.nf` but never consumed in `tspipe.nf`'s
  organise chain, and swept by `main.nf` `workflow.onComplete`) — excluded by decision; still open.
- `bin/variant_filter.py` line 51 argparse help still names `blacklist_snvs_hg38.tsv`; now harmless
  since the guard rejects the wrong schema. Cosmetic.
- `docker.userEmulation` (deprecated) left in place — the docker profile is dormant on gandalf.
- `references/blacklist_snvs_hg38.tsv` is now unreferenced and may be removed manually.
