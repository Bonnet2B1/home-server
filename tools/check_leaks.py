#!/usr/bin/env python3
"""Filet de securite du hook pre-commit.

Verifie le contenu indexe (staged). Bloque le commit si une valeur sensible
ou identifiante reste en clair. Renvoie 1 en cas de fuite.
"""
import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from redact import load_map  # noqa: E402

# Adresses legitimes, sans valeur identifiante.
ALLOWED_IPV4 = {
    "0.0.0.0", "127.0.0.1", "255.255.255.255",
    "1.1.1.1", "8.8.8.8", "9.9.9.9", "9.9.9.11",
    "100.64.0.0", "100.100.100.100",
    "141.227.149.187", "57.131.28.186",
}

IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
MAC = re.compile(r"(?<![0-9A-Fa-f:])[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}(?![0-9A-Fa-f:])")
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
    ).stdout


def is_private_or_tailnet(ip):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback or addr.is_link_local


def main():
    findings = []
    reals = [real for real, _ in load_map()]
    for path in staged_files():
        blob = staged_blob(path)
        if b"\0" in blob[:8000]:
            continue
        text = blob.decode("utf-8", "replace")
        name = path.decode("utf-8", "replace")
        for real in reals:
            if real in text:
                findings.append(f"{name} : valeur reelle « {real} »")
        for m in IPV4.finditer(text):
            ip = m.group(0)
            if ip in ALLOWED_IPV4:
                continue
            if is_private_or_tailnet(ip) or not ipaddress.ip_address(ip).is_global:
                findings.append(f"{name} : adresse IP « {ip} »")
        for m in MAC.finditer(text):
            findings.append(f"{name} : adresse MAC « {m.group(0)} »")
        for m in SECRET.finditer(text):
            findings.append(f"{name} : secret potentiel « {m.group(0)} »")
    if findings:
        print("pre-commit : masquage incomplet, commit refuse.", file=sys.stderr)
        for f in sorted(set(findings)):
            print(f"  - {f}", file=sys.stderr)
        print("Corrigez sanitize.map, puis relancez.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
