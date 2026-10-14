#!/usr/bin/env python3
"""Read-only, privacy-preserving aggregate comparison of AT CSV and HubSpot.
No names, addresses, IDs or tokens are printed or persisted.
"""
import collections
import csv
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request

TOKEN=os.environ["HUBSPOT_TOKEN"]
def fetch(path,params=None):
    url="https://api.hubapi.com"+path
    if params:url+="?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=40) as r:return json.load(r)

def norm(v):
    s=unicodedata.normalize("NFKD",str(v or "").casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]","",s)
def country(v):
    return norm(v) in ("at","aut","austria","osterreich")
def coords(p):
    for a,b in (("latitude","longitude"),("hs_latitude","hs_longitude"),("hs_gps_latitude","hs_gps_longitude")):
        try:
            lat=float(str(p.get(a) or "").replace(",","."));lng=float(str(p.get(b) or "").replace(",","."))
            if 46<=lat<=49.5 and 9<=lng<=18:return True
        except (ValueError,TypeError):pass
    return False

props=fetch("/crm/v3/properties/companies")["results"]
available={p["name"] for p in props}
wanted=["name","country","hs_country_code","land","address","city","zip","partner_id","forms_partner_id_focus_id","unternehmensname_mit_id","latitude","longitude","hs_latitude","hs_longitude","hs_gps_latitude","hs_gps_longitude","kundenstatus","public","efr_daten"]
fields=[x for x in wanted if x in available]
records=[];after=None
while True:
    params={"limit":100,"properties":",".join(fields)}
    if after:params["after"]=after
    page=fetch("/crm/v3/objects/companies",params)
    records.extend(x.get("properties",{}) for x in page.get("results",[]))
    after=page.get("paging",{}).get("next",{}).get("after")
    if not after:break
at=[p for p in records if country(p.get("country")) or country(p.get("hs_country_code"))]
with open("daten.csv",encoding="utf-8-sig",newline="") as f:rows=list(csv.reader(f))
header_index=next(i for i,row in enumerate(rows) if "KST" in row and "Netzwerk" in row)
header=rows[header_index]
old=[dict(zip(header,r)) for r in rows[header_index+1:] if any(v.strip() for v in r)]
def keys_csv(r):
    result=set()
    for field in ("KST","Netzkennung"):
        if norm(r.get(field)):result.add(("id",norm(r[field])))
    name=norm(r.get("Gesellschaft"));city=norm(r.get("Ort"));street=norm(r.get("Strasse") or r.get("Straße"))
    if name and city:result.add(("namecity",name,city))
    if street and city:result.add(("streetcity",street,city))
    return result
def keys_hub(p):
    result=set()
    for field in ("partner_id","forms_partner_id_focus_id"):
        if norm(p.get(field)):result.add(("id",norm(p[field])))
    name=norm(p.get("name"));city=norm(p.get("city"));street=norm(p.get("address"))
    if name and city:result.add(("namecity",name,city))
    if street and city:result.add(("streetcity",street,city))
    return result
hubkeys=[keys_hub(p) for p in at]
bykey=collections.defaultdict(set)
for i,ks in enumerate(hubkeys):
    for k in ks:bykey[k].add(i)
matched=set();ambiguous=0;method=collections.Counter();unmatched=collections.Counter()
for row in old:
    matches=set()
    keys=keys_csv(row)
    for k in keys:matches.update(bykey.get(k,set()))
    if len(matches)==1:
        matched.update(matches)
        if any(k[0]=="id" and k in hubkeys[next(iter(matches))] for k in keys):method["ID"]=method["ID"]+1
        elif any(k[0]=="namecity" and k in hubkeys[next(iter(matches))] for k in keys):method["Name + Ort"]+=1
        else:method["Straße + Ort"]+=1
    elif len(matches)>1:ambiguous+=1
    else:unmatched[row.get("Netzwerk") or "unbekannt"]+=1
print("Read-only aggregate AT reconciliation")
print("CSV total:",len(old),"CSV networks:",dict(collections.Counter(x.get("Netzwerk","") for x in old)))
print("HubSpot Austria candidates:",len(at))
print("HubSpot candidates with usable Austrian coordinates:",sum(coords(x) for x in at))
print("HubSpot active:",sum(x.get("kundenstatus")=="Aktiv" for x in at))
print("HubSpot with partner ID:",sum(bool(x.get("partner_id")) for x in at))
print("CSV rows uniquely matched:",sum(method.values()))
print("Match methods:",dict(method))
print("CSV rows with ambiguous matches:",ambiguous)
print("CSV rows unmatched by network:",dict(unmatched))
print("Unique matched HubSpot records:",len(matched))
print("Matched HubSpot records with coordinates:",sum(coords(at[i]) for i in matched))
print("Matched HubSpot records with status Aktiv:",sum(at[i].get("kundenstatus")=="Aktiv" for i in matched))
print("Privacy: no individual records, addresses, names, IDs, or credentials logged; no files changed.")
