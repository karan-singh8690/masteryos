package com.masteryos;

/**
 * MasteryOS Java SDK — official client library.
 *
 * Usage:
 *   MasteryOS client = new MasteryOS.Builder().apiKey("your-key").build();
 *   Map<String, Object> dashboard = client.learning().getDashboard();
 */

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;

public class MasteryOS {
    private static final String VERSION = "1.0.0";
    private static final String DEFAULT_BASE_URL = "https://api.masteryos.com";

    private final String apiKey;
    private final String baseUrl;
    private final HttpClient httpClient;
    private final int maxRetries;

    private final Learning learning;
    private final Auth auth;

    private MasteryOS(Builder builder) {
        this.apiKey = builder.apiKey;
        this.baseUrl = builder.baseUrl != null ? builder.baseUrl : DEFAULT_BASE_URL;
        this.maxRetries = builder.maxRetries != null ? builder.maxRetries : 3;
        this.httpClient = HttpClient.newBuilder()
                .timeout(Duration.ofSeconds(builder.timeout != null ? builder.timeout : 30))
                .build();
        this.learning = new Learning(this);
        this.auth = new Auth(this);
    }

    public Learning learning() { return learning; }
    public Auth auth() { return auth; }

    public static class Builder {
        private String apiKey;
        private String baseUrl;
        private Integer timeout;
        private Integer maxRetries;

        public Builder apiKey(String apiKey) { this.apiKey = apiKey; return this; }
        public Builder baseUrl(String baseUrl) { this.baseUrl = baseUrl; return this; }
        public Builder timeout(int seconds) { this.timeout = seconds; return this; }
        public Builder maxRetries(int retries) { this.maxRetries = retries; return this; }

        public MasteryOS build() {
            if (apiKey == null || apiKey.isEmpty()) {
                throw new IllegalArgumentException("API key is required");
            }
            return new MasteryOS(this);
        }
    }

    String request(String method, String path, String body) throws Exception {
        String url = baseUrl + path;
        HttpRequest.Builder reqBuilder = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .header("User-Agent", "masteryos-java/" + VERSION);

        if (body != null) {
            reqBuilder.method(method, HttpRequest.BodyPublishers.ofString(body));
        } else {
            reqBuilder.method(method, HttpRequest.BodyPublishers.noBody());
        }

        Exception lastError = null;
        for (int attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                HttpResponse<String> response = httpClient.send(reqBuilder.build(), HttpResponse.BodyHandlers.ofString());
                if (response.statusCode() >= 500 && attempt < maxRetries) {
                    Thread.sleep((long) Math.pow(2, attempt) * 1000);
                    continue;
                }
                if (response.statusCode() >= 400) {
                    throw new RuntimeException("API error [" + response.statusCode() + "]: " + response.body());
                }
                return response.body();
            } catch (Exception e) {
                lastError = e;
                if (attempt < maxRetries) {
                    Thread.sleep((long) Math.pow(2, attempt) * 1000);
                }
            }
        }
        throw new RuntimeException("Request failed after retries", lastError);
    }

    public static class Learning {
        private final MasteryOS client;
        Learning(MasteryOS client) { this.client = client; }

        public String getDashboard() throws Exception {
            return client.request("GET", "/api/v1/learning/dashboard", null);
        }

        public String startSession(String subjectId) throws Exception {
            return client.request("POST", "/api/v1/learning/sessions",
                "{\"subject_id\":\"" + subjectId + "\",\"intent\":\"mixed\",\"target_question_count\":10}");
        }
    }

    public static class Auth {
        private final MasteryOS client;
        Auth(MasteryOS client) { this.client = client; }

        public String login(String email, String password) throws Exception {
            return client.request("POST", "/api/v1/auth/login",
                "{\"email\":\"" + email + "\",\"password\":\"" + password + "\"}");
        }
    }
}
