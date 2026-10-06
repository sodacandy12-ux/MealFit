"""Read-only before/after count using the repository's actual Java quantity rules."""
import base64
import csv
import json
import subprocess
from collections import defaultdict
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path
from dotenv import dotenv_values
import psycopg

root=Path(__file__).resolve().parents[2]
out=root/'reports'/'kamis-update'
before=json.loads((out/'before_apply.json').read_text(encoding='utf-8'))
env=dotenv_values(root/'.env')
source=(root/'backend/src/main/java/com/human/backend/cost/repository/MemoryCostRepository.java').read_text(encoding='utf-8')
methods=[]
for name in ['sanitizeIngredientCost','isNoodleMenu','isMainMenu','isSnackOrSkewerMenu','isDessertOrSnack','isRiceMenu','isSoupMenu']:
    start=source.index('    private '+('MenuIngredientCostVo' if name=='sanitizeIngredientCost' else 'boolean')+' '+name+'(')
    body=source.index('{',start);depth=1;end=body+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    methods.append(source[start:end])
harness='''import java.math.BigDecimal; import java.io.*; import java.util.*;
public class MenuQuantityCounter {
static class MenuIngredientCostVo {
 String name; BigDecimal qty,price;
 MenuIngredientCostVo(Object... args){ name=(String)args[1];qty=(BigDecimal)args[4];price=(BigDecimal)args[5]; }
 Long getIngredientId(){return 1L;} String getIngredientName(){return name;}
 String getIngredientCategory(){return "";} Boolean getIsPrimary(){return false;}
 BigDecimal getQuantity(){return qty;} BigDecimal getStandardUnitPrice(){return price;}
 Object getPriceDate(){return null;} String getPriceSource(){return null;}
 String getMappingType(){return null;} BigDecimal getConfidenceScore(){return null;}
}
static String decode(String s){return new String(Base64.getDecoder().decode(s), java.nio.charset.StandardCharsets.UTF_8);}
public static void main(String[] args)throws Exception{
 MenuQuantityCounter obj=new MenuQuantityCounter();
 BufferedReader in=new BufferedReader(new InputStreamReader(System.in,java.nio.charset.StandardCharsets.UTF_8));
 String line; StringBuilder result=new StringBuilder();
 while((line=in.readLine())!=null){ String[] p=line.split("\\t",-1);
 MenuIngredientCostVo item=new MenuIngredientCostVo(1L,decode(p[2]),"",false,new BigDecimal(p[3]),BigDecimal.ZERO,null,null,null,null);
 result.append(obj.sanitizeIngredientCost(decode(p[0]),decode(p[1]),item).getQuantity().toPlainString()).append("\\n"); }
 System.out.print(result);
}
'''+ '\n'.join(methods)+'\n}\n'
java_path=out/'MenuQuantityCounter.java'
java_path.write_text(harness,encoding='utf-8')

with psycopg.connect(env['DB_URL'].removeprefix('jdbc:').split('?')[0],user=env['DB_USERNAME'],password=env['DB_PASSWORD'],
    options='-c default_transaction_read_only=on',connect_timeout=20) as conn,conn.cursor() as c:
    def rows(sql,params=()):
        c.execute(sql,params);cols=[d.name for d in c.description];return [dict(zip(cols,r)) for r in c.fetchall()]
    menus=rows('SELECT menu_id,name,upper_category,category FROM mealfit.menu')
    recipes=rows('''SELECT mi.menu_id,mi.ingredient_id,mi.quantity,i.name FROM mealfit.menu_ingredient mi
        JOIN mealfit.ingredient i ON i.ingredient_id=mi.ingredient_id ORDER BY mi.menu_id,mi.ingredient_id''')
    current_series=rows('SELECT * FROM mealfit.price_series')
    current_mappings=rows('SELECT * FROM mealfit.ingredient_price_mapping')
    current_prices=rows('''SELECT DISTINCT ON(series_id) series_id,price_id,price_date,standard_unit_price
        FROM mealfit.ingredient_price ORDER BY series_id,price_date DESC,price_id DESC''')
    older_prices=rows('''SELECT DISTINCT ON(series_id) series_id,price_id,price_date,standard_unit_price
        FROM mealfit.ingredient_price WHERE price_date NOT BETWEEN '2026-09-03' AND '2026-10-02'
        AND series_id=ANY(%s) ORDER BY series_id,price_date DESC,price_id DESC''',([s['series_id'] for s in before['series']],))
menu_map={m['menu_id']:m for m in menus}
encode=lambda s:base64.b64encode(str(s or '').encode('utf-8')).decode('ascii')
lines=[]
for r in recipes:
    m=menu_map[r['menu_id']];cat=(m['upper_category'] or '')+' '+(m['category'] or '')
    lines.append('\t'.join([encode(m['name']),encode(cat),encode(r['name']),str(r['quantity'] or 0)]))
res=subprocess.run(['java','-Dfile.encoding=UTF-8','--source','17',str(java_path)],input='\n'.join(lines)+'\n',
    encoding='utf-8',capture_output=True,check=True)
sanitized=[D(v) for v in res.stdout.splitlines()]
assert len(sanitized)==len(recipes)

def latest_prices(prices):
    latest={}
    for p in prices:
        sid=p['series_id'];key=(str(p['price_date']),p['price_id'])
        if sid not in latest or key>(str(latest[sid]['price_date']),latest[sid]['price_id']):latest[sid]=p
    return latest
def best_prices(series,mappings,prices):
    sources={s['series_id']:s for s in series};latest=latest_prices(prices);choices=defaultdict(list)
    for m in mappings:
        if not m['is_active'] or m['review_status']!='APPROVED' or m['series_id'] not in latest:continue
        s=sources[m['series_id']];p=latest[m['series_id']]
        rank=(0,m['priority'],not s['is_cost_basis'],s['price_type']!='WHOLESALE',-int(str(p['price_date']).replace('-','')))
        choices[m['ingredient_id']].append((rank,D(str(p['standard_unit_price']))*D(str(m['conversion_factor']))))
    for s in series:
        if s['series_id'] not in latest:continue
        p=latest[s['series_id']]
        rank=(1,2147483647,not s['is_cost_basis'],s['price_type']!='WHOLESALE',-int(str(p['price_date']).replace('-','')))
        choices[s['ingredient_id']].append((rank,D(str(p['standard_unit_price']))))
    return {i:sorted(v,key=lambda pair:pair[0])[0][1] for i,v in choices.items()}
oldprice=best_prices(before['series'],before['mappings'],older_prices+before['prices'])
newprice=best_prices(current_series,current_mappings,current_prices)
fallback={}
csv_path=root/'backend/src/main/java/com/human/backend/cost/dummy/ingredient_price.csv'
for p in csv.DictReader(csv_path.open(encoding='utf-8-sig')):
    i=int(p['ingredient_id']);key=p['price_date']
    if i not in fallback or key>fallback[i][0]:fallback[i]=(key,D(p['standard_unit_price']))

def count(prices):
    totals=defaultdict(D);display_totals=defaultdict(D);display_rounded=defaultdict(D);priced=defaultdict(int);total=defaultdict(int)
    for r,qty in zip(recipes,sanitized):
        mid=r['menu_id'];iid=r['ingredient_id'];price=prices.get(iid,D(0))
        totals[mid]+=qty*price
        display_price=price if price>0 else fallback.get(iid,('',D(0)))[1]
        display_totals[mid]+=qty*display_price
        display_rounded[mid]+=(qty*display_price).quantize(D(1),rounding=ROUND_HALF_UP)
        total[mid]+=1;priced[mid]+=int(price>0)
    return {'any_db_price':sum(v>0 for v in totals.values()),
        'db_cost_100_to_15000':sum(D(100)<=v<=D(15000) for v in totals.values()),
        'display_with_default_csv_fallback':sum(D(100)<=v<=D(15000) and D(100)<=display_rounded[mid]<=D(50000) for mid,v in display_totals.items()),
        'all_ingredients_db_priced':sum(priced[mid]==n for mid,n in total.items()),
        'no_db_price':sum(v==0 for v in totals.values()),'total_menus':len(menus)},display_totals
old,oldtot=count(oldprice);new,newtot=count(newprice)
result={'before':old,'after':new,'display_increase':new['display_with_default_csv_fallback']-old['display_with_default_csv_fallback'],
    'method':'Current Java quantity sanitizer; DB price ranking; default CSV fallback; 100~15000 won menu filter. Running AWS cache not inspected.'}
(out/'menu_coverage_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
