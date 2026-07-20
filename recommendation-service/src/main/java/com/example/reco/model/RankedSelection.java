package com.example.reco.model;

import java.util.List;

/** ADR-10/ADR-22: structured output of the LLM re-rank call, in the LLM's chosen order. */
public record RankedSelection(List<RankedItem> items) {
    public record RankedItem(String parentAsin, String rationale) {}
}
