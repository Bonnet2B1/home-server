#!/usr/bin/env python3
"""Masquage des valeurs sensibles (filtre Git).

Usage : redact.py clean   (valeur reelle -> jeton, cote travail -> index)
        redact.py smudge  (jeton -> valeur reelle, cote index -> travail)
        redact.py wrap    (entoure de backticks les jetons ecrits en prose)

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


def token_pattern():
    """Motif des jetons declares dans la table, le plus long d'abord."""
    tokens = sorted({token for _, token in load_map()}, key=len, reverse=True)
    return re.compile("|".join(re.escape(t) for t in tokens))


_INLINE_CODE = re.compile(r"(`[^`\n]*`)")


def _prose_parts(text):
    """Rend les morceaux de texte qui sont de la prose, pas du code.

    Exclut les blocs delimites par ``` et les spans de code en backticks.
    """
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for part in _INLINE_CODE.split(line)[::2]:
            yield part


def prose_tokens(text):
    """Rend chaque jeton ecrit en prose, donc absent du contenu publie."""
    for part in _prose_parts(text):
        for match in token_pattern().finditer(part):
            yield match.group(0)


def wrap_tokens(text):
    """Entoure de backticks les jetons ecrits en prose.

    GitHub traite `<TOKEN>` en prose comme du HTML brut et l'efface a
    l'affichage. Les blocs de code et les spans deja backtiques restent
    intacts.
    """
    pattern = token_pattern()
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        parts = _INLINE_CODE.split(line)
        for i in range(0, len(parts), 2):
            parts[i] = pattern.sub(lambda m: "`" + m.group(0) + "`", parts[i])
        out.append("".join(parts))
    return "".join(out)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "clean"
    data = sys.stdin.read()
    if mode == "wrap":
        data = wrap_tokens(data)
    else:
        data = redact_text(data, mode)
    sys.stdout.write(data)


if __name__ == "__main__":
    main()