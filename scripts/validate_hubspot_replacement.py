"""Run actual Public-only exporter in a temporary directory. No live files changed."""
import collections
import csv
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).with_name('sync_hubspot_at.py').resolve()
with tempfile.TemporaryDirectory() as directory:
    subprocess.run([sys.executable, str(script), '--audience', 'public'], cwd=directory, check=True)
    with (Path(directory) / 'daten.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    print('ACTUAL_PUBLIC_EXPORT_ROWS:', len(rows))
    print('NETWORK_COUNTS:', dict(collections.Counter(row['Netzwerk'] for row in rows)))
    print('MISSING_COORDINATES:', sum(not row['Lat./Breitengard'] or not row['Long./Längengrad'] for row in rows))
    print('Export works without an existing Excel/CSV list; repository files unchanged.')
