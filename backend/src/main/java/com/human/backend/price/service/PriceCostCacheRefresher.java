package com.human.backend.price.service;

import com.human.backend.cost.repository.MemoryCostRepository;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

@Component
public class PriceCostCacheRefresher {
    private final MemoryCostRepository costs;
    public PriceCostCacheRefresher(MemoryCostRepository costs) { this.costs = costs; }
    @EventListener
    public void onPricesCollected(PriceCollectionCompleted event) { costs.loadAllDbData(); }
}
