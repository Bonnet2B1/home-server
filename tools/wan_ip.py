#!/usr/bin/env python3
"""Veille sur l'adresse publique qui tourne.

L'adresse publique de la box peut changer sans prevenir. La table
sanitize.map ne contient que les valeurs ecrites : une adresse nouvelle
n'y figure pas, et ni le filtre ni le hook ne la connaissent.

Usage :
  wan_ip.py check   -- branche sur les hooks pre-commit et commit-msg.
                      Lit l'adresse publique actuelle, verifie qu'elle est
                      couverte par la table ou publiquement assumee, et
                      bloque un commit dont l'index (ou le message avec
                      --text) contient cette adresse en clair. Sans reseau,
                      il previent et finit par 0 : il ne bloque pas.
  wan_ip.py update  -- remplace la valeur reelle du jeton de la box A par
                      l'adresse publique actuelle dans sanitize.map.
                      Ne fait rien sans reseau.

Reparation ou test manuels :
  wan_ip.py check --ip <adresse>
  wan_ip.py check --text <fichier-message> --ip <adresse>
  wan_ip.py update --ip <adresse> --token <JETON>
"""
import ipaddress
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from redact import MAP, SEP, load_map  # noqa: E402
from check_leaks import ALLOWED_IPV4, staged_blob, staged_files  # noqa: E402

DEFAULT_TOKEN = "<WAN-IP-BOX-A>"
ENDPOINTS = (
    os.environ.get("WAN_IP_ENDPOINTS")
    or "https://api.ipify.org;https://ifconfig.me/ip;https://ipinfo.io/ip"
).split(";")


def fetch_ip(fast=False):
    """L'adresse publique actuelle, ou None si le reseau manque.

    En mode rapide (hook pre-commit), une seule adresse et un court delai.
    """
    candidates = ENDPOINTS[:1] if fast else ENDPOINTS
    for url in candidates:
        try:
            with urllib.request.urlopen(
                    url, timeout=2 if fast else 4) as resp:
                ip = resp.read().decode("utf-8", "replace").strip()
            ipaddress.ip_address(ip)
            return ip
        except Exception:
            continue
    return None


def is_covered(ip):
    for real, _ in load_map():
        if real == ip:
            return True
    return ip in ALLOWED_IPV4


def check(ip, text=None):
    if ip is None:
        print("wan_ip : adresse publique illisible (reseau ?). "
              "Verification differee.", file=sys.stderr)
        return 0
    if is_covered(ip):
        print("wan_ip : adresse publique couverte par la table.")
        return 0
    needle = ip.encode("latin-1")
    if text is not None:
        blob = Path(text).read_bytes()
        if needle in blob:
            print(f"wan_ip : l'adresse publique actuelle {ip} figure en "
                  f"clair dans le message ({Path(text).name}). Ajoutez-la "
                  "a sanitize.map (python3 tools/wan_ip.py update), puis "
                  "recommencez.", file=sys.stderr)
            return 1
        print(f"wan_ip : adresse publique {ip} non couverte et absente du "
              "message. Mettez la table a jour avant de la mentionner "
              "(python3 tools/wan_ip.py update).", file=sys.stderr)
        return 0
    for path in staged_files():
        res = staged_blob(path)
        if res.returncode != 0:
            continue
        if needle in res.stdout:
            name = path.decode("utf-8", "replace")
            print(f"wan_ip : l'adresse publique actuelle {ip} figure en "
                  f"clair dans l'index ({name}). Ajoutez-la a sanitize.map "
                  "(python3 tools/wan_ip.py update), puis recommencez.",
                  file=sys.stderr)
            return 1
    print(f"wan_ip : adresse publique {ip} non couverte et absente de "
          "l'index. Mettez la table a jour avant de la mentionner "
          "(python3 tools/wan_ip.py update).", file=sys.stderr)
    return 0


def update(ip, token):
    if ip is None:
        print("wan_ip : adresse publique illisible (reseau ?). "
              "Rien n'a change.", file=sys.stderr)
        return 2
    out = []
    found = 0
    for line in MAP.read_text(encoding="utf-8").splitlines(keepends=True):
        stripped = line.strip()
        if not stripped or stripped.lstrip().startswith("#"):
            out.append(line)
            continue
        real, _, tok = stripped.partition(SEP)
        if tok.strip() == token:
            found += 1
            if real.rstrip() == ip:
                print(f"wan_ip : {token} deja a jour ({ip}).")
                return 0
            indent = line[: len(line) - len(line.lstrip())]
            out.append(f"{indent}{ip}{SEP}{token}\n")
        else:
            out.append(line)
    if not found:
        print(f"wan_ip : jeton {token} introuvable dans sanitize.map.",
              file=sys.stderr)
        return 2
    MAP.write_text("".join(out), encoding="utf-8")
    print(f"wan_ip : {token} mis a jour dans sanitize.map.")
    return 0


def main():
    args = sys.argv[1:]
    mode = args[0] if args else None
    ip = None
    if "--ip" in args:
        i = args.index("--ip")
        ip = args[i + 1] if len(args) > i + 1 else None
    text = None
    if "--text" in args:
        i = args.index("--text")
        text = args[i + 1] if len(args) > i + 1 else None
    if mode == "check":
        return check(fetch_ip(fast=True) if ip is None else ip, text=text)
    if mode == "update":
        token = DEFAULT_TOKEN
        if "--token" in args:
            i = args.index("--token")
            if len(args) > i + 1:
                token = args[i + 1]
        return update(fetch_ip() if ip is None else ip, token)
    print("wan_ip : usage : check | update [--ip <adresse>] [--token <jeton>]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())