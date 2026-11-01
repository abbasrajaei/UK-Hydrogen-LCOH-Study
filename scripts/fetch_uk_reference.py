"""Download the public UK reference files. Standard Python only."""
import hashlib
import json
from pathlib import Path
import urllib.request
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw';RAW.mkdir(parents=True,exist_ok=True)
files={
    'uk_hydrogen_costs_2021.pdf':'https://assets.publishing.service.gov.uk/media/611b710e8fa8f53dc994e59d/Hydrogen_Production_Costs_2021.pdf',
    'uk_hydrogen_costs_2021_annex.xlsx':'https://assets.publishing.service.gov.uk/media/611a706ed3bf7f63a7b29216/Hydrogen_Production_Cost_2021_Annex.xlsx',
}
manifest=[]
for name,url in files.items():
    with urllib.request.urlopen(url,timeout=90) as response:
        raw=response.read()
    (RAW/name).write_bytes(raw)
    manifest.append({'file':name,'url':url,'bytes':len(raw),
                     'retrieved_utc':datetime.now(timezone.utc).isoformat(),
                     'sha256':hashlib.sha256(raw).hexdigest()})
    print(name,len(raw),'bytes')
(RAW/'uk_source_downloads.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
