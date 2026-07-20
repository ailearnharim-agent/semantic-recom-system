package com.example.reco.model;

import java.util.List;

public record RecommendationResponse(
    ParsedIntent parsedIntent,
    List<ProductResult> results,
    boolean degraded,
    String degradedReason
) {}
