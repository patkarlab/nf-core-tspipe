#!/usr/bin/env python3
"""
portability_inventory.py -- generated portability inventory for nf-core-tspipe (FREEZE step 1).

For every process it resolves the effective runtime on a given config chain (module directives,
then the config files in the order Nextflow loads them: general process settings < withLabel <
withName; later files win), classifies it (public container / local image / host environment),
lists the host conda environments and tool paths it depends on, and records every params.* it
uses. It also lists every absolute-path literal (/goast, /home/hemat, anaconda3) in code versus
comments, every params.* defined or referenced and where, every reference/asset path the
effective params point at (with existence and size when --check-paths is given), and every
network endpoint the pipeline or its scripts call.

Usage (repo root):
    python3 tools/portability_inventory.py \\
        --configs conf/modules.config conf/gandalf.config conf/twist_apply.config \\
        --entry workflows/tspipe.nf --check-paths \\
        --out docs/audit/2026-09-10/portability_inventory.md

nextflow.config and conf/base.config are always read first (they are part of every run);
--configs lists the profile and -c overlays in load order. Nothing in the repo is modified.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict
from datetime import date

RUNTIME_KEYS = ("container", "conda", "executor", "beforeScript", "maxForks", "cache", "shell")
LITERAL_RE = re.compile(r"(/goast/[^\s'\"`)\],;}]+|/home/hemat/[^\s'\"`)\],;}]+|[^\s'\"`)\],;}]*anaconda3/[^\s'\"`)\],;}]+)")
PARAM_REF_RE = re.compile(r"params\.([A-Za-z_][A-Za-z0-9_]*)")
PARAM_METHODS = {"containsKey", "get", "each", "keySet", "findAll", "collect", "put", "remove", "size"}
URL_RE = re.compile(r"https?://[^\s'\"`)\]<>,;]+")
NET_WORD_RE = re.compile(r"\b(curl|wget|requests\.(get|post|Session)|urllib\.request|urlopen|http\.client|httpx)\b")
ENV_RE = re.compile(r"anaconda3/envs/([A-Za-z0-9_.-]+)")
SCRIPT_RE = re.compile(r"(?<![\w/.-])([\w./-]+\.(?:py|sh|R|pl|jar))\b")
SHELL_NOISE = {
    "if", "then", "else", "elif", "fi", "for", "do", "done", "while", "case", "esac", "echo", "cat",
    "mkdir", "ln", "cp", "mv", "rm", "set", "export", "printf", "touch", "cd", "ls", "exit", "awk",
    "sed", "grep", "sort", "head", "tail", "cut", "tr", "gunzip", "zcat", "gzip", "wc", "uniq", "xargs",
    "readlink", "realpath", "basename", "dirname", "true", "false", "test", "return", "local", "read",
    "END_VERSIONS", "stub:", "script:", "def", "cat", "tee", "find", "chmod", "date", "sleep", "pwd",
    "paste", "join", "comm", "diff", "seq", "bash", "sh", "env", "source", "unset", "eval", "trap",
    "continue", "break", "rc=\\$?", "in", "shift",
}


# --------------------------------------------------------------------------------------------
# Low-level text helpers
# --------------------------------------------------------------------------------------------

def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def is_comment_line(line, ext):
    s = line.strip()
    if ext in (".py", ".sh", ".R", ".pl", ".txt", ".md", ".yml", ".yaml", ".tsv", ".csv"):
        return s.startswith("#")
    return s.startswith("//") or s.startswith("*") or s.startswith("/*") or s.startswith("#")


def match_brace(text, open_pos):
    """Return the index of the '}' matching the '{' at open_pos, skipping strings and comments."""
    depth = 0
    i = open_pos
    n = len(text)
    while i < n:
        c = text[i]
        two = text[i:i + 2]
        three = text[i:i + 3]
        if two == "//":
            j = text.find("\n", i)
            i = n if j < 0 else j + 1
            continue
        if two == "/*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if three in ('"""', "'''"):
            j = text.find(three, i + 3)
            i = n if j < 0 else j + 3
            continue
        if c in ("'", '"'):
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                j += 1
            i = j + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def find_blocks(text, header_re):
    """Yield (match, body, header_line) for every 'header {' block; header_re must end before '{'."""
    for m in header_re.finditer(text):
        open_pos = text.find("{", m.end())
        if open_pos < 0:
            continue
        close_pos = match_brace(text, open_pos)
        if close_pos < 0:
            continue
        yield m, text[open_pos + 1:close_pos], line_of(text, m.start()), open_pos, close_pos


def strip_comment(s):
    """Remove a trailing // comment that is outside quotes."""
    q = None
    i = 0
    while i < len(s) - 1:
        c = s[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in ("'", '"'):
            q = c
        elif s[i:i + 2] == "//":
            return s[:i].rstrip()
        i += 1
    return s


def strip_quotes(v):
    v = v.strip()
    for q in ('"""', "'''"):
        if v.startswith(q) and v.endswith(q) and len(v) >= 6:
            return v[3:-3].strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def parse_assignments(body):
    """Parse `key = value` statements in a config block body (skipping nested { } and [ ] values)."""
    out = OrderedDict()
    i = 0
    n = len(body)
    stmt_re = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=\s*", re.M)
    while True:
        m = stmt_re.search(body, i)
        if not m:
            break
        key = m.group(1)
        j = m.end()
        if j >= n:
            break
        c = body[j]
        if c == "[":
            depth = 0
            k = j
            while k < n:
                if body[k] == "[":
                    depth += 1
                elif body[k] == "]":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            value = body[j:k + 1]
            i = k + 1
        elif c == "{":
            k = match_brace(body, j)
            value = body[j:k + 1] if k > 0 else body[j:]
            i = k + 1 if k > 0 else n
        elif body[j:j + 3] in ('"""', "'''"):
            q = body[j:j + 3]
            k = body.find(q, j + 3)
            value = body[j:k + 3] if k > 0 else body[j:]
            i = k + 3 if k > 0 else n
        else:
            k = body.find("\n", j)
            k = n if k < 0 else k
            value = body[j:k]
            i = k + 1
        value = strip_comment(value.strip())
        out[key] = (value, line_of(body, m.start()))
    return out


# --------------------------------------------------------------------------------------------
# Modules: process definitions
# --------------------------------------------------------------------------------------------

PROCESS_RE = re.compile(r"^\s*process\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?=\{)", re.M)
SECTION_RE = re.compile(r"^\s*(input|output|when|script|shell|exec|stub):", re.M)


def parse_process(body, header_line):
    m = SECTION_RE.search(body)
    directives_text = body[:m.start()] if m else body
    rest = body[m.start():] if m else ""
    d = OrderedDict()
    labels = []
    for line in directives_text.splitlines():
        s = line.strip()
        s = strip_comment(s)
        mm = re.match(r"^(container|conda|executor|beforeScript|maxForks|cache|shell|label|tag|publishDir)\s+(.*)$", s)
        if not mm:
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if key == "label":
            labels.append(strip_quotes(val))
        elif key in ("tag", "publishDir"):
            continue
        else:
            d[key] = strip_quotes(val)
    params = sorted(set(p for p in PARAM_REF_RE.findall(body) if p not in PARAM_METHODS))
    scripts = sorted(set(SCRIPT_RE.findall(rest)))
    projectdir_refs = sorted(set(re.findall(r"\$\{projectDir\}/[^\s'\"`)\]}]+", rest)))
    literals = sorted(set(x for x in LITERAL_RE.findall(rest)))
    tools = []
    in_str = False
    for line in rest.splitlines():
        s = line.strip()
        if s.count('"""') % 2 == 1:
            in_str = not in_str
            continue
        if not in_str or not s or s.startswith("#") or s.startswith("\\") or s.startswith("-") or s.startswith("|") or s.startswith("<"):
            continue
        if s.startswith("${") or s.startswith("\\$") or s.startswith("$") or "=" in s.split()[0]:
            tok0 = s.split()[0]
            if not tok0.startswith("${params.") and not tok0.startswith("${py}") and not tok0.startswith("${cfg_bin}"):
                continue
        tok = s.split()[0]
        tok = re.sub(r"^\$\{params\.(\w+)\}", r"<params.\1>", tok)
        if tok in SHELL_NOISE or tok.endswith(":") or not re.match(r"^[A-Za-z<][A-Za-z0-9_./<>-]*$", tok):
            continue
        if tok.endswith(".yml") or tok.endswith(".tsv") or tok.endswith(".txt") or tok.startswith("*"):
            continue
        tools.append(tok)
    tools = sorted(set(tools))
    return {
        "directives": d,
        "labels": labels,
        "params": params,
        "scripts": scripts,
        "projectdir_refs": projectdir_refs,
        "literals": literals,
        "tools": tools,
        "header_line": header_line,
    }


def scan_modules(repo):
    procs = OrderedDict()
    for root in ("modules", "subworkflows", "workflows"):
        base = os.path.join(repo, root)
        if not os.path.isdir(base):
            continue
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith(".nf") or ".bak_" in fn:
                    continue
                path = os.path.join(dp, fn)
                text = read_text(path)
                for m, body, hl, _, _ in find_blocks(text, PROCESS_RE):
                    name = m.group(1)
                    info = parse_process(body, hl)
                    info["file"] = os.path.relpath(path, repo)
                    if name in procs:
                        info["duplicate_of"] = procs[name]["file"]
                    procs[name] = info
    return procs


# --------------------------------------------------------------------------------------------
# Configs: params and process selectors
# --------------------------------------------------------------------------------------------

def parse_config(path):
    text = read_text(path)
    result = {"params": OrderedDict(), "general": OrderedDict(), "withName": [], "withLabel": [], "misc": OrderedDict()}
    # profile bodies are applied only when selected; the selected profile's file is passed in --configs
    for m, body, hl, o, c in list(find_blocks(text, re.compile(r"^\s*profiles\s*(?=\{)", re.M))):
        text = text[:o + 1] + re.sub(r"[^\n]", " ", text[o + 1:c]) + text[c:]
    # params { } blocks (top-level only: skip those nested in profiles)
    for m, body, hl, o, c in find_blocks(text, re.compile(r"^\s*params\s*(?=\{)", re.M)):
        for k, (v, ln) in parse_assignments(body).items():
            result["params"][k] = (v, hl + ln - 1)
    # process { } blocks
    for m, body, hl, o, c in find_blocks(text, re.compile(r"^\s*process\s*(?=\{)", re.M)):
        sel_re = re.compile(r"^\s*(withName|withLabel)\s*:\s*(['\"])(.+?)\2\s*(?=\{)", re.M)
        inner_spans = []
        for sm, sbody, shl, so, sc in find_blocks(body, sel_re):
            inner_spans.append((so, sc))
            kind, pattern = sm.group(1), sm.group(3)
            assigns = OrderedDict((k, v) for k, (v, ln) in parse_assignments(sbody).items())
            result[kind].append({"pattern": pattern, "line": shl + hl - 1, "assign": assigns})
        # general assignments = those outside selector blocks
        masked = list(body)
        for so, sc in inner_spans:
            for k in range(so, sc + 1):
                masked[k] = " "
        masked = "".join(masked)
        masked = re.sub(r"^\s*(withName|withLabel)\s*:.*$", "", masked, flags=re.M)
        for k, (v, ln) in parse_assignments(masked).items():
            result["general"][k] = v
    # top-level `params.X = ...` assignments (outside a params { } block)
    for m in re.finditer(r"^\s*params\.(\w+)\s*=\s*(.+)$", text, re.M):
        result["params"].setdefault(m.group(1), (strip_comment(m.group(2).strip()), line_of(text, m.start())))
    # one-line process.X = ... and scope settings
    for m in re.finditer(r"^\s*process\.(\w+)\s*=\s*(.+)$", text, re.M):
        result["general"][m.group(1)] = strip_comment(m.group(2).strip())
    for scope in ("singularity", "docker", "conda", "executor", "env"):
        for m, body, hl, o, c in find_blocks(text, re.compile(r"^\s*%s\s*(?=\{)" % scope, re.M)):
            for k, (v, ln) in parse_assignments(body).items():
                result["misc"]["%s.%s" % (scope, k)] = v
    for m in re.finditer(r"^\s*includeConfig\s+['\"]([^'\"]+)['\"]", text, re.M):
        result["misc"].setdefault("includeConfig", []).append(m.group(1))
    return result


def selector_matches(pattern, name, labels=None):
    pats = [p.strip() for p in pattern.split("|")]
    for p in pats:
        if labels is not None:
            if p in labels:
                return True
            continue
        try:
            if re.fullmatch(p, name):
                return True
        except re.error:
            if p == name:
                return True
    return False


def resolve_runtime(procs, chain):
    """chain: list of (filename, parsed_config) in load order."""
    for name, info in procs.items():
        eff = OrderedDict((k, None) for k in RUNTIME_KEYS)
        prov = OrderedDict((k, None) for k in RUNTIME_KEYS)
        for k, v in info["directives"].items():
            if k in eff:
                eff[k] = v
                prov[k] = "module %s:%d" % (info["file"], info["header_line"])
        levels = [[], [], []]  # general, label, name -> list of (key, val, source)
        for fname, cfg in chain:
            for k, v in cfg["general"].items():
                if k in eff:
                    levels[0].append((k, v, "%s general" % fname))
            for blk in cfg["withLabel"]:
                if selector_matches(blk["pattern"], name, labels=info["labels"]):
                    for k, v in blk["assign"].items():
                        if k in eff:
                            levels[1].append((k, v, "%s withLabel '%s' L%d" % (fname, blk["pattern"], blk["line"])))
            for blk in cfg["withName"]:
                if selector_matches(blk["pattern"], name):
                    for k, v in blk["assign"].items():
                        if k in eff:
                            levels[2].append((k, v, "%s withName '%s' L%d" % (fname, blk["pattern"], blk["line"])))
        for lvl in levels:
            for k, v, src in lvl:
                eff[k] = strip_quotes(v)
                prov[k] = src
        info["effective"] = eff
        info["provenance"] = prov
        info["ext"] = OrderedDict()
        for fname, cfg in chain:
            for blk in cfg["withName"]:
                if selector_matches(blk["pattern"], name):
                    for k, v in blk["assign"].items():
                        if k.startswith("ext."):
                            info["ext"][k] = (strip_quotes(v), fname)


def classify(info, param_values):
    eff = info["effective"]
    cont = eff.get("container")
    if cont and cont.lower() != "null":
        img = cont.replace("docker://", "")
        if img.startswith("local/"):
            return "LOCAL_IMAGE", img
        return "PUBLIC_IMAGE", img
    envs = []
    bs = eff.get("beforeScript") or ""
    envs += ENV_RE.findall(bs)
    for p in info["params"]:
        val = param_values.get(p)
        if val and "anaconda3/envs/" in val:
            envs += ENV_RE.findall(val)
    for lit in info["literals"]:
        envs += ENV_RE.findall(lit)
    if any(s.startswith("conda run -n") for s in info["tools"]):
        envs.append("(conda run)")
    envs = sorted(set(envs))
    conda_dir = eff.get("conda")
    if conda_dir and conda_dir.lower() != "null":
        envs.append("conda directive: %s" % conda_dir)
    return "HOST", ", ".join(envs) if envs else "(global beforeScript env)"


# --------------------------------------------------------------------------------------------
# Params resolution
# --------------------------------------------------------------------------------------------

def collect_params(chain):
    """name -> list of (file, raw_value, line) in load order; effective = last."""
    defs = OrderedDict()
    for fname, cfg in chain:
        for k, (v, hl) in cfg["params"].items():
            defs.setdefault(k, []).append((fname, v, hl))
    return defs


def substitute(value, values, project_dir, depth=0):
    if value is None or depth > 8:
        return value
    v = strip_quotes(value)
    v = v.replace("${projectDir}", project_dir).replace("$projectDir", project_dir)
    changed = True
    while changed and depth < 8:
        changed = False
        for m in re.finditer(r"\$\{params\.([A-Za-z_]\w*)\}", v):
            inner = values.get(m.group(1))
            if inner is not None:
                v = v.replace(m.group(0), strip_quotes(inner))
                changed = True
        depth += 1
    return v


def effective_param_values(defs, project_dir):
    raw = OrderedDict((k, lst[-1][1]) for k, lst in defs.items())
    vals = OrderedDict()
    for k, v in raw.items():
        vals[k] = substitute(v, raw, project_dir)
    return vals


def looks_like_path(v):
    if not v or v in ("null", "true", "false"):
        return False
    return v.startswith("/") or v.startswith("${projectDir}")


# --------------------------------------------------------------------------------------------
# Repo-wide scans
# --------------------------------------------------------------------------------------------

SCAN_DIRS = ("nextflow.config", "main.nf", "conf", "modules", "subworkflows", "workflows", "bin", "tools", "launch_tspipe.sh")
SKIP_EXT = (".pyc", ".png", ".jpg", ".gz", ".zip", ".tgz", ".woff", ".woff2", ".ttf", ".ico", ".svg", ".bam", ".bai", ".hdf5", ".rds", ".RData", ".img", ".sif", ".pdf")


def iter_scan_files(repo, extra_dirs=()):
    for entry in SCAN_DIRS + tuple(extra_dirs):
        p = os.path.join(repo, entry)
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for dp, dns, fns in os.walk(p):
                dns[:] = [d for d in dns if d not in ("__pycache__", "node_modules", ".git", "work") and not d.startswith(".")]
                for fn in sorted(fns):
                    if fn.endswith(SKIP_EXT) or ".bak_" in fn:
                        continue
                    yield os.path.join(dp, fn)


def scan_literals(repo):
    hits = []
    for path in iter_scan_files(repo):
        rel = os.path.relpath(path, repo)
        ext = os.path.splitext(path)[1]
        try:
            text = read_text(path)
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for lit in LITERAL_RE.findall(line):
                hits.append({"file": rel, "line": i, "literal": lit, "comment": is_comment_line(line, ext)})
    return hits


def scan_param_refs(repo):
    refs = defaultdict(list)
    guarded = defaultdict(set)
    for path in iter_scan_files(repo):
        if not (path.endswith(".nf") or path.endswith(".config")):
            continue
        rel = os.path.relpath(path, repo)
        text = read_text(path)
        for m in re.finditer(r"containsKey\(\s*['\"](\w+)['\"]\s*\)", text):
            guarded[m.group(1)].add(rel)
        for i, line in enumerate(text.splitlines(), 1):
            for m in PARAM_REF_RE.finditer(line):
                p = m.group(1)
                if p in PARAM_METHODS or line[m.end():m.end() + 1] == "*":
                    continue
                refs[p].append((rel, i))
    return refs, guarded


def scan_network(repo):
    hits = []
    for path in iter_scan_files(repo):
        rel = os.path.relpath(path, repo)
        ext = os.path.splitext(path)[1]
        if ext not in (".nf", ".config", ".py", ".sh", ".R", ".pl", ".js", ".j2", ".html"):
            continue
        text = read_text(path)
        for i, line in enumerate(text.splitlines(), 1):
            urls = URL_RE.findall(line)
            words = NET_WORD_RE.findall(line)
            if urls or words:
                hits.append({"file": rel, "line": i, "urls": urls, "calls": [w[0] for w in words],
                             "comment": is_comment_line(line, ext), "text": line.strip()[:140]})
    return hits


def scan_projectdir_assets(repo, panel):
    refs = OrderedDict()
    for path in iter_scan_files(repo):
        if not path.endswith(".nf"):
            continue
        rel = os.path.relpath(path, repo)
        text = read_text(path)
        for i, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"\$\{projectDir\}/((?:\$\{params\.\w+\}|[^\s'\"`)\]}])+)", line):
                p = m.group(1).replace("${params.panel}", panel)
                if "${" in p:
                    continue
                refs.setdefault(p, []).append("%s:%d" % (rel, i))
    return refs


def include_reachability(repo, entry):
    """Process names reachable from an entry .nf through include chains."""
    seen_files = set()
    reached = set()
    stack = [entry]
    inc_re = re.compile(r"include\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]+)['\"]")
    while stack:
        f = stack.pop()
        f_abs = os.path.join(repo, f) if not os.path.isabs(f) else f
        if not f_abs.endswith(".nf"):
            f_abs += ".nf"
        f_abs = os.path.normpath(f_abs)
        if f_abs in seen_files or not os.path.isfile(f_abs):
            continue
        seen_files.add(f_abs)
        text = read_text(f_abs)
        for m in PROCESS_RE.finditer(text):
            reached.add(m.group(1))
        for m in inc_re.finditer(text):
            target = m.group(2)
            t_abs = os.path.normpath(os.path.join(os.path.dirname(f_abs), target))
            stack.append(t_abs)
    return reached


# --------------------------------------------------------------------------------------------
# Filesystem checks
# --------------------------------------------------------------------------------------------

def stat_path(p, do_md5=False, md5_limit=2 * 1024 ** 3):
    if not p or "${" in p:
        return {"status": "UNRESOLVED"}
    if os.path.isdir(p):
        try:
            n = len(os.listdir(p))
        except OSError:
            n = -1
        return {"status": "DIR", "entries": n}
    if os.path.isfile(p):
        size = os.path.getsize(p)
        rec = {"status": "FILE", "size": size}
        if do_md5 and size <= md5_limit:
            h = hashlib.md5()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            rec["md5"] = h.hexdigest()
        return rec
    return {"status": "MISSING"}


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return "%.0f %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f PB" % n


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------

def md_escape(s):
    return str(s).replace("|", "\\|")


def build_report(args, procs, chain, defs, values, refs, guarded, literals, network, asset_refs, reach, stats):
    today = date.today().isoformat()
    lines = []
    A = lines.append
    A("# Portability inventory -- nf-core-tspipe (generated %s)" % today)
    A("")
    A("Generated by `tools/portability_inventory.py` (repo untouched). Config chain: `nextflow.config`, "
      "`conf/base.config`, then %s. Resolution rule applied: module directive < general process "
      "setting < withLabel < withName; later files win for the same directive. Tool lists are heuristic "
      "(first token of each script line). Paths were %s." % (
          ", ".join("`%s`" % f for f, _ in chain[2:]),
          "stat'ed on this host" if args.check_paths else "NOT checked (run with --check-paths on gandalf)"))
    A("")
    # ---- 1. Runtime table --------------------------------------------------------------------
    counts = defaultdict(int)
    rows = []
    for name, info in procs.items():
        cls, detail = classify(info, values)
        info["class"] = cls
        info["class_detail"] = detail
        entry = "tspipe" if name in reach["tspipe"] else ("build_pon_twist" if name in reach["build_pon_twist"] else ("build_pon" if name in reach["build_pon"] else "-"))
        info["entry"] = entry
        if entry == "tspipe":
            counts[cls] += 1
        rows.append((name, info, cls, detail, entry))
    A("## 1. Process runtime (%d processes; tspipe reachable: %d)" % (len(procs), len([r for r in rows if r[4] == "tspipe"])))
    A("")
    A("tspipe processes by class: " + ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items())))
    A("")
    A("| Process | Entry | Class | Image / host env | Effective container (source) | executor | beforeScript source | Tools (heuristic) | Scripts / params.* |")
    A("|---|---|---|---|---|---|---|---|---|")
    for name, info, cls, detail, entry in sorted(rows, key=lambda r: (r[4] != "tspipe", r[2], r[0])):
        eff = info["effective"]
        prov = info["provenance"]
        cont = eff.get("container")
        cont_s = "%s (%s)" % (cont, prov["container"]) if cont else "none"
        bs = prov["beforeScript"] or "-"
        tools = ", ".join(info["tools"][:8]) + (" ..." if len(info["tools"]) > 8 else "")
        extras = ", ".join(info["scripts"][:6])
        pr = ", ".join(info["params"][:8]) + (" ..." if len(info["params"]) > 8 else "")
        A("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, entry, cls, md_escape(detail), md_escape(cont_s), eff.get("executor") or "-", md_escape(bs),
            md_escape(tools), md_escape((extras + " ; " if extras else "") + pr)))
    A("")
    # ---- 2. Host environments ----------------------------------------------------------------
    A("## 2. Host environments and tool installs the HOST-class processes depend on")
    A("")
    env_map = defaultdict(list)
    for name, info in procs.items():
        if info["class"] == "HOST" and info["entry"] != "-":
            env_map[info["class_detail"]].append(name)
    for env, names in sorted(env_map.items()):
        A("- **%s**: %s" % (env, ", ".join(sorted(names))))
    A("")
    A("Global beforeScript and scope settings from the chain (note: `conda.enabled = false` on gandalf means every "
      "`conda` directive is ignored there and the tool comes from the beforeScript PATH):")
    A("")
    for fname, cfg in chain:
        g = {k: v for k, v in cfg["general"].items() if k in RUNTIME_KEYS}
        if g or cfg["misc"]:
            A("- `%s`: general=%s; scopes=%s" % (fname, md_escape(json.dumps(g)), md_escape(json.dumps({k: v for k, v in cfg["misc"].items() if k != "includeConfig"}))))
    A("")
    A("Tool-path params (installs outside the repo) referenced by ext.* or scripts:")
    A("")
    for name, info in procs.items():
        if info["ext"]:
            A("- %s: %s" % (name, "; ".join("%s=%s (%s)" % (k, md_escape(v), f) for k, (v, f) in info["ext"].items())))
    A("")
    # ---- 3. Params ---------------------------------------------------------------------------
    A("## 3. params.* -- definitions and references")
    A("")
    A("| Param | Effective value | Defined in (load order) | Referenced in |")
    A("|---|---|---|---|")
    all_names = sorted(set(defs) | set(refs))
    undefined = []
    unused = []
    for p in all_names:
        d = defs.get(p, [])
        r = refs.get(p, [])
        dstr = "; ".join("%s:%d" % (f, hl) for f, v, hl in d) or "**UNDEFINED**"
        rfiles = sorted(set(f for f, _ in r))
        rstr = ", ".join(rfiles[:6]) + (" (+%d)" % (len(rfiles) - 6) if len(rfiles) > 6 else "") or "(unused)"
        if not d:
            undefined.append((p, sorted(set(f for f, _ in r)), p in guarded))
        if not r:
            unused.append(p)
        A("| %s | %s | %s | %s |" % (p, md_escape(values.get(p, "")), dstr, rstr))
    A("")
    if undefined:
        A("Referenced but defined in no config of this chain (null at run time unless passed on the CLI or guarded by containsKey):")
        A("")
        for p, files, g in undefined:
            A("- `params.%s`%s -- %s" % (p, " (containsKey-guarded)" if g else "", ", ".join(files)))
        A("")
    if unused:
        A("Defined but referenced nowhere in .nf/.config: " + ", ".join("`%s`" % p for p in unused))
        A("")
    # ---- 4. Reference / asset manifest -------------------------------------------------------
    A("## 4. Reference and asset paths the effective params point at")
    A("")
    A("| Param / asset | Resolved path | Status | Size / entries | md5 |")
    A("|---|---|---|---|---|")
    missing = []
    for p, v in values.items():
        if not looks_like_path(v):
            continue
        st = stats.get(("param", p), {"status": "?"})
        size = human(st["size"]) if st.get("status") == "FILE" else ("%d entries" % st["entries"] if st.get("status") == "DIR" else "")
        if st.get("status") == "MISSING":
            missing.append(v)
        A("| params.%s | %s | %s | %s | %s |" % (p, md_escape(v), st.get("status"), size, st.get("md5", "")))
    for rel, where in asset_refs.items():
        st = stats.get(("asset", rel), {"status": "?"})
        size = human(st["size"]) if st.get("status") == "FILE" else ("%d entries" % st["entries"] if st.get("status") == "DIR" else "")
        if st.get("status") == "MISSING":
            missing.append(rel)
        A("| ${projectDir}/%s (%s) | %s | %s | %s | %s |" % (md_escape(rel), md_escape(where[0]), md_escape(rel), st.get("status"), size, st.get("md5", "")))
    A("")
    if args.check_paths and missing:
        A("MISSING on this host: " + ", ".join("`%s`" % m for m in missing))
        A("")
    # ---- 4b. Bare-string path params -----------------------------------------------------------
    A("### 4b. Path-valued params used as bare strings inside process scripts")
    A("")
    A("Nextflow mounts only the work dir and staged `path` inputs into a container; these are passed as plain "
      "strings, so under Docker on clinical-23 each needs a bind mount (`docker.runOptions -v`) or conversion to a "
      "staged input. (gandalf covers them today with `singularity.runOptions -B /goast/hemat_data -B /home/hemat/programs`.)")
    A("")
    for name, info in procs.items():
        if info["entry"] == "-":
            continue
        bare = [p for p in info["params"] if looks_like_path(values.get(p, "") or "")]
        if bare:
            A("- %s: %s" % (name, ", ".join("`params.%s` = %s" % (p, md_escape(values[p])) for p in bare)))
    A("")
    # ---- 5. Literals -------------------------------------------------------------------------
    A("## 5. Absolute-path literals (/goast, /home/hemat, anaconda3)")
    A("")
    by_file = defaultdict(lambda: [0, 0])
    for h in literals:
        by_file[h["file"]][1 if h["comment"] else 0] += 1
    A("| File | In code | In comments |")
    A("|---|---|---|")
    for f, (c, m) in sorted(by_file.items(), key=lambda kv: (-kv[1][0], kv[0])):
        A("| %s | %d | %d |" % (f, c, m))
    A("")
    A("Code occurrences (each must become a param, an asset, a staged input, or a container path before the port):")
    A("")
    for h in literals:
        if not h["comment"]:
            A("- `%s:%d` %s" % (h["file"], h["line"], md_escape(h["literal"])))
    A("")
    # ---- 6. Network --------------------------------------------------------------------------
    A("## 6. Network endpoints and HTTP calls")
    A("")
    hosts = defaultdict(list)
    for h in network:
        for u in h["urls"]:
            m = re.match(r"https?://([^/]+)", u)
            hosts[m.group(1) if m else u].append("%s:%d%s" % (h["file"], h["line"], " (comment)" if h["comment"] else ""))
        for c in h["calls"]:
            hosts["(call: %s)" % c].append("%s:%d%s" % (h["file"], h["line"], " (comment)" if h["comment"] else ""))
    for host, where in sorted(hosts.items()):
        A("- **%s**: %s" % (md_escape(host), ", ".join(where[:8]) + (" (+%d)" % (len(where) - 8) if len(where) > 8 else "")))
    A("")
    # ---- 7. Work list ------------------------------------------------------------------------
    A("## 7. Derived A1 work list")
    A("")
    host_procs = [n for n, i in procs.items() if i["class"] == "HOST" and i["entry"] == "tspipe"]
    local_imgs = sorted(set(i["class_detail"] for i in procs.values() if i["class"] == "LOCAL_IMAGE" and i["entry"] == "tspipe"))
    public_imgs = sorted(set(i["class_detail"] for i in procs.values() if i["class"] == "PUBLIC_IMAGE" and i["entry"] == "tspipe"))
    A("- HOST-class tspipe processes to move onto a declared runtime (%d): %s" % (len(host_procs), ", ".join(sorted(host_procs))))
    A("- Local images to ship (%d): %s" % (len(local_imgs), ", ".join(local_imgs)))
    A("- Public images to pin and mirror (%d): %s" % (len(public_imgs), ", ".join(public_imgs)))
    A("- Processes with an explicit `executor 'local'` (module directive or withName; they run on the submit host under any profile): %s" % ", ".join(
        sorted(n for n, i in procs.items() if i["directives"].get("executor") == "local" or ("general" not in (i["provenance"].get("executor") or "") and (i["effective"].get("executor") or "") == "local"))))
    A("- `container = null` overrides in overlays (must be removed when the host envs become images): %s" % ", ".join(
        sorted(set("%s '%s'" % (f, b["pattern"]) for f, c in chain for b in c["withName"] if strip_quotes(b["assign"].get("container", "x")).lower() == "null"))))
    A("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="repo root (default: .)")
    ap.add_argument("--configs", nargs="*", default=["conf/modules.config"], help="config files after nextflow.config + base.config, in load order")
    ap.add_argument("--entry", default="workflows/tspipe.nf", help="entry workflow for reachability")
    ap.add_argument("--project-dir", default=None, help="value for ${projectDir} (default: --repo, absolute)")
    ap.add_argument("--check-paths", action="store_true", help="stat every resolved reference/asset path on this host")
    ap.add_argument("--md5", action="store_true", help="md5 files up to 2 GB (implies --check-paths)")
    ap.add_argument("--out", default=None, help="markdown output (default: stdout); a .json sidecar is written beside it")
    args = ap.parse_args()
    if args.md5:
        args.check_paths = True
    repo = os.path.abspath(args.repo)
    project_dir = os.path.abspath(args.project_dir) if args.project_dir else repo

    chain = []
    for f in ["nextflow.config", "conf/base.config"] + list(args.configs):
        p = os.path.join(repo, f)
        if not os.path.isfile(p):
            sys.stderr.write("[warn] config not found, skipped: %s\n" % f)
            continue
        chain.append((f, parse_config(p)))

    procs = scan_modules(repo)
    resolve_runtime(procs, chain)
    defs = collect_params(chain)
    values = effective_param_values(defs, project_dir)
    refs, guarded = scan_param_refs(repo)
    literals = scan_literals(repo)
    network = scan_network(repo)
    panel = strip_quotes(values.get("panel", "myeloid"))
    asset_refs = scan_projectdir_assets(repo, panel)
    reach = {
        "tspipe": include_reachability(repo, args.entry),
        "build_pon": include_reachability(repo, "workflows/build_pon.nf"),
        "build_pon_twist": include_reachability(repo, "workflows/build_pon_twist.nf"),
    }
    stats = {}
    if args.check_paths:
        for p, v in values.items():
            if looks_like_path(v):
                stats[("param", p)] = stat_path(v, args.md5)
        for rel in asset_refs:
            stats[("asset", rel)] = stat_path(os.path.join(project_dir, rel), args.md5)

    report = build_report(args, procs, chain, defs, values, refs, guarded, literals, network, asset_refs, reach, stats)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        side = os.path.splitext(args.out)[0] + ".json"
        payload = {
            "generated": date.today().isoformat(),
            "chain": [f for f, _ in chain],
            "processes": {n: {k: v for k, v in i.items() if k != "provenance"} for n, i in procs.items()},
            "params": values,
            "asset_refs": asset_refs,
            "stats": {"%s:%s" % k: v for k, v in stats.items()},
            "literals_code": [h for h in literals if not h["comment"]],
            "network": network,
        }
        with open(side, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, default=str)
        sys.stderr.write("[ok] wrote %s and %s\n" % (args.out, side))
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()
