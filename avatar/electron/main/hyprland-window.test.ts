import assert from 'node:assert/strict'
import { test } from 'vitest'
import {
  buildLuaCommands,
  calculateWindowPosition,
  findHyprlandClient,
  type HyprlandMonitor,
} from './hyprland-window'

const MONITOR: HyprlandMonitor = {
  id: 0,
  x: 0,
  y: 0,
  width: 1920,
  height: 1080,
  reserved: [0, 34, 0, 0],
}

test('findHyprlandClient matches the app class and process', () => {
  const clients = [
    { class: 'gillie-avatar', pid: 42, address: '0xabc' },
    { class: 'gillie-avatar', pid: 77, address: '0xdef' },
  ]

  assert.equal(findHyprlandClient(clients, 77)?.address, '0xdef')
  assert.equal(findHyprlandClient(clients, 99), undefined)
})

test('calculateWindowPosition uses the monitor work area', () => {
  assert.deepEqual(calculateWindowPosition(MONITOR, 430, 680, 24), {
    x: 1466,
    y: 376,
  })
})

test('buildLuaCommands enables stable floating and pinned properties', () => {
  const commands = buildLuaCommands(
    {
      address: '0xabc',
      pid: 42,
      floating: false,
      pinned: false,
      size: [1904, 1030],
    },
    MONITOR,
    430,
    680,
  ).join('\n')

  assert.match(commands, /float\(\{ action = "on"/)
  assert.match(commands, /resize\(\{ x = 430, y = 680/)
  assert.match(commands, /move\(\{ x = 1466, y = 376/)
  assert.match(commands, /pin\(\{ action = "on"/)
  assert.match(commands, /alter_zorder/)
  assert.match(commands, /prop = "no_blur"/)
  assert.match(commands, /prop = "decorate"/)
  assert.match(commands, /prop = "opacity", value = "1"/)
  assert.match(commands, /prop = "opacity_inactive_override", value = "1"/)
  assert.match(commands, /prop = "opacity_fullscreen_override", value = "1"/)
})

test('buildLuaCommands can refresh compositor properties without moving the window', () => {
  const commands = buildLuaCommands(
    {
      address: '0xabc',
      pid: 42,
      floating: true,
      pinned: true,
      size: [430, 680],
    },
    MONITOR,
    430,
    680,
    24,
    { reposition: false },
  ).join('\n')

  assert.doesNotMatch(commands, /window\.move/)
  assert.doesNotMatch(commands, /window\.pin/)
  assert.match(commands, /alter_zorder/)
  assert.match(commands, /prop = "no_blur"/)
  assert.match(commands, /prop = "opacity_override", value = "1"/)
})

test('buildLuaCommands restores an explicitly saved position', () => {
  const commands = buildLuaCommands(
    {
      address: '0xabc',
      pid: 42,
      floating: true,
      pinned: true,
      size: [430, 680],
    },
    MONITOR,
    430,
    680,
    24,
    { position: { x: 321, y: 234 }, reposition: true },
  ).join('\n')

  assert.match(commands, /window\.move\(\{ x = 321, y = 234/)
})
