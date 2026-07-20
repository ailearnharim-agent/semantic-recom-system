package com.example.reco.controller;

import com.example.reco.config.RecoProperties;
import com.example.reco.model.ParsedIntent;
import com.example.reco.model.ProductCandidate;
import com.example.reco.model.RankedSelection;
import com.example.reco.model.RecommendationRequest;
import com.example.reco.model.RecommendationResponse;
import com.example.reco.service.EmbeddingClient;
import com.example.reco.service.QueryUnderstandingService;
import com.example.reco.service.RankingService;
import com.example.reco.service.ResponseGuardService;
import com.example.reco.service.RetrievalService;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1")
public class RecommendationController {

    private static final Logger log = LoggerFactory.getLogger(RecommendationController.class);

    private final QueryUnderstandingService queryUnderstandingService;
    private final EmbeddingClient embeddingClient;
    private final RetrievalService retrievalService;
    private final RankingService rankingService;
    private final ResponseGuardService responseGuardService;
    private final RecoProperties props;

    public RecommendationController(QueryUnderstandingService queryUnderstandingService,
                                     EmbeddingClient embeddingClient,
                                     RetrievalService retrievalService,
                                     RankingService rankingService,
                                     ResponseGuardService responseGuardService,
                                     RecoProperties props) {
        this.queryUnderstandingService = queryUnderstandingService;
        this.embeddingClient = embeddingClient;
        this.retrievalService = retrievalService;
        this.rankingService = rankingService;
        this.responseGuardService = responseGuardService;
        this.props = props;
    }

    @PostMapping("/recommendations")
    public RecommendationResponse recommend(@Valid @RequestBody RecommendationRequest request) {
        int topK = request.topK() != null ? request.topK() : props.retrieval().finalTopK();

        ParsedIntent intent = queryUnderstandingService.understand(request.query());
        String embedText = intent.rewrittenQuery() != null ? intent.rewrittenQuery() : request.query();

        float[] vector = embeddingClient.embed(embedText);
        List<ProductCandidate> candidates = retrievalService.search(vector, intent);

        if (candidates.isEmpty()) {
            return new RecommendationResponse(intent, List.of(), true,
                    "No candidates matched (try relaxing price/category constraints).");
        }

        RankedSelection ranked;
        try {
            ranked = rankingService.rerank(request.query(), candidates);
        } catch (Exception e) {
            log.warn("Ranking LLM call failed, falling back to vector order: {}", e.getMessage());
            ranked = null;
        }

        var guardResult = responseGuardService.finalize(ranked, candidates, topK);
        return new RecommendationResponse(intent, guardResult.results(), guardResult.degraded(), guardResult.reason());
    }
}
