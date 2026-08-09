from __future__ import annotations
import argparse, re, sys, tomllib
from pathlib import Path
sys.dont_write_bytecode=True

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--repo-root',type=Path,default=Path.cwd()); a=ap.parse_args(); root=a.repo_root
    data=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))
    base=data['project'].get('dependencies',[])
    product=data['project'].get('optional-dependencies',{}).get('product',[])
    failures=[]
    if base: failures.append('base dependencies must remain empty at W23')
    for dep in product:
        if '==' not in dep: failures.append(f'product dependency is not exact-pinned: {dep}')
    lock=(root/'requirements/product.lock').read_text(encoding='utf-8').splitlines()
    pins=[x.strip() for x in lock if x.strip() and not x.lstrip().startswith('#')]
    for dep in product:
        normalized=re.split(r'[=<>!~; ]', dep, maxsplit=1)[0].lower().replace('_','-')
        if not any(re.split(r'[=<>!~; ]', x, maxsplit=1)[0].lower().replace('_','-')==normalized for x in pins): failures.append(f'missing lock pin for {dep}')
    if failures:
        print('FAIL: dependency policy'); [print('-',x) for x in failures]; return 1
    print(f'PASS: dependency policy ({len(product)} direct product pins; {len(pins)} locked entries)'); return 0
if __name__=='__main__': raise SystemExit(main())
