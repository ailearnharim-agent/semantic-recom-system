package com.example.reco.model;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RecommendationRequest(
    @NotBlank @Size(max = 500) String query,
    Integer topK
) {}
