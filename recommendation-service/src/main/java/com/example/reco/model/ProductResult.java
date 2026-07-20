package com.example.reco.model;

public record ProductResult(
    String parentAsin,
    String title,
    Double price,
    Double averageRating,
    String store,
    String rationale,
    double score
) {}
