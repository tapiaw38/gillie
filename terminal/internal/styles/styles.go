package styles

import "github.com/charmbracelet/lipgloss"

// Palette
const (
	CBg       = lipgloss.Color("233")
	CBgPanel  = lipgloss.Color("234")
	CAccent   = lipgloss.Color("99")  // violet
	CCyan     = lipgloss.Color("81")  // cyan
	CGreen    = lipgloss.Color("82")  // green
	CAmber    = lipgloss.Color("214") // amber
	CRed      = lipgloss.Color("196") // red
	CText     = lipgloss.Color("252") // light grey
	CTextDim  = lipgloss.Color("242") // dim grey
	CBorder   = lipgloss.Color("238") // subtle border
	CBorderHL = lipgloss.Color("99")  // highlighted border (matches accent)
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
			Foreground(lipgloss.Color("0")).
			Bold(true).
			Padding(0, 1)

	ModeTerminalTail = lipgloss.NewStyle().
				Background(CBg).
				Foreground(CGreen)

	ModeAI = lipgloss.NewStyle().
		Background(CAccent).
		Foreground(lipgloss.Color("255")).
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
