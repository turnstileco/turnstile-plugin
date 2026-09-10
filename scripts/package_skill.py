#!/usr/bin/env python3
"""Package a skill folder into a .skill bundle (a ZIP), or validate it.

Usage:
    python3 scripts/package_skill.py plugins/<plugin>/skills/<name>/ --out dist
    python3 scripts/package_skill.py plugins/<plugin>/skills/<name>/ --check

Layout rule (the #1 claude.ai upload failure): the skill FOLDER sits at the
archive root, with SKILL.md at the top of that folder —
    <skill-name>/SKILL.md
    <skill-name>/references/...
Never zip so SKILL.md itself is the archive root, and never double-nest.

Validation enforced (used by validate.yml on every PR and by release.yml):
  - SKILL.md exists at the top of the skill folder
  - frontmatter parses and carries name, description, version
  - version is semver (MAJOR.MINOR.PATCH)
  - frontmatter name matches the folder name
  - every archive path matches ARCNAME_RE, and no entry is a symlink. This runs
    in `--check` as well as at package time, because until 2026-07-09 it ran in
    neither: `--check` returned before package() and so never looked at a single
    archive path. A bundle with `@` in a filename shipped and could not be
    installed by anyone.

Output bundles are named <name>-v<version>.skill per SPEC.md.
Dependency-free: stdlib only.
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Deliberately aliased. This module has its own `parse_frontmatter`, and the two
# are NOT interchangeable: the local one takes a Path and returns a dict of
# top-level keys only; validate_skill's takes the file's *text* and returns
# (fields, errors) including the nested `metadata:` block. The flat local parser
# cannot see `metadata.surfaces` at all — its regex is anchored at column zero —
# which is exactly why this import exists.
from validate_skill import (  # noqa: E402
    declared_surfaces,
    parse_frontmatter as parse_frontmatter_text,
)

EXCLUDE_NAMES = {".DS_Store", "__pycache__", ".git", ".gitkeep"}
EXCLUDE_SUFFIXES = {".pyc"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Every path inside the bundle must match this, or claude.ai's uploader rejects the
# whole archive with "Zip file contains path with invalid characters" and installs
# nothing. One `@` in one filename is enough to make the whole bundle
# uninstallable. The bundle is the product, so its paths are part of the contract.
ARCNAME_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        fail(f"{skill_md}: no YAML frontmatter block (--- ... ---) at top of file")
    fields = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if kv:
            fields[kv.group(1)] = kv.group(2).strip().strip("\"'")
    return fields


def validate(skill_dir: Path) -> dict:
    if not skill_dir.is_dir():
        fail(f"{skill_dir}: not a directory")
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        fail(f"{skill_dir}: SKILL.md missing at top of skill folder")
    fm = parse_frontmatter(skill_md)
    for key in ("name", "description", "version"):
        if not fm.get(key):
            fail(f"{skill_md}: frontmatter missing required field '{key}'")
    if not SEMVER_RE.match(fm["version"]):
        fail(
            f"{skill_md}: version '{fm['version']}' is not semver "
            "(MAJOR.MINOR.PATCH — see SPEC.md)"
        )
    if fm["name"] != skill_dir.name:
        fail(
            f"{skill_md}: frontmatter name '{fm['name']}' does not match "
            f"folder name '{skill_dir.name}'"
        )
    check_archive_paths(skill_dir)
    return fm


def included_files(skill_dir: Path):
    for path in sorted(skill_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        if any(part in EXCLUDE_NAMES for part in path.relative_to(skill_dir).parts):
            continue
        yield path


def check_archive_paths(skill_dir: Path) -> None:
    """Assert every path that will land in the .skill is uploadable.

    This runs inside validate(), so `--check` performs it. That is the whole
    point: a `--check` that returns before enumerating the archive is a dry run
    that skips the exact step that breaks. A bundle with one invalid archive
    path ships as a release asset that nobody can install.

    Symlinks are rejected here rather than silently followed: TS-SEC-14 says a
    symlink is never packaged, and until now nothing enforced it at package time.
    `is_file()` follows symlinks, so the check must precede it.
    """
    problems = []
    for path in sorted(skill_dir.rglob("*")):
        rel = path.relative_to(skill_dir)
        if any(part in EXCLUDE_NAMES for part in rel.parts):
            continue
        if path.is_symlink():
            problems.append(f"  {rel}: symlink — never packaged (TS-SEC-14)")
            continue
        if not path.is_file() or path.suffix in EXCLUDE_SUFFIXES:
            continue
        arcname = f"{skill_dir.name}/{rel.as_posix()}"
        if not ARCNAME_RE.match(arcname):
            bad = sorted({c for c in arcname if not ARCNAME_RE.match(c)})
            chars = ", ".join(f"{c!r} (U+{ord(c):04X})" for c in bad)
            problems.append(f"  {arcname}: invalid character(s) {chars}")
    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        fail(
            f"{skill_dir.name}: {len(problems)} archive path(s) that cannot ship. "
            "Rename the file(s), or remove the symlink. Do not sanitize at package "
            "time: the bundle's paths must match the repo's, or the SKILL.md that "
            "references them is wrong."
        )


def package(skill_dir: Path, out_dir: Path, fm: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = out_dir / f"{fm['name']}-v{fm['version']}.skill"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in included_files(skill_dir):
            # skill folder at the archive root: <skill-name>/<relative path>
            arcname = Path(skill_dir.name) / path.relative_to(skill_dir)
            zf.write(path, arcname)
    return bundle


def skill_surfaces(skill_dir: Path) -> list:
    """`metadata.surfaces` for this skill, via the nested-aware parser."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    fields, errors = parse_frontmatter_text(text)
    if fields is None:
        fail(f"{skill_dir}/SKILL.md: {errors}")
    return declared_surfaces(fields.get("metadata"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("skill_dir", type=Path, help="path to the skill folder")
    ap.add_argument("--out", type=Path, default=Path("dist"), help="output directory")
    ap.add_argument(
        "--check", action="store_true", help="validate only; write nothing"
    )
    ap.add_argument(
        "--require-surface",
        metavar="SURFACE",
        help="skip (exit 0, write nothing) unless the skill declares this "
             "surface in metadata.surfaces. release.yml passes claude-ai: a "
             "skill that only runs in Claude Code has no working .skill upload "
             "path, and shipping one would advertise a download that cannot work",
    )
    args = ap.parse_args()

    skill_dir = args.skill_dir.resolve()
    fm = validate(skill_dir)

    if args.require_surface:
        surfaces = skill_surfaces(skill_dir)
        if args.require_surface not in surfaces:
            print(f"skip: {skill_dir.name} (surfaces: {', '.join(surfaces)} — "
                  f"does not include {args.require_surface})")
            return

    if args.check:
        print(f"ok: {skill_dir.name} v{fm['version']} conforms")
        return
    bundle = package(skill_dir, args.out, fm)
    print(f"packaged: {bundle}")


if __name__ == "__main__":
    main()
