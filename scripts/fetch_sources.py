"""Download public source files. Uses only the Python standard library."""
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)
BASE = 'https://api.neso.energy'
INPUT_ID = '88cfa584-db79-4573-a0c0-c14086257f8f'
OUTPUT_ID = 'cc2dad0c-393c-4ae0-ae67-a98703169ad4'

def get(url, filename):
    req = urllib.request.Request(url, headers={'User-Agent':'Hydrogen-TEA-public-data-study/0.1'})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read()
        final_url = response.url
    dest = RAW / filename
    dest.write_bytes(data)
    print(filename, len(data), 'bytes')
    return {'file':filename,'source_url':url,
            'retrieved_utc':datetime.now(timezone.utc).isoformat(),
            'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def api(action, **params):
    return BASE+'/api/3/action/'+action+'?'+urllib.parse.urlencode(params)

if __name__ == '__main__':
    jobs = [
        (api('datastore_search',resource_id=INPUT_ID,limit=100), 'neso_inputs.json'),
        (api('package_show',id='levelised-cost-of-green-hydrogen'), 'neso_package_metadata.json'),
        (api('datastore_search',resource_id=OUTPUT_ID,limit=5), 'neso_output_sample.json'),
    ]
    sql = ('SELECT * FROM "'+OUTPUT_ID+'" WHERE "Build Year" = \'2025\' '
           'AND "Scenario" = \'Central\' AND "Units" = \'£/kg H2\' '
           'AND "Capacity Factor" IN (0.05,0.50,0.95) '
           'AND "Electricity Price" IN (0,50,150) '
           'AND "Discount Factor" IN (0.06,0.08,0.15) '
           'ORDER BY "Tech", "Capacity Factor", "Electricity Price", "Discount Factor"')
    jobs.append((api('datastore_search_sql',sql=sql),'neso_reference_cases.json'))
    manifest=[]
    for url,filename in jobs:
        manifest.append(get(url,filename))
    (RAW/'download_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
