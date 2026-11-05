const test=require('node:test'),assert=require('node:assert/strict');
const S=require('../search.js');
const polygon=(box,properties={})=>({type:'Feature',properties,geometry:{type:'Polygon',coordinates:[[[box[0],box[1]],[box[2],box[1]],[box[2],box[3]],[box[0],box[3]],[box[0],box[1]]]]},_bbox:box});
const region={name:'Gesuchter Ort',state:'Südland',_feature:polygon([2,2,3,3]),_bbox:[2,2,3,3]};
const center={lat:1,lng:1,network:'FRANCHISE',ort:'Betriebsort',firma:'Demo GmbH',kst:'123',plz:'0000',mappable:true};
const area=polygon([0,0,4,4],{...center,minutes:30});
const intersectBoxes=(a,b)=>a._bbox[0]<=b._bbox[2]&&a._bbox[2]>=b._bbox[0]&&a._bbox[1]<=b._bbox[3]&&a._bbox[3]>=b._bbox[1];
test('neighbor center remains when its actual catchment reaches the queried municipality',()=>{
 const keys=S.coverageKeys('Gesuchter Ort',[region],[area],intersectBoxes);
 assert(!S.textMatches(center,'Gesuchter Ort'));
 assert(S.matches(center,'Gesuchter Ort',keys));
 assert(!S.matches({...center,lat:9,lng:9},'Gesuchter Ort',keys));
});
test('coverage respects network key, routable geometry and stated duration',()=>{
 const keys=S.coverageKeys('Gesuchter Ort',[region],[area],intersectBoxes);
 assert(!S.matches({...center,network:'EFR'},'Gesuchter Ort',keys));
 assert(!S.matches({...center,mappable:false},'Gesuchter Ort',keys));
 assert.equal(S.coverageKeys('Gesuchter Ort',[region],[{...area,properties:{...area.properties,minutes:15}}],intersectBoxes).size,0);
 assert.equal(S.coverageKeys('Gesuchter Ort',[region],[{properties:center}],intersectBoxes).size,0);
});
test('distant place does not keep a center merely because it is nearest',()=>{
 const far={...region,_feature:polygon([10,10,11,11]),_bbox:[10,10,11,11]};
 assert.equal(S.coverageKeys('Gesuchter Ort',[far],[area],()=>{throw Error('bbox must skip far geometry')}).size,0);
 assert(!S.matches(center,'Gesuchter Ort',new Set()));
});
test('empty query, names, postcode and cost-center search still work',()=>{
 assert(S.matches(center,'',new Set()));assert(S.textMatches(center,'123'));assert(S.textMatches(center,'0000'));assert(S.textMatches(center,'demo'));
 assert.equal(S.coverageKeys('unbekannt',[region],[area],intersectBoxes).size,0);
 assert.equal(S.coverageKeys('Ge',[region],[area],intersectBoxes).size,0);
});
test('exact municipality wins; spelling normalized without changing stored data',()=>{
 const regions=[{name:'Graz'},{name:'Graz-Umgebung'}];assert.equal(S.places('Graz',regions).length,1);
 assert.equal(S.normalize('  SÜD Straße  '),'sud strasse');assert.equal(S.places('Gesuchter Ort Sudland',[region]).length,1);
});
test('boundary touch counts; holes/disjoint geometry remain a geometry-library decision',()=>{
 const touch={...region,_feature:polygon([4,2,5,3]),_bbox:[4,2,5,3]};
 assert.equal(S.coverageKeys('Gesuchter Ort',[touch],[area],intersectBoxes).size,1);
 assert.equal(S.coverageKeys('Gesuchter Ort',[region],[area],()=>false).size,0);
});
