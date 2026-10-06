package com.human.backend.price.service;

import java.util.List;
import com.human.backend.price.entity.PriceSeries;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

@Service
public class PortfolioIngredientMappingService {
    private final JdbcTemplate jdbc;
    private final PortfolioMappingCalculator calculator;
    public PortfolioIngredientMappingService(JdbcTemplate jdbc, PortfolioMappingCalculator calculator) {
        this.jdbc = jdbc; this.calculator = calculator;
    }
    private record Candidate(long id, String name) {}

    /** Preserve approved/manual decisions; only add missing supported portfolio mappings. */
    public int addMissingMappings(PriceSeries series) {
        if (!"KAMIS_PORTFOLIO".equals(series.getSourceName()) && !"KAMIS".equals(series.getSourceName())) return 0;
        List<Candidate> candidates = jdbc.query("""
            SELECT i.ingredient_id, i.name FROM mealfit.ingredient i
            WHERE i.is_active IS TRUE AND i.standard_unit='g'
              AND NOT EXISTS (SELECT 1 FROM mealfit.ingredient_price_mapping m
                    WHERE m.ingredient_id=i.ingredient_id
                    AND ((m.review_status='APPROVED' AND m.is_active IS TRUE) OR m.review_status='REJECTED'))
            ORDER BY i.ingredient_id
            """, (rs, row) -> new Candidate(rs.getLong(1), rs.getString(2)));
        int added = 0;
        for (Candidate candidate : candidates) {
            if (!calculator.matches(candidate.name(), series)) continue;
            var mapping = calculator.calculate(candidate.name(), series.getVariety(), series.getSourceItemCode());
            added += jdbc.update("""
                INSERT INTO mealfit.ingredient_price_mapping
                    (ingredient_id,series_id,mapping_type,conversion_factor,confidence_score,
                     priority,review_status,is_active)
                SELECT ?,?,?,?,?,40,'APPROVED',TRUE
                WHERE NOT EXISTS (SELECT 1 FROM mealfit.ingredient_price_mapping
                    WHERE ingredient_id=? AND ((review_status='APPROVED' AND is_active IS TRUE) OR review_status='REJECTED'))
                ON CONFLICT (ingredient_id,series_id) DO NOTHING
                """, candidate.id(), series.getId(), mapping.type(), mapping.factor(), mapping.confidence(), candidate.id());
        }
        return added;
    }
}
