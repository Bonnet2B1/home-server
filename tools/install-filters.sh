#!/bin/sh
# Active le filtre de masquage et le hook pre-commit pour ce clone.
# A executer apres un clone neuf (la config Git locale n'est pas versionnee).
set -eu

root=$(git rev-parse --show-toplevel)
cd "$root"

git config filter.redact.clean "python3 \"$root/tools/redact.py\" clean"
git config filter.redact.smudge "python3 \"$root/tools/redact.py\" smudge"
git config filter.redact.required true
git config core.hooksPath "$root/.githooks"

echo "Filtre 'redact' et hook pre-commit actives pour $root"
