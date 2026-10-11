#!/usr/bin/env python3
"""Filet de securite des hooks pre-commit et commit-msg.

Verifie le contenu indexe (staged) et, avec --commit-msg <fichier>, le
message de commit. Bloque si une valeur sensible ou identifiante reste
en clair ou si un jeton est ecrit en prose sans backticks.
Renvoie 1 en cas de fuite, 2 en cas de mauvaise utilisation.
"""
import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from redact import load_map, prose_tokens, value_regex  # noqa: E402

# Adresses legitimes, sans valeur identifiante.
ALLOWED_IPV4 = {
    "0.0.0.0", "127.0.0.1", "255.255.255.255",
    "1.1.1.1", "8.8.8.8", "9.9.9.9", "9.9.9.11",
    "100.64.0.0", "100.100.100.100",
    "141.227.149.187", "57.131.28.186",
}

IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
MAC = re.compile(
    r"(?<![0-9A-Fa-f:-])"
    r"(?:[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}"
    r"|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})"
    r"(?![0-9A-Fa-f:-])")
SECRET = re.compile(r"tskey-[A-Za-z0-9]|-----BEGIN [A-Z ]*PRIVATE KEY-----")


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    return [p for p in out.split(b"\0") if p]


def staged_blob(path):
    return subprocess.run(
        ["git", "show", f":{path.decode('utf-8', 'replace')}"],
        cwd=ROOT, capture_output=True,
    )


def reals():
    """Les valeurs reelles de la table, une seule fois.

    Une table illisible est un echec, pas un silence : le filtre tournerait
    a vide et le hook avec lui.
    """
    try:
        return [real for real, _ in load_map()]
    except OSError as exc:
        sys.stderr.write(
            f"pre-commit : sanitize.map illisible ({exc}). "
            "Le filtre tourne a vide : commit refuse.\n")
        sys.exit(1)


def high_signal(real):
    """Valeur assez distinctive pour etre cherchee dans un fichier binaire."""
    return (any(c.isdigit() for c in real)
            or len(real) >= 6
            or any(c in real for c in ":./<>-_"))


def check_text(text, name, findings, is_markdown=False, binary=False):
    for real in reals():
        if binary and not high_signal(real):
            continue
        if re.search(value_regex(real), text):
            findings.append(f"{name} : valeur reelle « {real} »")
    for m in IPV4.finditer(text):
        ip = m.group(0)
        if ip in ALLOWED_IPV4:
            continue
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            continue  # octets hors bornes : pas une adresse exploitable
        if not addr.is_global:
            findings.append(f"{name} : adresse IP « {ip} »")
    for m in MAC.finditer(text):
        findings.append(f"{name} : adresse MAC « {m.group(0)} »")
    for m in SECRET.finditer(text):
        findings.append(f"{name} : secret potentiel « {m.group(0)} »")
    if is_markdown and not binary:
        for tok in prose_tokens(text):
            findings.append(f"{name} : jeton en prose hors backticks « {tok} »")


def check_index():
    findings = []
    for path in staged_files():
        res = staged_blob(path)
        name = path.decode("utf-8", "replace")
        if res.returncode != 0:
            findings.append(f"{name} : blob indexe illisible")
            continue
        blob = res.stdout
        if b"\0" in blob[:8000]:
            check_text(blob.decode("latin-1", "replace"), name, findings,
                       binary=True)
        else:
            check_text(blob.decode("utf-8", "replace"), name, findings,
                       is_markdown=name.endswith(".md"))
    return findings


def check_message(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    findings = []
    for real in reals():
        if re.search(value_regex(real), text):
            findings.append(f"message : valeur reelle « {real} »")
    for m in SECRET.finditer(text):
        findings.append(f"message : secret potentiel « {m.group(0)} »")
    for tok in prose_tokens(text):
        findings.append(f"message : jeton en prose hors backticks « {tok} »")
    return findings


def report(title, findings):
    if not findings:
        return 0
    print(f"{title} : contenu sensible, refuse.", file=sys.stderr)
    for f in sorted(set(findings)):
        print(f"  - {f}", file=sys.stderr)
    print("Masquez la valeur reelle (sanitize.map) ou entourez le jeton "
          "de backticks dans le fichier concerne.", file=sys.stderr)
    return 1


def main():
    if "--commit-msg" in sys.argv:
        idx = sys.argv.index("--commit-msg")
        if len(sys.argv) <= idx + 1 or not sys.argv[idx + 1]:
            sys.stderr.write("check_leaks : --commit-msg attend un chemin\n")
            return 2
        return report("commit-msg", check_message(sys.argv[idx + 1]))
    return report("pre-commit", check_index())


if __name__ == "__main__":
    sys.exit(main())