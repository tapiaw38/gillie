# Gillie Avatar

Realtime character presence for Gillie voice sessions: a transparent, always-on-top
Electron overlay that renders a VRM character, lip-syncs it to whatever the voice app is
playing, and exposes an MCP server so the assistant can drive its own body.

Built with Vue 3, TypeScript, three.js and electron-vite, following the same layout as
the `ui` app in this repository.

## Commands

```bash
npm install
npm run dev           # electron-vite dev (main + preload + renderer)
npm run build         # bundle into out/
npm test              # vitest suite plus the build-script tests
npm run type-check    # vue-tsc --build
npm run lint
npm run assets:check  # verify the character asset contract
npm run dist:linux    # package (see also dist:windows, dist:mac)
```

## Layout

```
electron/
  main/        Main process: window, tray, protocol handler, HTTP bridge, MCP server,
               and the platform audio listeners (PipeWire on Linux, native helper on
               macOS/Windows).
  preload/     Sandboxed CommonJS preload exposing window.avatarBridge.
src/
  avatar/      Framework-free three.js layer: VRM loading, animation mixer, procedural
               motion, lip sync, blink, camera framing, and the render stage.
  components/  AvatarStage.vue, the canvas the stage draws into.
  composables/ useAvatarBridge, which turns bridge events into the body animation.
  types/       Shared renderer-side bridge types.
public/assets/ model.vrm plus the .vrma animation clips.
native/        C++/Objective-C audio listener helpers (built by scripts/build-native.cjs).
scripts/       Asset contract, native build, packaging, and release helpers.
```

## Integration surface

The main process listens on `127.0.0.1:47850` (override with `AVATAR_BRIDGE_PORT`):

- `POST /events` accepts `state`, `audio-level`, and `animation` events.
- `POST /mcp` is a Streamable HTTP MCP endpoint exposing `play_animation`,
  `control_window`, `get_status`, `set_voice_state`, and `set_audio_level`.
- `GET /health` reports liveness plus the last voice state.

The `avatar://` URL scheme is also handled (`avatar://show`, `avatar://speaking?level=0.4`,
`avatar://dance`, and so on). Set `AVATAR_DEBUG=1` for verbose listener logging and
`AVATAR_TARGET_PROCESS_PATTERN` to change which application's audio is followed.

Environment lighting is generated at runtime with three.js `RoomEnvironment`, so no HDRI
file is fetched or shipped.

## Character assets

`public/assets/model.vrm` and the clips under `public/assets/animations/` are local media
and are ignored by Git. See `ASSET_LICENSES.md` before distributing any build that
contains them.

## License

MIT, Copyright (c) 2026 tapiaw38. See `LICENSE`.
