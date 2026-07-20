package com.example.reco.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "reco")
public record RecoProperties(EmbedService embedService, Retrieval retrieval) {
    public record EmbedService(String baseUrl) {}
    public record Retrieval(int vectorTopN, int finalTopK) {}
}
