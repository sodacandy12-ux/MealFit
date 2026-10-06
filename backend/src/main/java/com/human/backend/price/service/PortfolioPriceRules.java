package com.human.backend.price.service;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/** Shared portfolio assumptions; Python backfill reads the same JSON file. */
@Component
public class PortfolioPriceRules {
    public record Configuration(Map<String, String> rootItems, Map<String, BigDecimal> eachGrams,
            List<String> excludedWords, Map<String, BigDecimal> factors) {}
    private final Configuration config;

    public PortfolioPriceRules(JsonMapper mapper) {
        try (var input = new ClassPathResource("portfolio-price-rules.json").getInputStream()) {
            config = mapper.readValue(input.readAllBytes(), Configuration.class);
        } catch (IOException | RuntimeException exception) {
            throw new IllegalStateException("가격 환산 규칙을 읽을 수 없습니다.", exception);
        }
        if (config.rootItems() == null || config.excludedWords() == null || config.eachGrams() == null
                || config.factors() == null) {
            throw new IllegalStateException("가격 환산 규칙의 필수 항목이 누락됐습니다.");
        }
        config.eachGrams().values().forEach(this::validatePositive);
        config.factors().values().forEach(this::validatePositive);
    }

    private void validatePositive(BigDecimal value) {
        if (value == null || value.signum() <= 0) throw new IllegalStateException("가격 환산 기준은 양수여야 합니다.");
    }
    public String itemForRoot(String root) { return config.rootItems().get(root); }
    public BigDecimal eachGrams(String item) { return config.eachGrams().get(item); }
    public BigDecimal factor(String key) {
        BigDecimal value = config.factors().get(key);
        if (value == null) throw new IllegalStateException("가격 환산 기준이 없습니다: " + key);
        return value;
    }
    public boolean isSupportedIngredient(String name) {
        if (name == null || name.isBlank()) return false;
        String root = name.split(",", 2)[0].trim();
        if (itemForRoot(root) == null) return false;
        if (config.excludedWords().stream().anyMatch(name::contains)) return false;
        if ((root.equals("호박") || root.equals("고구마")) && name.contains("잎")) return false;
        return !(root.equals("명태") && (name.contains("알") || name.contains("내장")))
                && !(root.equals("멸치") && name.contains("젓갈"));
    }
}
