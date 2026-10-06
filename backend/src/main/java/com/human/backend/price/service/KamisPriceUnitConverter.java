package com.human.backend.price.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Locale;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

@Component
public class KamisPriceUnitConverter {
    private static final BigDecimal THOUSAND = BigDecimal.valueOf(1000);
    private static final Pattern UNIT = Pattern.compile(
            "(\\d+(?:\\.\\d+)?)\\s*(kg|㎏|그램|g|ml|ℓ|L|개|구|마리|장|손|속|포기)",
            Pattern.CASE_INSENSITIVE);
    private final PortfolioPriceRules rules;
    public KamisPriceUnitConverter(PortfolioPriceRules rules) { this.rules = rules; }

    public BigDecimal grams(String kindName, String itemCode) {
        var matches = UNIT.matcher(kindName == null ? "" : kindName);
        BigDecimal quantity = null;
        String unit = null;
        // 20kg(1kg): the final unit is the price actually returned by the API.
        while (matches.find()) {
            quantity = new BigDecimal(matches.group(1));
            unit = matches.group(2).toLowerCase(Locale.ROOT);
        }
        if (quantity == null || quantity.signum() <= 0) {
            throw new IllegalArgumentException("가격 응답의 단위를 확인할 수 없습니다: " + kindName);
        }
        return switch (unit) {
            case "kg", "㎏" -> quantity.multiply(THOUSAND);
            case "g", "그램" -> quantity;
            case "l", "ℓ", "ml" -> {
                if (!"9908".equals(itemCode)) throw new IllegalArgumentException("부피 환산 기준이 없는 품목입니다: " + itemCode);
                yield quantity.multiply(rules.factor("milkDensity"))
                        .multiply("ml".equals(unit) ? BigDecimal.ONE : THOUSAND);
            }
            default -> {
                BigDecimal each = rules.eachGrams(itemCode);
                if (each == null) throw new IllegalArgumentException("개당 중량 기준이 없는 품목입니다: " + itemCode);
                int count = "손".equals(unit) ? 2 : "속".equals(unit) ? 100 : 1;
                yield quantity.multiply(each).multiply(BigDecimal.valueOf(count));
            }
        };
    }

    public BigDecimal pricePerKilogram(BigDecimal price, String kindName, String itemCode) {
        if (price == null || price.signum() <= 0) throw new IllegalArgumentException("가격은 양수여야 합니다.");
        return price.multiply(THOUSAND).divide(grams(kindName, itemCode), 6, RoundingMode.HALF_UP);
    }
}
