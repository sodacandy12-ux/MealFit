package com.human.backend.price.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Set;
import org.springframework.stereotype.Component;
import com.human.backend.price.entity.PriceSeries;

/** Target recipe adjustments, applied once through ingredient_price_mapping. */
@Component
public class PortfolioMappingCalculator {
    private static final Set<String> GRAINS = Set.of("멥쌀", "찹쌀", "보리", "대두", "팥", "녹두", "메밀");
    private static final Set<String> MEATS = Set.of("소고기", "돼지고기", "닭고기", "갈치", "고등어", "삼치", "새우", "오징어", "명태", "꽁치");
    private static final Set<String> DRY_ITEMS = Set.of("241", "638", "639", "640", "641", "642", "660", "141", "142", "143", "144", "312", "313", "318", "319");
    private final PortfolioPriceRules rules;
    public record Mapping(BigDecimal factor, String type, BigDecimal confidence) {}
    public PortfolioMappingCalculator(PortfolioPriceRules rules) { this.rules = rules; }

    public String preferredItem(String name) {
        String root = root(name);
        if (name.equals("멸치, 액젓")) return "651";
        if (Set.of("멥쌀", "찹쌀").contains(root) && name.contains("현미")) return "115";
        if (root.equals("토마토") && name.contains("방울")) return "422";
        if (root.equals("배추") && name.contains("얼갈이")) return "215";
        if (root.equals("고추")) return name.contains("말린") ? "241" : name.contains("빨간") ? "243" : "242";
        if (root.equals("새우") && name.contains("젓갈")) return "650";
        if (root.equals("오징어") && name.contains("말린")) return "640";
        if (root.equals("명태") && contains(name, "북어", "황태")) return "639";
        return rules.itemForRoot(root);
    }

    public boolean matches(String name, PriceSeries series) {
        if (!rules.isSupportedIngredient(name) || series.getSourceItemCode() == null
                || !series.getSourceItemCode().equals(preferredItem(name))) return false;
        String kind = series.getSourceKindCode();
        // Do not attach a new ingredient to an explicitly different subtype.
        String root = root(name);
        if (root.equals("파")) return (name.contains("쪽파") ? "02" : "00").equals(kind);
        if (root.equals("오이")) return (name.contains("취청") ? "03" : name.contains("가시") ? "01" : "02").equals(kind);
        if (root.equals("호박")) return (name.contains("쥬키니") ? "02" : "01").equals(kind);
        if (root.equals("고추") && "242".equals(series.getSourceItemCode())) {
            return (name.contains("청양") ? "03" : name.contains("꽈리") ? "02" : name.contains("오이") ? "04" : "00").equals(kind);
        }
        if (root.equals("김")) return (name.contains("구운") ? "01" : "00").equals(kind);
        if (root.equals("소고기") || root.equals("돼지고기")) {
            String expected = root.equals("소고기")
                    ? part(name, new String[][]{{"안심","21"},{"등심","22"},{"설도","36"},{"양지","40"},{"갈비","50"}}, "36")
                    : part(name, new String[][]{{"삼겹","27"},{"목심","68"},{"갈비","28"},{"앞다리","25"}}, "25");
            if (!expected.equals(kind)) return false;
            if (root.equals("소고기")) return (name.contains("1++") ? "01" : name.contains("1+") ? "02" : "03").equals(series.getSourceRankCode());
        }
        return true;
    }

    public Mapping calculate(String name, String sourceKind, String itemCode) {
        String root = root(name);
        sourceKind = sourceKind == null ? "" : sourceKind;
        BigDecimal factor = BigDecimal.ONE;
        boolean cooked = contains(name, "삶은것", "데친것", "구운것", "찐것", "볶은것")
                || (Set.of("멥쌀", "찹쌀").contains(root) && name.contains(", 밥"));
        boolean dryTarget = name.contains("말린것") || root.equals("무말랭이");
        boolean drySource = contains(sourceKind, "말린", "마른", "건") || DRY_ITEMS.contains(itemCode);
        if (GRAINS.contains(root)) {
            if (cooked) factor = divide(factor, "grainCookedWeight");
            else if (name.contains("가루")) factor = factor.multiply(rules.factor("millingCost"));
        } else if (cooked && !(root.equals("김") && sourceKind.contains("구운"))) {
            factor = divide(factor, MEATS.contains(root) ? "meatCookingYield" : "vegetableCookingYield");
        }
        if (Set.of("미역", "다시마").contains(root) && !dryTarget && drySource) factor = divide(factor, "seaweedRehydration");
        else if (dryTarget && !drySource && !Set.of("소금", "아몬드", "호두").contains(root)) factor = factor.multiply(rules.factor("dryingWeightRatio"));
        if (Set.of("바지락", "꼬막", "전복").contains(root) || (root.equals("담치") && sourceKind.contains("안깐"))) {
            factor = divide(factor, Set.of("바지락", "꼬막").contains(root) ? "clamEdibleYield" : "shellfishEdibleYield");
        } else if (root.equals("새우") && !itemCode.equals("650")) factor = divide(factor, "shrimpEdibleYield");
        else if (Set.of("고등어", "갈치", "삼치", "꽁치", "조기(참조기)", "명태").contains(root)) factor = divide(factor, "fishEdibleYield");
        else if (root.equals("닭고기") && contains(name, "살코기", "가슴", "다리")) factor = divide(factor, "chickenEdibleYield");
        else if (root.equals("아보카도")) factor = divide(factor, "avocadoEdibleYield");
        if (name.contains("다진것")) factor = factor.multiply(rules.factor("mincingCost"));
        factor = factor.setScale(6, RoundingMode.HALF_UP);
        boolean adjusted = factor.compareTo(BigDecimal.ONE) != 0;
        return new Mapping(factor, adjusted ? "RAW_PROXY" : "VARIETY", new BigDecimal(adjusted ? "0.65" : "0.75"));
    }
    private BigDecimal divide(BigDecimal value, String key) { return value.divide(rules.factor(key), 12, RoundingMode.HALF_UP); }
    private String root(String name) { return name.split(",", 2)[0].trim(); }
    private boolean contains(String name, String... tokens) { for (String token : tokens) if (name.contains(token)) return true; return false; }
    private String part(String name, String[][] parts, String fallback) { for (String[] p : parts) if (name.contains(p[0])) return p[1]; return fallback; }
}
