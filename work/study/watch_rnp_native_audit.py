"""Maintain input-only native-rank/recovery manifests while the primary stream runs."""
import json
from pathlib import Path
import time
from datetime import datetime,timezone
from reconcile_rnp_native import main

BASE=Path(__file__).resolve().parent
cutoff=datetime(2026,10,27,13,tzinfo=timezone.utc).timestamp()
last=0
while time.time()<cutoff:
    if time.time()-last>=180:
        main()
        last=time.time()
        status=json.loads((BASE/'manifests/coordinate_collection_status.json').read_text())['status']
        if status!='running':
            requests=json.loads((BASE/'manifests/rnp_recovery_requests.json').read_text())
            recovery_path=BASE/'manifests/rnp_recovery_stream_status.json'
            recovery=json.loads(recovery_path.read_text())['status'] if recovery_path.exists() else None
            if not requests or recovery!='running':break
    time.sleep(15)
