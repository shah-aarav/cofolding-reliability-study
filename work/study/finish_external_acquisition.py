"""Run full external retry/verification automatically after collection finishes.

Only acquisition, native ranking and input sequence overlap; no accuracy labels.
"""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
CUTOFF=datetime(2026,10,27,13,tzinfo=timezone.utc).timestamp()
status_path=BASE/'manifests/external_acquisition_followup_status.json'

def checkpoint(status,error=None):
    status_path.write_text(json.dumps({'status':status,'time_utc':datetime.now(timezone.utc).isoformat(),
                                       'error':error,'experimental_outcomes_examined':False},indent=2))

try:
    checkpoint('waiting_for_full_collector')
    while time.time()<CUTOFF:
        status=json.loads((BASE/'manifests/openbind_collection_status.json').read_text())
        if status['status']!='running':break
        time.sleep(15)
    if time.time()>=CUTOFF:
        checkpoint('morning_cutoff_without_followup')
    else:
        environment=os.environ.copy()
        environment['PYTHONPATH']=str(BASE/'deps')
        for script in ('retry_openbind_failures.py','audit_openbind_native_outputs.py','audit_external_receptor_overlap.py'):
            checkpoint('running_'+script)
            subprocess.run([sys.executable,str(BASE/script)],cwd=BASE,env=environment,check=True,timeout=1200)
        checkpoint('completed_full_acquisition_followup')
except Exception as e:
    checkpoint('failed',f'{type(e).__name__}: {e}')
    raise
