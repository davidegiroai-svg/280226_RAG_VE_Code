from __future__ import annotations

import json
import subprocess
from pathlib import Path
from datetime import datetime

DEPTH = 4

KEY_FILES = [
    "docker-compose.yml",
    "compose.yaml",
    "compose.yml",
    "scripts/db_init.sql",
    ".env.example",
    "README.md",
]

KEY_DIRS = [
    "docs",
    "docs_source",
    "scripts",
    "api",
    "worker",
    "ui",
]

RISKY_PATTERNS = [
    ".env",
    ".env.*",
    "secrets*",
    "*secret*",
    "*token*",
    "*apikey*",
    "*api_key*",
    "*credential*",
]

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def safe_rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")

def tree_lines(root: Path, depth: int = DEPTH) -> list[str]:
    lines: list[str] = []
    root = root.resolve()

    def walk(dir_path: Path, level: int):
        if level > depth:
            return
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except Exception:
            return

        for e in entries:
            indent = "  " * level
            if e.is_dir():
                lines.append(f"{indent}{e.name}/")
                walk(e, level + 1)
            else:
                lines.append(f"{indent}{e.name}")

    lines.append(f"{root.name}/")
    walk(root, 1)
    return lines

def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, shell=False)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except Exception as ex:
        return 1, f"ERROR running {cmd}: {ex}"

def find_risky_paths(root: Path) -> list[str]:
    hits: set[str] = set()
    for pat in RISKY_PATTERNS:
        for p in root.rglob(pat):
            if p.is_file():
                hits.add(safe_rel(p, root))
    return sorted(hits)

def presence_checks(root: Path) -> dict:
    checks: dict[str, bool] = {}
    for f in KEY_FILES:
        checks[f] = (root / f).exists()
    for d in KEY_DIRS:
        checks[f"{d}/"] = (root / d).exists() and (root / d).is_dir()
    checks[".git/"] = (root / ".git").exists() and (root / ".git").is_dir()
    return checks

def main() -> int:
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent.resolve()

    out_dir = project_root / "_cc_status" / "audit" / "latest"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Tree
    (out_dir / "repo_tree.txt").write_text("\n".join(tree_lines(project_root, DEPTH)) + "\n", encoding="utf-8")

    # 2) Git status (se git repo)
    git_status_path = out_dir / "git_status.txt"
    if (project_root / ".git").exists():
        rc, out = run_cmd(["git", "status", "--porcelain"], cwd=project_root)
        git_status_path.write_text(out + "\n", encoding="utf-8")
    else:
        git_status_path.write_text("Not a git repo\n", encoding="utf-8")

    # 3) Risky paths (solo path, non contenuti)
    risky = find_risky_paths(project_root)
    (out_dir / "risky_paths.txt").write_text("\n".join(risky) + ("\n" if risky else ""), encoding="utf-8")

    # 4) Summary JSON
    summary = {
        "timestamp": now_iso(),
        "project_root": str(project_root).replace("\\", "/"),
        "presence_checks": presence_checks(project_root),
        "risky_paths_count": len(risky),
        "risky_paths_sample": risky[:50],
    }
    (out_dir / "audit_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("OK repo_audit completed. Outputs:", str(out_dir).replace("\\", "/"))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
