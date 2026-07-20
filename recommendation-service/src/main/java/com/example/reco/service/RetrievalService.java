package com.example.reco.service;

import com.example.reco.config.RecoProperties;
import com.example.reco.model.ParsedIntent;
import com.example.reco.model.ProductCandidate;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * ADR-13: pgvector similarity search directly against the `product` table
 * built by the Python pipeline. Fast-track note: uses plain JdbcTemplate
 * rather than Spring AI's PgVectorStore abstraction, since our schema
 * carries first-class product columns (price, rating, category) rather
 * than Spring AI's generic Document/metadata shape -- filtering on real
 * columns in SQL is simpler and faster to get right in this time box.
 */
@Service
public class RetrievalService {

    private final JdbcTemplate jdbcTemplate;
    private final RecoProperties props;

    public RetrievalService(JdbcTemplate jdbcTemplate, RecoProperties props) {
        this.jdbcTemplate = jdbcTemplate;
        this.props = props;
    }

    public List<ProductCandidate> search(float[] queryVector, ParsedIntent intent) {
        String vectorLiteral = toVectorLiteral(queryVector);

        StringBuilder sql = new StringBuilder("""
                SELECT parent_asin, title, price, average_rating, rating_number, store, product_text,
                       1 - (embedding <=> ?::vector) AS score
                FROM product
                WHERE 1=1
                """);
        List<Object> params = new ArrayList<>();
        params.add(vectorLiteral);

        if (intent != null && intent.priceMin() != null) {
            sql.append(" AND price >= ? ");
            params.add(intent.priceMin());
        }
        if (intent != null && intent.priceMax() != null) {
            sql.append(" AND price <= ? ");
            params.add(intent.priceMax());
        }
        sql.append(" ORDER BY embedding <=> ?::vector LIMIT ? ");
        params.add(vectorLiteral);
        params.add(props.retrieval().vectorTopN());

        return jdbcTemplate.query(sql.toString(), (rs, rowNum) -> new ProductCandidate(
                rs.getString("parent_asin"),
                rs.getString("title"),
                nullableDouble(rs, "price"),
                nullableDouble(rs, "average_rating"),
                (Integer) rs.getObject("rating_number"),
                rs.getString("store"),
                rs.getString("product_text"),
                rs.getDouble("score")
        ), params.toArray());
    }

    /** NUMERIC/REAL columns surface as BigDecimal/Float via getObject(); normalize to Double. */
    private Double nullableDouble(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
        double v = rs.getDouble(column);
        return rs.wasNull() ? null : v;
    }

    private String toVectorLiteral(float[] vector) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < vector.length; i++) {
            if (i > 0) sb.append(",");
            sb.append(vector[i]);
        }
        sb.append("]");
        return sb.toString();
    }
}
