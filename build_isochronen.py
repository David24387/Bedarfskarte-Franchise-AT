#!/usr/bin/env python3
import csv,json,os,time,urllib.request
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
 req=urllib.request.Request('https://api.heigit.org/openrouteservice/v2/isochrones/driving-car',data=body,headers={'Authorization':API_KEY,'Content-Type':'application/json','Accept':'application/geo+json','User-Agent':'Euromaster-Bedarfskarte-AT/1.3'},method='POST')
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
def point_in_ring(x,y,ring):
 inside=False
 if not ring:return False
 j=len(ring)-1
 for i in range(len(ring)):
  xi,yi=ring[i][0],ring[i][1]; xj,yj=ring[j][0],ring[j][1]
  if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/((yj-yi) or 1e-15)+xi: inside=not inside
  j=i
 return inside
def contains_geom(g,x,y):
 if not g:return False
 typ=g.get('type'); co=g.get('coordinates') or []
 polys=[co] if typ=='Polygon' else co if typ=='MultiPolygon' else []
 for poly in polys:
  if poly and point_in_ring(x,y,poly[0]) and not any(point_in_ring(x,y,h) for h in poly[1:]):return True
 return False
def valid_feature(f,c):
 try:
  p=f.get('properties') or {}
  if abs(float(p.get('lat'))-c['lat'])>1e-5 or abs(float(p.get('lng'))-c['lng'])>1e-5:return False
  return contains_geom(f.get('geometry'),c['lng'],c['lat'])
 except:return False
def main():
 rows=list(csv.reader(Path('daten.csv').open(encoding='utf-8-sig',newline='')))
 hi=next((i for i,r in enumerate(rows[:10]) if 'lat' in ' '.join(r).lower() and ('long' in ' '.join(r).lower() or 'lng' in ' '.join(r).lower() or 'längengrad' in ' '.join(r).lower())),0)
 h=[norm(x) for x in rows[hi]]; centers=[]
 for vals in rows[hi+1:]:
  d={h[i]:vals[i] if i<len(vals) else '' for i in range(len(h)) if h[i]}
  lat=num(get(d,'Lat.','Lat','Latitude','Lat./Breitengard','Lat./Breitengrad','Breitengrad')); lng=num(get(d,'Long.','Long','Lng','Longitude','Long./Längengrad','Längengrad')); plz=norm(get(d,'PLZ'))
  if lat is None or lng is None or not plz.upper().startswith('A-'):continue
  if not (46.2<=lat<=49.1 and 9.4<=lng<=17.3):continue
  centers.append({'lat':lat,'lng':lng,'name':norm(get(d,'Ort','KST','Netzkennung','Name')),'plz':plz,'netz':norm(get(d,'Netzkennung','KST'))})
 if not centers:raise SystemExit('Keine gültigen AT-Standorte mit Koordinaten erkannt.')
 cache={}
 if OUT.exists():
  try:
   for f in json.loads(OUT.read_text(encoding='utf-8')).get('features',[]):
    p=f.get('properties') or {}; cache[f"{float(p['lat']):.6f}|{float(p['lng']):.6f}"]=f
  except Exception as e:print('Cache nicht lesbar:',e)
 invalid=[]
 for c in centers:
  k=key(c)
  if k in cache and not valid_feature(cache[k],c): invalid.append(c); del cache[k]
 print(f'{len(centers)} AT-Standorte; {len(invalid)} ungültige Cache-Isochronen verworfen.')
 missing=[c for c in centers if key(c) not in cache]; batch=int(os.environ.get('ISOCHRONE_BATCH_SIZE','200'))
 print(f'{len(cache)} gültig im Cache; {len(missing)} neu/erneut zu berechnen.')
 for i,c in enumerate(missing[:batch],1):
  if i>1:time.sleep(3.5)
  try:
   data=request(c); fs=data.get('features') or []
   if not fs:raise RuntimeError('Keine Isochrone zurückgegeben')
   f=fs[0]; f['properties']={'name':c['name'],'plz':c['plz'],'netz':c['netz'],'minutes':30,'lat':c['lat'],'lng':c['lng']}
   if not valid_feature(f,c):raise RuntimeError('ORS-Isochrone enthält eigene Standortkoordinate nicht')
   cache[key(c)]=f; print('OK',c['name'])
  except Exception as e:print('FEHLER',c['name'],e)
 features=[cache[key(c)] for c in centers if key(c) in cache and valid_feature(cache[key(c)],c)]
 validkeys={key(c) for c in centers if key(c) in cache and valid_feature(cache[key(c)],c)}
 failed=[c for c in centers if key(c) not in validkeys]
 OUT.write_text(json.dumps({'type':'FeatureCollection','properties':{'minutes':30,'profile':'driving-car','country':'AT','source':'openrouteservice / OpenStreetMap','centers_total':len(centers),'centers_complete':len(features),'validation':'each center inside own isochrone'},'features':features},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(f'VALIDIERUNG: {len(features)}/{len(centers)} Standorte liegen in ihrer eigenen 30-Minuten-Isochrone.')
 if failed:
  print('FEHLEN/UNGÜLTIG:',', '.join(f"{c['name']} ({c['plz']})" for c in failed)); raise SystemExit(1)
if __name__=='__main__':main()
