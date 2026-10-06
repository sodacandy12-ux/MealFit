"""Read-only checks of the applied mappings and price range."""
import json
from pathlib import Path
from dotenv import dotenv_values
import psycopg

root=Path(__file__).resolve().parents[2]
out=root/'reports'/'kamis-update'
plan=json.loads((out/'plan.json').read_text(encoding='utf-8'))
before=json.loads((out/'before_apply.json').read_text(encoding='utf-8'))
env=dotenv_values(root/'.env')
ids=[m['ingredient_id'] for m in plan['mappings']]
with psycopg.connect(env['DB_URL'].removeprefix('jdbc:').split('?')[0],user=env['DB_USERNAME'],
    password=env['DB_PASSWORD'],connect_timeout=20,options='-c default_transaction_read_only=on') as conn,conn.cursor() as c:
    c.execute('''SELECT i.ingredient_code,i.name,m.conversion_factor,m.mapping_type,
        m.confidence_score,latest.price_date,latest.standard_unit_price*m.conversion_factor AS unit_price
        FROM mealfit.ingredient_price_mapping m JOIN mealfit.ingredient i ON i.ingredient_id=m.ingredient_id
        JOIN mealfit.price_series s ON s.series_id=m.series_id
        JOIN LATERAL(SELECT p.price_date,p.standard_unit_price FROM mealfit.ingredient_price p
        WHERE p.series_id=s.series_id ORDER BY p.price_date DESC LIMIT 1) latest ON TRUE
        WHERE m.ingredient_id=ANY(%s) AND s.source_name='KAMIS_PORTFOLIO'
        AND m.review_status='APPROVED' AND m.is_active ORDER BY i.ingredient_code''',(ids,))
    columns=[d.name for d in c.description];rows=[dict(zip(columns,r)) for r in c.fetchall()]
    assert len({r['ingredient_code'] for r in rows})==len(ids), 'Mapping coverage mismatch'
    assert all(str(r['price_date'])>=plan['start'] and r['unit_price']>0 for r in rows)
    c.execute('SELECT * FROM mealfit.ingredient_price_mapping WHERE mapping_id=ANY(%s)',
        ([m['mapping_id'] for m in before['mappings']],))
    columns=[d.name for d in c.description];oldrows={r['mapping_id']:r for r in [dict(zip(columns,r)) for r in c.fetchall()]}
    for old in before['mappings']:
        actual=oldrows[old['mapping_id']]
        for key in ('ingredient_id','series_id','mapping_type','conversion_factor','confidence_score','priority','review_status','is_active'):
            assert str(actual[key])==str(old[key]),'Existing mapping changed'
    c.execute("SELECT count(*) FROM mealfit.ingredient_price WHERE original_price<=0 OR unit_quantity<=0")
    assert c.fetchone()[0]==0,'Nonpositive prices'
    c.execute('''SELECT count(*),min(price_date),max(price_date) FROM mealfit.ingredient_price p
        JOIN mealfit.price_series s ON s.series_id=p.series_id WHERE s.source_name='KAMIS_PORTFOLIO' ''')
    n,first,last=c.fetchone()
    assert str(first)>=plan['start'] and str(last)<=plan['end'],'Out-of-range new prices'
    result={'verified_new_ingredients':len(rows),'reference_price_rows':n,'reference_first':str(first),
        'reference_last':str(last),'prior_mappings_preserved':len(before['mappings']),
        'min_estimated_won_per_g':str(min(r['unit_price'] for r in rows)),
        'max_estimated_won_per_g':str(max(r['unit_price'] for r in rows))}
    (out/'verified_mappings.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'verification_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
