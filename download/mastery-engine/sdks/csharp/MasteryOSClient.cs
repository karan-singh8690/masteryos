// MasteryOS C# SDK — official client library.
//
// Usage:
//   var client = new MasteryOSClient("your-api-key");
//   var dashboard = await client.Learning.GetDashboardAsync();

using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace MasteryOS;

public class MasteryOSClient
{
    private const string Version = "1.0.0";
    private const string DefaultBaseUrl = "https://api.masteryos.com";
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private readonly int _maxRetries;

    public LearningService Learning { get; }
    public AuthService Auth { get; }

    public MasteryOSClient(string apiKey, string? baseUrl = null, int timeoutSeconds = 30, int maxRetries = 3)
    {
        _baseUrl = (baseUrl ?? DefaultBaseUrl).TrimEnd('/');
        _maxRetries = maxRetries;
        _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(timeoutSeconds) };
        _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
        _httpClient.DefaultRequestHeaders.Add("User-Agent", $"masteryos-csharp/{Version}");

        Learning = new LearningService(this);
        Auth = new AuthService(this);
    }

    public class APIError : Exception
    {
        public int StatusCode { get; }
        public APIError(int statusCode, string message) : base($"[{statusCode}] {message}")
        {
            StatusCode = statusCode;
        }
    }

    internal async Task<JsonElement> RequestAsync(string method, string path, object? body = null)
    {
        var url = $"{_baseUrl}{path}";
        Exception? lastError = null;

        for (int attempt = 0; attempt <= _maxRetries; attempt++)
        {
            try
            {
                var request = new HttpRequestMessage(new HttpMethod(method), url);
                if (body != null)
                {
                    request.Content = new StringContent(
                        JsonSerializer.Serialize(body),
                        Encoding.UTF8,
                        "application/json");
                }

                var response = await _httpClient.SendAsync(request);

                if ((int)response.StatusCode >= 500 && attempt < _maxRetries)
                {
                    await Task.Delay((int)Math.Pow(2, attempt) * 1000);
                    continue;
                }

                var content = await response.Content.ReadAsStringAsync();
                if ((int)response.StatusCode >= 400)
                {
                    throw new APIError((int)response.StatusCode, content);
                }

                return JsonDocument.Parse(content).RootElement.Clone();
            }
            catch (Exception e)
            {
                lastError = e;
                if (attempt < _maxRetries)
                {
                    await Task.Delay((int)Math.Pow(2, attempt) * 1000);
                }
            }
        }
        throw lastError ?? new Exception("Request failed");
    }

    public class LearningService
    {
        private readonly MasteryOSClient _client;
        internal LearningService(MasteryOSClient client) { _client = client; }

        public Task<JsonElement> GetDashboardAsync() =>
            _client.RequestAsync("GET", "/api/v1/learning/dashboard");

        public Task<JsonElement> StartSessionAsync(string subjectId) =>
            _client.RequestAsync("POST", "/api/v1/learning/sessions",
                new { subject_id = subjectId, intent = "mixed", target_question_count = 10 });
    }

    public class AuthService
    {
        private readonly MasteryOSClient _client;
        internal AuthService(MasteryOSClient client) { _client = client; }

        public Task<JsonElement> LoginAsync(string email, string password) =>
            _client.RequestAsync("POST", "/api/v1/auth/login", new { email, password });
    }
}
