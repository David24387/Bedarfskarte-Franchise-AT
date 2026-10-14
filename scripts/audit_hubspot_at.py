#!/usr/bin/env python3
"""Read-only HubSpot AT field and mapping audit. Prints aggregate counts only."""
import csv, collections, io, json, os, urllib.parse, urllib.request
token=os.environ["HUBSPOT_TOKEN"]
base="https://api.hubapi.com"
def get(path, params=None):
    url=base+path+("?"+urllib.parse.urlencode(params) if params else "")
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as response:return json.load(response)
properties=get("/crm/v3/properties/companies")["results"]
names={p["name"] for p in properties}
wanted=["name","country","hs_country_code","land","partner_id","forms_partner_id_focus_id","unternehmensname_mit_id","address","city","zip","latitude","longitude","hs_latitude","hs_longitude","hs_gps_latitude","hs_gps_longitude","kundenstatus","rla_status","public","efr_daten"]
fields=[n for n in wanted if n in names]
print("Available candidate properties:",", ".join(fields))
for p in properties:
    if p["name"] in ("kundenstatus","rla_status","public","bg_status","prioritatspartner"):
        print("Enum",p["name"],"options:",[(o.get("label"),o.get("value")) for o in p.get("options",[])])
rows=[];after=None
while True:
    params={"limit":100,"properties":",".join(fields)}
    if after:params["after"]=after
    result=get("/crm/v3/objects/companies",params)
    rows.extend(result.get("results",[]))
    after=result.get("paging",{}).get("next",{}).get("after")
    if not after:break
at=[r["properties"] for r in rows if any(str(r["properties"].get(k) or "").strip().casefold() in ("at","aut","austria","österreich","osterreich") for k in ("country","hs_country_code"))]
print("Companies scanned:",len(rows),"AT candidates:",len(at))
print("Field non-empty counts:",dict(sorted((f,sum(bool(r.get(f)) for r in at)) for f in fields)))
for f in ("land","kundenstatus","rla_status","public"):
    if f in fields:print("Value distribution",f,dict(collections.Counter(str(r.get(f) or "<empty>") for r in at).most_common(20)))
with open("daten.csv",encoding="utf-8-sig",newline="") as fp:
    csvrows=list(csv.reader(fp))
header=next(i for i,row in enumerate(csvrows) if "KST" in row and "Netzwerk" in row)
existing=[dict(zip(csvrows[header],row)) for row in csvrows[header+1:] if row]
print("Existing CSV records:",len(existing))
print("Existing networks:",dict(collections.Counter(r.get("Netzwerk","") for r in existing)))
print("NOTE: no data files changed; no individual company values printed.")
