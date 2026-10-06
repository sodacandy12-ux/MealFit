"""Name-based scope estimate. No database changes or approved mappings."""
import csv
import json
from collections import Counter
from pathlib import Path

out=Path(__file__).resolve().parents[2]/'reports'/'kamis-audit'
db=json.loads((out/'db_snapshot.json').read_text(encoding='utf-8'))
# Commodity families observed in the live KAMIS responses or stored KAMIS series.
families=set('가지 갈치 감자 고구마 고등어 고추 고춧가루 귤 녹두 느타리버섯 다시마 닭고기 담치 당근 대두 돼지고기 들깨 들깻잎 레몬 마늘 망고 메밀 멜론 멥쌀 멸치 명태 무 미나리 미역 바나나 배 배추 보리 부추 브로콜리 사과 삼치 상추 새우 생강 소고기 시금치 양배추 양파 열무 오렌지 오징어 전복 참깨 찹쌀 토마토 파 파인애플 파프리카 팥 팽이버섯 포도 피망 호박 수박 참외 땅콩 호두 아몬드 복숭아 체리 블루베리 아보카도 키위 꽁치 낙지 꼬막 바지락 김 달걀 우유 소금'.split())
families.update(['큰느타리버섯(새송이버섯)','애느타리버섯','조기(참조기)'])
families.update(['오이','미니수박','미니파프리카','무말랭이'])
processed=['통조림','잼','페이스트','장조림','양념','조미','장아찌','피클','훈제','튀김','스크램블','부침','가공우유','강화우유','저지방우유','가공염','구운소금','소금꽃','엿기름','시래기','난황','난백']
# Some shell/skin text denotes edible part rather than a separate commodity;
# count these conservatively as additional review rather than automatically matchable.
rows=[]
for i in db['ingredients']:
    name=i['name']; root=name.split(',')[0]
    existing=bool(i['direct_price'] or i['mapped_price'])
    known=root in families or name=='멸치, 액젓'
    if existing:
        status='기존 가격 연결'
    elif not known:
        status='다른 가격 출처 또는 별도 조사 필요'
    elif any(t in name for t in processed) or (root=='멸치' and '젓갈' in name) or (root=='명태' and ('알' in name or '내장' in name)) or (root in ['호박','고구마'] and '잎' in name):
        status='동일 계열이나 가공품·부위 별도 검토'
    else:
        status='대표가격·수율 적용 후보'
    rows.append({**i,'scope':status})
with (out/'portfolio_scope_candidates.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('counts',dict(Counter(i['scope'] for i in rows)))
print('candidate roots',Counter(i['name'].split(',')[0] for i in rows if i['scope']=='대표가격·수율 적용 후보').most_common())
print('borderline',[(i['ingredient_code'],i['name']) for i in rows if i['scope']=='동일 계열이나 가공품·부위 별도 검토'])
