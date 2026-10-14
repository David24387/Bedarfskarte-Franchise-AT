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
import difflib

def zipnorm(s):
    return re.sub(r"[^0-9]","",str(s or ""))

def tokens(s):
    s=unicodedata.normalize("NFKD",str(s or "").casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    return set(re.findall(r"[a-z0-9]+",s))-{"gmbh","kg","co","und","firma","gesmbh","mbh","e","u"}

def similar(a,b):
    x,y=tokens(a),tokens(b)
    return len(x&y)/len(x|y) if x and y else 0

# Strict tiers: one-to-one exact match first, then high-confidence suggestions.
assigned=set()
outcomes={}
for row_idx,row in enumerate(old):
    hits=set()
    for key in keys_csv(row):hits.update(bykey.get(key,set()))
    if len(hits)==1:
        i=next(iter(hits))
        outcomes[row_idx]=("exact",i)
        assigned.add(i)
    elif len(hits)>1:
        outcomes[row_idx]=("ambiguous",None)

# Additional strict, unique matches by zip + street or zip + city + near-exact name.
for row_idx,row in enumerate(old):
    if row_idx in outcomes:continue
    postal=zipnorm(row.get("PLZ"))
    if not postal:continue
    hits=[]
    for i,p in enumerate(at):
        if i in assigned or zipnorm(p.get("zip"))!=postal:continue
        city_equal=norm(row.get("Ort"))==norm(p.get("city")) and bool(norm(row.get("Ort")))
        street_equal=norm(row.get("Strasse") or row.get("Straße"))==norm(p.get("address")) and bool(norm(p.get("address")))
        name_ratio=difflib.SequenceMatcher(None,norm(row.get("Gesellschaft")),norm(p.get("name"))).ratio()
        if street_equal or (city_equal and name_ratio>=0.90):hits.append(i)
    if len(hits)==1:
        outcomes[row_idx]=("postal_strict",hits[0]);assigned.add(hits[0])
    elif len(hits)>1:outcomes[row_idx]=("ambiguous_postal",None)

# Suggestions are never treated as confirmed matches.
suggestions=collections.Counter()
for row_idx,row in enumerate(old):
    if row_idx in outcomes:continue
    postal=zipnorm(row.get("PLZ"))
    candidates=[]
    for i,p in enumerate(at):
        if i in assigned:continue
        same_zip=bool(postal and postal==zipnorm(p.get("zip")))
        same_city=bool(norm(row.get("Ort")) and norm(row.get("Ort"))==norm(p.get("city")))
        name_sim=similar(row.get("Gesellschaft"),p.get("name"))
        street_sim=similar(row.get("Strasse") or row.get("Straße"),p.get("address"))
        score=2*same_zip+same_city+2*name_sim+street_sim
        if score>=3.2 and (same_zip or same_city):candidates.append((score,i))
    candidates.sort(reverse=True)
    if candidates and (len(candidates)==1 or candidates[0][0]-candidates[1][0]>=1.0):
        suggestions[row.get("Netzwerk") or "unbekannt"]+=1

confirmed=collections.Counter()
unmatched=collections.Counter()
for idx,row in enumerate(old):
    status=outcomes.get(idx,("unmatched",None))[0]
    confirmed[status]+=1
    if status=="unmatched":unmatched[row.get("Netzwerk") or "unbekannt"]+=1
print("Read-only extended AT reconciliation (aggregates only)")
print("CSV total:",len(old))
print("HubSpot AT candidates:",len(at))
print("Previous exact unique:",confirmed["exact"])
print("New strict postal matches:",confirmed["postal_strict"])
print("Ambiguous exact:",confirmed["ambiguous"])
print("Ambiguous postal:",confirmed["ambiguous_postal"])
print("Remaining unmatched by network:",dict(unmatched))
print("Potential suggestions, NOT confirmed, by network:",dict(suggestions))
print("Matched HubSpot active:",sum(at[i].get("kundenstatus")=="Aktiv" for i in assigned))
print("Matched HubSpot with coordinates:",sum(coords(at[i]) for i in assigned))
print("HubSpot candidates with coordinates:",sum(coords(p) for p in at))
print("Network mapping: no verified HubSpot Franchise/EFR/PLP field established yet.")
print("Privacy: aggregate counts only; no record names, addresses, IDs, or tokens printed; no data files changed.")
