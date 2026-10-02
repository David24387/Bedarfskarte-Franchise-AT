#!/usr/bin/env python3
import csv, io, json, math, urllib.request, bisect
from pathlib import Path

AEST='https://data.statistik.gv.at/data/OGDEXT_AEST_GEMTAB_1.csv'
GEO='https://raw.githubusercontent.com/ginseng666/GeoJSON-TopoJSON-Austria/master/2021/simplified-99.9/gemeinden_999_geo.json'
PKW={1:702,2:670,3:363,4:667,5:631,6:651,7:577,8:555,9:548}
INCOME={1:31200,2:31600,3:28200,4:30100,5:30700,6:30800,7:31300,8:30600,9:31000}
STATE={1:'Burgenland',2:'Niederösterreich',3:'Wien',4:'Kärnten',5:'Steiermark',6:'Oberösterreich',7:'Salzburg',8:'Tirol',9:'Vorarlberg'}
UA={'User-Agent':'Euromaster-Franchise-Potential-AT/2.0'}

def get(url):
 req=urllib.request.Request(url,headers=UA)
 with urllib.request.urlopen(req,timeout=90) as r:return r.read()
def fnum(v):
 try:return float(str(v).replace('.','').replace(',','.'))
 except:return None
def area_ring(ring):
 if len(ring)<3:return 0
 R=6371008.8;s=0
 for i in range(len(ring)):
  lon1,lat1=map(math.radians,ring[i-1][:2]);lon2,lat2=map(math.radians,ring[i][:2]);s+=(lon2-lon1)*(2+math.sin(lat1)+math.sin(lat2))
 return abs(s)*R*R/2
def area(g):
 co=g.get('coordinates',[]);polys=[co] if g.get('type')=='Polygon' else co if g.get('type')=='MultiPolygon' else []
 return sum(max(0,area_ring(p[0])-sum(area_ring(h) for h in p[1:])) for p in polys if p)/1e6
def pct(vals,v):return bisect.bisect_right(vals,v)/len(vals) if vals and v is not None else None
def point_ring(x,y,ring):
 inside=False;j=len(ring)-1
 for i in range(len(ring)):
  xi,yi=ring[i][:2];xj,yj=ring[j][:2]
  if ((yi>y)!=(yj>y)) and x < (xj-xi)*(y-yi)/((yj-yi) or 1e-15)+xi:inside=not inside
  j=i
 return inside
def contains(g,x,y):
 co=g.get('coordinates',[]);polys=[co] if g.get('type')=='Polygon' else co if g.get('type')=='MultiPolygon' else []
 return any(p and point_ring(x,y,p[0]) and not any(point_ring(x,y,h) for h in p[1:]) for p in polys)
def bbox(g):
 pts=[]
 def walk(v):
  if isinstance(v,list) and len(v)>=2 and isinstance(v[0],(int,float)) and isinstance(v[1],(int,float)):pts.append(v[:2])
  elif isinstance(v,list):
   for z in v:walk(z)
 walk(g.get('coordinates',[]));return [min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)] if pts else None

def demand_share(g,iso_geoms):
 # Rasterstichprobe innerhalb der Gemeinde. Ein Punkt ist Bedarf, wenn er in keiner 30-Min-Isochrone liegt.
 b=bbox(g)
 if not b:return 0
 inside=uncovered=0;n=9
 for iy in range(n):
  y=b[1]+(iy+.5)/n*(b[3]-b[1])
  for ix in range(n):
   x=b[0]+(ix+.5)/n*(b[2]-b[0])
   if not contains(g,x,y):continue
   inside+=1
   cov=False
   for ig,ib in iso_geoms:
    if x<ib[0] or y<ib[1] or x>ib[2] or y>ib[3]:continue
    if contains(ig,x,y):cov=True;break
   if not cov:uncovered+=1
 return uncovered/inside if inside else 0

def main():
 raw=get(AEST).decode('utf-8-sig');dialect=csv.Sniffer().sniff(raw[:5000],delimiters=';,');rows=list(csv.DictReader(io.StringIO(raw),dialect=dialect))
 years=[int(r.get('JAHR','0') or 0) for r in rows if str(r.get('JAHR','')).isdigit()];year=max(years);rows=[r for r in rows if str(r.get('JAHR'))==str(year)]
 bycode={''.join(c for c in str(r.get('GCD','')) if c.isdigit())[-5:].zfill(5):r for r in rows}
 geo=json.loads(get(GEO));regions=[]
 for ft in geo.get('features',[]):
  p=ft.get('properties') or {};code=str(p.get('iso','')).zfill(5);r=bycode.get(code)
  if not r:continue
  pop=fnum(r.get('BEV_ABSOLUT'));jobs=fnum(r.get('BESCH_AST'));km2=area(ft.get('geometry') or {})
  if not pop or not km2:continue
  state=int(code[0]);regions.append({'code':code,'name':p.get('name') or r.get('GEM_NAME') or code,'state':STATE.get(state,''),'geometry':ft['geometry'],'population':round(pop),'popDensity':round(pop/km2,1),'workDensity':round((jobs or 0)/pop*1000,1),'pkwDensity':PKW.get(state),'income':INCOME.get(state),'year':year})
 metrics=['popDensity','pkwDensity','income','workDensity'];weights={'popDensity':.30,'pkwDensity':.25,'income':.25,'workDensity':.20}
 sortedvals={k:sorted(x[k] for x in regions if x.get(k) is not None) for k in metrics}
 for x in regions:
  parts=[]
  for k in metrics:
   q=pct(sortedvals[k],x.get(k));x[k+'Pct']=round(q*100,1) if q is not None else None
   if q is not None:parts.append((weights[k],q))
  ws=sum(w for w,_ in parts);x['score']=round(100*sum(w*q for w,q in parts)/ws) if ws else None

 # WICHTIG: Top 20 % werden nicht aus allen Gemeinden Österreichs bestimmt,
 # sondern ausschließlich aus Gemeinden mit realer Franchise-Bedarfslücke (>30 Min Fahrzeit).
 iso_geoms=[]
 if Path('isochronen.json').exists():
  ij=json.loads(Path('isochronen.json').read_text(encoding='utf-8'))
  for f in ij.get('features',[]):
   g=f.get('geometry') or {};b=bbox(g)
   if b:iso_geoms.append((g,b))
 if not iso_geoms:raise SystemExit('isochronen.json fehlt/leer – Top-20-Bedarfsranking kann nicht korrekt berechnet werden.')
 for i,x in enumerate(regions,1):
  share=demand_share(x['geometry'],iso_geoms);x['demandShare']=round(share*100,1);x['hasDemandGap']=share>0
  if i%250==0:print(f'Bedarfsprüfung {i}/{len(regions)}')
 eligible=[x for x in regions if x.get('hasDemandGap') and x.get('score') is not None]
 eligible.sort(key=lambda x:(x['score'],x.get('demandShare',0)),reverse=True)
 top_count=max(1,math.ceil(len(eligible)*.20)) if eligible else 0
 selected=eligible[:top_count]
 selected_codes={x['code'] for x in selected}
 cut=min((x['score'] for x in selected),default=None)
 for x in regions:x['isTop20Demand']=x['code'] in selected_codes

 out={'source':'Statistik Austria Open Data / Regionale Gesamtrechnungen','methodology':'AT Marktpotenzial: Bevölkerungsdichte 30 %, Pkw-Dichte 25 %, verfügbares Einkommen je Einwohner 25 %, Arbeitsplatzkonzentration 20 %. Top 20 % werden ausschließlich innerhalb der tatsächlichen >30-Minuten-Franchise-Bedarfslücken gerankt.','years':{'municipal':year,'pkw':2025,'income':2024},'weights':weights,'top20Cutoff':cut,'top20DemandCount':top_count,'demandRegionCount':len(eligible),'regions':regions}
 Path('regionaldaten.json').write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 Path('regionaldaten_audit.json').write_text(json.dumps({'regions':len(regions),'year':year,'demandRegions':len(eligible),'top20DemandCount':top_count,'top20Cutoff':cut,'top20Codes':sorted(selected_codes),'states':STATE,'weights':weights},ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'OK: {len(regions)} Gemeinden; {len(eligible)} mit Bedarf; Top 20 % = {top_count} Gemeinden; Cutoff {cut}')
if __name__=='__main__':main()
