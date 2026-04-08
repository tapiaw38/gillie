package styles

import "github.com/charmbracelet/lipgloss"

// Palette — Catppuccin Mocha
const (
	CBg       = lipgloss.Color("#1e1e2e") // Base
	CBgPanel  = lipgloss.Color("#181825") // Mantle
	CAccent   = lipgloss.Color("#cba6f7") // Mauve
	CCyan     = lipgloss.Color("#89dceb") // Sky
	CGreen    = lipgloss.Color("#a6e3a1") // Green
	CAmber    = lipgloss.Color("#fab387") // Peach
	CRed      = lipgloss.Color("#f38ba8") // Red
	CText     = lipgloss.Color("#cdd6f4") // Text
	CTextDim  = lipgloss.Color("#6c7086") // Overlay0
	CBorder   = lipgloss.Color("#45475a") // Surface1
	CBorderHL = lipgloss.Color("#cba6f7") // Mauve
)

var (
	// ─── Status bar ───────────────────────────────────────────────────────────

	StatusBar = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CText)

	StatusName = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CCyan).
			Bold(true)

	StatusDim = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CTextDim)

	StatusHint = lipgloss.NewStyle().
			Background(CBg).
			Foreground(lipgloss.Color("240"))

	StatusSep = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CBorder)

	// ─── Mode pills ───────────────────────────────────────────────────────────

	ModeTerminal = lipgloss.NewStyle().
			Background(CGreen).
			Foreground(lipgloss.Color("#1e1e2e")).
			Bold(true).
			Padding(0, 1)

	ModeTerminalTail = lipgloss.NewStyle().
				Background(CBg).
				Foreground(CGreen)

	ModeAI = lipgloss.NewStyle().
		Background(CAccent).
		Foreground(lipgloss.Color("#1e1e2e")).
		Bold(true).
		Padding(0, 1)

	ModeAITail = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CAccent)

	// ─── AI panel ─────────────────────────────────────────────────────────────
	// No Background on panel content — lipgloss ends every Render() with
	// \x1b[m (full reset), which also resets the background, leaving empty
	// cells at terminal-default color. We rely on the rounded border for
	// visual separation instead of fighting ANSI resets.

	AIPanelBorder = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(CBorderHL)

	AIPanelTitle = lipgloss.NewStyle().
			Foreground(CAccent).
			Bold(true)

	AIPanelHint = lipgloss.NewStyle().
			Foreground(CTextDim)

	AIPanelDivider = lipgloss.NewStyle().
			Foreground(CBorder)

	// ─── Messages ─────────────────────────────────────────────────────────────

	UserLabel = lipgloss.NewStyle().
			Foreground(CCyan).
			Bold(true)

	UserMsg = lipgloss.NewStyle().
		Foreground(CText).
		PaddingLeft(2)

	AssistantLabel = lipgloss.NewStyle().
			Foreground(CAccent).
			Bold(true)

	AssistantMsg = lipgloss.NewStyle().
			Foreground(CText).
			PaddingLeft(2)

	ToolMsg = lipgloss.NewStyle().
		Foreground(CAmber).
		PaddingLeft(2).
		Italic(true)

	ToolResult = lipgloss.NewStyle().
			Foreground(CTextDim).
			PaddingLeft(2)

	// ─── Input ────────────────────────────────────────────────────────────────

	AIInput = lipgloss.NewStyle().
		Border(lipgloss.NormalBorder(), true, false, false, false).
		BorderForeground(CBorderHL).
		PaddingLeft(1)

	// ─── Misc ─────────────────────────────────────────────────────────────────

	ErrorMsg = lipgloss.NewStyle().
			Background(CBg).
			Foreground(CRed)

	Cursor = lipgloss.NewStyle().
		Reverse(true)
)
