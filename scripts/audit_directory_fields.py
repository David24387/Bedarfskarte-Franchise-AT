"""Read-only metadata and aggregate completeness for Public partner directory fields."""
import collections
import json
from sync_hubspot_at import api, mapping, norm

props=api('/crm/v3/properties/companies')['results']
config=mapping(props);lc,pub,networks,yes=config
terms=['telefon','phone','email','mail','offnung','opening','dienstleist','service','ermurl','euromasterurl','bundesland','state','oem','firmenbuch','ust','vat','vertragsstart','geschaftsfuhr','website','domain']
selected=[p for p in props if any(t in norm(p['name']+' '+p.get('label','')) for t in terms)]
for p in selected:
    print('FIELD_DEFINITION:',json.dumps({k:p.get(k) for k in ('name','label','type','fieldType','options')},ensure_ascii=False))
wanted=list(dict.fromkeys(['name',lc,pub]+[p['name'] for p in selected]))
records=[];after=None
while True:
    params={'limit':100,'properties':','.join(wanted)}
    if after is not None:params['after']=after
    page=api('/crm/v3/objects/companies',params)
    records.extend(page['results'])
    after=page.get('paging',{}).get('next',{}).get('after')
    if after is None:break
public=[r['properties'] for r in records if r['properties'].get(lc) in networks and r['properties'].get(pub)==yes]
print('PUBLIC_TOTAL:',len(public))
print('FIELD_COMPLETENESS:',json.dumps({p['name']:sum(bool(str(r.get(p['name']) or '').strip()) for r in public) for p in selected}))
