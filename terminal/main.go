package main

import (
	"flag"
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"gillie-terminal/internal/api"
	"gillie-terminal/internal/ui"
)

func main() {
	host := flag.String("host", "127.0.0.1", "Gillie API host")
	port := flag.Int("port", 8000, "Gillie API port")
	shell := flag.String("shell", "", "Shell to spawn (default: $SHELL or /bin/bash)")
	convID := flag.String("conv-id", "", "Attach to existing conversation ID")
	flag.Parse()

	resolvedShell := *shell
	if resolvedShell == "" {
		resolvedShell = os.Getenv("SHELL")
		if resolvedShell == "" {
			resolvedShell = "/bin/bash"
		}
	}

	baseURL := fmt.Sprintf("http://%s:%d", *host, *port)

	apiClient := api.NewClient(baseURL)

	conv, err := apiClient.FindOrCreateConversation(*convID, "GTerm")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: could not connect to Gillie API (%v)\n", err)
		fmt.Fprintf(os.Stderr, "AI features disabled. Start with: gillie start\n")
	}

	convIDResolved := ""
	if conv != nil {
		convIDResolved = conv.ID
	}

	model := ui.NewModel(ui.Config{
		Shell:     resolvedShell,
		BaseURL:   baseURL,
		ConvID:    convIDResolved,
		Assistant: "GTerm",
		APIClient: apiClient,
	})

	p := tea.NewProgram(
		model,
		tea.WithAltScreen(),
		tea.WithMouseCellMotion(),
	)

	if _, err := p.Run(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}
