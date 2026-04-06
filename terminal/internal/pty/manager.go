package pty

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/creack/pty"
	"github.com/google/uuid"
)

// ansiEscape matches ANSI/VT escape sequences so we can strip them from
// captured output before returning it to the LLM.
var ansiEscape = regexp.MustCompile(`\x1b\[[0-9;]*[A-Za-z]|\x1b[^[]|\r`)

// OutputMsg carries raw bytes read from the PTY.
type OutputMsg []byte

// Manager wraps a PTY process and exposes read/write/resize.
type Manager struct {
	shell string
	ptmx  *os.File
	mu    sync.Mutex

	OutputCh chan OutputMsg // buffered — reader goroutine sends here
	ExitCh   chan struct{}  // closed when the process exits

	// Capture mode: when captureMode is true, readLoop also sends a copy of
	// all output to captureCh. Only one capture can be active at a time.
	captureMu   sync.Mutex
	captureMode bool
	captureCh   chan []byte
}

func NewManager(shell string) *Manager {
	return &Manager{
		shell:    shell,
		OutputCh: make(chan OutputMsg, 256),
		ExitCh:   make(chan struct{}),
	}
}

// Start spawns the shell in a PTY with the given initial size.
func (m *Manager) Start(cols, rows int) error {
	cmd := exec.Command(m.shell)
	cmd.Env = append(os.Environ(),
		"TERM=xterm-256color",
		"COLORTERM=truecolor",
	)

	ptmx, err := pty.StartWithSize(cmd, &pty.Winsize{
		Cols: uint16(cols),
		Rows: uint16(rows),
	})
	if err != nil {
		return err
	}

	m.mu.Lock()
	m.ptmx = ptmx
	m.mu.Unlock()

	go m.readLoop(cmd)
	return nil
}

func (m *Manager) readLoop(cmd *exec.Cmd) {
	defer close(m.ExitCh)
	defer close(m.OutputCh)

	buf := make([]byte, 4096)
	for {
		n, err := m.ptmx.Read(buf)
		if n > 0 {
			out := make([]byte, n)
			copy(out, buf[:n])
			m.OutputCh <- OutputMsg(out)

			// Also forward to capture channel when capture mode is active.
			m.captureMu.Lock()
			if m.captureMode && m.captureCh != nil {
				select {
				case m.captureCh <- out:
				default:
				}
			}
			m.captureMu.Unlock()
		}
		if err != nil {
			break
		}
	}
	_ = cmd.Wait()
}

// Write sends bytes to the PTY (keyboard input).
func (m *Manager) Write(data []byte) {
	m.mu.Lock()
	ptmx := m.ptmx
	m.mu.Unlock()

	if ptmx != nil {
		_, _ = ptmx.Write(data)
	}
}

// Resize notifies the PTY of a terminal size change.
func (m *Manager) Resize(cols, rows int) {
	m.mu.Lock()
	ptmx := m.ptmx
	m.mu.Unlock()

	if ptmx != nil {
		_ = pty.Setsize(ptmx, &pty.Winsize{
			Cols: uint16(cols),
			Rows: uint16(rows),
		})
	}
}

// Close terminates the PTY.
func (m *Manager) Close() {
	m.mu.Lock()
	ptmx := m.ptmx
	m.mu.Unlock()

	if ptmx != nil {
		_ = ptmx.Close()
	}
}

// RunAndCapture runs a command in the PTY and returns its output.
//
// Strategy:
//  1. Send "stty -echo" alone (user sees this one short line, then echo is off).
//  2. Wait 300 ms for it to execute on the remote.
//  3. Send the real command + re-enable echo + print the done marker in
//     ANSI concealed mode (\033[8m) so it is invisible in the terminal but
//     still detectable in the capture buffer.
func (m *Manager) RunAndCapture(command string, timeout time.Duration) (string, error) {
	doneMarker := "GTERM_DONE_" + uuid.New().String()

	ch := make(chan []byte, 512)
	m.captureMu.Lock()
	m.captureMode = true
	m.captureCh = ch
	m.captureMu.Unlock()
	defer func() {
		m.captureMu.Lock()
		m.captureMode = false
		m.captureCh = nil
		m.captureMu.Unlock()
	}()

	// Phase 1: disable remote echo.
	// This single short line is echoed once; after it executes the remote PTY
	// stops echoing subsequent input.
	m.Write([]byte("stty -echo 2>/dev/null\r"))
	time.Sleep(300 * time.Millisecond)

	// Phase 2: run command silently.
	// Leading space → HISTCONTROL=ignorespace skips it from shell history.
	// Done marker printed with SGR 8 (concealed) — invisible in terminal but
	// detectable in the raw capture buffer.
	m.Write([]byte(fmt.Sprintf(
		" %s; stty echo 2>/dev/null; printf '\\033[8m%s\\033[0m\\n'\r",
		command, doneMarker,
	)))

	var buf bytes.Buffer
	deadline := time.After(timeout)
	for {
		select {
		case chunk, ok := <-ch:
			if !ok {
				return cleanCapturedOutput(buf.String(), doneMarker),
					fmt.Errorf("PTY closed before command finished")
			}
			buf.Write(chunk)
			if bytes.Contains(buf.Bytes(), []byte(doneMarker)) {
				return cleanCapturedOutput(buf.String(), doneMarker), nil
			}
		case <-deadline:
			return cleanCapturedOutput(buf.String(), doneMarker),
				fmt.Errorf("PTY command timed out after %s", timeout)
		}
	}
}

// cleanCapturedOutput strips ANSI escape sequences, the echoed command line,
// and the sentinel line from captured PTY output.
func cleanCapturedOutput(raw, marker string) string {
	// Remove everything from the marker onwards.
	if i := strings.Index(raw, marker); i >= 0 {
		raw = raw[:i]
	}
	// Strip ANSI escape sequences.
	raw = ansiEscape.ReplaceAllString(raw, "")
	// Drop the first line (the echoed injected command).
	if i := strings.Index(raw, "\n"); i >= 0 {
		raw = raw[i+1:]
	}
	return strings.TrimSpace(raw)
}
