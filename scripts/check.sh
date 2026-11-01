#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 scripts/build.py --check
python3 -m unittest discover -s tests -p 'test_*.py' -v
.tools/bin/luau tests/policy.luau
.tools/bin/luau tests/jobs.luau
python3 - <<'PY'
from pathlib import Path
import subprocess
sources = [str(p) for p in sorted(Path('src').rglob('*.luau'))]
sources.append('dist/PetSimAutomation.lua')
subprocess.run(['.tools/bin/luau-compile', *sources], check=True, stdout=subprocess.DEVNULL)
print(f'Compiled {len(sources)} source/bundle files.')
PY
mkdir -p build
.tools/bin/rojo build default.project.json -o build/PetSimAutomation.rbxlx
