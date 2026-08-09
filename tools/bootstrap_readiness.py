from __future__ import annotations
import argparse
import importlib
import json
import sys
from pathlib import Path


def check(root: Path, *, profile: str = 'core') -> dict[str, object]:
    root=Path(root).resolve()
    if profile not in {'core','product'}: raise ValueError('profile must be core or product')
    required=[
        'pyproject.toml','AGENTS.md','governance/PROJECT_IDENTITY.yaml',
        'src/aggie_analytics/__init__.py','tools/validate_repository.py'
    ]
    missing=[x for x in required if not (root/x).is_file()]
    # Project policy currently targets Python 3.12; keep a tolerant check for the
    # repository validation host while recording the exact interpreter.
    python_supported=sys.version_info >= (3,11) and sys.version_info < (3,14)
    src=str(root/'src')
    if src not in sys.path: sys.path.insert(0,src)
    try:
        importlib.import_module('aggie_analytics'); base_ok=True; base_error=None
    except Exception as exc:  # pragma: no cover - diagnostic path
        base_ok=False; base_error=f'{type(exc).__name__}: {exc}'
    product={}
    if profile=='product':
        for name in ('fastapi','uvicorn'):
            try:
                mod=importlib.import_module(name); product[name]=getattr(mod,'__version__','INSTALLED_VERSION_UNKNOWN')
            except Exception: product[name]='NOT_INSTALLED'
    return {
        'schema_version':'aggie.bootstrap.readiness.v1',
        'profile':profile,
        'python_version':sys.version.split()[0],
        'python_supported':python_supported,
        'required_files_ok':not missing,
        'missing_required_files':missing,
        'base_import_ok':base_ok,
        'base_import_error':base_error,
        'product_dependencies':product,
        'mutated_environment':False,
        'note':'Check-only readiness probe; package installation remains an explicit operator action.',
    }


def main()->int:
    ap=argparse.ArgumentParser(description='Non-mutating bootstrap/readiness probe.')
    ap.add_argument('--repo-root',type=Path,default=Path.cwd())
    ap.add_argument('--profile',choices=('core','product'),default='core')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    result=check(args.repo_root,profile=args.profile)
    text=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text,encoding='utf-8')
    print(text,end='')
    return 0 if result['python_supported'] and result['required_files_ok'] and result['base_import_ok'] else 1

if __name__=='__main__': raise SystemExit(main())
