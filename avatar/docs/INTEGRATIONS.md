# Gillie Avatar integrations

Gillie Avatar accepts small state and level messages from local voice experiences.
The character renderer never needs raw audio, transcripts, prompts, credentials,
or host-application internals.

The bundled Codex and ChatGPT integration uses native process-scoped output
listeners because those applications do not currently expose a supported
cross-process realtime voice event stream. If an official event stream becomes
available, it can map to the same contract without changing Gillie Avatar's window or
animation system.

## Codex MCP server

Gillie Avatar serves a Streamable HTTP MCP endpoint while the app is running. Add it
to Codex once:

```bash
codex mcp add avatar --url http://127.0.0.1:47850/mcp
```

Start a new Codex session after registering the server. You can inspect the
saved connection with:

```bash
codex mcp get avatar
```

Gillie Avatar exposes these tools:

| Tool | Input | Effect |
| --- | --- | --- |
| `play_animation` | `animation`: one role declared by `public/assets/manifest.json` | Shows Gillie Avatar and plays an installed animation once |
| `control_window` | `action`: `show`, `hide`, or `toggle` | Controls the Gillie Avatar window without quitting the app |
| `get_status` | None | Reads window visibility, voice state, and listener status |

Animation names are read from `public/assets/manifest.json`, grouped by role,
rather than hardcoded file paths. Future character packs can add or replace
roles without changing MCP configuration or granting filesystem access.

An MCP-triggered animation temporarily takes priority over voice-driven body
motion. Lip sync continues while the clip plays. A newer MCP animation replaces
the current one; when the one-shot clip finishes, Gillie Avatar returns to the current
idle, listening, or speaking state.

The MCP endpoint uses the same port as the local HTTP API. If
`AVATAR_BRIDGE_PORT` changes it, update the URL registered with Codex to match.

## Automatic listeners

### Linux

Gillie Avatar polls the PipeWire graph for a Codex, ChatGPT, or Gillie playback node.
It attaches `pw-record` to that one stream, calculates RMS amplitude in memory,
and discards every sample after calculation. The stream remains connected to its
normal output device. `AVATAR_TARGET_PROCESS_PATTERN` retargets this node
search, exactly as it does for the Windows and macOS helpers.

### Windows

The native helper uses WASAPI application loopback with
`PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE`. Audio from other
applications is excluded. Gillie Avatar supports Windows 10 build 20348 and newer.

### macOS

The native helper creates a private, unmuted Core Audio process tap and private
aggregate device for the selected voice process. Gillie Avatar supports macOS 14.2
and newer and declares why it requests System Audio Recording permission.

Set `AVATAR_TARGET_PROCESS_PATTERN` to a case-insensitive regular expression
to target another desktop voice application:

```bash
AVATAR_TARGET_PROCESS_PATTERN='my-voice-app' avatar
```

## URL protocol

Installed packages register `avatar://`.

| URL | Effect |
| --- | --- |
| `avatar://show` | Show and focus Gillie Avatar |
| `avatar://hide` | Hide Gillie Avatar without quitting |
| `avatar://toggle` | Toggle visibility |
| `avatar://listening` | Begin a listening state |
| `avatar://thinking` | Settle the character while a response is prepared |
| `avatar://speaking?level=0.3` | Begin speaking and optionally set a level |
| `avatar://inactive` | End the voice state without hiding Gillie Avatar |
| `avatar://greeting` | Preview the greeting motion |
| `avatar://happy` | Preview the happy motion |
| `avatar://finger-gun` | Preview the finger-gun motion |
| `avatar://dance` | Preview a dance motion |

Open these URLs with `xdg-open` on Linux, `open` on macOS, or `start` on
Windows.

## Loopback HTTP API

Gillie Avatar listens on `127.0.0.1:47850` by default. Override the port with
`AVATAR_BRIDGE_PORT`. Native clients may omit `Origin`; browser clients are
restricted to trusted local and supported app origins. Requests with a
non-loopback `Host` are rejected.

Voice state:

```json
{
  "type": "state",
  "state": {
    "phase": "active",
    "activity": "speaking",
    "microphoneMuted": false,
    "outputMuted": false
  }
}
```

Allowed phases are `inactive`, `starting`, `active`, and `stopping`. Allowed
activities are `idle`, `listening`, and `speaking`.

Normalized level:

```json
{
  "type": "audio-level",
  "level": 0.31
}
```

Animation preview:

```json
{
  "type": "animation",
  "animation": "DANCE"
}
```

Allowed animation events are generated from roles in the asset manifest. `IDLE`
and `TALK` are automatic voice-driven states; deliberate gesture events come
from the remaining manifest roles.

Send events:

```bash
curl -H 'Content-Type: application/json' \
  --data '{"type":"state","state":{"phase":"active","activity":"speaking","microphoneMuted":false,"outputMuted":false}}' \
  http://127.0.0.1:47850/events
```

`GET /health` reports whether Gillie Avatar is running and returns the last state. It
does not expose user content.
