"""Portfolio mappings and last-30-day KAMIS prices. Preview/fetch never writes DB.

New normalized reference series use KAMIS_PORTFOLIO. The updated backend
collects these using the same shared unit assumptions as this one-off script.
"""
from __future__ import annotations
import argparse
import csv
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg
import requests
from dotenv import dotenv_values
from portfolio_price_rules import preference, source_grams, mapping_factor

ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'reports'/'kamis-audit'
OUT=ROOT/'reports'/'kamis-update'
START=date(2026,9,3)
END=date(2026,10,2)
D=Decimal
REGIONS={'서울':'1101','부산':'2100','대전':'2501','전국':''}

def save(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def job_key(spec):
    return '_'.join(str(spec[k]) for k in ('category','item','kind','rank','cls','country'))

def prepare():
    db=json.loads((AUDIT/'db_snapshot.json').read_text(encoding='utf-8'))
    scope=list(csv.DictReader((AUDIT/'portfolio_scope_candidates.csv').open(encoding='utf-8-sig')))
    targets=[i for i in scope if i['scope'] in ('기존 가격 연결','대표가격·수율 적용 후보')]
    catalog=[]
    for p in sorted(AUDIT.glob('category_*.json')):
        _,cls,category=p.stem.split('_')
        for r in json.loads(p.read_text(encoding='utf-8'))['data'].get('item',[]):
            item,kind,rank=r['item_code'],r['kind_code'],r['rank_code']
            if category=='500' and cls=='02':continue
            catalog.append({'category':category,'item':item,'kind':kind,'rank':rank,'cls':cls,
                'country':'1101','item_name':r['item_name'],'kind_name':r['kind_name'],'grade':r['rank']})
    jobs={}
    existing=[]
    for s in db['series']:
        if s['source_name']!='KAMIS':continue
        spec={'category':s['source_category_code'],'item':s['source_item_code'],'kind':s['source_kind_code'],
            'rank':s['source_rank_code'],'cls':'01' if s['source_category_code']=='500' or s['price_type']=='RETAIL' else '02',
            'country':REGIONS[s['region']]}
        key=job_key(spec);jobs[key]=spec;existing.append({**s,'job':key})
    mappings=[];unresolved=[]
    for target in targets:
        if target['scope']=='기존 가격 연결':continue
        item,kind,rank=preference(target['name'])
        options=[r for r in catalog if r['item']==item]
        if not options:
            unresolved.append({'code':target['ingredient_code'],'name':target['name'],'reason':'No current KAMIS catalog item'})
            continue
        # Exact variety/rank first; otherwise record a category proxy, not an exact match.
        def score(r):
            return (int(kind is not None and r['kind']==kind)*30 + int(rank is not None and r['rank']==rank)*20
                + int(r['cls']=='02')*5 + int(r['rank'] in ('04','03','30','71'))*3
                + int('국산' in r['kind_name'])*2 + int(r['kind'] in ('00','01')))
        chosen=max(options,key=score)
        spec={k:chosen[k] for k in ('category','item','kind','rank','cls','country')}
        key=job_key(spec);jobs[key]=spec
        factor,note=mapping_factor(target['name'],chosen['kind_name'],chosen['item'])
        proxy=(kind is not None and chosen['kind']!=kind) or (rank is not None and chosen['rank']!=rank)
        # Source-owner matching avoids attaching a processed target as an exact raw commodity.
        source_matches=[s for s in db['series'] if (s['source_item_code'],s['source_kind_code'],s['source_rank_code'])==(chosen['item'],chosen['kind'],chosen['rank'])]
        owner=source_matches[0]['ingredient_id'] if source_matches else int(target['ingredient_id'])
        mappings.append({'ingredient_id':int(target['ingredient_id']),'ingredient_code':target['ingredient_code'],
            'name':target['name'],'job':key,'owner_id':owner,'spec':chosen,'factor':str(factor),'note':note,
            'mapping_type':'CATEGORY_PROXY' if proxy else 'RAW_PROXY' if factor!=1 else 'VARIETY',
            'confidence':'0.60' if proxy else '0.65' if factor!=1 else '0.75'})
    plan={'start':str(START),'end':str(END),'existing':existing,'jobs':jobs,'mappings':mappings,'unresolved':unresolved}
    save(OUT/'plan.json',plan)
    with (OUT/'mapping_preview.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['ingredient_code','name','mapping_type','factor','confidence','note','job']
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(mappings)
    print('PREVIEW',json.dumps({'new_mapping_candidates':len(mappings),'existing_series':len(existing),
        'api_jobs':len(jobs),'unresolved':len(unresolved)},ensure_ascii=False),flush=True)
    return plan

def fetch(plan,env):
    def one(pair):
        key,s=pair;path=OUT/'responses'/(key+'.json')
        if path.exists():
            cached=json.loads(path.read_text(encoding='utf-8'))
            if cached.get('status') in ('000','001'):return key,cached
        params={'action':'periodRetailProductList' if s['cls']=='01' else 'periodWholesaleProductList',
            'p_startday':str(START),'p_endday':str(END),'p_itemcategorycode':s['category'],
            'p_itemcode':s['item'],'p_kindcode':s['kind'],'p_productrankcode':s['rank'],
            'p_countrycode':s['country'],'p_convert_kg_yn':'Y',
            'p_cert_key':env['KAMIS_API_KEY'],'p_cert_id':env['KAMIS_CERT_ID'],'p_returntype':'json'}
        result=None
        for attempt in range(3):
            try:
                r=requests.get('https://www.kamis.or.kr/service/price/xml.do',params=params,timeout=35)
                if r.status_code!=200:raise ValueError('HTTP '+str(r.status_code))
                data=r.json().get('data',{})
                if not isinstance(data,dict):raise ValueError('Unexpected response shape')
                result={'status':str(data.get('error_code')),'rows':data.get('item') or []}
                if result['status'] in ('000','001'):break
            except Exception as e:
                # Exception messages can contain authenticated request URLs. Keep only the type.
                result={'status':'ERROR','error_type':type(e).__name__,'rows':[]}
            time.sleep(attempt+1)
        save(path,result)
        return key,result
    stats=defaultdict(int)
    with ThreadPoolExecutor(max_workers=4) as pool:
        fs=[pool.submit(one,pair) for pair in plan['jobs'].items()]
        for n,f in enumerate(as_completed(fs),1):
            key,res=f.result();stats[res['status']]+=1
            if n%20==0 or n==len(fs):print('FETCH',n,'/',len(fs),dict(stats),flush=True)
    save(OUT/'fetch_summary.json',dict(stats))

def parse_day(row):
    raw=str(row.get('regday',''));year=str(row.get('yyyy',''))
    for value in (raw,year+'-'+raw.replace('/','-')):
        try:return date.fromisoformat(value)
        except ValueError:pass
    return None

def actual_prices(key,spec,region,market=None):
    path=OUT/'responses'/(key+'.json')
    if not path.exists():return [],'NOT_FETCHED'
    payload=json.loads(path.read_text(encoding='utf-8'))
    if payload['status']!='000':return [],payload['status']
    groups=defaultdict(list)
    for row in payload['rows']:
        if not isinstance(row,dict) or not row.get('itemname'):continue
        if region!='전국' and row.get('countyname')!=region:continue
        dt=parse_day(row)
        if dt is None or not START<=dt<=END:continue
        try:
            price=D(str(row['price']).replace(',',''))
            if not price.is_finite() or price<=0:continue
            grams,basis=source_grams(row.get('kindname'),spec['item'])
            if grams<=0:raise ValueError('Nonpositive unit')
        except (ValueError,ArithmeticError):continue
        normalized=price*1000/grams
        groups[str(dt)].append((row.get('marketname'),normalized,basis,row.get('kindname')))
    prices=[]
    for dt,rows in sorted(groups.items()):
        exact=[r for r in rows if market and r[0]==market]
        chosen=exact or rows
        normalized=sum(r[1] for r in chosen)/len(chosen)
        prices.append({'date':dt,'price_per_kg':str(normalized.quantize(D('0.000001'))),
            'basis':chosen[0][2],'source_kind':chosen[0][3],'observations':len(chosen)})
    return prices,'OK' if prices else 'NO_VALID_ROWS'

def validation(plan):
    successful=[];failed=[]
    latest_estimates=[]
    for m in plan['mappings']:
        prices,status=actual_prices(m['job'],plan['jobs'][m['job']],'서울')
        (successful if prices else failed).append({**m,'price_days':len(prices),'status':status})
        if prices:
            estimate=D(prices[-1]['price_per_kg'])*D(m['factor'])/1000
            if not D('0.001') <= estimate <= D(1000):
                raise ValueError('Implausible unit price: '+m['ingredient_code'])
            latest_estimates.append((estimate,m['ingredient_code'],m['name']))
    existing_ok=[];existing_failed=[]
    for s in plan['existing']:
        prices,status=actual_prices(s['job'],plan['jobs'][s['job']],s['region'],s['market'])
        (existing_ok if prices else existing_failed).append({'series_id':s['series_id'],'code':s['ingredient_code'],
            'job':s['job'],'region':s['region'],'price_days':len(prices),'status':status})
    result={'mapping_success':successful,'mapping_failed':failed,'existing_success':existing_ok,'existing_failed':existing_failed,
        'latest_estimate_min':min(latest_estimates) if latest_estimates else None,
        'latest_estimate_max':max(latest_estimates) if latest_estimates else None}
    save(OUT/'validation.json',result)
    print('VALIDATION',{'mapping_ready':len(successful),'mapping_no_prices':len(failed),
        'existing_ready':len(existing_ok),'existing_no_prices':len(existing_failed)},flush=True)
    return result

def connect(env):
    return psycopg.connect(env['DB_URL'].removeprefix('jdbc:').split('?')[0],
        user=env['DB_USERNAME'],password=env['DB_PASSWORD'],prepare_threshold=None,connect_timeout=20)

def apply(plan,env):
    verified=validation(plan)
    if not verified['mapping_success']:raise ValueError('No validated mappings; refusing empty application')
    stats={'new_series':0,'mapping_upserts':0,'existing_price_upserts':0,'reference_price_upserts':0}
    new_series={}
    with connect(env) as conn,conn.cursor() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('mealfit_portfolio_price_update'))")
        # Backup every overwritten row before the single atomic transaction.
        backup={}
        for key,sql,params in [
            ('series','SELECT * FROM mealfit.price_series',()),
            ('mappings','SELECT * FROM mealfit.ingredient_price_mapping',()),
            ('prices','SELECT * FROM mealfit.ingredient_price WHERE price_date BETWEEN %s AND %s',(START,END))]:
            c.execute(sql,params);cols=[d.name for d in c.description]
            backup[key]=[dict(zip(cols,r)) for r in c.fetchall()]
        # Do not overwrite the original backup on retry.
        backup_path=OUT/'before_apply.json'
        if not backup_path.exists():save(backup_path,backup)
        for s in plan['existing']:
            prices,status=actual_prices(s['job'],plan['jobs'][s['job']],s['region'],s['market'])
            if not prices:continue
            for p in prices:
                c.execute('''INSERT INTO mealfit.ingredient_price(series_id,price_date,original_price,unit_quantity)
                    VALUES(%s,%s,%s,1000) ON CONFLICT(series_id,price_date) DO UPDATE
                    SET original_price=EXCLUDED.original_price,unit_quantity=EXCLUDED.unit_quantity,collected_at=CURRENT_TIMESTAMP''',
                    (s['series_id'],p['date'],D(p['price_per_kg'])))
                stats['existing_price_upserts']+=1
        for m in verified['mapping_success']:
            key=m['job'];s=m['spec']
            if key not in new_series:
                price_type='RETAIL' if s['cls']=='01' else 'WHOLESALE'
                c.execute('''SELECT series_id FROM mealfit.price_series WHERE source_name='KAMIS_PORTFOLIO'
                    AND source_category_code=%s AND source_item_code=%s AND source_kind_code=%s
                    AND source_rank_code=%s AND price_type=%s AND region='서울'
                    AND market='서울 대표가격' ORDER BY series_id LIMIT 1''',
                    (s['category'],s['item'],s['kind'],s['rank'],price_type))
                found=c.fetchone()
                if found:series_id=found[0]
                else:
                    c.execute('''INSERT INTO mealfit.price_series(ingredient_id,source_name,source_category_code,
                        source_item_code,source_kind_code,source_rank_code,variety,grade,price_type,
                        market,region,original_unit,unit_quantity,is_cost_basis)
                        VALUES(%s,'KAMIS_PORTFOLIO',%s,%s,%s,%s,%s,%s,%s,'서울 대표가격','서울','kg',1,false)
                        RETURNING series_id''',(m['owner_id'],s['category'],s['item'],s['kind'],s['rank'],
                        s['kind_name'],s['grade'],price_type))
                    series_id=c.fetchone()[0];stats['new_series']+=1
                new_series[key]=series_id
                prices,status=actual_prices(key,plan['jobs'][key],'서울')
                for p in prices:
                    c.execute('''INSERT INTO mealfit.ingredient_price(series_id,price_date,original_price,unit_quantity)
                        VALUES(%s,%s,%s,1000) ON CONFLICT(series_id,price_date) DO UPDATE
                        SET original_price=EXCLUDED.original_price,unit_quantity=EXCLUDED.unit_quantity,collected_at=CURRENT_TIMESTAMP''',
                        (series_id,p['date'],D(p['price_per_kg'])))
                    stats['reference_price_upserts']+=1
            c.execute('''INSERT INTO mealfit.ingredient_price_mapping(ingredient_id,series_id,mapping_type,
                conversion_factor,confidence_score,priority,review_status,is_active)
                VALUES(%s,%s,%s,%s,%s,40,'APPROVED',TRUE)
                ON CONFLICT(ingredient_id,series_id) DO UPDATE SET mapping_type=EXCLUDED.mapping_type,
                conversion_factor=EXCLUDED.conversion_factor,confidence_score=EXCLUDED.confidence_score,
                priority=EXCLUDED.priority,review_status='APPROVED',is_active=TRUE,updated_at=CURRENT_TIMESTAMP''',
                (m['ingredient_id'],new_series[key],m['mapping_type'],D(m['factor']),D(m['confidence'])))
            stats['mapping_upserts']+=1
        # Preserve all previously approved mappings. New proxies have lower priority (40).
        c.execute('''SELECT count(*) FROM mealfit.ingredient i WHERE EXISTS(
            SELECT 1 FROM mealfit.price_series s JOIN mealfit.ingredient_price p ON p.series_id=s.series_id
            WHERE s.ingredient_id=i.ingredient_id) OR EXISTS(
            SELECT 1 FROM mealfit.ingredient_price_mapping m JOIN mealfit.ingredient_price p ON p.series_id=m.series_id
            WHERE m.ingredient_id=i.ingredient_id AND m.review_status='APPROVED' AND m.is_active)''')
        stats['covered_ingredients']=c.fetchone()[0]
        c.execute('''SELECT count(*),min(price_date),max(price_date) FROM mealfit.ingredient_price WHERE price_date BETWEEN %s AND %s''',(START,END))
        stats['month_rows'],stats['first_date'],stats['last_date']=c.fetchone()
        conn.commit()
    save(OUT/'applied_summary.json',stats)
    print('APPLIED',json.dumps(stats,default=str,ensure_ascii=False),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--apply',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    # KAMIS echoes credentials in condition. Audit outputs must never retain it.
    for f in (ROOT/'reports').rglob('*.json'):
        data=json.loads(f.read_text(encoding='utf-8'))
        if isinstance(data,dict) and 'condition' in data:data.pop('condition');save(f,data)
    plan=prepare();env=dotenv_values(ROOT/'.env')
    if args.fetch:fetch(plan,env)
    if args.apply:apply(plan,env)
    else:validation(plan)

if __name__=='__main__':main()
