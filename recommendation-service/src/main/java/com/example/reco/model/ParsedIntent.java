package com.example.reco.model;

/** ADR-09: schema-constrained structured output from the query-understanding LLM call. */
public record ParsedIntent(
    String rewrittenQuery,
    String category,
    String occasion,
    String season,
    Double priceMin,
    Double priceMax
) {
    public static ParsedIntent fallback(String rawQuery) {
        return new ParsedIntent(rawQuery, null, null, null, null, null);
    }
}
