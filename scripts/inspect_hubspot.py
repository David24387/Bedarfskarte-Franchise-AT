#!/usr/bin/env python3
"""Read-only HubSpot inventory. Never logs tokens, names or personal data."""
import json, os, urllib.request, urllib.parse, urllib.error
TOKEN=os.environ.get("HUBSPOT_TOKEN")
if not TOKEN:
    raise SystemExit("HUBSPOT_TOKEN missing: configure GitHub Actions secret")
BASE="https://api.hubapi.com"
def get(path, params=None):
    url=BASE+path+("?"+urllib.parse.urlencode(params) if params else "")
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=35) as res:return json.load(res)
    except urllib.error.HTTPError as e:
        raise SystemExit("HubSpot API error HTTP %s for %s (check token scopes)"%(e.code,path))
def pages(path,params=None):
    after=None
    while True:
        p=dict(params or {})
        if after:p["after"]=after
        data=get(path,p)
        yield from data.get("results",[])
        after=data.get("paging",{}).get("next",{}).get("after")
        if not after:break
props=list(pages("/crm/v3/properties/companies"))
names={p["name"] for p in props}
keys=("country","land","region","austria","österreich","euromaster","partner","netz","network","latitude","longitude","status","franchise","plp","efr","street","address","city","zip")
candidates=[{"name":p["name"],"label":p.get("label",""),"type":p.get("type","")} for p in props if any(k in (p["name"]+" "+p.get("label","")).lower() for k in keys)]
print("Company properties:",len(props))
print("Candidate field definitions (no CRM record values):")
print(json.dumps(candidates,ensure_ascii=False,indent=2))
country_fields=[x for x in ("country","country_code","hs_country_code") if x in names]
if not country_fields:
    print("No standard country field found. Need mapping before importing.")
else:
    fields=list(dict.fromkeys(["name"]+country_fields))
    counts={}
    total=0
    for row in pages("/crm/v3/objects/companies",{"limit":100,"properties":",".join(fields)}):
        total+=1
        v=row.get("properties",{})
        if any(str(v.get(k) or "").strip().casefold() in ("at","aut","austria","österreich","osterreich") for k in country_fields):
            counts["AT exact matches"]=counts.get("AT exact matches",0)+1
    print("Companies scanned:",total)
    print("Country-only Austria candidates:",counts.get("AT exact matches",0))
    print("IMPORTANT: not yet filtered to Euromaster; no map data was changed.")
