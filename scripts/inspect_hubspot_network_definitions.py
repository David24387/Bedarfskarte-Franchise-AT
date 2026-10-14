#!/usr/bin/env python3
"""Inspect HubSpot company property definitions only. No company records."""
import json
import os
import re
import urllib.request

request=urllib.request.Request(
    "https://api.hubapi.com/crm/v3/properties/companies",
    headers={"Authorization":"Bearer "+os.environ["HUBSPOT_TOKEN"]}
)
with urllib.request.urlopen(request,timeout=40) as response:
    properties=json.load(response)["results"]

terms=("netzwerk","network","franchise","efr","plp","partner","betriebstyp","standorttyp")
candidates=[
    p for p in properties
    if any(t in (p.get("name","")+" "+p.get("label","")).casefold() for t in terms)
]
print("Company property definitions:",len(properties))
print("Possible network-related field definitions:",len(candidates))
for prop in candidates:
    options=prop.get("options") or []
    print("Field:",prop["name"],"| label:",prop.get("label",""),
          "| type:",prop.get("type",""),
          "| option count:",len(options))
    for opt in options:
        label=str(opt.get("label",""))
        value=str(opt.get("value",""))
        if any(re.search(r"(?<![a-z])"+re.escape(t)+r"(?![a-z])",(label+" "+value).casefold()) for t in ("franchise","efr","plp")):
            print("  Network option:",label,"/",value)
print("Only property metadata inspected. No company records requested or changed.")
