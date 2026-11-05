/* Local place/catchment search. Uses the map's existing municipality boundaries and isochrones. */
(function(root){
'use strict';
const normalize=value=>String(value??'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/ß/g,'ss').toLowerCase().trim().replace(/\s+/g,' ');
const siteKey=c=>Number(c.lat).toFixed(6)+'|'+Number(c.lng).toFixed(6)+'|'+String(c.network||'').toUpperCase();
const textMatches=(c,q)=>!q||normalize([c.ort,c.plz,c.netz,c.kst,c.str,c.firma].join(' ')).includes(normalize(q));
function places(query,regions){
 const q=normalize(query);if(q.length<3)return [];
 // Prefer an exact municipality name; e.g. "Graz" must not also select "Graz-Umgebung".
 const exact=regions.filter(r=>normalize(r.name)===q);
 if(exact.length)return exact;
 return regions.filter(r=>normalize(r.name).includes(q)||normalize(r.name+' '+(r.state||'')).includes(q));
}
function coverageKeys(query,regions,features,intersects){
 const result=new Set(),matches=places(query,regions);
 if(!matches.length)return result;
 for(const f of features){
  const geometry=f.geometry;if(!geometry||!['Polygon','MultiPolygon'].includes(geometry.type))continue;
  // Do not interpret a shorter routing polygon as a 30-minute catchment.
  if(f.properties?.minutes!=null&&Number(f.properties.minutes)!==30)continue;
  if(f.properties?.seconds!=null&&Number(f.properties.seconds)!==1800)continue;
  for(const r of matches){
   const region=r._feature||(r.geometry?{type:'Feature',properties:{},geometry:r.geometry}:null);
   if(!region)continue;
   const a=f._bbox,b=r._bbox;
   if(a&&b&&(a[0]>b[2]||a[2]<b[0]||a[1]>b[3]||a[3]<b[1]))continue;
   try{if(intersects(f,region)){result.add(siteKey(f.properties||{}));break}}catch{ /* Unusable geometry is not a match. */ }
  }
 }
 return result;
}
const matches=(c,query,coverage)=>textMatches(c,query)||(Boolean(c.mappable)&&coverage.has(siteKey(c)));
const api={normalize,siteKey,textMatches,places,coverageKeys,matches};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PartnerSearch=api;
})(typeof globalThis!=='undefined'?globalThis:this);
