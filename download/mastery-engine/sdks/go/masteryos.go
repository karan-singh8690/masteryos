// Package masteryos provides a Go client for the MasteryOS API.
//
// Usage:
//   client := masteryos.New("your-api-key")
//   dashboard, err := client.Learning.GetDashboard()
package masteryos

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const Version = "1.0.0"
const DefaultBaseURL = "https://api.masteryos.com"

// Client is the main MasteryOS API client.
type Client struct {
	APIKey     string
	BaseURL    string
	HTTPClient *http.Client
	MaxRetries int

	Learning *LearningService
	Auth     *AuthService
}

// New creates a new MasteryOS client with the given API key.
func New(apiKey string) *Client {
	c := &Client{
		APIKey:     apiKey,
		BaseURL:    DefaultBaseURL,
		HTTPClient: &http.Client{Timeout: 30 * time.Second},
		MaxRetries: 3,
	}
	c.Learning = &LearningService{client: c}
	c.Auth = &AuthService{client: c}
	return c
}

// APIError represents an API error response.
type APIError struct {
	StatusCode int
	Message    string
	Code       string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("[%d] %s", e.StatusCode, e.Message)
}

func (c *Client) do(method, path string, body interface{}) (map[string]interface{}, error) {
	var reqBody io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewReader(jsonBody)
	}

	url := c.BaseURL + path
	var lastErr error

	for attempt := 0; attempt <= c.MaxRetries; attempt++ {
		req, err := http.NewRequest(method, url, reqBody)
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", "Bearer "+c.APIKey)
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("User-Agent", "masteryos-go/"+Version)

		resp, err := c.HTTPClient.Do(req)
		if err != nil {
			lastErr = err
			if attempt < c.MaxRetries {
				time.Sleep(time.Duration(1<<attempt) * time.Second)
				continue
			}
			return nil, err
		}
		defer resp.Body.Close()

		var result map[string]interface{}
		json.NewDecoder(resp.Body).Decode(&result)

		if resp.StatusCode >= 400 {
			return nil, &APIError{StatusCode: resp.StatusCode, Message: fmt.Sprintf("%v", result["detail"])}
		}
		return result, nil
	}
	return nil, lastErr
}

// LearningService provides learning endpoints.
type LearningService struct{ client *Client }

func (s *LearningService) GetDashboard() (map[string]interface{}, error) {
	return s.client.do("GET", "/api/v1/learning/dashboard", nil)
}

func (s *LearningService) StartSession(subjectID string) (map[string]interface{}, error) {
	return s.client.do("POST", "/api/v1/learning/sessions", map[string]interface{}{
		"subject_id": subjectID, "intent": "mixed", "target_question_count": 10,
	})
}

// AuthService provides authentication endpoints.
type AuthService struct{ client *Client }

func (s *AuthService) Login(email, password string) (map[string]interface{}, error) {
	return s.client.do("POST", "/api/v1/auth/login", map[string]interface{}{
		"email": email, "password": password,
	})
}
