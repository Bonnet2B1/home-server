#!/usr/bin/env python3
"""Masquage des valeurs sensibles (filtre Git).

Usage : redact.py clean   (valeur reelle -> jeton, cote travail -> index)
        redact.py smudge  (jeton -> valeur reelle, cote index -> travail)

Lit stdin, ecrit stdout. Lit la table sanitize.map.
"""
import re
import sys
from pathlib import Path

MAP = Path(__file__).resolve().parent.parent / "sanitize.map"
SEP = " => "


def load_map():
    pairs = []
    for line in MAP.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        real, _, token = line.partition(SEP)
        real = real.rstrip()
        token = token.strip()
        if real and token:
            pairs.append((real, token))
    return pairs


def _boundary(regex):
    return r"(?<![0-9A-Za-z])" + regex + r"(?![0-9A-Za-z])"


def redact_text(data, mode="clean"):
    pairs = load_map()
    if mode == "clean":
        table = pairs
    else:
        seen = {}
        for real, token in pairs:
            seen.setdefault(token, real)
        table = [(token, real) for token, real in seen.items()]
    # Plus long d'abord, pour ne pas couper un motif qui en contient un autre.
    for left, right in sorted(table, key=lambda p: -len(p[0])):
        data = re.sub(_boundary(re.escape(left)), lambda _: right, data)
    return data


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "clean"
    sys.stdout.write(redact_text(sys.stdin.read(), mode))


if __name__ == "__main__":
    main()
