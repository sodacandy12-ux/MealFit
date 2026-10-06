import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import dotenv_values
import requests
import psycopg

root=Path(__file__).resolve().parents[2]
out=root/'reports'/'kamis-update'
out.mkdir(parents=True,exist_ok=True)
env=dotenv_values(root/'.env')
def fetch(spec):
    category,item,kind,rank,cls=spec
    params={'action':'periodRetailProductList' if cls=='01' else 'periodWholesaleProductList',
        'p_startday':'2026-09-03','p_endday':'2026-10-02','p_itemcategorycode':category,
        'p_itemcode':item,'p_kindcode':kind,'p_productrankcode':rank,'p_countrycode':'1101',
        'p_convert_kg_yn':'Y','p_cert_key':env['KAMIS_API_KEY'],'p_cert_id':env['KAMIS_CERT_ID'],'p_returntype':'json'}
    r=requests.get('https://www.kamis.or.kr/service/price/xml.do',params=params,timeout=40)
    p=r.json();p.pop('condition',None);data=p.get('data',{});rows=data.get('item',[]) if isinstance(data,dict) else []
    (out/('_'.join(spec)+'.json')).write_text(json.dumps(p,ensure_ascii=False),encoding='utf-8')
    actual=[i for i in rows if isinstance(i,dict) and i.get('yyyy') and i.get('price')]
    print(spec,'code',data.get('error_code') if isinstance(data,dict) else str(type(data)), 'rows',len(actual), 'sample',actual[:1],flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(fetch,[('100','111','01','04','02'),('200','224','01','04','02'),('200','223','02','04','02'),('500','9903','21','71','01'),('600','652','00','30','01'),('500','4304','68','00','01'),('200','248','00','04','01'),('300','318','00','05','01')]))
with psycopg.connect(env['DB_URL'].removeprefix('jdbc:').split('?')[0],user=env['DB_USERNAME'],password=env['DB_PASSWORD'],connect_timeout=15,options='-c default_transaction_read_only=on') as conn:
    with conn.cursor() as c:
        c.execute("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid IN ('mealfit.price_series'::regclass,'mealfit.ingredient_price'::regclass)")
        print('constraints',c.fetchall())
