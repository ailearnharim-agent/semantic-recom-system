package com.example.reco.service;

import com.example.reco.model.ParsedIntent;
import org.springframework.ai.chat.client.ChatClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** ADR-09: LLM structured extraction. ADR-15: falls back to the raw query, no filters, on any failure. */
@Service
public class QueryUnderstandingService {

    private static final Logger log = LoggerFactory.getLogger(QueryUnderstandingService.class);

    private static final String SYSTEM_PROMPT = """
            You extract shopping intent from a natural-language fashion product query.
            - rewrittenQuery: rewrite the query into a dense, descriptive semantic search phrase
              (expand implied attributes, e.g. "beach" implies lightweight/breathable fabric).
            - category, occasion, season: extract only if clearly implied by the query, else null.
            - priceMin, priceMax: extract ONLY if the user stated an explicit price constraint
              (e.g. "under $50"), else null. Never guess a price range.
            """;

    private final ChatClient chatClient;

    public QueryUnderstandingService(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    public ParsedIntent understand(String rawQuery) {
        try {
            ParsedIntent result = chatClient.prompt()
                    .system(SYSTEM_PROMPT)
                    .user(rawQuery)
                    .call()
                    .entity(ParsedIntent.class);

            if (result == null || result.rewrittenQuery() == null || result.rewrittenQuery().isBlank()) {
                return ParsedIntent.fallback(rawQuery);
            }
            return result;
        } catch (Exception e) {
            log.warn("Query understanding failed, falling back to raw query: {}", e.getMessage());
            return ParsedIntent.fallback(rawQuery);
        }
    }
}
