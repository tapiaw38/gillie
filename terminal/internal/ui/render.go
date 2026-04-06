package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"github.com/hinshun/vt10x"
)

// Attr bit masks — vt10x keeps these unexported, so we mirror them here.
// Order matches the iota in vt10x/state.go.
const (
	attrReverse   int16 = 1 << 0
	attrUnderline int16 = 1 << 1
	attrBold      int16 = 1 << 2
	// attrGfx    int16 = 1 << 3  (not used for rendering)
	attrItalic  int16 = 1 << 4
	// attrBlink  int16 = 1 << 5  (lipgloss doesn't support it)
	// attrWrap   int16 = 1 << 6  (not used for rendering)
	attrConceal int16 = 1 << 7
)

// renderScreen converts the vt10x Terminal state into a lipgloss-rendered
// string ready to be placed in the bubbletea View.
func renderScreen(term vt10x.Terminal, width, height int) string {
	var sb strings.Builder

	term.Lock()
	defer term.Unlock()

	cursor := term.Cursor()

	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			glyph := term.Cell(x, y)
			// SGR 8 (concealed) — render as a plain space, invisible to the user
			// but the bytes are still in the PTY capture buffer for detection.
			if glyph.Mode&attrConceal != 0 {
				sb.WriteString(" ")
				continue
			}
			ch := string(glyph.Char)
			if ch == "" || glyph.Char == 0 {
				ch = " "
			}
			style := glyphStyle(glyph, x == cursor.X && y == cursor.Y)
			sb.WriteString(style.Render(ch))
		}
		if y < height-1 {
			sb.WriteString("\n")
		}
	}

	return sb.String()
}

// glyphStyle builds the lipgloss.Style for a single vt10x Glyph.
func glyphStyle(g vt10x.Glyph, isCursor bool) lipgloss.Style {
	s := lipgloss.NewStyle()

	fg := vtColor(g.FG)
	bg := vtColor(g.BG)

	if isCursor {
		fg, bg = bg, fg
		if fg == "" {
			fg = "0"
		}
		if bg == "" {
			bg = "7"
		}
	}

	if fg != "" {
		s = s.Foreground(lipgloss.Color(fg))
	}
	if bg != "" {
		s = s.Background(lipgloss.Color(bg))
	}

	if g.Mode&attrBold != 0 {
		s = s.Bold(true)
	}
	if g.Mode&attrUnderline != 0 {
		s = s.Underline(true)
	}
	if g.Mode&attrItalic != 0 {
		s = s.Italic(true)
	}
	if g.Mode&attrReverse != 0 && !isCursor {
		s = s.Reverse(true)
	}

	return s
}

// vtColor converts a vt10x.Color to a lipgloss color string.
// Returns "" for default/unset colors (vt10x stores them above 1<<24).
func vtColor(c vt10x.Color) string {
	if c >= vt10x.DefaultFG {
		return "" // default terminal color
	}
	return fmt.Sprintf("%d", uint32(c))
}
