# 2026-05-19 — Morning findings & VV stack migration

## Headline

VV REST stack's PostgreSQL (VVTA) and MySQL (VDB) databases were running on
**anonymous Docker volumes**. This was the actual root cause of yesterday's
"VV stack crashes three times under load" symptom — every `docker compose down`
cycle risked orphaning the data volumes and yielding an empty cluster on next
`up`. Migrated both databases to named persistent volumes. Migration verified
end-to-end with live queries.

Yesterday's audit-recommended fix ("migrate `/var/lib/docker` to `/goast`") was
based on a wrong premise and was NOT done. Reasoning below.

---

## Corrections to docs/audit/2026-05-18/end_of_day.md

The 2026-05-18 audit had three factual errors that the bootstrap then carried
forward as today's priority 1:

1. **"Move `/var/lib/docker` from `/` (70 GB)"** — `/var/lib/docker` does not
   exist on this host. Docker's data-root was already at `/home/hemat/docker-data`
   (set in `/etc/docker/daemon.json` as `"data-root": "/home/hemat/docker-data"`).
   It had been moved off `/var/lib/docker` at some prior point.

2. **"Disk pressure on `/` (70 GB, 23% used)"** — `/` is fine (23% used, 55G
   free). The actual disk pressure was on `/home` (97% / 13G free) where the
   Docker data-root lives, AND on `/goast` (90% / 759G free) where pipeline
   output lands. Both contributed to yesterday's crashes via different
   mechanisms.

3. **"VV REST recovery procedure: refresh matviews after `docker compose up`"** —
   This is symptomatic, not causal. The real reason matviews needed refreshing
   was that PGDATA was empty: the anonymous volume holding VVTA was orphaned
   during a `docker compose down`/up cycle, so postgres came up with a fresh
   data directory, re-ran `docker-entrypoint-initdb.d/` (which only seeds
   schema/roles), and presented empty matviews to the pipeline.

The log evidence is in `/goast/hemat_data/vv_migration_20260519/migration_logs/`
(see `migrate_20260519_073220.log`) and the docker logs captured around
2026-05-18 14:39 UTC showing `FATAL: role "vvta_admin" does not exist` and
`materialized view "transcript_lengths_mv" has not been populated` — both
consistent with a fresh, mostly-empty postgres cluster.

---

## What was actually done today

### 1. Disk reclaim on /goast (90% → 87%)

- Emptied `/goast/.Trash-1005/files/` — reclaimed ~244 GB. Contents were
  primarily methylation work (`beta_matrices*`, `ayush 1`, `ayush 2`,
  `GSE136724`). If UID 1005 was ayush, his trash is now empty.
- Deleted orphan `/goast/docker-data/` (168K, empty, mtime 2026-04-07). This
  was the artifact from a previous abandoned migration that had confused
  yesterday's audit.
- Deleted `ichorcna.tar` and `ichorcna_v1.3.tar` under
  `/goast/hemat_data/temp/docker/ichorcna/` — image is loaded in Docker as
  `molhemat/ichorcna:1.3` and recreatable with `docker save`. Saved ~6 GB.
  Kept `ichorcna_v1.2.tar`, Dockerfile, build.log, R libraries.

### 2. Disk reclaim on /home (97% → 94%)

- `docker container prune` removed 16 stopped containers (~182 MB).
- `docker builder prune` removed stale build cache (~184 MB).
- Removed four large unused images: `nanoporetech/dorado` (14.6G),
  `sparse-nn` + `molhemat/sparse-nn` (8.4G unique), `r-keras` +
  `molhemat/r-keras` (2.1G unique), `rocker/ml` (6.5G unique once r-keras
  was removed). Total ~31 GB reclaim from images.
- Removed old anonymous volumes from VV stack after migration verification
  (~5 GB).
- Net `/home` change: 97% → 94%, 13G → 26G free.

### 3. VV stack volume migration (the main event)

**Diagnosis path:**

- `df -h` showed `/home` at 97%, where Docker data-root lives. Yesterday's
  audit blamed `/var/lib/docker` on `/`, which doesn't exist.
- `docker logs` on `rest_variantvalidator-rv-vvta-1` showed yesterday's
  failure signature: `FATAL: role "vvta_admin" does not exist` followed by
  `ERROR: relation "transcript_lengths_mv" does not exist` — postgres
  starting against an empty cluster.
- `ls -la` on the VVTA data volume showed every file mtime'd to May 18,
  confirming a fresh `initdb` had happened yesterday (the "rv-vdb crashed
  mid-init: recreated from clean state" line in yesterday's audit was true
  of VVTA too).
- Reading the compose file at
  `/goast/hemat_data/targeted-seq-pipeline/software/rest_variantValidator/docker-compose.yml`
  revealed `rv-vdb` and `rv-vvta` had **no volume declarations**. They were
  relying on Docker auto-creating anonymous volumes for the `VOLUME`
  directives baked into the postgres/mysql base images. Anonymous volumes
  detach from containers on recreation.

**Migration steps (preserved in
`/goast/hemat_data/vv_migration_20260519/migration_logs/`):**

1. Tarball backup of live VVTA (876 MB compressed from 4 GB raw) and VDB
   (81 MB from 713 MB raw) to `/goast/hemat_data/vv_migration_20260519/`.
   Backups taken with postgres/mysql still running — not crash-consistent
   but acceptable given the additional safety nets.
2. `docker compose down` (no `-v`) — anonymous volumes preserved on disk.
3. Created named volumes `rest_variantvalidator_vvta-data` and
   `rest_variantvalidator_vdb-data` with `docker volume create`.
4. Copied data from old anonymous volumes to new named volumes using
   `docker run` with both volumes mounted. File counts matched
   (1413 VVTA, 175 VDB).
5. Updated compose file to declare named volumes. Backup at
   `docker-compose.yml.bak_20260519_073220`.
6. `docker compose up -d --remove-orphans` — all 4 containers came up clean.

**Verification:**

- `\du` in VVTA shows `uta_admin` role with Superuser intact.
- `\dn` shows `vvta_2025_02` schema present.
- All 10 matviews populated (`ispopulated = t`).
- `SELECT count(*) FROM vvta_2025_02.transcript_lengths_mv;` returns 459044.
- `GET /VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G>T/all`
  returns HTTP 200 with correct COL1A1 annotations.

---

## Issues encountered and lessons

### My (Claude's) script errors during migration

Three errors in the migration script that the user's vigilance caught:

1. **Broken sha256 verification.** Script ran `tar --sort=name -cf - .
   | sha256sum` inside an alpine container; busybox `tar` doesn't support
   `--sort=name`, so the pipeline silently failed and `sha256sum` hashed
   nothing. Returned `e3b0c442...b855` (the empty-string hash) for both
   source and destination and declared "byte-identical." We were lucky
   `cp -a` is reliable. File-count verification still ran and passed.
   *Lesson: never write a verification check without exercising it
   against a known-good and known-bad case first.*

2. **`$HOME` evaluates to `/root` under `sudo`.** The compose file used
   `${HOME}/variantvalidator_data/seqdata` as the bind-mount source. When
   compose re-evaluated this on `up`, `$HOME` was `/root` (not `/home/hemat`)
   because compose was run via sudo. Fixed by hardcoding absolute paths.
   *Lesson: pre-flight checks should include `compose config` output to
   surface variable expansion before any state change.*

3. **Case-sensitive `YES` confirmation aborted mid-migration.** User typed
   `yes`, script wanted `YES`. Compose file was already edited when the
   script aborted, leaving in-between state. Recovered by hand-editing.
   *Lesson: confirmation prompts should accept case-insensitive y/yes/Y/YES,
   or fail before any state-changing action.*

### Gunicorn 3-worker boot

Today's gunicorn launches with `--workers 3` repeatedly failed: all three
workers hit 99% CPU during VV library initialization, then died before
completing boot. Hypothesis: resource contention during simultaneous
metadata load (memory, postgres connection limits, or boot deadline).

`--workers 1 --threads 5` runs fine and is what's currently in production.
VV REST is now serving on port 8000 with this config.

### Trash deletion ownership

`/goast/.Trash-1005/` was UID 1005's trash. Did not verify whose UID 1005
was before emptying. If 1005 was ayush, his trash (including methylation
artifacts from his classifier work) is permanently gone. User chose to
proceed without verifying ownership.

---

## Open items for tomorrow / later

| Item | Why deferred |
|---|---|
| Investigate gunicorn 3-worker failure | Workaround in place. 1 worker × 5 threads sufficient for current pipeline throughput. Worth revisiting with `--preload` or staggered boot for production scaling. |
| `$HOME → /root` bug in compose file | Hardcoded `/home/hemat` paths today. Should switch to `.env` file with explicit `HOST_VV_DATA=/home/hemat/variantvalidator_data` so sudo evaluation doesn't matter. |
| VV gunicorn auto-start | Currently a manual `docker exec -d ... gunicorn ...` step after `compose up`. Belongs in container entrypoint or a compose-launched sidecar. Yesterday's audit noted this as a known issue too. |
| VV healthcheck script (`tools/vv_healthcheck.sh`) | Was yesterday's priority 1b. Now lower priority — the root cause is fixed, no longer firefighting symptoms. Worth writing in next dedicated infra session. |
| Old anonymous volumes already removed; tarballs on /goast retained as cold backup | Keep tarballs for ~1 week of pipeline traffic, then delete. Path: `/goast/hemat_data/vv_migration_20260519/*.tgz`. |

---

## Recovery runbook (replaces yesterday's "VV REST recovery procedure")

If the VV stack needs to be brought up from scratch:

```bash
cd /goast/hemat_data/targeted-seq-pipeline/software/rest_variantValidator

# 1. Start the stack — named volumes will be reused, no data loss.
sudo docker compose up -d

# 2. Wait for postgres/mysql to be ready
sleep 20

# 3. Launch gunicorn manually (not auto-started by compose).
sudo docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
    gunicorn -b 0.0.0.0:8000 --workers 1 --threads 5 --timeout 600 \
    wsgi:app --chdir ./rest_VariantValidator/

# 4. Wait for VV library init (60-90s for full warm-up)
sleep 90

# 5. Verify
sudo docker exec rest_variantvalidator-rest-variantvalidator-1 ps -ef | grep gunicorn
curl -i -m 60 "http://localhost:8000/VariantValidator/variantvalidator/GRCh38/NM_000088.4%3Ac.589G%3ET/all" | head -10
```

**Do NOT** run `docker compose down -v` or `docker volume prune` against this
project — that would delete the named data volumes. The named volumes are now
the persistent store.

---

## Disk-state at end of session

```
Filesystem              Size  Used Avail Use%  Mounted on
/dev/mapper/rl-root      70G   16G   55G  23%  /
/dev/mapper/rl-home     372G  346G   26G  94%  /home
/dev/mapper/goast-data  7.0T  6.1T  957G  87%  /goast
```

`/home` still tight at 94%. Long-term plan should consider either:
- Migrating Docker data-root to a roomier filesystem (the original "move
  Docker" intent, but to `/goast` not `/var/lib/docker`), or
- Expanding `/home`'s LVM (if free PEs available in the `rl` VG).

Not a today problem; not on fire.

---

## Time accounting

Morning session ran ~3 hours on infrastructure. Pipeline backlog
(B1, D2, B5, B4, B2, D1, coverage drift, containerization) remains open
for the remainder of today / tomorrow.
