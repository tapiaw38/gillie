package api

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Conversation holds the minimal info we need from the API.
type Conversation struct {
	ID    string `json:"id"`
	Title string `json:"title"`
}

// Client talks to the Gillie REST API.
type Client struct {
	baseURL    string
	httpClient *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

// FindOrCreateConversation returns an existing conversation by ID, or finds/creates
// one titled title. Returns nil (no error) when the API is unreachable.
func (c *Client) FindOrCreateConversation(convID, title string) (*Conversation, error) {
	if convID != "" {
		return &Conversation{ID: convID}, nil
	}
	return c.findOrCreate(title)
}

func (c *Client) findOrCreate(title string) (*Conversation, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/conversation/user")
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Data []Conversation `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	for _, conv := range result.Data {
		if conv.Title == title {
			return &conv, nil
		}
	}

	return c.create(title)
}

func (c *Client) create(title string) (*Conversation, error) {
	body, _ := json.Marshal(map[string]string{"title": title})
	resp, err := c.httpClient.Post(
		c.baseURL+"/conversation/",
		"application/json",
		strings.NewReader(string(body)),
	)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Data Conversation `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result.Data, nil
}

// StreamToken is a single event from the SSE stream.
type StreamToken struct {
	Type    string // "text", "tool_call", "tool_result", "done", "error"
	Content string
	Name    string // tool name when Type == "tool_call"
	Summary string // when Type == "tool_result"
}

// StreamMessage sends a message to a conversation and returns a channel of tokens.
// The channel is closed when the stream ends or on error.
func (c *Client) StreamMessage(convID, content string) (<-chan StreamToken, error) {
	form := url.Values{}
	form.Set("content", content)

	req, err := http.NewRequest(
		"POST",
		fmt.Sprintf("%s/conversation/%s/message/stream", c.baseURL, convID),
		strings.NewReader(form.Encode()),
	)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("X-GTerm-Session", "1")

	client := &http.Client{Timeout: 900 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		resp.Body.Close()
		return nil, fmt.Errorf("API returned %d", resp.StatusCode)
	}

	ch := make(chan StreamToken, 64)

	go func() {
		defer resp.Body.Close()
		defer close(ch)

		scanner := bufio.NewScanner(resp.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if !strings.HasPrefix(line, "data: ") {
				continue
			}
			payload := line[6:]
			if payload == "[DONE]" {
				ch <- StreamToken{Type: "done"}
				return
			}

			var raw any
			if err := json.Unmarshal([]byte(payload), &raw); err != nil {
				// plain string token
				ch <- StreamToken{Type: "text", Content: payload}
				continue
			}

			switch v := raw.(type) {
			case string:
				ch <- StreamToken{Type: "text", Content: v}
			case map[string]any:
				t, _ := v["type"].(string)
				switch t {
				case "tool_call":
					name, _ := v["name"].(string)
					arg, _ := v["arg"].(string)
					ch <- StreamToken{Type: "tool_call", Name: name, Content: arg}
				case "tool_result":
					summary, _ := v["summary"].(string)
					ch <- StreamToken{Type: "tool_result", Summary: summary}
				case "pty_command":
					requestID, _ := v["request_id"].(string)
					command, _ := v["command"].(string)
					// Reuse Name for request_id and Content for the command.
					ch <- StreamToken{Type: "pty_command", Name: requestID, Content: command}
				}
			}
		}
	}()

	return ch, nil
}

// SubmitPtyResult sends the captured PTY output back to the API so the
// waiting LLM tool coroutine can be unblocked with the shell output.
func (c *Client) SubmitPtyResult(convID, requestID, output string) error {
	body, _ := json.Marshal(map[string]string{
		"request_id": requestID,
		"output":     output,
	})
	resp, err := c.httpClient.Post(
		fmt.Sprintf("%s/conversation/%s/pty-result", c.baseURL, convID),
		"application/json",
		bytes.NewReader(body),
	)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("pty-result: API returned %d", resp.StatusCode)
	}
	return nil
}
