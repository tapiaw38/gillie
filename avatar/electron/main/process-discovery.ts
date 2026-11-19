import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const DEFAULT_VOICE_APP_PATTERN =
  /(?:^|[\\/\s._=-])(?:codex(?:-desktop)?|chatgpt|openai(?:-codex)?|gillie)(?=$|[\\/\s._=-])/i

export interface ProcessEntry {
  pid: number
  parentId: number
  name: string
  command: string
}

export interface VoiceProcessTree {
  pids: number[]
  rootPids: number[]
}

type ExecFileRunner = (
  file: string,
  args: readonly string[],
  options: Record<string, unknown>,
) => Promise<{ stdout: string }>

export function parseMacProcessList(output: string): ProcessEntry[] {
  return output
    .split(/\r?\n/)
    .map((line) => /^\s*(\d+)\s+(\d+)\s+(\S+)(?:\s+(.*))?$/.exec(line))
    .filter((match): match is RegExpExecArray => match != null)
    .map((match) => ({
      pid: Number(match[1]),
      parentId: Number(match[2]),
      name: match[3],
      command: match[4] ?? '',
    }))
}

export function parseWindowsProcessList(output: string): ProcessEntry[] {
  const trimmed = output.trim()
  if (!trimmed) return []
  const parsed = JSON.parse(trimmed)
  return (Array.isArray(parsed) ? parsed : [parsed])
    .map((entry: Record<string, unknown>) => ({
      pid: Number(entry.ProcessId),
      parentId: Number(entry.ParentProcessId),
      name: String(entry.Name ?? ''),
      command: String(entry.CommandLine ?? ''),
    }))
    .filter((entry) => Number.isInteger(entry.pid) && entry.pid > 0)
}

export function identityMatches(
  entry: ProcessEntry,
  pattern: RegExp = DEFAULT_VOICE_APP_PATTERN,
): boolean {
  pattern.lastIndex = 0
  return pattern.test(`${entry.name} ${entry.command}`)
}

export function selectVoiceProcessTree(
  processes: ProcessEntry[],
  {
    ownProcessId = process.pid,
    pattern = DEFAULT_VOICE_APP_PATTERN,
  }: { ownProcessId?: number; pattern?: RegExp } = {},
): VoiceProcessTree {
  const byId = new Map(processes.map((entry) => [entry.pid, entry]))
  const directlyMatched = new Set(
    processes
      .filter((entry) => entry.pid !== ownProcessId && identityMatches(entry, pattern))
      .map((entry) => entry.pid),
  )
  const matched = new Set<number>()

  for (const entry of processes) {
    let current: ProcessEntry | undefined = entry
    const visited = new Set<number>()
    for (let depth = 0; current && depth < 20; depth += 1) {
      if (visited.has(current.pid)) break
      visited.add(current.pid)
      if (directlyMatched.has(current.pid)) {
        matched.add(entry.pid)
        break
      }
      current = byId.get(current.parentId)
    }
  }

  const roots = [...directlyMatched]
    .filter((pid) => !directlyMatched.has(byId.get(pid)?.parentId ?? -1))
    .sort((left, right) => left - right)

  return {
    pids: [...matched].sort((left, right) => left - right),
    rootPids: roots,
  }
}

export function configuredPattern(
  environment: NodeJS.ProcessEnv = process.env,
): RegExp {
  const source = environment.AVATAR_TARGET_PROCESS_PATTERN
  if (!source) return DEFAULT_VOICE_APP_PATTERN
  try {
    return new RegExp(source, 'i')
  } catch {
    return DEFAULT_VOICE_APP_PATTERN
  }
}

export async function discoverVoiceProcesses({
  platform = process.platform,
  run = execFileAsync as unknown as ExecFileRunner,
  environment = process.env,
  ownProcessId = process.pid,
}: {
  platform?: NodeJS.Platform
  run?: ExecFileRunner
  environment?: NodeJS.ProcessEnv
  ownProcessId?: number
} = {}): Promise<VoiceProcessTree> {
  let processes: ProcessEntry[]
  if (platform === 'darwin') {
    const { stdout } = await run('ps', ['-axo', 'pid=,ppid=,comm=,args='], {
      encoding: 'utf8',
      maxBuffer: 4 * 1024 * 1024,
      timeout: 3_000,
    })
    processes = parseMacProcessList(stdout)
  } else if (platform === 'win32') {
    const command =
      'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress'
    const { stdout } = await run(
      'powershell.exe',
      ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', command],
      {
        encoding: 'utf8',
        maxBuffer: 8 * 1024 * 1024,
        timeout: 5_000,
        windowsHide: true,
      },
    )
    processes = parseWindowsProcessList(stdout)
  } else {
    return { pids: [], rootPids: [] }
  }

  return selectVoiceProcessTree(processes, {
    ownProcessId,
    pattern: configuredPattern(environment),
  })
}
