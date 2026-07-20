package com.example.reco.model;

/** Row shape returned by RetrievalService's vector similarity query (ADR-13). */
public record ProductCandidate(
    String parentAsin,
    String title,
    Double price,
    Double averageRating,
    Integer ratingNumber,
    String store,
    String productText,
    double vectorScore
) {}
