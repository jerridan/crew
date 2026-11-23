// Tests of the board pane mod (hooks/orch-board.tsx), spec #155 R5 to R13
// and R16. Every test stubs the board command and the launcher with a
// `process.run` hook beneath the plugin: no test runs crew-orch.py or
// launcher.py, and none opens a terminal tab.
import type { On } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

import FIXTURE from './fixtures/board-json'
import FIXTURE_TEXT from './fixtures/board-text'

const PLUGIN = 'crew'
const PANE_ID = 'orch-board'
const BOARD_PY = '/skills/orchestrator/scripts/crew-orch.py'
const LAUNCHER_PY = '/skills/orchestrator/scripts/launcher.py'
const NOW = Date.parse('2026-11-16T12:00:00Z')
const SURFACES = ['terminal', 'desktop'] as const

type Json = ReturnType<typeof JSON.parse>
type Run = { exitCode: number; stdout: string; stderr: string }

const clone = (value: unknown): Json => JSON.parse(JSON.stringify(value))

// ---------------------------------------------------------------- board data

const row = (n: number, id: string, extra: object = {}) => ({
  n,
  id,
  marks: '●●◐○○',
  status: 'build',
  pr: null,
  ticket: null,
  text: '',
  age: '',
  launch_tab: null,
  ...extra,
})

const group = (id: string, title: string, rows: unknown[], extra: object = {}) => ({
  kind: 'group',
  id,
  title,
  ticket: null,
  repo: null,
  merged: 0,
  total: rows.length,
  rows,
  ...extra,
})

const singles = (rows: unknown[]) => ({
  kind: 'single',
  id: null,
  title: 'Single items',
  ticket: null,
  repo: null,
  merged: null,
  total: null,
  rows,
})

const entry = (id: string, extra: object = {}) => ({
  id,
  kind: 'question',
  age: '5m',
  item: '-',
  item_id: null,
  text: `text of ${id}`,
  recommend: null,
  ...extra,
})

const board = (extra: object = {}) => ({
  version: 1,
  orch: 'x',
  plan: null,
  needs_you: { count: 0, entries: [] as unknown[] },
  sections: [] as unknown[],
  done: 0,
  legend: 'spec → split → build → review → PR',
  ...extra,
})

const needs = (...entries: unknown[]) => ({ count: entries.length, entries })

// ---------------------------------------------------------------- the world

type World = {
  board: string[][]
  launcher: string[][]
  other: string[][]
  toasts: string[]
  writes: string[]
  reads: string[]
  opens: unknown[]
  open: { value: boolean }
  clock: ReturnType<typeof mock.clock>
}

// Stands for the engine beneath the plugin. `boards` answers each run of the
// board command in turn, and repeats its last answer.
const world = (
  on: On,
  boards: (Json | Run)[],
  options: {
    env?: Record<string, string>
    launcher?: Run
    // Holds a run of either command until the promise it returns settles.
    hold?: (argv: string[]) => Promise<void> | undefined
  } = {},
): World => {
  const w: World = {
    board: [],
    launcher: [],
    other: [],
    toasts: [],
    writes: [],
    reads: [],
    opens: [],
    open: { value: true },
    clock: mock.clock(on, { now: NOW }),
  }
  mock.env(on, options.env ?? {})
  on('process.run', async (_, e) => {
    const argv = [...e.argv]
    if (argv[0] === 'python3' && argv[1]?.endsWith(BOARD_PY)) {
      w.board.push(argv)
      const next = boards[Math.min(w.board.length, boards.length) - 1]
      await options.hold?.(argv)
      const run =
        next && typeof next === 'object' && 'exitCode' in next
          ? (next as Run)
          : { exitCode: 0, stdout: JSON.stringify(next), stderr: '' }
      return { value: { ...run, isStdoutTruncated: false, isStderrTruncated: false } }
    }
    if (argv[0] === 'python3' && argv[1]?.endsWith(LAUNCHER_PY)) {
      w.launcher.push(argv)
      await options.hold?.(argv)
      const run = options.launcher ?? { exitCode: 0, stdout: '', stderr: '' }
      return { value: { ...run, isStdoutTruncated: false, isStderrTruncated: false } }
    }
    w.other.push(argv)
    return { deny: `no stub for ${argv.join(' ')}` }
  })
  on('ui.toast', (_, e) => {
    w.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.open', (_, e) => {
    w.opens.push(e)
    w.open.value = true
    return { value: { isPlaced: true } }
  })
  on('ui.panes', () => ({
    value: w.open.value
      ? [{ id: PANE_ID, title: 'Board', isShown: true, isFocused: true, isPlaced: true }]
      : [],
  }))
  on('fs.write', (_, e) => {
    w.writes.push(e.path)
    return { deny: 'the pane must not write' }
  })
  const noRead = (what: string) => {
    w.reads.push(what)
    return { deny: 'the pane must not read a record file' }
  }
  on('fs.read', (_, e) => noRead(`read ${e.path}`))
  on('fs.stat', (_, e) => noRead(`stat ${e.path}`))
  on('fs.exists', (_, e) => noRead(`exists ${e.path}`))
  on('fs.list', (_, e) => noRead(`list ${String(e.path)}`))
  on('command.register', () => ({ value: { command: 'orch-board' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  return w
}

const start = async ($: Json) =>
  $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })

const command = async ($: Json, args = '') => {
  await start($)
  return $.command.run({
    command: 'orch-board',
    args,
    presentation: { isFullscreen: true, columns: 200 },
  } as never)
}

const pane = (columns = 200, bodyRows = 80) => ({
  plugin: PLUGIN,
  component: 'Pane',
  requestId: PANE_ID,
  props: {
    title: 'Board',
    isFocused: true,
    bodyColumns: columns,
    placement: 'dock',
    scroll: { offset: 0, bodyRows },
    view: {},
  },
}) as const

const mount = ($: Json, surface: (typeof SURFACES)[number] = 'terminal', columns = 200, bodyRows = 80) =>
  $.ui.mount({ ...pane(columns, bodyRows), surface })

// ---------------------------------------------------------------- tree reads

type Node = { type?: string; props?: Record<string, unknown>; children?: unknown[] }

// The shown text of a node: its strings, in document order.
const words = (node: unknown): string => {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(words).join('')
  const n = node as Node
  return words(n.children)
}

// Every key in the tree, in document order.
const keys = (node: unknown, out: string[] = []): string[] => {
  if (node == null || typeof node !== 'object') return out
  if (Array.isArray(node)) {
    for (const child of node) keys(child, out)
    return out
  }
  const n = node as Node
  if (typeof n.props?.key === 'string') out.push(n.props.key)
  keys(n.children, out)
  return out
}

// The elements of a type, in document order.
const all = (node: unknown, type: string, out: Node[] = []): Node[] => {
  if (node == null || typeof node !== 'object') return out
  if (Array.isArray(node)) {
    for (const child of node) all(child, type, out)
    return out
  }
  const n = node as Node
  if (n.type === type) out.push(n)
  all(n.children, type, out)
  return out
}

// The element with a key.
const byKey = (node: unknown, key: string): Node | undefined => {
  if (node == null || typeof node !== 'object') return undefined
  if (Array.isArray(node)) {
    for (const child of node) {
      const got = byKey(child, key)
      if (got) return got
    }
    return undefined
  }
  const n = node as Node
  if (n.props?.key === key) return n
  return byKey(n.children, key)
}

// The cells of a row: each child's shown text.
const cells = (node: Node | undefined) =>
  (node?.children ?? []).map(child => words(child)).map(text => text.trim())

// The cell widths of a row.
const widths = (node: Node | undefined) =>
  (node?.children ?? []).map(child => Number((child as Node).props?.width ?? 0))

const before = (list: string[], a: string, b: string) => {
  expect(list.indexOf(a), `${a} is drawn`).toBeGreaterThanOrEqual(0)
  expect(list.indexOf(b), `${b} is drawn`).toBeGreaterThan(list.indexOf(a))
}

// ---------------------------------------------------------------- R13

test('R13 /orch-board x runs the board command with --orch x', async ($, on) => {
  const w = world(on, [board()])
  await command($, 'x')
  expect(w.board).toHaveLength(1)
  expect(w.board[0]?.slice(2)).toEqual(['--orch', 'x', 'board', '--json'])
  expect(w.board[0]?.[1] ?? '').toEndWith(BOARD_PY)
  expect(w.opens).toHaveLength(1)
})

test('R13 a read for x that ends after /orch-board y does not draw x under y', async ($, on) => {
  const g = gate()
  const forX = board({ sections: [singles([row(1, 'from-x')])] })
  const forY = board({ sections: [singles([row(1, 'from-y')])] })
  const w = world(on, [forX, forY], { hold: argv => (argv.includes('x') ? g.promise : undefined) })
  await start($)
  const first = runCommand($, 'x')
  await until(() => w.board.length === 1)
  await runCommand($, 'y')
  g.open()
  await first
  const ui = await mount($)
  const text = words(await ui.drawn())
  expect(text).toContain('from-y')
  expect(text).not.toContain('from-x')
  await ui.unmount()
})

test('R13 with no argument the name comes from CREW_ORCH', async ($, on) => {
  const w = world(on, [board()], { env: { CREW_ORCH: 'y' } })
  await command($, '')
  expect(w.board.map(argv => argv.slice(2))).toEqual([['--orch', 'y', 'board', '--json']])
})

test('R13 with no argument and no CREW_ORCH the pane says the name is missing and runs nothing', async ($, on) => {
  const w = world(on, [board()])
  await command($, '')
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    expect(words(await ui.drawn())).toMatch(/no orchestrator name/i)
    await ui.unmount()
  }
  await w.clock.advance(20_000)
  expect(w.board).toHaveLength(0)
  expect(w.launcher).toHaveLength(0)
})

// ---------------------------------------------------------------- R5

test('R5 the pane draws the values and the order the JSON gives', async ($, on) => {
  const data = board({
    sections: [
      group('g', 'Group', [
        row(3, 'gamma', { status: 'custom word' }),
        row(1, 'alpha', { status: 'another word' }),
        row(2, 'beta'),
      ]),
    ],
  })
  const w = world(on, [data])
  await command($, 'x')
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    const tree = await ui.drawn()
    const rows = keys(tree).filter(k => k.startsWith('row-'))
    expect(rows).toEqual(['row-3', 'row-1', 'row-2'])
    expect(cells(byKey(tree, 'row-3'))).toContain('custom word')
    expect(cells(byKey(tree, 'row-1'))).toContain('another word')
    await ui.unmount()
  }
  // The board command is the one command the pane runs.
  expect(w.other).toHaveLength(0)
  for (const argv of w.board) expect(argv.slice(2)).toEqual(['--orch', 'x', 'board', '--json'])
})

test('R5 a board version the pane does not know shows one line and no rows', async ($, on) => {
  world(on, [board({ version: 2, sections: [singles([row(1, 'alpha')])] })])
  await command($, 'x')
  const ui = await mount($)
  const tree = await ui.drawn()
  expect(words(tree)).toMatch(/version 2/)
  expect(keys(tree).filter(k => k.startsWith('row-'))).toHaveLength(0)
  await ui.unmount()
})

test('R5 a failed board command shows its exit code', async ($, on) => {
  world(on, [{ exitCode: 1, stdout: '', stderr: "crew-orch: no orchestrator record 'x'" }])
  await command($, 'x')
  const ui = await mount($)
  const text = words(await ui.drawn())
  expect(text).toContain('exited 1')
  expect(text).toContain("no orchestrator record 'x'")
  await ui.unmount()
})

// ---------------------------------------------------------------- R6

test('R6 the pane reads the board again every 5 s, and stops when it closes', async ($, on) => {
  const a = board({ sections: [singles([row(1, 'alpha', { text: 'doing', age: '40s' })])] })
  const b = board({ sections: [singles([row(1, 'alpha', { text: 'doing', age: '45s' })])] })
  const w = world(on, [a, b])
  await command($, 'x')
  const ui = await mount($)
  expect(cells(byKey(await ui.drawn(), 'row-1'))).toContain('40s')
  await w.clock.advance(4_999)
  expect(w.board).toHaveLength(1)
  await w.clock.advance(1)
  expect(w.board).toHaveLength(2)
  expect(cells(byKey(await ui.drawn(), 'row-1'))).toContain('45s')
  // The pane reads no record file: the board command is its one source.
  expect(w.reads).toEqual([])
  // The pane closes: the timer runs the command no more.
  w.open.value = false
  await w.clock.advance(5_000)
  const runs = w.board.length
  await w.clock.advance(30_000)
  expect(w.board).toHaveLength(runs)
  expect(runs).toBeLessThanOrEqual(2)
  await ui.unmount()
})

// ---------------------------------------------------------------- R7

const LAYOUT = board({
  plan: {
    windows: [
      { key: 'five_hour', label: '5h', used_pct: 68, meter: '███████░░░', resets: '1:30 PM', full_at: '12:50 PM' },
      { key: 'seven_day', label: '7d', used_pct: 31, meter: '███░░░░░░░', resets: 'Thu', full_at: '' },
    ],
    word: 'SLOWED: 2 of 3 slots',
  },
  needs_you: needs(
    entry('d1', { kind: 'decision', recommend: 'take the editor' }),
    entry('q2', { item: 'g1/beta', item_id: 'beta' }),
  ),
  sections: [
    group('g1', 'First group', [row(1, 'alpha'), row(2, 'beta')]),
    group('g2', 'Second group', [row(3, 'gamma')]),
    singles([row(5, 'eps'), row(4, 'delta')]),
  ],
  done: 2,
})

test('R7 the sections and rows show in the order of the data', async ($, on) => {
  world(on, [LAYOUT])
  await command($, 'x')
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    const tree = await ui.drawn()
    const order = keys(tree)
    const want = [
      'plan-five_hour',
      'plan-seven_day',
      'needs',
      'need-d1',
      'recommend-d1',
      'need-q2',
      'group-g1',
      'row-1',
      'row-2',
      'group-g2',
      'row-3',
      'singles',
      'row-5',
      'row-4',
      'footer',
    ]
    want.slice(1).forEach((key, i) => before(order, want[i] ?? '', key))
    expect(words(byKey(tree, 'needs'))).toContain('Needs you 2')
    expect(words(byKey(tree, 'recommend-d1'))).toContain('Recommended: take the editor')
    expect(byKey(tree, 'recommend-q2')).toBeUndefined()
    expect(words(byKey(tree, 'plan-five_hour'))).toContain('SLOWED: 2 of 3 slots')
    expect(words(byKey(tree, 'plan-five_hour'))).toContain('███████░░░')
    const footer = words(byKey(tree, 'footer'))
    expect(footer).toContain('Done 2')
    expect(footer).toContain('type a number and Enter to go to the tab')
    expect(footer).toContain('spec → split → build → review → PR')
    await ui.unmount()
  }
})

test('R7 with plan null the pane has no Plan line and no meter', async ($, on) => {
  world(on, [{ ...LAYOUT, plan: null }])
  await command($, 'x')
  const ui = await mount($)
  const text = words(await ui.drawn())
  expect(text).not.toContain('Plan')
  expect(text).not.toMatch(/[█░]/)
  await ui.unmount()
})

test('R7 with no usage windows the pane shows the pace word and no meter', async ($, on) => {
  world(on, [{ ...LAYOUT, plan: { windows: [], word: 'STOPPED' } }])
  await command($, 'x')
  const ui = await mount($)
  const text = words(await ui.drawn())
  expect(text).toContain('STOPPED')
  expect(text).not.toMatch(/[█░]/)
  await ui.unmount()
})

// ---------------------------------------------------------------- R8

test('R8 a PR and a ticket with a URL are links, a ticket with no URL is plain text', async ($, on) => {
  const data = board({
    sections: [
      group('g', 'Group', [row(1, 'alpha', { pr: { number: 7, label: '#7', url: 'https://github.com/o/r/pull/7' } })], {
        ticket: { id: 'GRP-1', url: 'https://linear.example/GRP-1' },
      }),
      singles([
        row(2, 'beta', { ticket: { id: 'o/r#12', url: 'https://github.com/o/r/issues/12' } }),
        row(3, 'gamma', { ticket: { id: 'PLAIN-3', url: null } }),
      ]),
    ],
  })
  world(on, [data])
  await command($, 'x')
  for (const surface of SURFACES) {
    const ui = await mount($, surface)
    const tree = await ui.drawn()
    const links = all(tree, 'Link').map(l => [words(l), l.props?.href])
    expect(links).toContainEqual(['#7', 'https://github.com/o/r/pull/7'])
    expect(links).toContainEqual(['GRP-1', 'https://linear.example/GRP-1'])
    expect(links).toContainEqual(['o/r#12', 'https://github.com/o/r/issues/12'])
    expect(links.map(l => l[0])).not.toContain('PLAIN-3')
    expect(cells(byKey(tree, 'row-3'))).toContain('PLAIN-3')
    await ui.unmount()
  }
})

// ---------------------------------------------------------------- R9

const FOCUS = board({
  sections: [
    singles([
      row(1, 'alpha', { launch_tab: null }),
      row(2, 'beta', { launch_tab: 'H2' }),
      row(3, 'gamma', { launch_tab: 'H' }),
      row(12, 'twelve', { launch_tab: 'H12' }),
    ]),
  ],
})

test('R9 a row number and Enter runs launcher.py focus with the row handle', async ($, on) => {
  const w = world(on, [FOCUS])
  await command($, 'x')
  const ui = await mount($)
  await ui.input({ key: 'go', text: '3' })
  expect(w.launcher).toHaveLength(1)
  expect(w.launcher[0]?.[1] ?? '').toEndWith(LAUNCHER_PY)
  expect(w.launcher[0]?.slice(2)).toEqual(['focus', 'H'])
  await ui.input({ key: 'go', text: '12' })
  expect(w.launcher[1]?.slice(2)).toEqual(['focus', 'H12'])
  await ui.unmount()
})

test('R9 a row with no tab runs nothing and says so', async ($, on) => {
  const w = world(on, [FOCUS])
  await command($, 'x')
  const ui = await mount($)
  await ui.input({ key: 'go', text: '1' })
  expect(w.launcher).toHaveLength(0)
  expect(words(byKey(await ui.drawn(), 'line'))).toMatch(/row 1 .*has no tab/i)
  await ui.unmount()
})

test('R9 a number that no row has runs nothing and shows one line', async ($, on) => {
  const w = world(on, [FOCUS])
  await command($, 'x')
  const ui = await mount($)
  await ui.input({ key: 'go', text: '7' })
  expect(w.launcher).toHaveLength(0)
  expect(words(byKey(await ui.drawn(), 'line'))).toMatch(/no row 7/i)
  await ui.unmount()
})

test('R9 a non-zero exit of the launcher shows its exit code', async ($, on) => {
  const w = world(on, [FOCUS], { launcher: { exitCode: 3, stdout: '', stderr: 'launcher: no such tab' } })
  await command($, 'x')
  const ui = await mount($)
  await ui.input({ key: 'go', text: '2' })
  expect(w.launcher).toHaveLength(1)
  const line = words(byKey(await ui.drawn(), 'line'))
  expect(line).toContain('exited 3')
  await ui.unmount()
})

test('R9 focus exit 7 makes one launcher call and shows the exit code and the stderr text', async ($, on) => {
  const w = world(on, [FOCUS], { launcher: { exitCode: 7, stdout: '', stderr: 'launcher: no tmux pane %7\n' } })
  await command($, 'x')
  const ui = await mount($)
  await ui.input({ key: 'go', text: '2' })
  expect(w.launcher).toHaveLength(1)
  const line = words(byKey(await ui.drawn(), 'line'))
  expect(line).toContain('exited 7')
  expect(line).toContain('launcher: no tmux pane %7')
  await ui.unmount()
})

// A promise and the function that settles it.
const gate = () => {
  let open = () => {}
  const promise = new Promise<void>(resolve => {
    open = resolve
  })
  return { promise, open }
}

// Wait until a condition holds, a bounded number of turns.
const until = async (ok: () => boolean) => {
  for (let i = 0; i < 1000 && !ok(); i++) await new Promise(r => setTimeout(r, 0))
  expect(ok()).toBe(true)
}

const runCommand = ($: Json, args: string) =>
  $.command.run({ command: 'orch-board', args, presentation: { isFullscreen: true, columns: 200 } } as never)

test('R9 a focus result that ends after /orch-board y shows no line under y', async ($, on) => {
  const g = gate()
  const w = world(on, [FOCUS], { hold: argv => (argv.includes('focus') ? g.promise : undefined) })
  await command($, 'x')
  const ui = await mount($)
  const typed = ui.input({ key: 'go', text: '2' })
  await until(() => w.launcher.length === 1)
  await runCommand($, 'y')
  g.open()
  await typed
  expect(byKey(await ui.drawn(), 'line')).toBeUndefined()
  await ui.unmount()
})

// ---------------------------------------------------------------- R10

const withNeeds = (...ids: string[]) => board({ needs_you: needs(...ids.map(id => entry(id))) })

test('R10 a new Needs-you entry shows one toast, once', async ($, on) => {
  const w = world(on, [withNeeds('d1', 'q2'), withNeeds('d1', 'q2', 'q3'), withNeeds('d1', 'q2', 'q3')])
  await command($, 'x')
  expect(w.toasts).toEqual([])
  await w.clock.advance(5_000)
  expect(w.toasts).toHaveLength(1)
  expect(w.toasts[0]).toContain('q3')
  await w.clock.advance(5_000)
  expect(w.board).toHaveLength(3)
  expect(w.toasts).toHaveLength(1)
})

// What the pane kept in $.state before a reload of the mod: a host store
// that starts with that value, read and written through the state events.
const kept = (on: On, seen: string[]) => {
  let held = {
    value: {
      shape: 'orch-board-1',
      value: { name: 'x', board: withNeeds(...seen), error: null, line: null, seen, primed: true },
    } as unknown,
    version: 4,
  }
  on('state.get', () => ({ value: held }))
  on('state.set', (_, e) => {
    const ifVersion = (e as { ifVersion?: number }).ifVersion
    if (ifVersion !== undefined && ifVersion !== held.version) {
      return { value: { isSet: false, version: held.version } }
    }
    held = { value: e.value, version: held.version + 1 }
    return { value: { isSet: true, version: held.version } }
  })
}

test('R10 after a reload the pane does not toast an id it already toasted', async ($, on) => {
  const w = world(on, [withNeeds('d1', 'q2', 'q3')])
  kept(on, ['d1', 'q2', 'q3'])
  const ui = await mount($)
  await w.clock.advance(5_000)
  expect(w.board.length).toBeGreaterThanOrEqual(1)
  expect(w.toasts).toEqual([])
  await ui.unmount()
})

test('R10 after a reload the pane toasts an id it has not seen', async ($, on) => {
  const w = world(on, [withNeeds('d1', 'q2', 'q3', 'q4')])
  kept(on, ['d1', 'q2', 'q3'])
  const ui = await mount($)
  await w.clock.advance(5_000)
  expect(w.toasts).toHaveLength(1)
  expect(w.toasts[0]).toContain('q4')
  await ui.unmount()
})

// ---------------------------------------------------------------- R11

// The breakpoint: below 60 columns the pane drops the marks, the ticket and
// the age columns. At any width the row text truncates first.
for (const columns of [40, 60]) {
  test(`R11 at ${columns} columns each row is one line with its n, id, status and PR`, async ($, on) => {
    world(on, [FIXTURE])
    await command($, 'x')
    const ui = await mount($, 'terminal', columns)
    const tree = await ui.drawn()
    for (const section of FIXTURE.sections) {
      for (const r of section.rows as Json[]) {
        const node = byKey(tree, `row-${r.n}`)
        const got = cells(node)
        const sizes = widths(node)
        const gap = Number(node?.props?.gap ?? 0)
        const indent = Number(node?.props?.paddingLeft ?? 0)
        // One line: the cells fit the width, and no cell holds more than its width.
        expect(indent + sizes.reduce((s, x) => s + x, 0) + gap * (sizes.length - 1)).toBeLessThanOrEqual(columns)
        got.forEach((text, i) => expect(text.length).toBeLessThanOrEqual(sizes[i] ?? 0))
        expect(got).toContain(String(r.n))
        expect(got).toContain(r.id)
        expect(got).toContain(r.status)
        if (r.pr) expect(got).toContain(r.pr.label)
        if (r.text.length > 0 && columns === 40) expect(got.join(' ')).not.toContain(r.text)
        if (columns < 60) expect(got).not.toContain(r.marks)
      }
    }
    await ui.unmount()
  })
}

// A row's width: its indent, its cells and the gaps between them.
const rowWidth = (node: Node | undefined) => {
  const sizes = widths(node)
  const gap = Number(node?.props?.gap ?? 0)
  const indent = Number(node?.props?.paddingLeft ?? 0)
  return indent + sizes.reduce((s, x) => s + x, 0) + gap * (sizes.length - 1)
}

test('R11 at 80 columns the row text truncates before the single-item ticket', async ($, on) => {
  world(on, [FIXTURE])
  await command($, 'x')
  const ui = await mount($, 'terminal', 80)
  const tree = await ui.drawn()
  const loner = (FIXTURE.sections as Json[]).flatMap(s => s.rows).find((r: Json) => r.ticket)
  expect(cells(byKey(tree, `row-${loner.n}`))).toContain(loner.ticket.id)
  for (const section of FIXTURE.sections) {
    for (const r of section.rows as Json[]) expect(rowWidth(byKey(tree, `row-${r.n}`))).toBeLessThanOrEqual(80)
  }
  await ui.unmount()
})

for (const columns of [40, 60]) {
  test(`R11 at ${columns} columns each Needs-you row fits the pane and keeps its question readable`, async ($, on) => {
    world(on, [FIXTURE])
    await command($, 'x')
    const ui = await mount($, 'terminal', columns)
    const tree = await ui.drawn()
    for (const e of FIXTURE.needs_you.entries as Json[]) {
      const node = byKey(tree, `need-${e.id}`)
      const got = cells(node)
      expect(rowWidth(node)).toBeLessThanOrEqual(columns)
      got.forEach((text, i) => expect(text.length).toBeLessThanOrEqual(widths(node)[i] ?? 0))
      expect(got).toContain(e.id)
      // The question wraps: its lines hold all of it, and the first line
      // starts it.
      const question = got.at(-1) ?? ''
      expect(e.text.startsWith(question)).toBe(true)
      const textLines = lineNodes(tree).filter(n => lineKey(n).startsWith(`need-${e.id}-`))
      expect(strip(question + textLines.map(n => words(n)).join(''))).toBe(strip(e.text))
      if (columns < 60) {
        expect(got).not.toContain(e.kind)
        expect(got).not.toContain(e.age)
      }
      if (e.recommend !== null) {
        const rec = byKey(tree, `recommend-${e.id}`)
        expect(Number(rec?.props?.paddingLeft ?? 0) + words(rec).length).toBeLessThanOrEqual(columns)
        // The recommendation wraps: its lines hold all of it.
        const recLines = lineNodes(tree).filter(n => /^recommend-/.test(lineKey(n)) && lineKey(n).startsWith(`recommend-${e.id}`))
        expect(strip(recLines.map(n => words(n)).join(''))).toBe(strip(`Recommended: ${e.recommend}`))
      }
    }
    await ui.unmount()
  })
}

test('R11 at 24 columns no row is wider than the pane', async ($, on) => {
  world(on, [FIXTURE])
  await command($, 'x')
  const ui = await mount($, 'terminal', 24)
  const tree = await ui.drawn()
  for (const section of FIXTURE.sections) {
    for (const r of section.rows as Json[]) {
      const node = byKey(tree, `row-${r.n}`)
      expect(rowWidth(node)).toBeLessThanOrEqual(24)
      expect(cells(node)).toContain(String(r.n))
    }
  }
  for (const e of FIXTURE.needs_you.entries as Json[]) expect(rowWidth(byKey(tree, `need-${e.id}`))).toBeLessThanOrEqual(24)
  await ui.unmount()
})

// ---------------------------------------------------------------- R12

test('R12 the pane writes no file', async ($, on) => {
  const w = world(on, [withNeeds('d1'), withNeeds('d1', 'q2')], { env: { CREW_ORCH: 'x' } })
  await command($, '')
  const ui = await mount($)
  await w.clock.advance(15_000)
  await ui.input({ key: 'go', text: '9' })
  expect(w.writes).toEqual([])
  await ui.unmount()
})

// ---------------------------------------------------------------- R16

// The text fixture's lines, as the text view prints them: each keeps its
// leading space.
const TEXT_LINES = (FIXTURE_TEXT as string).split('\n')

const lineOf = (pattern: RegExp) => {
  const i = TEXT_LINES.findIndex(l => pattern.test(l))
  expect(i, `a text line matches ${pattern}`).toBeGreaterThanOrEqual(0)
  return { i, line: TEXT_LINES[i] ?? '' }
}

// Each value is in the line, in order.
const inOrder = (line: string, values: string[]) => {
  let at = 0
  for (const value of values.filter(v => v !== '')) {
    const got = line.indexOf(value, at)
    expect(got, `"${value}" in order in "${line}"`).toBeGreaterThanOrEqual(0)
    at = got + value.length
  }
}

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

test('R16 at 200 columns the pane shows what the text view shows', async ($, on) => {
  world(on, [FIXTURE])
  await command($, 'x')
  const ui = await mount($, 'terminal', 200)
  const tree = await ui.drawn()
  let last = -1
  const next = (i: number, what: string) => {
    expect(i, `${what} comes after line ${last}`).toBeGreaterThan(last)
    last = i
  }
  for (const w of FIXTURE.plan.windows) {
    const pane = cells(byKey(tree, `plan-${w.key}`)).join(' ')
    const values = [w.label, w.meter, `${w.used_pct}%`, w.resets, w.full_at]
    inOrder(pane, values)
    const { i, line } = lineOf(new RegExp(`${w.label} ${w.meter}`))
    inOrder(line, values)
    next(i, w.label)
  }
  const needsLine = lineOf(/^ Needs you +3$/)
  expect(words(byKey(tree, 'needs'))).toContain(`Needs you ${FIXTURE.needs_you.count}`)
  next(needsLine.i, 'Needs you')
  for (const e of FIXTURE.needs_you.entries as Json[]) {
    const values = [e.id, e.kind, e.age, e.item, e.text]
    expect(cells(byKey(tree, `need-${e.id}`))).toEqual(values)
    const { i, line } = lineOf(new RegExp(`^  ${e.id} `))
    inOrder(line, values)
    next(i, e.id)
    if (e.recommend) {
      expect(words(byKey(tree, `recommend-${e.id}`)).trim()).toBe(`Recommended: ${e.recommend}`)
      expect((TEXT_LINES[i + 1] ?? '').trim()).toBe(`Recommended: ${e.recommend}`)
    }
  }
  const drawnRows: string[] = []
  const textRows: string[] = []
  for (const s of FIXTURE.sections as Json[]) {
    const head = [s.title, s.ticket?.id ?? '', s.repo ?? '', s.kind === 'group' ? `${s.merged} of ${s.total} merged` : '']
    inOrder(words(byKey(tree, s.kind === 'group' ? `group-${s.id}` : 'singles')), head)
    const { i, line } = lineOf(new RegExp(`^ ${escape(s.title)}`))
    inOrder(line, head)
    next(i, s.title)
    for (const r of s.rows as Json[]) {
      const values = [String(r.n), r.id, r.marks, r.status, r.pr?.label ?? '', r.ticket?.id ?? '', r.text, r.age]
      const got = cells(byKey(tree, `row-${r.n}`))
      expect(got.filter(c => c !== '')).toEqual(values.filter(v => v !== ''))
      const found = lineOf(new RegExp(`^ +${r.n} ${escape(r.id)}( |$)`))
      inOrder(found.line, values)
      next(found.i, r.id)
      drawnRows.push(`${r.n} ${r.id}`)
    }
  }
  for (const l of TEXT_LINES) {
    const m = /^ +(\d+) (\S+)/.exec(l)
    if (m) textRows.push(`${m[1]} ${m[2]}`)
  }
  expect(keys(tree).filter(k => k.startsWith('row-'))).toEqual(drawnRows.map(r => `row-${r.split(' ')[0]}`))
  expect(drawnRows).toEqual(textRows)
  const done = lineOf(/^ Done  1 /)
  next(done.i, 'Done')
  expect(words(byKey(tree, 'footer'))).toContain(`Done ${FIXTURE.done}`)
  await ui.unmount()
})

// ---------------------------------------------------------------- full text and window

// Terminal cells of a text, counted apart from the mod: a wide East Asian
// character or an emoji takes 2.
const cellsOf = (text: string) => {
  let total = 0
  for (const { segment } of new Intl.Segmenter().segment(text)) {
    total += /\p{Extended_Pictographic}|[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]/u.test(segment) ? 2 : 1
  }
  return total
}

const strip = (text: string) => text.replace(/\s+/g, '')

// The lines of a drawn tree: the children of its root.
const lineNodes = (tree: unknown) => ((tree as Node).children ?? []) as Node[]

const lineKey = (n: Node) => String(n.props?.key ?? '')

// The width of a drawn line, in cells.
const lineWidth = (n: Node) => {
  const kids = (n.children ?? []) as Node[]
  const pad = Number(n.props?.paddingLeft ?? 0)
  const gap = Number(n.props?.gap ?? 0)
  if (n.type === 'Input') return 0
  const sized = kids.length > 0 && kids.every(k => typeof k === 'object' && k?.props?.width !== undefined)
  const parts = sized ? kids.map(k => Number(k.props?.width)) : kids.map(k => cellsOf(words(k)))
  return pad + parts.reduce((a, b) => a + b, 0) + gap * Math.max(0, parts.length - 1)
}

const submit = ($ui: Json, text: string) => $ui.input({ key: 'go', text })

const longBoard = (count: number, extra: object = {}) =>
  board({
    sections: [singles(Array.from({ length: count }, (_, i) => row(i + 1, `item-${i + 1}`, { launch_tab: `H${i + 1}` })))],
    ...extra,
  })

const FAMILY = '\u{1F468}\u200D\u{1F469}\u200D\u{1F467}'

const TEXTS = {
  words: Array.from({ length: 40 }, (_, i) => `word${i}`).join(' ') + ' ' + 'x'.repeat(130),
  wide: `${'\u6F22\u5B57'.repeat(70)} ${FAMILY.repeat(40)} end`,
}

for (const [what, text] of Object.entries(TEXTS)) {
  for (const columns of [24, 40, 60, 80, 200]) {
    test(`R1 at ${columns} columns the pane shows all of a ${what} text and recommendation, in lines no wider than the pane`, async ($, on) => {
      const recommend = `${text} rec`
      world(on, [board({ needs_you: needs(entry('e1', { text, recommend })) })])
      await command($, 'x')
      const ui = await mount($, 'terminal', columns, 400)
      const tree = await ui.drawn()
      const list = lineNodes(tree)
      const first = list.findIndex(n => lineKey(n) === 'need-e1')
      const last = list.findIndex(n => lineKey(n) === 'gap-needs')
      expect(first).toBeGreaterThanOrEqual(0)
      const mine = list.slice(first, last)
      const texts = mine.map(n => words(n))
      const joined = strip(texts.join(''))
      expect(joined).toContain(strip(text))
      expect(joined).toContain(strip(`Recommended: ${recommend}`))
      for (const n of list) expect(lineWidth(n), `${lineKey(n)} fits ${columns}`).toBeLessThanOrEqual(columns)
      // A break never falls inside a grapheme.
      const bars = texts.join('|')
      expect(bars).not.toContain('\u200D|')
      expect(bars).not.toContain('|\u200D')
      await ui.unmount()
    })
  }
}

const viewKeys = (tree: unknown) => lineNodes(tree).map(lineKey)

// The keys of the whole board, with no window.
const fullKeys = async ($: Json, columns: number) => {
  const ui = await mount($, 'terminal', columns, 400)
  const got = viewKeys(await ui.drawn())
  await ui.unmount()
  return got
}

// Page down until the lower mark goes; every view is kept.
const walk = async (ui: Json, word: string, markKey: string) => {
  const views: Json[] = [await ui.drawn()]
  for (let i = 0; i < 80 && byKey(views.at(-1), markKey); i++) {
    await submit(ui, word)
    views.push(await ui.drawn())
  }
  return views
}

test('R2 d pages down until every board line has been drawn, and t returns to the top', async ($, on) => {
  world(on, [longBoard(30)])
  await command($, 'x')
  const want = (await fullKeys($, 80)).filter(k => k !== 'go')
  const ui = await mount($, 'terminal', 80, 10)
  const views = await walk(ui, 'd', 'mark-down')
  const seen = new Set<string>()
  for (const v of views) {
    expect(lineNodes(v).length).toBeLessThanOrEqual(10)
    viewKeys(v).forEach(k => seen.add(k))
  }
  for (const k of want) expect(seen.has(k), `${k} is drawn in a view`).toBe(true)
  expect(views.length).toBeGreaterThan(2)
  await submit(ui, 't')
  const top = await ui.drawn()
  expect(viewKeys(top)[0]).toBe(want[0])
  expect(byKey(top, 'mark-up')).toBeUndefined()
  await ui.unmount()
})

test('R2 the marks show above, below, both or neither', async ($, on) => {
  world(on, [longBoard(30)])
  await command($, 'x')
  const ui = await mount($, 'terminal', 80, 10)
  let tree = await ui.drawn()
  expect(byKey(tree, 'mark-up')).toBeUndefined()
  expect(words(byKey(tree, 'mark-down'))).toMatch(/^↓ \d+ more · d$/)
  await submit(ui, 'd')
  tree = await ui.drawn()
  expect(words(byKey(tree, 'mark-up'))).toMatch(/^↑ \d+ more · u$/)
  expect(words(byKey(tree, 'mark-down'))).toMatch(/^↓ \d+ more · d$/)
  expect(lineKey(lineNodes(tree)[0] as Node)).toBe('mark-up')
  await submit(ui, 'b')
  tree = await ui.drawn()
  expect(words(byKey(tree, 'mark-up'))).toMatch(/^↑ \d+ more · u$/)
  expect(byKey(tree, 'mark-down')).toBeUndefined()
  await ui.unmount()
  const fits = await mount($, 'terminal', 80, 200)
  tree = await fits.drawn()
  expect(byKey(tree, 'mark-up')).toBeUndefined()
  expect(byKey(tree, 'mark-down')).toBeUndefined()
  await fits.unmount()
})

for (const bodyRows of [6, 7, 8, 10]) {
  test(`R2 with ${bodyRows} rows b then u walks to the top and every board line is drawn`, async ($, on) => {
    world(on, [longBoard(25, { plan: FIXTURE.plan, needs_you: needs(entry('q1', { text: 'a question '.repeat(8) })) })])
    await command($, 'x')
    const want = (await fullKeys($, 40)).filter(k => k !== 'go')
    const ui = await mount($, 'terminal', 40, bodyRows)
    await submit(ui, 'b')
    const seen = new Set<string>()
    let tree = await ui.drawn()
    for (let i = 0; i < 80; i++) {
      expect(lineNodes(tree).length).toBeLessThanOrEqual(bodyRows)
      viewKeys(tree).forEach(k => seen.add(k))
      if (!byKey(tree, 'mark-up')) break
      await submit(ui, 'u')
      tree = await ui.drawn()
    }
    expect(byKey(tree, 'mark-up')).toBeUndefined()
    for (const k of want) expect(seen.has(k), `${k} is drawn`).toBe(true)
    await ui.unmount()
  })
}

test('R2 at 24 columns the Plan details stay in the list, and paging reaches them', async ($, on) => {
  world(on, [FIXTURE])
  await command($, 'x')
  const list = lineNodes(await (async () => {
    const ui = await mount($, 'terminal', 24, 400)
    const t = await ui.drawn()
    await ui.unmount()
    return t
  })())
  const plan = strip(list.filter(n => lineKey(n).startsWith('plan-')).map(n => words(n)).join(''))
  for (const w of FIXTURE.plan.windows) {
    expect(plan).toContain(strip(w.label + w.meter))
    expect(plan).toContain(strip(w.resets ?? ''))
    expect(plan).toContain(strip(w.full_at ? `full at about ${w.full_at}` : ''))
  }
  expect(plan).toContain(strip(FIXTURE.plan.word))
  for (const n of list.filter(n => lineKey(n).startsWith('plan-'))) expect(lineWidth(n), lineKey(n)).toBeLessThanOrEqual(24)
  const want = viewKeys(await (async () => {
    const ui = await mount($, 'terminal', 24, 400)
    const t = await ui.drawn()
    await ui.unmount()
    return t
  })()).filter(k => k !== 'go')
  const ui = await mount($, 'terminal', 24, 8)
  const seen = new Set<string>()
  for (const v of await walk(ui, 'd', 'mark-down')) {
    expect(lineNodes(v).length).toBeLessThanOrEqual(8)
    viewKeys(v).forEach(k => seen.add(k))
  }
  for (const k of want) expect(seen.has(k), `${k} is drawn`).toBe(true)
  await ui.unmount()
})

test('R2 in a short, narrow pane the result line of a submission leaves room for a board line', async ($, on) => {
  world(on, [longBoard(12)])
  await command($, 'x')
  const ui = await mount($, 'terminal', 24, 4)
  await submit(ui, '99')
  const tree = await ui.drawn()
  expect(lineNodes(tree).length).toBeLessThanOrEqual(4)
  expect(viewKeys(tree).some(k => k.startsWith('row-') || k === 'singles' || k === 'needs')).toBe(true)
  const walked = await walk(ui, 'd', 'mark-down')
  await submit(ui, 't')
  await ui.unmount()
  const big = await mount($, 'terminal', 24, 400)
  await submit(big, '99')
  const want = viewKeys(await big.drawn()).filter(k => k !== 'go')
  await big.unmount()
  expect(want).toContain('line')
  const seen = new Set<string>()
  for (const v of walked) {
    expect(lineNodes(v).length).toBeLessThanOrEqual(4)
    viewKeys(v).forEach(k => seen.add(k))
  }
  for (const k of want) expect(seen.has(k), `${k} is drawn`).toBe(true)
})

test('R3 a row number runs launcher.py focus for a row out of the current view', async ($, on) => {
  const w = world(on, [longBoard(30)])
  await command($, 'x')
  const ui = await mount($, 'terminal', 80, 10)
  await submit(ui, '28')
  expect(w.launcher).toHaveLength(1)
  expect(w.launcher[0]?.slice(2)).toEqual(['focus', 'H28'])
  await submit(ui, 'b')
  await submit(ui, '1')
  expect(w.launcher[1]?.slice(2)).toEqual(['focus', 'H1'])
  await ui.unmount()
})
