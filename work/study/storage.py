"""Project-local storage accounting. All quantities are decimal bytes."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 15_000_000_000
RESERVE = 500_000_000

def used_bytes():
    return sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file() and not p.is_symlink())

def guard(additional=0):
    used = used_bytes()
    if additional < 0 or used + additional + RESERVE > LIMIT:
        raise RuntimeError(f'Storage ceiling: used={used}, requested={additional}, limit={LIMIT}, reserve={RESERVE}')
    free = shutil.disk_usage(ROOT).free
    if additional + RESERVE > free:
        raise RuntimeError(f'Insufficient physical disk: free={free}, requested={additional}')
    return {'project_bytes': used, 'limit_bytes': LIMIT, 'reserved_headroom_bytes': RESERVE, 'disk_free_bytes': free}

if __name__ == '__main__':
    import json
    print(json.dumps(guard(), indent=2))
