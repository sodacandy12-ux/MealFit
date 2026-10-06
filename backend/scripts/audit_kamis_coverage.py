"""Read-only snapshot of database coverage and KAMIS catalog responses."""
import json
from pathlib import Path
import psycopg
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'reports' / 'kamis-audit'
OUT.mkdir(parents=True, exist_ok=True)
env = dotenv_values(ROOT / '.env')
url = env['DB_URL'].removeprefix('jdbc:').split('?')[0]
try:
    conn = psycopg.connect(url, user=env['DB_USERNAME'], password=env['DB_PASSWORD'], connect_timeout=15, options='-c default_transaction_read_only=on')
    with conn, conn.cursor() as cur:
        queries = {
            'ingredients': '''SELECT i.ingredient_id, i.ingredient_code, i.name, i.standard_unit, i.is_active,
                count(DISTINCT mi.menu_id) AS menu_count,
                EXISTS (SELECT 1 FROM mealfit.ingredient_price_mapping m WHERE m.ingredient_id=i.ingredient_id AND m.is_active AND m.review_status='APPROVED') AS approved_mapping,
                EXISTS (SELECT 1 FROM mealfit.price_series ps JOIN mealfit.ingredient_price p ON p.series_id=ps.series_id WHERE ps.ingredient_id=i.ingredient_id) AS direct_price,
                EXISTS (SELECT 1 FROM mealfit.ingredient_price_mapping m JOIN mealfit.ingredient_price p ON p.series_id=m.series_id WHERE m.ingredient_id=i.ingredient_id AND m.is_active AND m.review_status='APPROVED') AS mapped_price
                FROM mealfit.ingredient i LEFT JOIN mealfit.menu_ingredient mi ON mi.ingredient_id=i.ingredient_id
                GROUP BY i.ingredient_id ORDER BY menu_count DESC, i.ingredient_id''',
            'series': '''SELECT ps.*, i.name AS ingredient_name, i.ingredient_code,
                count(p.price_id) AS price_count, max(p.price_date) AS latest_date
                FROM mealfit.price_series ps JOIN mealfit.ingredient i ON i.ingredient_id=ps.ingredient_id
                LEFT JOIN mealfit.ingredient_price p ON p.series_id=ps.series_id
                GROUP BY ps.series_id, i.ingredient_id ORDER BY ps.series_id''',
            'mappings': 'SELECT * FROM mealfit.ingredient_price_mapping ORDER BY ingredient_id, series_id',
            'menus': 'SELECT count(*) AS menu_count FROM mealfit.menu',
        }
        data = {}
        for key, sql in queries.items():
            cur.execute(sql)
            cols = [d.name for d in cur.description]
            data[key] = [dict(zip(cols, row)) for row in cur.fetchall()]
        (OUT / 'db_snapshot.json').write_text(json.dumps(data, ensure_ascii=False, default=str), encoding='utf-8')
        print('DB snapshot:', {k: len(v) for k,v in data.items()}, flush=True)
except Exception as e:
    print('DB failed:', type(e).__name__, flush=True)
    raise SystemExit(1)

params = {'p_cert_key': env['KAMIS_API_KEY'], 'p_cert_id': env['KAMIS_CERT_ID'], 'p_returntype': 'json'}
try:
    r = requests.get('https://www.kamis.or.kr/service/price/xml.do', params={**params, 'action':'dailySalesList'}, timeout=40)
    r.raise_for_status()
    payload = r.json()
    payload.pop('condition', None)
    (OUT / 'kamis_daily_sales.json').write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    print('KAMIS dailySalesList saved; keys:', list(payload), flush=True)
except Exception as e:
    print('KAMIS failed:', type(e).__name__, flush=True)
    raise SystemExit(2)
