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
MODES = ("clean", "smudge", "wrap")


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


def value_regex(value):
    """Regex d'une valeur, coherente entre le filtre et le hook.

    Une valeur courte purement alphabetique (un nom d'hote, un compte)
    ne se masque qu'aux frontieres de mots, pour ne pas emporter un
    morceau d'un mot plus long. Toutes les autres valeurs (IP, MAC,
    chemins, hostnames, jetons) se masquent partout : une valeur collée
    a un autre caractere est masquee, donc le hook ne bloque plus un
    commit qu'aucune correction de la table ne pourrait deverrouiller.
    """
    if value.isalpha() and len(value) < 6:
        return _boundary(re.escape(value))
    return re.escape(value)


def redact_text(data, mode="clean"):
    if mode not in ("clean", "smudge"):
        raise ValueError(mode)
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
        data = re.sub(value_regex(left), lambda _: right, data)
    return data


def token_pattern():
    """Motif des jetons declares dans la table, le plus long d'abord."""
    tokens = sorted({token for _, token in load_map()}, key=len, reverse=True)
    return re.compile("|".join(re.escape(t) for t in tokens))


_INLINE_CODE = re.compile(r"(`[^`\n]*`)")
# Lien inline `[texte](url)` et URL nue : la prose ne les racoute pas.
# Le groupe capturant conserve les delimiteurs dans re.split, pour que
# wrap_tokens puisse les recopier tels quels.
_LINK_OR_URL = re.compile(r"(!?\[[^\]\n]*\]\([^)\n]*\)|https?://[^\s'\"`)]+)")
_INDENTED_CODE = re.compile(r"^(?: {4}|\t)")


def _prose_parts(text):
    """Rend les morceaux de texte qui sont de la prose, pas du code.

    Exclut les blocs delimites par ```, les spans de code en backticks,
    les lignes code en retrait (4 espaces ou tabulation) et les liens
    Markdown ou URLs.
    """
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or _INDENTED_CODE.match(line):
            continue
        for part in _INLINE_CODE.split(line)[::2]:
            for seg in _LINK_OR_URL.split(part)[::2]:
                yield seg


def prose_tokens(text):
    """Rend chaque jeton ecrit en prose, donc absent du contenu publie."""
    for part in _prose_parts(text):
        for match in token_pattern().finditer(part):
            yield match.group(0)


def wrap_tokens(text):
    """Entoure de backticks les jetons ecrits en prose.

    GitHub traite `<TOKEN>` en prose comme du HTML brut et l'efface a
    l'affichage. Les blocs de code, les spans deja backtiques, les liens
    Markdown, les URLs et les lignes code en retrait restent intacts.
    """
    pattern = token_pattern()
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence or _INDENTED_CODE.match(line):
            out.append(line)
            continue
        parts = _INLINE_CODE.split(line)
        for i in range(0, len(parts), 2):
            chunks = _LINK_OR_URL.split(parts[i])
            for j in range(0, len(chunks), 2):
                chunks[j] = pattern.sub(
                    lambda m: "`" + m.group(0) + "`", chunks[j])
            parts[i] = "".join(chunks)
        out.append("".join(parts))
    return "".join(out)


def main():
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode not in MODES:
            sys.stderr.write(f"redact : mode inconnu '{mode}' "
                             f"(attendu : {', '.join(MODES)})\n")
            return 2
    else:
        mode = "clean"
    data = sys.stdin.read()
    if mode == "wrap":
        data = wrap_tokens(data)
    else:
        data = redact_text(data, mode)
    sys.stdout.write(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())