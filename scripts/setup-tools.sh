#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    echo 'This setup script supports Linux x86_64 only.' >&2
    exit 1
fi

mkdir -p .tools/bin .tools/downloads

download() {
    local url="$1" archive="$2" checksum="$3"
    if ! echo "$checksum  $archive" | sha256sum --check --status 2>/dev/null; then
        curl --fail --location --show-error --silent --retry 2 \
            --connect-timeout 15 --max-time 120 "$url" -o "$archive"
    fi
    echo "$checksum  $archive" | sha256sum --check
}

download \
    'https://github.com/luau-lang/luau/releases/download/0.745/luau-ubuntu.zip' \
    '.tools/downloads/luau-0.745-ubuntu.zip' \
    '186e5ddaa2b048ebc7390c11ed1b00c04e7d3beaffed429250329e3575d2ece2'
download \
    'https://github.com/rojo-rbx/rojo/releases/download/v7.7.1/rojo-7.7.1-linux-x86_64.zip' \
    '.tools/downloads/rojo-7.7.1-linux-x86_64.zip' \
    '00feb4fa0829a1dd72b49df2639da519a352bfe13cadcd83969e2ba2bb5693c4'

python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile

tools = Path('.tools')
for archive, names in [
    ('luau-0.745-ubuntu.zip', ('luau', 'luau-analyze', 'luau-compile')),
    ('rojo-7.7.1-linux-x86_64.zip', ('rojo',)),
]:
    with ZipFile(tools / 'downloads' / archive) as release:
        for name in names:
            destination = tools / 'bin' / name
            destination.write_bytes(release.read(name))
            destination.chmod(0o755)
PY

.tools/bin/luau-compile --help > /dev/null
.tools/bin/rojo --version
echo 'Tools installed in .tools/bin.'
