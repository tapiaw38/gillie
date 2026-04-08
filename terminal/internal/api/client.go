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
	workspace  string
	httpClient *http.Client
}

func NewClient(baseURL, workspace string) *Client {
	return &Client{
		baseURL:   baseURL,
		workspace: workspace,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (c *Client) addWorkspaceHeader(req *http.Request) {
	if c.workspace != "" {
		req.Header.Set("X-Gillie-Workspace", c.workspace)
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
	req, err := http.NewRequest("GET", c.baseURL+"/conversation/user", nil)
	if err != nil {
		return nil, err
	}
	c.addWorkspaceHeader(req)
	resp, err := c.httpClient.Do(req)
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
	req, err := http.NewRequest("POST", c.baseURL+"/conversation/", strings.NewReader(string(body)))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	c.addWorkspaceHeader(req)
	resp, err := c.httpClient.Do(req)
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
	c.addWorkspaceHeader(req)

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
	req, err := http.NewRequest("POST",
		fmt.Sprintf("%s/conversation/%s/pty-result", c.baseURL, convID),
		bytes.NewReader(body),
	)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	c.addWorkspaceHeader(req)
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("pty-result: API returned %d", resp.StatusCode)
	}
	return nil
}
