import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from dotenv import dotenv_values

root = Path(__file__).resolve().parents[2]
out = root / 'reports' / 'kamis-audit'
env = dotenv_values(root / '.env')
base = {'p_cert_key':env['KAMIS_API_KEY'], 'p_cert_id':env['KAMIS_CERT_ID'], 'p_returntype':'json'}
def fetch(pair):
    cls, cat = pair
    params = {**base, 'action':'dailyPriceByCategoryList', 'p_product_cls_code':cls,
        'p_item_category_code':cat, 'p_convert_kg_yn':'Y', 'p_regday':'2026-10-02'}
    try:
        r=requests.get('https://www.kamis.or.kr/service/price/xml.do',params=params,timeout=35)
        payload=r.json()
        payload.pop('condition', None)
        (out / f'category_{cls}_{cat}.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        data=payload.get('data',{})
        print(cls,cat,'code',data.get('error_code') if isinstance(data,dict) else type(data).__name__,flush=True)
    except Exception as e:
        print(cls,cat,type(e).__name__,flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(fetch,[(c,k) for c in ['01','02'] for k in ['100','200','300','400','500','600']]))
