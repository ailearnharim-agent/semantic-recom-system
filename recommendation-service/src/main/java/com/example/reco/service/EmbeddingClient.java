package com.example.reco.service;

import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

/**
 * Fast-track substitution for ADR-07 (in-JVM ONNX embedding). Calls the
 * Python embed-service, which runs the exact bge-small-en-v1.5 model used
 * to build the pgvector index, guaranteeing embedding-space parity. See
 * README "Fast-track deviations" for the migration path back to in-JVM ONNX.
 */
@Service
public class EmbeddingClient {

    private final RestClient restClient;

    public EmbeddingClient(RestClient embedServiceRestClient) {
        this.restClient = embedServiceRestClient;
    }

    public float[] embed(String text) {
        EmbedResponse response = restClient.post()
                .uri("/embed")
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("text", text))
                .retrieve()
                .body(EmbedResponse.class);

        if (response == null || response.embedding() == null) {
            throw new IllegalStateException("embed-service returned no embedding for query");
        }
        List<Double> raw = response.embedding();
        float[] out = new float[raw.size()];
        for (int i = 0; i < raw.size(); i++) {
            out[i] = raw.get(i).floatValue();
        }
        return out;
    }

    private record EmbedResponse(List<Double> embedding, int dim) {}
}
