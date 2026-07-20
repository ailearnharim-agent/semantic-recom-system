package com.example.reco.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.client.RestClient;

import javax.sql.DataSource;

@Configuration
@EnableConfigurationProperties(RecoProperties.class)
public class AppConfig {

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }

    @Bean
    public RestClient embedServiceRestClient(RecoProperties props) {
        // SimpleClientHttpRequestFactory (HttpURLConnection-based) instead of the JDK
        // HttpClient default: the latter's cleartext HTTP/2-upgrade attempt confuses
        // uvicorn/h11's connection handling and silently drops the request body.
        return RestClient.builder()
                .baseUrl(props.embedService().baseUrl())
                .requestFactory(new SimpleClientHttpRequestFactory())
                .build();
    }
}
