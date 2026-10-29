"""Bounded, resumable-by-file official-source acquisition; no execution of fetched text."""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from storage import ROOT, guard

BASE = Path(__file__).resolve().parent
LEDGER = BASE / 'data' / 'downloads.jsonl'
EXPECTED_MD5 = {'rnp_scores':'58648b836ff9434bc929b7fad25cd9bb'}
SOURCES = {
 'rnp_record': ('https://zenodo.org/api/records/18366081', 'sources/rnp_record.json', 5_000_000),
 'openbind_record': ('https://zenodo.org/api/records/20798528', 'sources/openbind_record.json', 5_000_000),
 'kin_record': ('https://api.figshare.com/v2/articles/31986663', 'sources/kin_record.json', 5_000_000),
 'rnp_readme': ('https://raw.githubusercontent.com/plinder-org/runs-n-poses/main/README.md', 'sources/rnp_README.md', 2_000_000),
 'rnp_versions': ('https://raw.githubusercontent.com/plinder-org/runs-n-poses/main/versions.txt', 'sources/rnp_versions.txt', 2_000_000),
 'rnp_extract_scores': ('https://raw.githubusercontent.com/plinder-org/runs-n-poses/main/extract_scores.ipynb', 'sources/rnp_extract_scores.ipynb', 10_000_000),
 'openbind_readme': ('https://raw.githubusercontent.com/OpenBind-Consortium/EV-A71_2A_benchmark/main/README.md', 'sources/openbind_README.md', 2_000_000),
 'kin_readme': ('https://raw.githubusercontent.com/THGLab/KinConfBench/main/README.md', 'sources/kin_README.md', 2_000_000),
 'parallax_readme': ('https://huggingface.co/datasets/ThorKl/PLI-parallax/raw/main/README.md', 'sources/parallax_README.md', 3_000_000),
 'parallax_files': ('https://huggingface.co/api/datasets/ThorKl/PLI-parallax/tree/main/deposit?recursive=false', 'sources/parallax_files.json', 3_000_000),
 'rnp_annotations': ('https://zenodo.org/records/18366081/files/annotations.csv?download=1', 'data/rnp/annotations.csv', 8_000_000),
 'rnp_inputs': ('https://zenodo.org/records/18366081/files/inputs.json?download=1', 'data/rnp/inputs.json', 8_000_000),
 'rnp_scores': ('https://zenodo.org/records/18366081/files/predictions.tar.gz?download=1', 'data/rnp/predictions.tar.gz', 64_000_000),
 'rnp_terms': ('https://zenodo.org/records/18366081/files/OUTPUT_TERMS_OF_USE.md?download=1', 'sources/rnp_OUTPUT_TERMS_OF_USE.md', 1_000_000),
 'rnp_terms_short': ('https://zenodo.org/records/18366081/files/Legally_Binding_Terms_of_Use.txt?download=1', 'sources/rnp_TERMS.txt', 1_000_000),
 'parallax_methods': ('https://huggingface.co/datasets/ThorKl/PLI-parallax/raw/main/deposit/README.md', 'sources/parallax_methods.md', 2_000_000),
 'parallax_splits': ('https://huggingface.co/datasets/ThorKl/PLI-parallax/raw/main/deposit/SPLITS.md', 'sources/parallax_SPLITS.md', 1_000_000),
 'parallax_validation': ('https://huggingface.co/datasets/ThorKl/PLI-parallax/raw/main/notebooks/pli_parallax_validation_notebook.ipynb', 'sources/parallax_validation.ipynb', 5_000_000),
 'jshs_2027_rules': ('https://www.jshs.org/wp-content/uploads/2026/08/JSHS-Core-Rules-of-Competition-2026-27.pdf', 'sources/JSHS_rules_2026_27.pdf', 5_000_000),
 'parallax_tree': ('https://huggingface.co/api/datasets/ThorKl/PLI-parallax/tree/main?recursive=true', 'sources/parallax_tree.json', 3_000_000),
 'rnp_repository_tree': ('https://api.github.com/repos/plinder-org/runs-n-poses/git/trees/main?recursive=1', 'sources/rnp_repository_tree.json', 5_000_000),
 'openbind_inference_tree': ('https://api.github.com/repos/OmeirK/cofolding_evaluation/git/trees/main?recursive=1', 'sources/openbind_inference_tree.json', 5_000_000),
 'rnp_preprint_pdf': ('https://www.researchsquare.com/article/rs-7311192/v1.pdf', 'sources/rnp_preprint_v1.pdf', 25_000_000),
 'rnp_protenix_run': ('https://raw.githubusercontent.com/plinder-org/runs-n-poses/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/examples/utils/run_protenix.sh', 'sources/rnp_run_protenix.sh.txt', 1_000_000),
}

def record(entry):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def fetch(key):
    url, relative, cap = SOURCES[key]
    target = BASE / relative
    if target.exists():
        print(json.dumps({'source': key, 'status': 'already_exists', 'bytes': target.stat().st_size}), flush=True)
        return
    guard(cap)
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + '.part')
    entry = {'key': key, 'url': url, 'path': str(target.relative_to(ROOT)), 'time_utc': datetime.now(timezone.utc).isoformat()}
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'ProteinLigandReliabilityResearch/0.1 (public data analysis)', 'Accept':'*/*'})
        with urllib.request.urlopen(request, timeout=90) as response:
            length = response.headers.get('Content-Length')
            if length and int(length) > cap:
                raise RuntimeError(f'Advertised response {length} exceeds cap {cap}')
            entry['resolved_url'] = response.geturl()
            entry['content_type'] = response.headers.get('Content-Type')
            total = 0
            sha = hashlib.sha256()
            md5 = hashlib.md5()
            started = time.monotonic()
            with part.open('wb') as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > cap:
                        raise RuntimeError('Response exceeded storage cap')
                    if time.monotonic() - started > 600:
                        raise TimeoutError('Acquisition exceeded ten-minute per-file limit')
                    f.write(chunk)
                    sha.update(chunk)
                    md5.update(chunk)
            if length and total != int(length):
                raise RuntimeError('Incomplete response')
            if target.suffix == '.json':
                json.loads(part.read_text(encoding='utf-8'))
            if target.suffix == '.pdf':
                with part.open('rb') as f:
                    if f.read(5) != b'%PDF-':
                        raise RuntimeError('PDF source returned non-PDF content')
            if key in EXPECTED_MD5 and md5.hexdigest() != EXPECTED_MD5[key]:
                raise RuntimeError('Published source MD5 mismatch')
            os.replace(part, target)
            entry.update(status='downloaded', bytes=total, sha256=sha.hexdigest(), md5=md5.hexdigest())
    except Exception as e:
        if part.exists():
            part.unlink()  # Only this script's incomplete download, never user material.
        entry.update(status='error', error=f'{type(e).__name__}: {e}')
    record(entry)
    print(json.dumps(entry, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('sources', nargs='*', choices=list(SOURCES))
    args = parser.parse_args()
    for key in args.sources or list(SOURCES):
        fetch(key)
    print(json.dumps(guard()), flush=True)
