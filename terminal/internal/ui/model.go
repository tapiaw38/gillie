package ui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/hinshun/vt10x"
	"gillie-terminal/internal/api"
	gpty "gillie-terminal/internal/pty"
	"gillie-terminal/internal/styles"
)

// ─── Modes ────────────────────────────────────────────────────────────────────

type Mode int

const (
	ModeTerminal Mode = iota
	ModeAI
)

// aiPanelHeight is the total vertical budget (in lines) for the AI panel.
// Breakdown: 1 top border + 1 title + 1 divider + 12 viewport + 2 input + 1 bottom border = 18
const aiPanelHeight = 18

// ─── Bubbletea messages ───────────────────────────────────────────────────────

type ptyOutputMsg []byte
type ptyExitMsg struct{}

// aiStreamOpenMsg carries the open stream channel after the HTTP connection
// is established. Subsequent tokens arrive as aiTokenMsg.
type aiStreamOpenMsg struct{ ch <-chan api.StreamToken }
type aiTokenMsg api.StreamToken
type aiStreamDoneMsg struct{}
type aiStreamErrMsg struct{ err error }

// ptyCommandMsg is dispatched when the AI requests a command be run in the PTY.
type ptyCommandMsg struct {
	requestID string
	command   string
}

// ptyResultMsg carries the captured output (or error) after RunAndCapture.
type ptyResultMsg struct {
	requestID string
	output    string
	err       error
}

// ─── AI history entry ─────────────────────────────────────────────────────────

type aiEntry struct {
	role    string // "user" | "assistant" | "tool"
	content string
}

// ─── Config ───────────────────────────────────────────────────────────────────

type Config struct {
	Shell     string
	BaseURL   string
	ConvID    string
	Assistant string
	APIClient *api.Client
}

// ─── Model ────────────────────────────────────────────────────────────────────

type Model struct {
	// Terminal emulation
	pty     *gpty.Manager
	vtState vt10x.Terminal

	// Layout
	width      int
	height     int
	termHeight int

	// Mode
	mode          Mode
	focusTerminal bool // true when keyboard focus is on the PTY while ModeAI

	// AI panel
	aiInput    textinput.Model
	aiViewport viewport.Model
	aiEntries  []aiEntry
	streamCh   <-chan api.StreamToken // open stream; nil when idle
	streaming  bool

	// Token stats
	tokensIn  int
	tokensOut int

	// Config
	convID    string
	assistant string
	apiClient *api.Client

	// Transient error banner
	errMsg string
}

// ─── Constructor ──────────────────────────────────────────────────────────────

func NewModel(cfg Config) *Model {
	inp := textinput.New()
	inp.Placeholder = "Ask…"
	inp.Prompt = "▶ "
	inp.PromptStyle = lipgloss.NewStyle().Foreground(styles.CAccent)
	inp.PlaceholderStyle = lipgloss.NewStyle().Foreground(styles.CTextDim)
	inp.TextStyle = lipgloss.NewStyle().Foreground(styles.CText)
	inp.CharLimit = 2048

	// 18 total - 1 top border - 1 title - 1 divider - 2 input area - 1 bottom border = 12
	vp := viewport.New(0, aiPanelHeight-6)

	m := &Model{
		pty:        gpty.NewManager(cfg.Shell),
		convID:     cfg.ConvID,
		assistant:  cfg.Assistant,
		apiClient:  cfg.APIClient,
		aiInput:    inp,
		aiViewport: vp,
	}

	m.vtState = vt10x.New(vt10x.WithSize(80, 24))

	return m
}

// ─── Init ─────────────────────────────────────────────────────────────────────

func (m *Model) Init() tea.Cmd {
	return tea.EnableMouseCellMotion
}

// ─── Update ───────────────────────────────────────────────────────────────────

func (m *Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {

	case tea.WindowSizeMsg:
		firstStart := m.width == 0
		m.width = msg.Width
		m.height = msg.Height - 1 // reserve 1 line for status bar

		m.recalcTermHeight()
		m.vtState.Resize(m.width, m.termHeight)
		m.pty.Resize(m.width, m.termHeight)
		m.aiViewport.Width = m.width - 2 // -2 for rounded border left+right
		m.aiViewport.Height = aiPanelHeight - 6

		if firstStart {
			if err := m.pty.Start(m.width, m.termHeight); err != nil {
				m.errMsg = fmt.Sprintf("PTY error: %v", err)
				return m, nil
			}
			return m, waitForPtyOutput(m.pty.OutputCh)
		}

	case ptyOutputMsg:
		m.vtState.Write(msg)
		return m, waitForPtyOutput(m.pty.OutputCh)

	case ptyExitMsg:
		return m, tea.Quit

	// aiStreamOpenMsg: HTTP connection established, start reading tokens
	case aiStreamOpenMsg:
		m.streamCh = msg.ch
		return m, readNextToken(m.streamCh)

	// aiTokenMsg: one token (or control event) from the stream
	case aiTokenMsg:
		tok := api.StreamToken(msg)
		switch tok.Type {
		case "text":
			m.appendToLastAssistant(tok.Content)
			m.tokensOut += max(1, len(tok.Content)/4)
			m.refreshAIViewport()
			return m, readNextToken(m.streamCh)

		case "tool_call":
			m.aiEntries = append(m.aiEntries, aiEntry{
				role:    "tool",
				content: fmt.Sprintf("  %s %s", tok.Name, tok.Content),
			})
			m.refreshAIViewport()
			return m, readNextToken(m.streamCh)

		case "tool_result":
			m.aiEntries = append(m.aiEntries, aiEntry{
				role:    "tool",
				content: fmt.Sprintf("  %s", tok.Summary),
			})
			m.refreshAIViewport()
			return m, readNextToken(m.streamCh)

		case "pty_command":
			// AI wants to run a command in the active PTY session.
			m.aiEntries = append(m.aiEntries, aiEntry{
				role:    "tool",
				content: fmt.Sprintf("  running in PTY: %s", tok.Content),
			})
			m.refreshAIViewport()
			cmd := runPtyCommand(m.pty, m.apiClient, m.convID, tok.Name, tok.Content)
			return m, tea.Batch(readNextToken(m.streamCh), cmd)

		case "done":
			m.streaming = false
			m.streamCh = nil
			m.refreshAIViewport()
		}

	case aiStreamDoneMsg:
		m.streaming = false
		m.streamCh = nil

	case aiStreamErrMsg:
		m.streaming = false
		m.streamCh = nil
		m.errMsg = msg.err.Error()

	case ptyResultMsg:
		if msg.err != nil {
			m.errMsg = fmt.Sprintf("PTY capture error: %v", msg.err)
		}

	case tea.MouseMsg:
		if m.mode == ModeTerminal {
			switch msg.Button {
			case tea.MouseButtonWheelUp:
				m.pty.Write([]byte{0x1b, '[', 'A', 0x1b, '[', 'A', 0x1b, '[', 'A'})
			case tea.MouseButtonWheelDown:
				m.pty.Write([]byte{0x1b, '[', 'B', 0x1b, '[', 'B', 0x1b, '[', 'B'})
			}
			return m, nil
		}
		if m.mode == ModeAI {
			// Left click: route keyboard focus based on which area was clicked.
			// Row 0 = status bar, rows 1..termHeight = terminal, rest = AI panel.
			if msg.Action == tea.MouseActionPress && msg.Button == tea.MouseButtonLeft {
				if msg.Y >= 1 && msg.Y <= m.termHeight {
					m.focusTerminal = true
					m.aiInput.Blur()
					return m, nil
				}
				if msg.Y > m.termHeight {
					m.focusTerminal = false
					return m, m.aiInput.Focus()
				}
			}
			// Forward every other mouse event (scroll, motion, release…) to the
			// viewport and always return — never let mouse events fall through to
			// the text input or generate secondary key messages.
			var vpCmd tea.Cmd
			m.aiViewport, vpCmd = m.aiViewport.Update(msg)
			return m, vpCmd
		}

	case tea.KeyMsg:
		// Ctrl+Q: quit from terminal mode, go back to terminal from AI mode
		if msg.Type == tea.KeyCtrlQ {
			if m.mode == ModeAI {
				return m, m.toggleMode()
			}
			m.pty.Close()
			return m, tea.Quit
		}

		// Ctrl+G toggles AI panel
		if msg.Type == tea.KeyCtrlG {
			return m, m.toggleMode()
		}

		// Terminal input: pure terminal mode, OR AI mode with terminal focus
		if m.mode == ModeTerminal || (m.mode == ModeAI && m.focusTerminal) {
			if b := keyToBytes(msg); b != nil {
				m.pty.Write(b)
			}
			return m, nil
		}

		// AI mode input (AI panel has focus)
		if msg.Type == tea.KeyEscape {
			return m, m.toggleMode()
		}
		if msg.Type == tea.KeyEnter {
			return m, m.submitAI()
		}
		// Scroll keys go to the viewport, not the text input
		if msg.Type == tea.KeyUp || msg.Type == tea.KeyDown ||
			msg.Type == tea.KeyPgUp || msg.Type == tea.KeyPgDown {
			var vpCmd tea.Cmd
			m.aiViewport, vpCmd = m.aiViewport.Update(msg)
			return m, vpCmd
		}
		var inputCmd tea.Cmd
		m.aiInput, inputCmd = m.aiInput.Update(msg)
		return m, inputCmd
	}

	return m, nil
}

// ─── View ─────────────────────────────────────────────────────────────────────

func (m *Model) View() string {
	status := m.renderStatus()
	term := m.renderTerminal()

	if m.mode == ModeAI {
		return lipgloss.JoinVertical(lipgloss.Left, status, term, m.renderAIPanel())
	}
	return lipgloss.JoinVertical(lipgloss.Left, status, term)
}

// ─── Status bar ───────────────────────────────────────────────────────────────

func (m *Model) renderStatus() string {
	modeLabel := styles.ModeTerminal.Render(">_") + styles.ModeTerminalTail.Render("▌")
	if m.mode == ModeAI {
		modeLabel = styles.ModeAI.Render("✦") + styles.ModeAITail.Render("▌")
	}

	sep := styles.StatusSep.Render(" │ ")
	left := "  " + styles.StatusName.Render("✨🐙 "+m.assistant) + sep + modeLabel
	if m.errMsg != "" {
		left += "  " + styles.ErrorMsg.Render("⚠ "+m.errMsg)
	}

	hint := styles.StatusHint.Render("^G toggle  ^Q quit")
	var tokenInfo string
	total := m.tokensIn + m.tokensOut
	if total > 0 {
		cost := (float64(m.tokensIn)*0.27 + float64(m.tokensOut)*1.10) / 1_000_000
		tokenInfo = styles.StatusDim.Render(fmt.Sprintf("~%d tok · $%.4f", total, cost)) + sep
	}
	right := tokenInfo + hint + "  "

	gap := max(1, m.width-lipgloss.Width(left)-lipgloss.Width(right))

	return styles.StatusBar.Width(m.width).Render(
		left + strings.Repeat(" ", gap) + right,
	)
}

// ─── Terminal ─────────────────────────────────────────────────────────────────

func (m *Model) renderTerminal() string {
	return renderScreen(m.vtState, m.width, m.termHeight)
}

// ─── AI panel ─────────────────────────────────────────────────────────────────

func (m *Model) renderAIPanel() string {
	// innerWidth is the content area of the rounded border (total - 2 for left/right border)
	innerWidth := m.width - 2

	// Title row with right-aligned hint
	titleLeft := styles.AIPanelTitle.Render("✨🐙 " + m.assistant)
	titleRight := styles.AIPanelHint.Render("Esc / Ctrl+G to close")
	titleGap := max(1, innerWidth-lipgloss.Width(titleLeft)-lipgloss.Width(titleRight))
	title := titleLeft + strings.Repeat(" ", titleGap) + titleRight

	// Divider line
	divider := styles.AIPanelDivider.Render(strings.Repeat("─", innerWidth))

	// Viewport
	m.aiViewport.Width = innerWidth
	vpView := m.aiViewport.View()

	// Input area: prompt takes ~2 chars, padding 1 on left, some buffer
	m.aiInput.Width = innerWidth - 6
	inputArea := styles.AIInput.Width(innerWidth).Render(m.aiInput.View())

	content := lipgloss.JoinVertical(lipgloss.Left,
		title,
		divider,
		vpView,
		inputArea,
	)

	return styles.AIPanelBorder.Width(innerWidth).Render(content)
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

func (m *Model) toggleMode() tea.Cmd {
	if m.mode == ModeTerminal {
		m.mode = ModeAI
		m.focusTerminal = false // AI input gets focus when opening the panel
		m.recalcTermHeight()
		m.vtState.Resize(m.width, m.termHeight)
		m.pty.Resize(m.width, m.termHeight)
		// Enable mouse capture for click-routing and viewport scrolling.
		return tea.Batch(m.aiInput.Focus(), tea.EnableMouseCellMotion)
	}
	m.mode = ModeTerminal
	m.focusTerminal = false
	m.recalcTermHeight()
	m.vtState.Resize(m.width, m.termHeight)
	m.pty.Resize(m.width, m.termHeight)
	m.aiInput.Blur()
	return tea.EnableMouseCellMotion
}

func (m *Model) recalcTermHeight() {
	if m.mode == ModeAI {
		m.termHeight = m.height - aiPanelHeight
	} else {
		m.termHeight = m.height
	}
	if m.termHeight < 4 {
		m.termHeight = 4
	}
}

func (m *Model) submitAI() tea.Cmd {
	content := strings.TrimSpace(m.aiInput.Value())
	if content == "" {
		return nil
	}
	if m.convID == "" {
		m.errMsg = "API not connected — run: gillie start"
		return nil
	}
	if m.streaming {
		return nil
	}
	m.aiInput.SetValue("")
	m.aiEntries = append(m.aiEntries, aiEntry{role: "user", content: content})
	m.aiEntries = append(m.aiEntries, aiEntry{role: "assistant", content: ""})
	m.streaming = true
	m.tokensIn += max(1, len(content)/4)
	m.refreshAIViewport()

	return openStream(m.apiClient, m.convID, content)
}

func (m *Model) appendToLastAssistant(text string) {
	for i := len(m.aiEntries) - 1; i >= 0; i-- {
		if m.aiEntries[i].role == "assistant" {
			m.aiEntries[i].content += text
			return
		}
	}
}

func (m *Model) refreshAIViewport() {
	var sb strings.Builder
	for i, e := range m.aiEntries {
		if i > 0 {
			sb.WriteString("\n")
		}
		switch e.role {
		case "user":
			sb.WriteString(styles.UserLabel.Render("You"))
			sb.WriteString("\n")
			sb.WriteString(styles.UserMsg.Render(e.content))
		case "assistant":
			c := e.content
			if m.streaming && c == "" {
				c = lipgloss.NewStyle().Foreground(styles.CAccent).Render("●")
			}
			sb.WriteString(styles.AssistantLabel.Render(m.assistant))
			sb.WriteString("\n")
			sb.WriteString(styles.AssistantMsg.Render(c))
		case "tool":
			sb.WriteString(styles.ToolMsg.Render(e.content))
		}
		sb.WriteString("\n")
	}
	m.aiViewport.SetContent(sb.String())
	m.aiViewport.GotoBottom()
}

// ─── Tea commands ─────────────────────────────────────────────────────────────

func waitForPtyOutput(ch <-chan gpty.OutputMsg) tea.Cmd {
	return func() tea.Msg {
		msg, ok := <-ch
		if !ok {
			return ptyExitMsg{}
		}
		return ptyOutputMsg(msg)
	}
}

// openStream establishes the HTTP SSE connection and returns the channel.
func openStream(client *api.Client, convID, content string) tea.Cmd {
	return func() tea.Msg {
		ch, err := client.StreamMessage(convID, content)
		if err != nil {
			return aiStreamErrMsg{err}
		}
		return aiStreamOpenMsg{ch: ch}
	}
}

// readNextToken reads one token from the open stream channel.
func readNextToken(ch <-chan api.StreamToken) tea.Cmd {
	if ch == nil {
		return nil
	}
	return func() tea.Msg {
		tok, ok := <-ch
		if !ok {
			return aiStreamDoneMsg{}
		}
		return aiTokenMsg(tok)
	}
}

// runPtyCommand runs a command in the active PTY, captures its output, and
// POSTs the result back to the API so the waiting LLM tool is unblocked.
func runPtyCommand(pty *gpty.Manager, client *api.Client, convID, requestID, command string) tea.Cmd {
	return func() tea.Msg {
		output, err := pty.RunAndCapture(command, 60*time.Second)
		if err != nil {
			// Still try to submit what we got so the LLM isn't blocked.
			_ = client.SubmitPtyResult(convID, requestID, output)
			return ptyResultMsg{requestID: requestID, output: output, err: err}
		}
		if submitErr := client.SubmitPtyResult(convID, requestID, output); submitErr != nil {
			return ptyResultMsg{requestID: requestID, output: output, err: submitErr}
		}
		return ptyResultMsg{requestID: requestID, output: output}
	}
}

