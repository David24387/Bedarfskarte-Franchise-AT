#!/usr/bin/env python3
import csv,json,os,time,urllib.request,urllib.error
from pathlib import Path
API_KEY=os.environ.get('ORS_API_KEY','').strip(); OUT=Path('isochronen.json'); RANGE=1800
if not API_KEY: raise SystemExit('ORS_API_KEY fehlt.')
def norm(v): return (v or '').strip()
def num(v):
 try:return float(norm(v).replace(',','.'))
 except:return None
def get(d,*names):
 low={str(k).strip().lower():v for k,v in d.items()}
 for n in names:
  if n.lower() in low:return low[n.lower()]
 return ''
def key(c):return f"{c['lat']:.6f}|{c['lng']:.6f}"
def request(c):
 body=json.dumps({'locations':[[c['lng'],c['lat']]],'range':[RANGE],'range_type':'time','location_type':'start'}).encode()
 req=urllib.request.Request('https://api.heigit.org/openrouteservice/v2/isochrones/driving-car',data=body,headers={'Authorization':API_KEY,'Content-Type':'application/json','Accept':'application/geo+json','User-Agent':'Euromaster-Bedarfskarte-AT/1.0'},method='POST')
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def main():
 rows=list(csv.reader(Path('daten.csv').open(encoding='utf-8-sig',newline='')))
 hi=next((i for i,r in enumerate(rows[:10]) if 'lat' in ' '.join(r).lower() and ('long' in ' '.join(r).lower() or 'lng' in ' '.join(r).lower())),0)
 h=[norm(x) for x in rows[hi]]; centers=[]
 for vals in rows[hi+1:]:
  d={h[i]:vals[i] if i<len(vals) else '' for i in range(len(h)) if h[i]}
  lat=num(get(d,'Lat.','Lat','Latitude'));lng=num(get(d,'Long.','Long','Lng','Longitude'))
  if lat is None or lng is None:continue
  # Sicherheitsfilter Österreich
  if not (46.2 <= lat <= 49.1 and 9.4 <= lng <= 17.3):continue
  centers.append({'lat':lat,'lng':lng,'name':norm(get(d,'Ort','KST','Netzkennung','Name')),'plz':norm(get(d,'PLZ')),'netz':norm(get(d,'Netzkennung'))})
 if not centers:raise SystemExit('Keine gültigen AT-Standorte mit Koordinaten erkannt.')
 cache={}
 if OUT.exists():
  try:
   for f in json.loads(OUT.read_text(encoding='utf-8')).get('features',[]):
    p=f.get('properties') or {}; cache[f"{float(p['lat']):.6f}|{float(p['lng']):.6f}"]=f
  except Exception as e:print('Cache nicht lesbar:',e)
 batch=int(os.environ.get('ISOCHRONE_BATCH_SIZE','25'));missing=[c for c in centers if key(c) not in cache]
 print(f'{len(centers)} AT-Standorte; {len(cache)} Cache; {len(missing)} offen.')
 for i,c in enumerate(missing[:batch],1):
  if i>1:time.sleep(3.5)
  try:
   data=request(c);f=(data.get('features') or [])[0];f['properties']={'name':c['name'],'plz':c['plz'],'netz':c['netz'],'minutes':30,'lat':c['lat'],'lng':c['lng']};cache[key(c)]=f;print('OK',c['name'])
  except Exception as e:print('OFFEN',c['name'],e)
 features=[cache[key(c)] for c in centers if key(c) in cache]
 if not features:raise SystemExit('Noch keine Isochronen verfügbar.')
 OUT.write_text(json.dumps({'type':'FeatureCollection','properties':{'minutes':30,'profile':'driving-car','country':'AT','source':'openrouteservice / OpenStreetMap'},'features':features},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(f'{len(features)}/{len(centers)} Fahrzeitgebiete gespeichert.')
if __name__=='__main__':main()
