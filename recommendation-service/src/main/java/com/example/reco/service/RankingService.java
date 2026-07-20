package com.example.reco.service;

import com.example.reco.config.RecoProperties;
import com.example.reco.model.ProductCandidate;
import com.example.reco.model.RankedSelection;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

/**
 * ADR-10: second ChatClient call, selects/orders the final top-K from the
 * vector-recall candidates. Fast-track note: ADR-22's cross-encoder stage
 * (narrowing 25 -> 12 before this call) is deferred -- the LLM sees the
 * vector-recall candidates directly. See README fast-track deviations.
 */
@Service
public class RankingService {

    private final ChatClient chatClient;
    private final RecoProperties props;

    public RankingService(ChatClient.Builder builder, RecoProperties props) {
        this.chatClient = builder.build();
        this.props = props;
    }

    public RankedSelection rerank(String originalQuery, List<ProductCandidate> candidates) {
        String candidateBlock = candidates.stream()
                .map(c -> "- asin=%s | title=%s | price=%s | rating=%s | text=%s".formatted(
                        c.parentAsin(), c.title(), c.price(), c.averageRating(),
                        truncate(c.productText(), 220)))
                .collect(Collectors.joining("\n"));

        String systemPrompt = """
                You select and rank the best product matches for a shopper's query, choosing
                ONLY from the candidate list below. Never invent an asin that is not listed.
                Return at most %d items, ordered best-first. Each item needs a one-sentence
                rationale grounded only in that candidate's own text -- do not claim an
                attribute (e.g. "waterproof") that isn't present in it.
                """.formatted(props.retrieval().finalTopK());

        return chatClient.prompt()
                .system(systemPrompt)
                .user("Query: %s\n\nCandidates:\n%s".formatted(originalQuery, candidateBlock))
                .call()
                .entity(RankedSelection.class);
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() <= max ? s : s.substring(0, max);
    }
}
