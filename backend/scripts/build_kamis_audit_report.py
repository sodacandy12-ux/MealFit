import csv
import json
from pathlib import Path

out=Path(__file__).resolve().parents[2]/'reports'/'kamis-audit'
db=json.loads((out/'db_snapshot.json').read_text(encoding='utf-8'))
ingredients={i['ingredient_code']:i for i in db['ingredients']}
catalog=[]
for f in sorted(out.glob('category_*.json')):
    _,cls,cat=f.stem.split('_')
    for r in json.loads(f.read_text(encoding='utf-8'))['data'].get('item',[]):
        catalog.append({'구분':cls,'부류코드':cat,**r})
missing=[i for i in ingredients.values() if not(i['direct_price'] or i['mapped_price'])]
def write_csv(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (out/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
write_csv('kamis_catalog_20261002.csv',catalog)
write_csv('missing_ingredients.csv',missing)

# Explicitly reviewed candidates; these are proposals, not approved database mappings.
choices=[
('F00017','111','01','04','02','기존 가격 재사용','동명 F00016의 가격이 있음. 식품 코드별 세부 속성 확인 후 연결'),
('F00827','211','02','04','02','기존 가격 재사용','동명 F00815의 가격이 있음. 재배시기·품종 확인'),
('F00830','211','02','04','02','기존 가격 재사용','동명 F00815의 가격이 있음. 재배시기·품종 확인'),
('F03158','142','00','04','02','기존 가격 재사용','동명 F00482의 가격이 있음. 원산지 확인'),
('F02838','248','00','04','01','신규 가격 수집','국산 또는 중국산(품종 01) 중 실제 구매 원산지 선택'),
('F02875','652','00','30','01','신규 가격 수집','천일염; 실제 구매 규격 확인'),
('F02870','652','00','30','01','신규 가격 수집','천일염; 실제 구매 규격 확인'),
('F02876','652','00','30','01','가공 차이 검토','가는소금의 분쇄·포장 비용 차이. 천일염 대체가격으로만 사용'),
('F02877','652','00','30','01','가공 차이 검토','굵은소금; 구매 규격 확인 후 천일염 연결 검토'),
('F01147','246','02','04','02','신규 가격 수집','쪽파. 대파(품종 00) 가격과 구분'),
('F01148','246','02','04','02','신규 가격 수집','같은 이름의 별도 식품 코드. 쪽파로 검토'),
('F00620','242','00','04','02','신규 가격 수집','일반 풋고추. 청양·꽈리·오이고추와 구분'),
('F00627','242','00','04','02','신규 가격 수집','녹광 풋고추'),
('F01617','4304','68','00','01','가격 수집 복구','승인된 시계열이 있으나 가격 행이 0개. API 목심 가격 있음'),
('F01599','4304','28','00','01','가격 수집 복구','승인된 시계열이 있으나 가격 행이 0개. API 갈비 가격 있음'),
('F00567','318','00','05','01','신규 가격 수집','수입 호두. 탈각 여부·건조 상태 확인'),
('F00537','319','00','05','01','신규 가격 수집','수입 아몬드. 탈각 여부·건조 상태 확인'),
('F02063','651','00','30','01','신규 가격 수집','멸치액젓. 브랜드·농도 차이 확인'),
('F02384','661','00','30','01','가식부 환산','바지락 냉장 1kg. 껍데기 포함 구매 중량과 메뉴 가식부 중량 구분'),
('F02368','665','00','30','01','가식부 환산','새꼬막. 껍데기 포함 여부 확인'),
('F02367','665','00','30','01','품종·가식부 검토','꼬막과 새꼬막 품종 차이 확인. 자동 정확매칭 불가'),
('F01182','224','01','04','02','개수 중량 환산','애호박 20개. 1개 실측 중량 필요; 쥬키니로 대체 금지'),
('F01035','223','02','04','02','개수 중량 환산','다다기 50개. 1개 실측 중량 필요'),
('F01038','223','03','04','02','개수 중량 환산','취청 50개. 1개 실측 중량 필요'),
('F01875','9903','21','71','01','개수 가식부 환산','특란 10구 또는 30구. 껍질 제외 중량과 크기 확인'),
('F02658','9908','01','00','01','부피 중량 환산','흰우유 1L. g 단위로 쓰려면 밀도 적용'),
('F02576','641','00','30','01','장수 중량 환산','마른김 10장. 김밥용 규격과 1장 중량 확인'),
('F02581','641','00','30','01','장수 중량 환산','마른김 10장. 품종·1장 중량 확인'),
('F02582','641','01','30','01','장수 중량 환산','구운김 10장. 조미김과 구분'),
('F01431','430','00','04','01','개수 가식부 환산','아보카도 1개. 씨·껍질 제외 수율 필요'),
('F01398','429','02','04','01','생냉동 대체 검토','메뉴 생블루베리 vs KAMIS 수입 냉동. 정확매칭 아님'),
('F02476','664','00','30','01','생냉동 대체 검토','메뉴 생낙지 vs KAMIS 수입 냉동. 원산지·상태 확인'),
('F01947','612','01','30','01','생냉동 대체 검토','꽁치 냉동 수입 5마리. 상태 차이와 마리 중량 환산 필요'),
('F01003','245','00','04','02','조리 수율 환산','데친 양파 vs 생양파. 조리 전 구매 중량으로 환산'),
('F00703','232','01','04','02','조리 수율 환산','데친 당근 vs 무세척 국산 생당근. 손질·조리 수율 필요'),
('F00953','213','00','04','02','조리 수율 환산','데친 시금치 vs 생시금치'),
('F00079','111','01','04','02','조리 수율 환산','밥 vs 생쌀. 취반 수율 적용; 같은 g에 같은 가격 적용 금지'),
('F02841','312','01','04','02','조리 수율 환산','볶은 참깨 vs 원물 참깨. 볶음 수율·가공 비용 필요'),
('F00551','312','01','04','02','조리 수율 환산','볶은 참깨 vs 원물 참깨. 별도 식품 코드'),
('F01185','224','01','04','02','조리·개수 환산','데친 애호박. 개당 중량 및 조리 수율 필요'),
('F03386','258','03','04','02','가공 차이 검토','다진 마늘 vs 깐마늘. 가공 손실·비용 확인'),
('F01155','256','00','04','02','품종 대체 검토','빨강 파프리카 vs 색상 미구분 대표가격. 정확매칭 아님'),
('F01157','256','00','04','02','품종 대체 검토','주황 파프리카 vs 색상 미구분 대표가격. 정확매칭 아님'),
]
review=[]
for code,item,kind,rank,cls,status,note in choices:
    i=ingredients[code]
    hits=[r for r in catalog if r['구분']==cls and r['item_code']==item and r['kind_code']==kind and r['rank_code']==rank]
    if not hits:
        raise ValueError('Missing live catalog candidate '+code)
    r=hits[0]
    review.append({'식품코드':code,'식재료':i['name'],'사용메뉴수':i['menu_count'],'분류':status,
        'KAMIS부류코드':r['부류코드'],'품목코드':item,'품종코드':kind,'등급코드':rank,
        '조회구분':cls,'KAMIS품목':r['item_name'],'KAMIS품종':r['kind_name'],'응답단위':r['unit'],
        '조회일가격':r['dpr1'],'검토사항':note})
write_csv('reviewed_candidates.csv',review)
catalog_items=len({r['item_code'] for r in catalog})
pending_ids={m['ingredient_id'] for m in db['mappings'] if m['review_status']=='PROPOSED'}
source_owner_ids={s['ingredient_id'] for s in db['series']}
pending=[]
for i in missing:
    if i['ingredient_id'] in pending_ids:
        maps=[m for m in db['mappings'] if m['ingredient_id']==i['ingredient_id'] and m['review_status']=='PROPOSED']
        pending.append({**i,'candidate_rows':len(maps),'mapping_types':','.join(sorted({m['mapping_type'] for m in maps}))})
write_csv('existing_pending_ingredients.csv',pending)
lines=['# KAMIS・메뉴젠 가격 연결 점검','',
'조회 기준: 2026-10-02 (한국 시간). E 드라이브 .env에 설정된 DB를 읽기 전용으로 조회. AWS 실행 컨테이너가 같은 DB를 사용하는지는 별도 확인 필요. DB나 배포 설정은 변경하지 않음.','',
f'- 메뉴: {db["menus"][0]["menu_count"]:,}개',
f'- 메뉴에 사용되는 식재료: {len(ingredients):,}개',
f'- 직접 연결 또는 승인 매핑으로 가격 행이 존재하는 식재료: {len(ingredients)-len(missing)}개',
f'- 가격 행이 연결되지 않은 식재료: {len(missing):,}개 (승인 매핑은 있으나 가격 행이 없는 2개 포함)',
f'- 기존 승인대기 후보: {len(pending)}개 식재료, 765개 매핑 행. 서로 다른 지역 시계열 등이 중복되어 매핑 행 수와 식재료 수는 다름.',
f'- 실제 부류별 API 응답: {catalog_items}개 품목코드 / {len(catalog)}개 응답 행. 조사일 또는 과거 비교 가격만 있는 행도 포함하므로 모두 당일 가격이 있다는 뜻은 아님.',
'- 검토한 미연결 후보: 43개. 자동 승인 가능한 목록이 아님. 세부 품종, 원산지, 구매 단위와 수율을 확인해야 함.','',
'## 우선 검토할 식재료','',
'| 식품코드 | 식재료 | 사용 메뉴 수 | KAMIS 품목/품종/등급 | 분류 | 검토사항 |',
'|---|---|---:|---|---|---|']
for r in review:
    lines.append(f'| {r["식품코드"]} | {r["식재료"]} | {r["사용메뉴수"]} | {r["품목코드"]}/{r["품종코드"]}/{r["등급코드"]} | {r["분류"]} | {r["검토사항"]} |')
lines+=['','## 해석과 제한','',
'- 후보는 현재 DB에서 가격 연결이 없는 식재료만 대상으로 삼음. 선택한 KAMIS 조합이 실제 조회 응답에 존재하는지 확인했으나, 신규 시계열 적재나 메뉴젠 식품별 원산지·영양 상세정보 확인까지 완료한 것은 아님.',
'- KAMIS productno(상품 기준 API)와 item_code(부류별 API)는 서로 다른 식별자. 수집에는 부류/품목/품종/등급/지역/도소매 조합을 사용해야 함.',
'- p_convert_kg_yn=Y를 사용해도 애호박, 다다기오이, 달걀, 김, 우유 등은 개수/장수/부피 단위가 남음. 응답 unit이 원래 단위를 유지하면서 kind_name에 1kg 표시가 붙는 사례도 관찰됨. 위 CSV 가격은 원본 응답이며 원/g 환산 단가가 아님. 단위 검증 전 계산에 적용하지 말 것.',
'- 축산 품목은 도매 조회 구분에서도 소매와 같은 응답이 관찰됨. 이 결과만으로 도매 가격이라고 분류하지 말 것. 육류 후보는 소매 응답을 기준으로 제시함.',
f'- 부류별 조회 {catalog_items}개 품목은 이번 날짜에 관찰된 범위. 연중 전체 제공 코드표를 뜻하지 않으며, 계절 품목은 기간별 API로 추가 검증해야 함.',
'- 간장, 참기름, 콩기름, 설탕, 두부, 고추장, 된장, 밀가루, 물엿, 표고버섯 등은 이번 응답에서 직접 대응 품목을 확인하지 못함. 다른 원료 가격으로 자동 대체하지 말고 구매 단가 또는 별도 출처 검토.',
'- 소금꽃·구운소금·함초소금은 일반 천일염과 다른 상품. 늙은호박·단호박·호박잎은 애호박과 다른 식재료. 볶은 견과류·조미김·가공우유는 원물 가격과 차이가 있으므로 위 검토 후보에 정확매칭으로 넣지 않음.',
'- 가격 연결 여부는 가격 행 존재 기준이며 최신성, 지역 적합성, 수율 정확성을 보장하지 않음. DB 시계열별 최신 가격 날짜는 2024-11-05~2026-09-22로 분포함.','',
'공식 문서: https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&boardno=1',
'기간별 도매 API: https://www.kamis.or.kr/customer/reference/openapi_list.do?action=detail&boardno=16','',
'부류별 실제 조회 품목: '+', '.join(sorted({r['item_name'] for r in catalog})), '']
(out/'매핑_점검_결과.md').write_text('\n'.join(lines),encoding='utf-8')
print({'catalog_items':catalog_items,'catalog_rows':len(catalog),'missing':len(missing),'reviewed':len(review),'pending_ingredients':len(pending)})
