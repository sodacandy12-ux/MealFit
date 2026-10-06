"""Explicit portfolio estimates, not nutritional/purchasing-grade conversion factors."""
import re
import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

D=Decimal
RULES=json.loads((Path(__file__).resolve().parents[1]/'src/main/resources/portfolio-price-rules.json').read_text(encoding='utf-8'))
ROOT_ITEMS=RULES['rootItems']
EACH_GRAMS=RULES['eachGrams']
def assumption(key):return D(str(RULES['factors'][key]))

def source_grams(kind_name, item_code):
    """Use the LAST unit: '20kg(1kg)' is 1kg; never trust stale daily unit metadata."""
    units=re.findall(r'(\d+(?:\.\d+)?)\s*(kg|㎏|g|그램|L|ℓ|ml|mL|개|구|마리|장|손|속|포기)',kind_name or '',re.I)
    if not units:
        raise ValueError('Unknown source unit: '+str(kind_name))
    qty,unit=units[-1];q=D(qty)
    if q<=0:raise ValueError('Nonpositive source quantity')
    if unit.lower() in ('kg','㎏'): return q*1000,'kg'
    if unit.lower() in ('g','그램'): return q,'g'
    if unit.lower() in ('l','ℓ','ml'):
        if str(item_code)!='9908':raise ValueError('No density assumption: '+str(item_code))
        return q*assumption('milkDensity')*(1 if unit.lower()=='ml' else 1000),'milk-density'
    each=EACH_GRAMS.get(str(item_code))
    if each is None: raise ValueError('Missing each weight: '+str(item_code))
    multiplier=2 if unit=='손' else 100 if unit=='속' else 1
    return q*D(str(each))*multiplier,'estimated-'+unit

def preference(name):
    root=name.split(',')[0];item=ROOT_ITEMS.get(root);kind=None;rank=None
    if name=='멸치, 액젓': item='651'
    if root in ('멥쌀','찹쌀') and '현미' in name: item='115'
    if root=='토마토' and '방울' in name: item='422'
    if root=='배추' and '얼갈이' in name: item='215'
    if root=='고추':
        if '말린' in name: item='241'
        elif '빨간' in name: item='243'
        else: kind='03' if '청양' in name else '02' if '꽈리' in name else '04' if '오이' in name else '00'
    if root=='파': kind='02' if '쪽파' in name else '00'
    if root=='오이': kind='03' if '취청' in name else '01' if '가시' in name else '02'
    if root=='호박': kind='02' if '쥬키니' in name else '01'
    if root=='상추': kind='01' if '적색' in name else '02'
    if root=='돼지고기':
        kind=next((k for part,k in [('삼겹','27'),('목심','68'),('갈비','28'),('앞다리','25')] if part in name),'25')
    if root=='소고기':
        kind=next((k for part,k in [('안심','21'),('등심','22'),('설도','36'),('양지','40'),('갈비','50')] if part in name),'36')
        rank='01' if '1++' in name else '02' if '1+' in name else '03'
    if root=='김': kind='01' if '구운' in name else '00'
    if root=='닭고기':kind='99'
    if root=='새우' and '젓갈' in name:item='650'
    if root=='오징어' and '말린' in name:item='640'
    if root=='명태' and ('북어' in name or '황태' in name): item='639'
    if root=='멸치' and '젓갈' not in name and '액젓' not in name: kind='00'
    if root=='애느타리버섯':kind='01'
    if root=='포도':kind='06' if '샤인' in name else '03' if '거봉' in name else '01'
    return item,kind,rank

def mapping_factor(name, source_kind, item_code):
    root=name.split(',')[0];factor=D(1);notes=[]
    cooked=any(t in name for t in ('삶은것','데친것','구운것','찐것','볶은것')) or (root in ('멥쌀','찹쌀') and ', 밥' in name)
    dry_target='말린것' in name or root=='무말랭이'
    dry_source=any(t in source_kind for t in ('말린','마른','건')) or item_code in ('241','638','639','640','641','642','660','141','142','143','144','312','313','318','319')
    if root in ('멥쌀','찹쌀','보리','대두','팥','녹두','메밀'):
        if cooked:
            factor/=assumption('grainCookedWeight');notes.append('조리후 중량 '+str(assumption('grainCookedWeight'))+'배')
        elif '가루' in name: factor*=assumption('millingCost');notes.append('제분 비용 추정')
    elif cooked and not (root=='김' and '구운' in source_kind):
        yield_value=assumption('meatCookingYield') if root in ('소고기','돼지고기','닭고기','갈치','고등어','삼치','새우','오징어','명태','꽁치') else assumption('vegetableCookingYield')
        factor/=yield_value;notes.append('조리 수율 '+str(yield_value))
    if root in ('미역','다시마') and not dry_target and dry_source:
        factor/=assumption('seaweedRehydration');notes.append('건조→수화 중량 추정')
    elif dry_target and not dry_source and root not in ('소금','아몬드','호두'):
        factor*=assumption('dryingWeightRatio');notes.append('생것→건조 중량 추정')
    if (root in ('바지락','꼬막','전복','담치') and '안깐' in source_kind) or root in ('바지락','꼬막','전복'):
        factor/=assumption('clamEdibleYield') if root in ('바지락','꼬막') else assumption('shellfishEdibleYield');notes.append('가식부 수율 추정')
    elif root=='새우' and item_code!='650': factor/=assumption('shrimpEdibleYield');notes.append('새우 가식부 추정')
    elif root in ('고등어','갈치','삼치','꽁치','조기(참조기)','명태'):
        factor/=assumption('fishEdibleYield');notes.append('생선 가식부 추정')
    elif root=='닭고기' and any(t in name for t in ('살코기','가슴','다리')):
        factor/=assumption('chickenEdibleYield');notes.append('닭 가식부 추정')
    elif root=='아보카도':factor/=assumption('avocadoEdibleYield');notes.append('아보카도 가식부 추정')
    if '가루' in name and root=='고춧가루': pass
    if '다진것' in name:factor*=assumption('mincingCost');notes.append('분쇄가공 비용 추정')
    return factor.quantize(D('0.000001'),rounding=ROUND_HALF_UP),'; '.join(notes) or '동일 중량 대표가격'
