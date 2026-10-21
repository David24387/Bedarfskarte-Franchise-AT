"""Detailed read-only reconciliation; CRM details leave Actions only encrypted."""
import base64
import csv
import difflib
import json
import math
import os
from pathlib import Path
import re
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sync_hubspot_at import norm, coordinates

ORDINALS = [4,6,10,11,12,14,19,27,28,31,33,37,39,40,41,43,46,57,60,61,62,63,64,81,9,47,72]
STOP = {'gmbh','gesmbh','mbh','kg','co','e','u','und','firma','fa','inh','og','kfz','reifen','auto','autoservice','gesellschaft','reifenzentrum'}

def words(s):
    s=re.sub(r'^\s*\d{3}[A-Za-z]\s+', '', str(s or ''))
    return {norm(t) for t in re.findall(r'\w+',s) if norm(t) not in STOP and len(norm(t))>2}

def postal(s): return re.sub(r'[^0-9]', '', str(s or ''))
def street(s): return norm(re.sub(r'str\.(?=\s|$)', 'strasse', str(s or ''), flags=re.I))
def distance(row,p):
    a,b=coordinates(p)
    if not a:return None
    try:
        x,y=(float(row[k].replace(',','.')) for k in ('Lat./Breitengard','Long./Längengrad'))
        la,lb=math.radians(x),math.radians(float(a));da=lb-la;db=math.radians(float(b)-y)
        return round(12742*math.asin(min(1,math.sqrt(math.sin(da/2)**2+math.cos(la)*math.cos(lb)*math.sin(db/2)**2))),3)
    except (ValueError,KeyError):return None

def report(records,config):
    lc,public,networks,yes=config
    rows=list(csv.reader(Path('daten.csv').open(encoding='utf-8-sig',newline='')))
    hi=next(i for i,r in enumerate(rows) if 'KST' in r and 'Netzwerk' in r)
    old=[dict(zip(rows[hi],r)) for r in rows[hi+1:] if any(r)]
    reports=[]
    for ordinal in ORDINALS:
        row=old[ordinal-1]; candidates=[]; ow=words(row['Gesellschaft'])
        for record in records:
            p=record.get('properties',{});name=p.get('name') or ''; nw=words(name)
            overlap=len(ow&nw)/max(1,min(len(ow),len(nw)))
            ratio=difflib.SequenceMatcher(None,norm(row['Gesellschaft']),norm(name)).ratio()
            samezip=bool(postal(row['PLZ']) and postal(row['PLZ'])==postal(p.get('zip')))
            samecity=bool(norm(row['Ort']) and norm(row['Ort'])==norm(p.get('city')))
            samestreet=bool(street(row['Strasse']) and street(row['Strasse'])==street(p.get('address')))
            strratio=difflib.SequenceMatcher(None,street(row['Strasse']),street(p.get('address'))).ratio()
            identifiers=[p.get(k) or '' for k in ('partner_id','forms_partner_id_focus_id','unternehmensname_mit_id')]
            sameid=any(norm(row.get(k)) and norm(row[k])==norm(v) for k in ('KST','Netzkennung') for v in identifiers)
            dist=distance(row,p)
            score=6*sameid+4*samestreet+2*samezip+samecity+3*overlap+2*ratio+strratio+(2 if dist is not None and dist<.2 else 0)
            if sameid or overlap>.4 or ratio>.65 or (samezip and strratio>.5) or samestreet:
                candidates.append({'score':round(score,3),'id':record['id'],'name':name,'address':p.get('address'),'zip':p.get('zip'),'city':p.get('city'),
                   'country':p.get('country'),'country_code':p.get('hs_country_code'),'lifecycle':p.get(lc),'public':p.get(public),
                   'eligible_lifecycle':p.get(lc) in networks,'is_public':p.get(public)==yes,
                   'network':networks.get(p.get(lc)), 'partner_ids':identifiers[:2],
                   'evidence':{'same_id':sameid,'same_street':samestreet,'same_zip':samezip,'same_city':samecity,
                   'name_overlap':round(overlap,3),'name_ratio':round(ratio,3),'street_ratio':round(strratio,3),'distance_km':dist}})
        candidates.sort(key=lambda c:c['score'],reverse=True)
        reports.append({'ordinal':ordinal,'legacy':row,'candidates':candidates[:4]})
    key=AESGCM.generate_key(bit_length=256);nonce=os.urandom(12)
    ciphertext=AESGCM(key).encrypt(nonce,json.dumps(reports,ensure_ascii=False).encode(),None)
    pub=serialization.load_pem_public_key(Path(__file__).with_name('reconciliation_public.pem').read_bytes())
    wrapped=pub.encrypt(key,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    sealed={'key':base64.b64encode(wrapped).decode(),'nonce':base64.b64encode(nonce).decode(),'data':base64.b64encode(ciphertext).decode()}
    print('SEALED_RECONCILIATION:'+base64.b64encode(json.dumps(sealed).encode()).decode())
