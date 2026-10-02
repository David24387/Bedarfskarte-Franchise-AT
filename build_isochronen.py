#!/usr/bin/env python3
import csv,json,os,time,urllib.request,urllib.error
from pathlib import Path
API_KEY=os.environ.get('ORS_API_KEY','').strip(); OUT=Path('isochronen.json'); RANGE=1800; ENGINE_VERSION=2
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
def request(c,max_attempts=6):
 body=json.dumps({'locations':[[c['lng'],c['lat']]],'range':[RANGE],'range_type':'time','location_type':'start','smoothing':0.0,'attributes':['area','reachfactor']}).encode()
 for attempt in range(1,max_attempts+1):
  try:
   req=urllib.request.Request('https://api.heigit.org/openrouteservice/v2/isochrones/driving-car',data=body,headers={'Authorization':API_KEY,'Content-Type':'application/json','Accept':'application/geo+json','Accept-Encoding':'identity','Connection':'close','User-Agent':'Euromaster-Bedarfskarte-AT/2.1'},method='POST')
   with urllib.request.urlopen(req,timeout=120) as r:
    raw=r.read()
   data=json.loads(raw.decode('utf-8'))
   if not isinstance(data,dict) or not data.get('features'):raise ValueError('ORS-Antwort ohne Features')
   return data
  except Exception as e:
   code=getattr(e,'code',None)
   if isinstance(e,urllib.error.HTTPError) and code not in {408,429,500,502,503,504}:raise
   if attempt==max_attempts:raise
   wait=min(60,5*(2**(attempt-1)))
   print(f"  ORS-Antwort für {c['name']} fehlerhaft ({type(e).__name__}{' HTTP '+str(code) if code else ''}) – Versuch {attempt}/{max_attempts}, erneut in {wait}s")
   time.sleep(wait)
def point_in_ring(x,y,ring):
 inside=False;j=len(ring)-1
 for i in range(len(ring)):
  xi,yi=ring[i][0],ring[i][1];xj,yj=ring[j][0],ring[j][1]
  if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/((yj-yi) or 1e-15)+xi:inside=not inside
  j=i
 return inside
def contains_geom(g,x,y):
 if not g:return False
 co=g.get('coordinates') or [];polys=[co] if g.get('type')=='Polygon' else co if g.get('type')=='MultiPolygon' else []
 return any(poly and point_in_ring(x,y,poly[0]) and not any(point_in_ring(x,y,h) for h in poly[1:]) for poly in polys)
def valid_feature(f,c):
 try:return contains_geom(f.get('geometry'),c['lng'],c['lat'])
 except:return False
def save_cache(cache,centers):
 features=[cache[key(c)] for c in centers if key(c) in cache and valid_feature(cache[key(c)],c)]
 OUT.write_text(json.dumps({'type':'FeatureCollection','properties':{'minutes':30,'seconds':RANGE,'profile':'driving-car','range_type':'time','smoothing':0,'engine_version':ENGINE_VERSION,'country':'AT','source':'openrouteservice / OpenStreetMap','centers_total':len(centers),'centers_complete':len(features),'networks':['Franchise','EFR','PLP']},'features':features},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 return features
def main():
 rows=list(csv.reader(Path('daten.csv').open(encoding='utf-8-sig',newline='')))
 hi=next((i for i,r in enumerate(rows[:10]) if 'lat' in ' '.join(r).lower() and ('long' in ' '.join(r).lower() or 'längengrad' in ' '.join(r).lower())),0);h=[norm(x) for x in rows[hi]];centers=[];skipped=[]
 for vals in rows[hi+1:]:
  d={h[i]:vals[i] if i<len(vals) else '' for i in range(len(h)) if h[i]};network=norm(get(d,'Netzwerk')).upper();status=norm(get(d,'Status')).lower()
  if network not in {'FRANCHISE','EFR','PLP'} or (status and status!='geöffnet'):continue
  lat=num(get(d,'Lat.','Lat','Latitude','Lat./Breitengard','Lat./Breitengrad','Breitengrad'));lng=num(get(d,'Long.','Long','Lng','Longitude','Long./Längengrad','Längengrad'))
  if lat is None or lng is None or not (46.2<=lat<=49.1 and 9.4<=lng<=17.3):skipped.append(norm(get(d,'Ort')));continue
  centers.append({'lat':lat,'lng':lng,'name':norm(get(d,'Ort','KST','Netzkennung','Name')),'plz':norm(get(d,'PLZ')),'netz':norm(get(d,'Netzkennung','KST')),'network':network})
 print(f'{len(centers)} offene AT-Netzstandorte erkannt (Franchise + EFR + PLP).')
 if skipped:print('WARNUNG Koordinaten unbrauchbar:',', '.join(skipped))
 cache={};old_version=None
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text(encoding='utf-8'));old_version=(old.get('properties') or {}).get('engine_version')
   if old_version==ENGINE_VERSION:
    for f in old.get('features',[]):
     p=f.get('properties') or {};cache[f"{float(p['lat']):.6f}|{float(p['lng']):.6f}"]=f
   else:print(f'Isochronen-Engine geändert ({old_version} -> {ENGINE_VERSION}): alle {len(centers)} Flächen werden frisch berechnet.')
  except Exception as e:print('Cache nicht lesbar:',e)
 for c in centers:
  if key(c) in cache and not valid_feature(cache[key(c)],c):del cache[key(c)]
 missing=[c for c in centers if key(c) not in cache];print(f'{len(cache)} im aktuellen Cache; {len(missing)} frisch zu berechnen.')
 for i,c in enumerate(missing,1):
  if i>1:time.sleep(3.5)
  try:
   fs=request(c).get('features') or [];f=fs[0] if fs else None
   if not f:raise RuntimeError('Keine Isochrone')
   orsprops=f.get('properties') or {}
   f['properties']={'name':c['name'],'plz':c['plz'],'netz':c['netz'],'network':c['network'],'minutes':30,'seconds':RANGE,'profile':'driving-car','smoothing':0,'lat':c['lat'],'lng':c['lng'],'area':orsprops.get('area'),'reachfactor':orsprops.get('reachfactor'),'engine_version':ENGINE_VERSION}
   if not valid_feature(f,c):raise RuntimeError('eigener Standort nicht in Isochrone')
   cache[key(c)]=f;save_cache(cache,centers);print(f"OK {i}/{len(missing)} {c['network']} {c['name']} (Zwischenstand gespeichert)")
  except Exception as e:
   save_cache(cache,centers);print('FEHLER',c['name'],repr(e))
 features=save_cache(cache,centers);failed=[c for c in centers if key(c) not in cache or not valid_feature(cache[key(c)],c)]
 print(f'VALIDIERUNG: {len(features)}/{len(centers)} Standorte mit validierter 30-Minuten-Isochrone.')
 if failed:print('FEHLEN:',', '.join(c['name'] for c in failed));raise SystemExit(1)
if __name__=='__main__':main()
