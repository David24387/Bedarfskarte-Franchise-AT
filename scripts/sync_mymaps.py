#!/usr/bin/env python3
"""Fetch the public Google My Maps KML feed, validate points, emit GeoJSON."""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MID = "1YohYaQNa3ucvD0dS8X4BO3CVUJE"
URL = f"https://www.google.com/maps/d/kml?mid={MID}&forcekml=1"
NS = {"k": "http://www.opengis.net/kml/2.2"}
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; FranchiseATMapSync/1.0)"})
with urllib.request.urlopen(req, timeout=90) as response:
    data = response.read()
root = ET.fromstring(data)
features = []
for p in root.findall(".//k:Placemark", NS):
    name = (p.findtext("k:name", default="", namespaces=NS) or "").strip()
    description = (p.findtext("k:description", default="", namespaces=NS) or "").strip()
    for point in p.findall(".//k:Point", NS):
        coordinates = point.findtext("k:coordinates", default="", namespaces=NS).strip()
        try:
            lng, lat = map(float, coordinates.split(",")[:2])
        except (ValueError, IndexError):
            continue
        if not (9.0 <= lng <= 18.0 and 46.0 <= lat <= 50.0):
            continue
        features.append({"type":"Feature","geometry":{"type":"Point","coordinates":[lng,lat]},
                         "properties":{"name":name,"description":description,"source":"Google My Maps"}})
if not features:
    raise SystemExit("No valid Austrian point features found; refusing to overwrite previous data.")
output = {"type":"FeatureCollection","features":features}
target = Path("mymaps_standorte.geojson")
target.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
print(f"Synced {len(features)} Google My Maps points to {target}")
