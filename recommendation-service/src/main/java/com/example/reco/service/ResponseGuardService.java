package com.example.reco.service;

import com.example.reco.model.ProductCandidate;
import com.example.reco.model.ProductResult;
import com.example.reco.model.RankedSelection;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * ADR-23: the single place that owns LLM-failure handling for the rerank
 * step -- grounding check (ADR-12) plus a deterministic fallback floor.
 */
@Service
public class ResponseGuardService {

    public record GuardResult(List<ProductResult> results, boolean degraded, String reason) {}

    public GuardResult finalize(RankedSelection ranked, List<ProductCandidate> candidates, int topK) {
        Map<String, ProductCandidate> byAsin = candidates.stream()
                .collect(Collectors.toMap(ProductCandidate::parentAsin, c -> c, (a, b) -> a));

        if (ranked != null && ranked.items() != null && !ranked.items().isEmpty()) {
            List<ProductResult> grounded = new ArrayList<>();
            for (RankedSelection.RankedItem item : ranked.items()) {
                ProductCandidate c = byAsin.get(item.parentAsin());
                if (c == null) {
                    continue; // ADR-12: drop anything not in the actual candidate set passed to the LLM
                }
                grounded.add(new ProductResult(
                        c.parentAsin(), c.title(), c.price(), c.averageRating(), c.store(),
                        item.rationale(), c.vectorScore()));
                if (grounded.size() >= topK) break;
            }
            if (!grounded.isEmpty()) {
                return new GuardResult(grounded, false, null);
            }
        }

        // Deterministic floor: LLM unavailable, malformed, or fully ungrounded output.
        List<ProductResult> fallback = candidates.stream()
                .limit(topK)
                .map(c -> new ProductResult(
                        c.parentAsin(), c.title(), c.price(), c.averageRating(), c.store(),
                        "Matched on similarity to your query.", c.vectorScore()))
                .toList();
        return new GuardResult(fallback, true,
                "LLM re-rank unavailable or returned no grounded results; showing vector-similarity ranking.");
    }
}
