# Memo 22 — Paths of the development server in the configuration, and other findings of the review of 25 November 2026

Date: 25 November 2026

Pipeline: nf-core-tspipe, Twist myeloid panel

Affects: installation on any server other than gandalf and clinical-23; no effect on results

Corrected in: branch `fix/high-fraction-loh-and-site-portability`, commit 02aa42e (marker PORTABLE_V1); not released

Status: corrected and checked by resolving the configuration and by a stub run of the whole workflow; the installation checks of SOP-TSPIPE-001 sections 7.9 and 7.10 on each server are outstanding

---

## 1. Summary

The pipeline could not be installed on a further server without editing files of the release, and several defaults pointed at paths that exist only on gandalf. Section 7.8 of SOP-TSPIPE-001 already describes the most serious instance, the hmftools reference paths, and the workaround by which clinical-23 lives with it. This memo lists what was found, what was changed, and what was left as it is.

The review also found several things that are not about paths. They are listed in section 5, each with what was done about it. One of them needs the custodian's attention before the next release: `main` carries a change to the variant filter that is in no release and in no changelog.

## 2. How paths of gandalf reached other servers

The hmftools reference paths were written into the panel overlay, `conf/twist_apply.config`, with their location under `/goast`. A panel overlay is merged after the site profile, so no site profile could redirect them. clinical-23 redirected them with a parameter file, and a run started without that file failed at AMBER.

`nextflow.config` carried values of gandalf as the defaults for every site: the output directory under `/goast`, and three paths under `/home/hemat` for a Python environment, the older pipeline tree and OncoVI. A site inherited them unless its profile happened to override each one.

A further server needed its profile registered in the `profiles` block of `nextflow.config`. That file is part of the tagged release, and section 11 of the standard operating procedure requires a release checkout to be unmodified.

The installation check and the sandbox script added the apptainer directory of clinical-23 to the search path themselves. The launcher of gandalf defaulted to the development tree's path on that server, and the launcher of clinical-23 to the directory name of the first release.

## 3. What was changed

The site profile now names the directory of the hmftools resource bundle in one parameter, `hmf_root`, and the workflow finds the four reference files under it. A parameter file that names the files one by one, as `params_clinical23.yaml` does, still takes precedence, so the existing installation on clinical-23 runs as before with or without it.

The defaults in `nextflow.config` are neutral. The output directory defaults to a directory under the place of launch. The Python environment and OncoVI default to their locations inside the container image, which `conf/containers.config` already set for both servers, and the path of the older pipeline tree, which no process reads any more, is unset. The output directory of gandalf moved into `conf/gandalf.config`.

A new profile, `site`, reads `conf/site.config`, which git ignores, or the file named in the environment variable `TSPIPE_SITE_CONFIG`. A further server is configured by copying `conf/site_template.config` to that name and setting, in most cases, one line. No tracked file is edited. `docs/INSTALL.md` describes the steps.

The installation check takes the directory of the container runtime from the resolved profile, checks the hmftools files under `hmf_root`, and fails when a parameter of a profile other than gandalf still points at `/goast` or `/home/hemat`. The launchers default to the checkout they are in.

The resolved configuration of the profiles `gandalf` and `clinical23` with the Twist overlay was compared before and after. It differs only as intended: the hmftools files are no longer separate parameters, `legacy_root` is unset, the switch `baf_het_loss` of memo 21 is added, and on clinical-23 the hmftools root is on its own storage and no default points at gandalf. `tests/stub/run_stub_site.sh` builds a throw-away site from the template and runs the whole workflow in stub mode, 115 tasks, and checks that no task script names a path of another site.

## 4. What remains specific to the two servers

The profiles `gandalf` and `clinical23` and their launchers describe those two servers and are meant to. The samplesheets under `pon_samplesheets/` name FASTQ files on gandalf. The scripts that build the panels of normals, the PureCN database, the DECoN pools and the container image run on gandalf and name its paths; they are development tooling and were not touched. `conf/twist_pon_noncontainer.config` is for gandalf only by design.

`tools/run_pipeline.sh` still calls itself the production launcher. It defaults to paths of gandalf and its checks predate the container image. It was not changed. It should be removed or rewritten, since WI-TSPIPE-002 and WI-TSPIPE-003 now define how runs are launched.

Most of `docs/INSTALL.md` was written before release 1.0.0. Its quick start and its section on site configuration were brought up to date and a note at the top points to the standard operating procedure. The rest of the document was left, and still describes the arrangement on gandalf at that time.

## 5. Other findings

`main` is three commits ahead of tag v1.0.2. The last of them, 438d308 of 18 November 2026, is labelled as documentation for WI-TSPIPE-003. It also changes `bin/variant_filter.py` (marker HOTSPOT_EXEMPT_V1: the filters LOW_CALLERS and LOW_DEPTH now exempt every hotspot residue of `assets/myeloid_hotspots.tsv` with a non-synonymous consequence, where only the two U2AF1 hotspots were exempt before), the NPM1 line of that table, and the variant browser of the dashboard (marker DASH_CEBPA_BZIP_V1). These changes are in no release, in no changelog entry and in no audit record. The release checkouts on both servers do not have them. A release cut from `main` will include them, and they change which variants reach the clinical table, so they need their own validation and their own entry. Nothing was changed here; the changelog now names them under "Unreleased" so that they are not overlooked.

On gandalf the container option `--no-home` has not been in effect since 2 September 2026. `conf/gandalf.config` had two `singularity` blocks; the second, added for the bind mounts, replaced the `runOptions` of the first. Tasks on gandalf therefore see the home directory of the user, and tasks on clinical-23 do not. Releases v1.0.0 to v1.0.2 were validated on gandalf in this state. The two blocks were merged into one with the value that was in effect, so nothing changes; whether to add `--no-home` on gandalf is a change to a validated runtime and is left to the custodian.

A launch without a panel overlay stopped with a workflow construction error that named an internal channel. As the workflow stands, a run without `conf/twist_apply.config` cannot proceed, because the reporting stage reads the copy-number results unconditionally. The launch now stops before any task with a message that names the overlay.

`launch_tspipe.sh` tested, and tried to restart, the local VariantValidator stack, although the pipeline has used the public service since 3 September 2026. Its default now is the endpoint the pipeline uses.

`manifest.version` in `nextflow.config` reads 1.0.0, although tags v1.0.1 and v1.0.2 exist, and `CHANGELOG.md` has no entry for either of those releases. The work instructions record the version from the git tag, so no run record is wrong, but the three should agree. Both were left for the next release.

The per-arm B-allele detector calls balanced arms in a sample that carries about 10 percent or more of a second genome. This predates memo 21. The detector now warns of such a sample and the dashboard shows the warning; the verdicts themselves are unchanged.

For deletions and gains the detector's column `f_estimate` is not the clonal fraction but the shift on the scale of a copy-neutral event, which understates the clone. This also predates memo 21 and was left; `docs/sops/baf_het_loss.md` describes it under its limits.

## 6. What remains before release

Changes to site configuration do not need a re-validation of calling behaviour, but section 11 of SOP-TSPIPE-001 requires the installation qualification of section 7.9 and the golden regression of section 7.10 to be repeated on each server.

The standard operating procedure describes the state before this change in several places, and these need revising with the release: section 7.8, on creating the site configuration and on the role of the parameter file; the row "Unknown configuration profile" of section 10.2; item 6 of section 11; section 12; and the installation record of Annex A, which lists the hmftools entries of `params_clinical23.yaml`. WI-TSPIPE-002 lists a missing parameter file among the reasons for which the launcher refuses to start; the launcher now starts without it and says so in its log.
