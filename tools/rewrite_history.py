#!/usr/bin/env python3
"""Reecriture de l'historique de `main` vers la branche `sanitize`.

Pour chaque commit, dans l'ordre :
  - masque le contenu de chaque fichier texte (via sanitize.map) ;
  - masque le message de commit ;
  - remplace l'auteur et le commiteur par Eli <eli@users.noreply.github.com>,
    en conservant les dates.

Ne touche pas a `main`, ne purge rien, ne pousse rien.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from redact import redact_text  # noqa: E402

SOURCE = "main"
TARGET = "sanitize"
NAME = "Eli"
EMAIL = "eli@users.noreply.github.com"


def git(*args, **kw):
    env = kw.pop("env", None)
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          check=True, env=env, **kw)


def parse_ident(line):
    # "Nom <email> 1696000000 +0200"
    name, _, rest = line.partition(" <")
    email, _, date = rest.partition("> ")
    return name, email, date.strip()


def main():
    index = ROOT / ".git" / "tmp_rewrite_index"
    if index.exists():
        index.unlink()

    commits = git("rev-list", "--reverse", SOURCE).stdout.decode().split()
    mapping = {}
    for old in commits:
        raw = git("cat-file", "-p", old).stdout.decode("utf-8", "replace")
        header, _, message = raw.partition("\n\n")
        lines = header.splitlines()
        author = next(l[7:] for l in lines if l.startswith("author "))
        committer = next(l[10:] for l in lines if l.startswith("committer "))
        parents = [l.split()[1] for l in lines if l.startswith("parent ")]
        _, _, adate = parse_ident(author)
        _, _, cdate = parse_ident(committer)

        tree_old = git("rev-parse", f"{old}^{{tree}}").stdout.decode().strip()
        ienv = dict(os.environ, GIT_INDEX_FILE=str(index))
        subprocess.run(["git", "read-tree", tree_old], cwd=ROOT, check=True, env=ienv)

        for rec in git("ls-tree", "-r", "-z", tree_old).stdout.split(b"\0"):
            if not rec:
                continue
            meta, path = rec.split(b"\t", 1)
            mode, typ, sha = meta.decode().split()
            if typ != "blob":
                continue
            content = git("cat-file", "blob", sha).stdout
            if b"\0" in content[:8000]:
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
            new = redact_text(text, "clean")
            if new == text:
                continue
            h = git("hash-object", "-w", "--stdin",
                    input=new.encode()).stdout.decode().strip()
            subprocess.run(["git", "update-index", "--cacheinfo",
                            f"{mode},{h},{path.decode()}"],
                           cwd=ROOT, check=True, env=ienv)

        new_tree = subprocess.run(["git", "write-tree"], cwd=ROOT, check=True,
                                  env=ienv, capture_output=True).stdout.decode().strip()
        cenv = dict(os.environ,
                    GIT_AUTHOR_NAME=NAME, GIT_AUTHOR_EMAIL=EMAIL, GIT_AUTHOR_DATE=adate,
                    GIT_COMMITTER_NAME=NAME, GIT_COMMITTER_EMAIL=EMAIL, GIT_COMMITTER_DATE=cdate)
        args = ["commit-tree", new_tree]
        for p in parents:
            args += ["-p", mapping[p]]
        res = subprocess.run(["git", *args], cwd=ROOT, check=True, env=cenv,
                             input=redact_text(message, "clean").encode(),
                             capture_output=True)
        new_sha = res.stdout.decode().strip()
        mapping[old] = new_sha
        print(f"{old[:8]} -> {new_sha[:8]}", file=sys.stderr)

    head = mapping[commits[-1]]
    git("update-ref", f"refs/heads/{TARGET}", head)
    if index.exists():
        index.unlink()
    print(f"\n{TARGET} -> {head}", file=sys.stderr)


if __name__ == "__main__":
    main()
