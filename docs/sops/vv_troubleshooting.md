---
title: "VariantValidator Docker Stack: Troubleshooting and Recovery SOP"
subtitle: "Targeted Sequencing Pipeline — Bioinformatics Team"
author: "Hematology Lab Bioinformatics"
date: "Version 1.0 — May 2026"
geometry: margin=0.9in
fontsize: 10pt
colorlinks: true
linkcolor: blue
urlcolor: blue
toc: true
toc-depth: 2
header-includes:
  - \usepackage{fvextra}
  - \DefineVerbatimEnvironment{Highlighting}{Verbatim}{breaklines,commandchars=\\\{\}}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{VariantValidator Troubleshooting SOP}
  - \fancyhead[R]{\thepage}
---

\newpage

# 1. Purpose and Scope

This SOP documents how to diagnose and recover from failures of the locally
hosted VariantValidator (VV) REST API used by the targeted sequencing
pipeline. VV runs as a four-container Docker stack on `gandalf`. When VV is
unreachable, the pipeline step `TSPIPE:ANNOTATION:VARIANT_VALIDATOR` fails
and the entire Nextflow run aborts, blocking all downstream annotation and
clinical report generation for the batch.

This document is the authoritative reference for the bioinformatics team
when a VV-related failure is suspected. Use it directly under live
incident conditions — the diagnostic section is structured as a decision
tree, and the quick-reference card in Appendix A is the single page to
print or pin.

The SOP assumes basic familiarity with the shell and with Docker
commands. No knowledge of the VV internals is required.

# 2. System Architecture

VV is hosted as a Docker Compose stack with four containers, all
running on `gandalf`.

| Container                                          | Role                                            |
|----------------------------------------------------|-------------------------------------------------|
| `rest_variantvalidator-rest-variantvalidator-1`    | Flask/gunicorn REST API (the public endpoint)   |
| `rest_variantvalidator-rv-vvta-1`                  | VV transcript annotation database (PostgreSQL)  |
| `rest_variantvalidator-rv-seqrepo-1`               | SeqRepo reference sequence store                |
| `rest_variantvalidator-rv-vdb-1`                   | Validator database                              |

The REST container exposes the API on container port `5000`, mapped to
host port `5001`. The pipeline talks to `http://localhost:5001`. The three
backing-data containers communicate with the REST container on the
internal Docker network only.

**Compose stack location**

```
~/targeted-seq-pipeline/software/rest_variantValidator
```

**Persistent volumes (do not delete without an escalation path)**

```
rest_variantvalidator_vvta-data
rest_variantvalidator_vdb-data
```

These volumes hold the VVTA and VDB database contents and take hours to
rebuild from scratch.

## 2.1 The Critical Operational Detail

The single most important fact about this stack — and the root cause of
nearly every incident this team has seen — is the following:

> **The `gunicorn` process inside the REST container does not start
> automatically when the container starts.** It must be launched
> separately with `docker exec`. If the container is restarted (host
> reboot, manual `docker restart`, OOM kill of the worker), `docker ps`
> will still report the container as `Up`, but the REST endpoint will be
> dead.

This explains why "the container is up but the endpoint returns nothing"
is the failure mode you will encounter most often. Diagnostic procedures
in Section 4 explicitly test for this.

# 3. Failure Modes

| Mode | Description                                                | `docker ps` shows | Health check returns | Most common cause                            |
|------|------------------------------------------------------------|-------------------|----------------------|----------------------------------------------|
| A    | All containers down                                        | Missing rows      | `HTTP 000`           | Host reboot, Docker daemon restart           |
| B    | Containers `Up`, gunicorn dead inside REST container       | All 4 `Up`        | `HTTP 000`           | Container restart, OOM, manual `docker restart` |
| C    | Gunicorn running but app erroring                          | All 4 `Up`        | `HTTP 5xx`           | VVTA/SeqRepo/VDB unreachable, internal error |
| D    | Port not bound on host (rare)                              | All 4 `Up`        | `HTTP 000`           | Docker-proxy crash, port conflict            |

Mode B is by far the most common (~90% of incidents to date).
Modes A, C, D require different recovery paths and are described in
Section 5.

# 4. Diagnostic Decision Tree

Work through these three checks in order. Each takes seconds. Do not skip
ahead; the failure mode is determined by the *combination* of outputs.

## 4.1 Step 1 — Health probe

This is the single most important command. If it returns `HTTP 200`,
VV is healthy and the problem is somewhere else (the pipeline, the
script, the data — not VV).

```bash
curl -sf -o /dev/null -w 'HTTP %{http_code}\n' --max-time 10 \
  "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G%3ET/all?content-type=application/json"
```

| Returns        | Interpretation                                       | Go to     |
|----------------|------------------------------------------------------|-----------|
| `HTTP 200`     | VV is healthy. The problem lies elsewhere.           | Section 7 |
| `HTTP 000`     | Connection refused or timeout. VV unreachable.       | Step 2    |
| `HTTP 5xx`     | Endpoint up but application failing.                 | Step 4    |
| `HTTP 4xx`     | Should not happen with this URL; treat as 5xx.       | Step 4    |

The test variant is `NM_000088.4:c.589G>T` (a single SNV in COL1A1, a
canonical MANE transcript). It exercises the main VV code path without
depending on any panel-specific data. Do not change the test variant.

## 4.2 Step 2 — Container status

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -i variantvalidator
```

Expected output — four lines, all showing `Up`:

```
rest_variantvalidator-rest-variantvalidator-1   Up X hours
rest_variantvalidator-rv-vvta-1                 Up X hours
rest_variantvalidator-rv-seqrepo-1              Up X hours
rest_variantvalidator-rv-vdb-1                  Up X hours
```

| Result                          | Failure mode | Recovery procedure   |
|---------------------------------|--------------|----------------------|
| Any container missing or down   | A            | Section 5.1          |
| All four containers `Up`        | (continue)   | Step 3               |

## 4.3 Step 3 — Gunicorn check inside the REST container

This step distinguishes Mode B (gunicorn dead) from Modes C/D.

```bash
docker exec rest_variantvalidator-rest-variantvalidator-1 ps -ef \
  | grep -E '[g]unicorn'
```

Expected output when healthy — two lines (master + worker):

```
root   13   0  ...  /usr/local/bin/python3.12 /usr/local/bin/gunicorn -b 0.0.0.0:5000 ...
root   20  13  ...  /usr/local/bin/python3.12 /usr/local/bin/gunicorn -b 0.0.0.0:5000 ...
```

| Result                | Failure mode | Recovery procedure |
|-----------------------|--------------|--------------------|
| Empty output          | B (most common) | Section 5.2     |
| Master + worker shown | C or D       | Step 4             |

## 4.4 Step 4 — Application error log

If gunicorn is running but the endpoint is returning 5xx or 000,
read the application error log.

```bash
docker exec rest_variantvalidator-rest-variantvalidator-1 \
  tail -n 100 /tmp/vv_error.log
```

| Log content                                                    | Likely cause                                  | Recovery |
|----------------------------------------------------------------|-----------------------------------------------|----------|
| `Connection refused` to vvta / seqrepo / vdb                   | Backing DB container started after REST       | 5.3      |
| `MemoryError` or worker killed                                 | OOM                                           | 5.3      |
| `psycopg2.OperationalError` or PostgreSQL error                | VVTA database problem                         | 5.4 (escalate) |
| `[CRITICAL] WORKER TIMEOUT`                                    | Single slow query; usually transient          | 5.3      |
| Worker booted, no further entries                              | Still warming up; wait 90s, recheck Step 1    | —        |

If Step 3 showed gunicorn running but Step 1 still returns `HTTP 000`,
the port mapping itself may have failed. Verify:

```bash
docker port rest_variantvalidator-rest-variantvalidator-1
# Expected: 5000/tcp -> 0.0.0.0:5001

ss -ltnp 2>/dev/null | grep :5001 || netstat -ltnp 2>/dev/null | grep :5001
# Expected: a docker-proxy or LISTEN entry on :5001
```

If neither shows the expected output, this is Mode D — proceed to
Section 5.5.

# 5. Recovery Procedures

Each procedure ends with a verification step. Do not consider the
incident resolved until Section 6's verification succeeds.

## 5.1 Procedure A — All containers down

```bash
cd ~/targeted-seq-pipeline/software/rest_variantValidator
docker compose up -d
sleep 30
```

Expected warnings (safe to ignore):

```
WARN[0000] /...docker-compose.yml: the attribute `version` is obsolete...
WARN[0000] volume "rest_variantvalidator_vdb-data" already exists...
WARN[0000] volume "rest_variantvalidator_vvta-data" already exists...
```

These warnings indicate the named volumes are pre-existing (correct
behavior — those volumes hold the database state). They do not need to
be fixed.

After 30 seconds, the containers will be `Up` but gunicorn will not be
running. **Continue immediately to Procedure B.**

## 5.2 Procedure B — Gunicorn dead inside running container (most common)

This is the standard recovery for the most common failure mode.

```bash
docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
  bash -c 'cd /app/rest_VariantValidator && gunicorn -b 0.0.0.0:5000 --timeout 600 app --threads=5'
```

The `-d` flag detaches; the command returns immediately. **Gunicorn
itself takes 60 to 120 seconds to complete worker warm-up** (HGVS
library loading, VVTA / SeqRepo / VDB connection setup, internal cache
population). Do not test the endpoint immediately — it will return
`HTTP 000` until warm-up completes.

```bash
sleep 90
```

Then proceed to Section 6 (Verification). If the verification fails
after a further 60 seconds, check the application error log
(Step 4) — gunicorn started but the worker crashed during init, which
means Procedure C.

## 5.3 Procedure C — Worker initialization failure

This applies when gunicorn is running but the app is erroring (Step 4
showed log entries indicating database or memory problems).

```bash
cd ~/targeted-seq-pipeline/software/rest_variantValidator
docker compose restart
sleep 60
```

A full `restart` recreates all four containers in the correct order,
ensuring VVTA / SeqRepo / VDB are fully ready before REST attempts to
connect. After the restart, gunicorn will again need to be started
manually — return to Procedure B.

If the error log specifically shows `MemoryError`, also check host
memory pressure:

```bash
free -h
docker stats --no-stream rest_variantvalidator-rest-variantvalidator-1
```

Sustained high memory use by the REST container may indicate a memory
leak in gunicorn — restart of the REST container alone usually
resolves the immediate symptom.

## 5.4 Procedure D — Database container problem

If Step 4 showed a `psycopg2.OperationalError` or persistent
PostgreSQL error from the VVTA container, the data store itself may
be unhealthy. This is outside routine recovery — escalate per
Section 8.

Before escalating, gather and preserve the following for the on-call
engineer:

```bash
docker logs --tail 200 rest_variantvalidator-rv-vvta-1 \
  > /tmp/vvta_logs_$(date +%Y%m%d_%H%M%S).log

docker exec rest_variantvalidator-rest-variantvalidator-1 \
  tail -n 500 /tmp/vv_error.log \
  > /tmp/vv_error_$(date +%Y%m%d_%H%M%S).log
```

## 5.5 Procedure D2 — Port not bound on host

If Step 4's port-mapping check showed no listener on `:5001`:

```bash
cd ~/targeted-seq-pipeline/software/rest_variantValidator
docker compose down
docker compose up -d
sleep 30
```

Then return to Procedure B for the gunicorn step.

If a `docker compose down` cannot complete (hangs), the Docker daemon
itself may need restart. Escalate per Section 8.

# 6. Verification

After every recovery procedure, both checks below must succeed before
considering the incident closed.

## 6.1 Gunicorn process is running

```bash
docker exec rest_variantvalidator-rest-variantvalidator-1 ps -ef | grep -E '[g]unicorn'
```

Must show at least one master and one worker process.

## 6.2 Endpoint returns HTTP 200 with valid JSON

```bash
curl -sf -o /dev/null -w 'HTTP %{http_code}\n' --max-time 15 \
  "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G%3ET/all?content-type=application/json"
```

Must return `HTTP 200`.

For an extra-paranoid check, fetch the full response and confirm the
flag is `gene_variant`:

```bash
curl -s --max-time 15 \
  "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G%3ET/all?content-type=application/json" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("flag:", d.get("flag"))'
```

Expected output: `flag: gene_variant`.

# 7. Resuming the Pipeline

Once verification (Section 6) succeeds, resume the affected Nextflow
run using `-resume`. Critical: **keep the same `--outdir`** as the
failed run — Nextflow's resume logic uses the work directory layout
under the original output, and changing `--outdir` invalidates the
cache.

Example for the present batch:

```bash
cd /goast/hemat_data/nf-core-tspipe
nextflow run . --input samplesheet.csv \
    --outdir test_run/<YYYYMMDD_HHMMSS> \
    -profile gandalf,singularity -resume -bg
```

All cached upstream tasks will be reused; the run will pick up at the
first non-cached process (typically `VARIANT_VALIDATOR` for the
sample that failed, followed by the remaining samples).

If the problem started recurring during this same resume, the issue
is likely Mode C (worker init failure) rather than Mode B
(gunicorn died once). Escalate.

# 8. Escalation Criteria

Escalate to the pipeline lead (or whoever holds the on-call rotation
for this stack) when **any** of the following are true:

1. Recovery procedures B and C have both been attempted and verification
   still fails after 10 minutes.
2. The VV error log shows a `psycopg2.OperationalError`, repeated
   `WORKER TIMEOUT`, or any `CRITICAL` line that does not clear
   within one restart cycle.
3. Multiple independent crashes occur within a 60-minute window
   (suggests an underlying issue beyond simple gunicorn death).
4. A pipeline batch is on a clinical deadline and is at risk of
   missing it.
5. The host memory or disk usage is anomalously high during the
   incident.

When escalating, attach the diagnostic outputs gathered in Section 5.4
(VVTA log + VV error log) plus the output of `docker ps -a` and
`docker stats --no-stream`.

# 9. Preventive Measures

Two layered defenses are in place in addition to this SOP. Both should
be verified at the start of every pipeline batch.

## 9.1 Launch wrapper preflight

The launch wrapper (`launch_tspipe.sh`) performs a VV health check
*before* invoking Nextflow. If VV is not reachable on the initial
probe, the wrapper attempts a bounded auto-recovery (one cycle of
Procedure B) and only launches Nextflow if VV subsequently returns
`HTTP 200`. If preflight fails, the wrapper exits with code 10 and
no Nextflow tasks are scheduled.

To run a pipeline batch *with* preflight protection:

```bash
~/targeted-seq-pipeline/scripts/launch_tspipe.sh
```

To run *without* preflight (legacy direct invocation, not
recommended):

```bash
nextflow run . --input samplesheet.csv -profile gandalf,singularity ...
```

The wrapper sources its parameters from environment variables.
Override defaults by exporting them before invocation. See the
wrapper script header for the full list.

## 9.2 In-script retry block

The production VV script
(`scripts/17_variant_validator.py`) and its nf-core counterpart
(`bin/17_variant_validator.py`) wrap the initial VV connection check
in a retry-with-exponential-backoff loop (default: 3 attempts at
30 / 60 / 120 second intervals). This protects against transient VV
outages that occur *during* a Nextflow run, after preflight has
already passed.

The defaults are designed to outlast one full gunicorn warm-up cycle
(~90 s). They can be tuned per-invocation:

```bash
python 17_variant_validator.py \
    --sample <S> --input <T> --outdir <D> \
    --vv-url http://localhost:5001 \
    --connect-retries 5 --connect-backoff 60
```

## 9.3 Optional: scheduled health monitoring

A cron job that runs the Section 6.2 health check every 5 minutes
and pages on three consecutive failures is recommended but not yet
implemented. Tracked as a future enhancement.

# Appendix A: One-Page Quick Reference

Print this page and pin it near the workstation used for pipeline
operations.

\fbox{\parbox{\textwidth}{
\textbf{VV health check (always run first)}

\begin{verbatim}
curl -sf -o /dev/null -w 'HTTP %{http_code}\n' --max-time 10 \
  "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/\
NM_000088.4:c.589G%3ET/all?content-type=application/json"
\end{verbatim}

\textbf{HTTP 200} = healthy. Stop here.

\textbf{HTTP 000} = unreachable. Continue below.

\textbf{HTTP 5xx} = app erroring. See SOP Section 4.4 / 5.3.

\medskip

\textbf{Container check}

\begin{verbatim}
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -i variantvalidator
\end{verbatim}

If any of the 4 containers is missing or not \texttt{Up}:

\begin{verbatim}
cd ~/targeted-seq-pipeline/software/rest_variantValidator
docker compose up -d
sleep 30
\end{verbatim}

\medskip

\textbf{Gunicorn check (the most important one)}

\begin{verbatim}
docker exec rest_variantvalidator-rest-variantvalidator-1 ps -ef \
  | grep -E '[g]unicorn'
\end{verbatim}

If empty (most common cause of failure):

\begin{verbatim}
docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
  bash -c 'cd /app/rest_VariantValidator && \
gunicorn -b 0.0.0.0:5000 --timeout 600 app --threads=5'
sleep 90    # CRITICAL — worker takes 60–120s to warm up
\end{verbatim}

Re-run health check.

\medskip

\textbf{Still failing? Read the app log}

\begin{verbatim}
docker exec rest_variantvalidator-rest-variantvalidator-1 \
  tail -n 100 /tmp/vv_error.log
\end{verbatim}

Escalate if: DatabaseError, MemoryError, or repeated worker crashes.

\medskip

\textbf{After recovery: resume the pipeline}

\begin{verbatim}
cd /goast/hemat_data/nf-core-tspipe
nextflow run . --input samplesheet.csv \
  --outdir test_run/<same-as-before> \
  -profile gandalf,singularity -resume -bg
\end{verbatim}
}}

# Appendix B: Incident Log

The team should maintain a running log of VV incidents in this
appendix as new entries are appended in chronological order. At
minimum each entry records:

- Date, time, batch ID
- Symptom observed
- Failure mode (A / B / C / D from Section 3)
- Recovery procedure used
- Time to recovery
- Notes / anything the SOP did not predict

A template:

```
## Incident YYYY-MM-DD HH:MM
Batch:           <batch-id>
Symptom:         <one-line description>
Failure mode:    <A / B / C / D>
Procedure used:  <5.x>
Time to recovery:<minutes>
Notes:           <anything new the team learned>
```

## Incident 2026-05-22 14:48

**Batch:** `20260522_144827` (sample `26CGH775-MYCNV`)

**Symptom:** `TSPIPE:ANNOTATION:VARIANT_VALIDATOR` exited with status 1;
`.command.err` showed `Cannot connect to VariantValidator at http://localhost:5001`.

**Failure mode:** B (containers `Up`, gunicorn process dead inside the
REST container). Confirmed via
`docker exec rest_variantvalidator-rest-variantvalidator-1 ps -ef | grep gunicorn`
returning empty output.

**Procedure used:** Section 5.2 (manual gunicorn start). This SOP was
authored retrospectively during the incident response itself; the
procedure is now codified in Section 5.2 above.

**Time to recovery:** Approximately 25 minutes wall-clock, the majority
spent on SOP authorship. Gunicorn warm-up alone was about 3 minutes
after the manual restart command.

**Verification:** Pipeline resume launched at 17:20:24 passed VV
preflight (`HTTP 200` returned in 1 second) and completed cleanly with
38 cached tasks reused over an 8-second total wall time. Clinical output
published at `test_run/20260522_144827/26CGH775-MYCNV/clinical/`.

**Root cause:** Not investigated in depth. The container itself did not
restart; only the `gunicorn` process inside it died. Possible causes
include worker OOM, accidental interaction with the container, or an
upstream signal. Worth a follow-up if the pattern recurs.

**Follow-up actions delivered after this incident:**

- `docs/sops/vv_troubleshooting.md` (this document)
- `scripts/launch_tspipe.sh` - preflight wrapper with VV health probe
  and bounded auto-recovery
- Retry-on-startup-connection-failure block in
  `scripts/17_variant_validator.py` (3 attempts at 30 / 60 / 120 s
  exponential backoff)
- Mirror copies of the above in the `nf-core-tspipe` repository


# Appendix C: Glossary

**gunicorn** — Python WSGI HTTP server. The process inside the REST
container that actually serves HTTP requests for VV. If gunicorn is
not running, the endpoint returns nothing.

**HTTP 000** — Not a real HTTP code. `curl` reports `000` when the
connection itself could not be established (refused, timed out, no
listener). Functionally synonymous with "VV is unreachable."

**MANE Select** — Matched Annotation from NCBI and EMBL-EBI Select.
The canonical transcript per gene, used as the default in HGVS
queries.

**REST API** — The HTTP interface VV exposes. Pipeline scripts make
GET requests to `http://localhost:5001/VariantValidator/...`.

**SeqRepo** — Sequence repository providing reference sequence access.
One of VV's backing data stores.

**VVTA** — VariantValidator Transcript Annotation database. A
PostgreSQL database holding transcript-level annotations.

**VDB** — VariantValidator validation database. The second backing
data store.

**worker warm-up** — When gunicorn first starts, its worker process
must load HGVS libraries, open database connections, and populate
in-memory caches before it can serve requests. This takes 60 to 120
seconds. Until warm-up completes, the worker appears at near-100%
CPU and the endpoint will not respond.

# Appendix D: Document History

| Version | Date         | Author           | Changes                          |
|---------|--------------|------------------|----------------------------------|
| 1.0     | 2026-05-22   | Hematology Lab   | Initial release                  |

\noindent The canonical source of this SOP is the
`docs/sops/vv_troubleshooting.md` file in the
`targeted-seq-pipeline` repository on GitHub. All edits should be
made via pull request; the PDF for circulation is a rendered
artifact and should not be edited directly.
