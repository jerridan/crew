import type { On } from 'claude-code'

type UiOpenResult = { isPlaced: true } | { isPlaced: false; reason: string }
import { expect, mock, test } from 'claude-code/testing'

const BOARD = '/rec/queue/board.json'

const PANE = {
  plugin: 'crew',
  component: 'Pane',
  requestId: 'review-board',
  props: {
    title: 'Review board',
    isFocused: false,
    bodyColumns: 120,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

const row = (
  pr: number,
  stage: string,
  next: string,
  at: string,
  extra: object = {},
) => ({
  repo: 'o/r',
  pr,
  title: `title ${pr}`,
  author: 'ann',
  stage,
  next,
  head: 'abc',
  last: { at, text: `event ${pr}` },
  url: `https://example.test/${pr}`,
  watch: 'w1',
  policy: 'review',
  ...extra,
})

const board = (rows: object[]) =>
  JSON.stringify({
    version: 1,
    owner: { session_id: 's1', since: '2026-01-01T00:00:00Z' },
    updated_at: '2026-01-01T00:00:00Z',
    watches: [
      {
        id: 'w1',
        source: 'slack:#dev',
        policy: 'assist',
        status: 'active',
        since: '2026-01-01T00:00:00Z',
        last_checked: null,
        found: 3,
      },
      {
        id: 'w2',
        source: 'direct',
        policy: 'review',
        status: 'stopped',
        since: '2026-01-01T00:00:00Z',
        last_checked: '2026-01-01T01:00:00Z',
        found: 0,
      },
    ],
    rows,
  })

const ROWS = [
  row(1, 'approve', 'you', '2026-01-01T10:00:00Z'),
  row(2, 'reviewing', 'crew', '2026-01-01T12:00:00Z'),
  row(3, 'triage', 'crew', '2026-01-01T11:00:00Z'),
  row(4, 'fixing', 'you', '2026-01-01T09:00:00Z'),
  row(5, 'reviewing', 'ci', '2026-01-01T13:00:00Z'),
  row(6, 'blocked', 'author', '2026-01-01T08:00:00Z'),
  row(7, 'merged', '-', '2026-01-01T07:00:00Z'),
]

const words = (node: unknown): string => {
  if (node == null) return ''
  if (typeof node === 'string') return node
  if (Array.isArray(node)) return node.map(words).join(' ')
  const n = node as { text?: unknown; children?: unknown }
  return [words(n.text), words(n.children)].join(' ')
}

const order = (text: string) =>
  [...text.matchAll(/#(\d+)\b/g)].map(m => Number(m[1]))

// Stands for the engine beneath the plugin.
const world = (
  on: On,
  file: () => string,
  open: () => UiOpenResult = () => ({ isPlaced: true }),
) => {
  const seen = { reads: 0, opens: 0, closes: 0, status: [] as unknown[] }
  mock.env(on, { CREW_RECORD_ROOT: '/rec', HOME: '/home/me' })
  const clock = mock.clock(on)
  on('fs.read', (_, e) => {
    if (e.path !== BOARD) return { deny: `no ${e.path}` }
    seen.reads += 1
    return { value: file() }
  })
  on('ui.open', () => {
    seen.opens += 1
    return { value: open() }
  })
  on('ui.close', () => {
    seen.closes += 1
    return { value: undefined }
  })
  on('ui.status', (_, e) => {
    seen.status.push(e.text)
    return { value: undefined }
  })
  on('command.register', () => ({ value: { command: 'review-board' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('skill.prompt', (_, e) => ({ text: e.text }))
  on('command.run', () => ({ text: 'engine' }))
  return { seen, clock }
}

const command = (columns: number) =>
  ({
    command: 'review-board',
    presentation: { isFullscreen: true, columns },
  }) as never

const STATUS =
  'review board · watching 1 · 2 need you · 1 blocked · 5 active · 1 merged'

test('rows sort next:you first, then stage order, then newest', async ($, on) => {
  world(on, () => board(ROWS))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const drawn = words(await ui.drawn())
  // Needs you: 4 (fixing) before 1 (approve). In flight: triage 3, reviewing
  // 5 (newer) before 2, then blocked 6. Done is collapsed, so 7 is absent.
  expect(order(drawn)).toEqual([4, 1, 3, 5, 2, 6])
  for (const name of ['Watching', 'Needs you', 'In flight', 'Done']) {
    expect(drawn).toContain(name)
  }
  await ui.unmount()
})

test('Done stays collapsed behind a button, and the choice survives a redraw', async ($, on) => {
  world(on, () => board(ROWS))
  let ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(order(words(await ui.drawn()))).not.toContain(7)
  await ui.press({ key: 'toggle-done' })
  expect(order(words(await ui.drawn()))).toContain(7)
  await ui.unmount()
  ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(order(words(await ui.drawn()))).toContain(7)
  await ui.unmount()
})

test('the title is capped at 60 characters and an assist watch shows in yellow', async ($, on) => {
  const long = 'x'.repeat(90)
  world(on, () => board([row(8, 'triage', 'crew', '2026-01-01T10:00:00Z', { title: long, policy: 'assist' })]))
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const drawn = words(await ui.drawn())
  expect(drawn).not.toContain('x'.repeat(61))
  expect(drawn).toContain('x'.repeat(59))
  expect(JSON.stringify(await ui.drawn())).toContain('yellow')
  await ui.unmount()
})

test('In flight shows +N more when it exceeds the room', async ($, on) => {
  const many = Array.from({ length: 30 }, (_, i) =>
    row(100 + i, 'reviewing', 'crew', `2026-01-01T10:${String(i).padStart(2, '0')}:00Z`),
  )
  world(on, () => board(many))
  const ui = await $.ui.mount({
    ...PANE,
    props: { ...PANE.props, scroll: { offset: 0, bodyRows: 12 } },
    surface: 'terminal',
  })
  const drawn = words(await ui.drawn())
  expect(drawn).toMatch(/\+\d+ more/)
  // Every line the pane draws counts: the Done button stays inside bodyRows.
  const root = (await ui.drawn()) as { children?: { props?: { key?: string } }[] }
  const lines = root.children ?? []
  const at = lines.findIndex(c => c.props?.key === 'toggle-done')
  expect(at).toBeGreaterThanOrEqual(0)
  expect(at + 1).toBeLessThanOrEqual(12)
  await ui.unmount()
})

for (const name of ['crew:review-queue', 'review-queue']) {
  test(`the ${name} skill prompt arms the board`, async ($, on) => {
    const w = world(on, () => board(ROWS))
    await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
    expect(w.seen.reads).toBe(0)
    await $.skill.prompt({ skill: name, text: 'go' })
    await w.clock.settle()
    expect(w.seen.opens).toBe(1)
    expect(w.seen.status.at(-1)).toBe(STATUS)
    // The poll reads again every 3 seconds, and redraws on a change.
    const before = w.seen.reads
    await w.clock.advance(3000)
    expect(w.seen.reads).toBeGreaterThan(before)
  })
}

test('the poll updates the status line when the board changes', async ($, on) => {
  let rows = ROWS
  const w = world(on, () => board(rows))
  await $.skill.prompt({ skill: 'review-queue', text: 'go' })
  await w.clock.settle()
  rows = ROWS.filter(r => r.pr !== 7)
  await w.clock.advance(3000)
  expect(w.seen.status.at(-1)).toBe(
    'review board · watching 1 · 2 need you · 1 blocked · 5 active · 0 merged',
  )
})

test('a skill that is not the queue leaves the board unarmed', async ($, on) => {
  const w = world(on, () => board(ROWS))
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await $.skill.prompt({ skill: 'crew:project-lead', text: 'go' })
  await w.clock.advance(10000)
  expect(w.seen.reads).toBe(0)
  expect(w.seen.opens).toBe(0)
  expect(w.seen.status).toEqual([])
  // The command still opens the pane by hand.
  await $.command.run(command(120))
  expect(w.seen.opens).toBe(1)
})

test('/review-board prints the table as text, fitted to the width, under 110 columns', async ($, on) => {
  const w = world(on, () => board(ROWS))
  const out = await $.command.run(command(80))
  expect(w.seen.opens).toBe(0)
  expect(out.text).toContain('Needs you')
  expect(order(out.text ?? '')).toEqual([4, 1, 3, 5, 2, 6])
  for (const line of (out.text ?? '').split('\n')) {
    expect(line.length).toBeLessThanOrEqual(80)
  }
})

test('/review-board opens the pane from 110 columns', async ($, on) => {
  const w = world(on, () => board(ROWS))
  const out = await $.command.run(command(120))
  expect(w.seen.opens).toBe(1)
  expect(out.text).not.toContain('Needs you')
})

test('the status line clears when every row is done, and the pane stays open', async ($, on) => {
  let rows: object[] = ROWS
  const w = world(on, () => board(rows))
  await $.skill.prompt({ skill: 'review-queue', text: 'go' })
  await w.clock.settle()
  rows = [row(7, 'merged', '-', '2026-01-01T07:00:00Z'), row(9, 'closed', '-', '2026-01-01T07:00:00Z')]
  await w.clock.advance(3000)
  expect(w.seen.status.at(-1)).toBeUndefined()
  expect(w.seen.closes).toBe(0)
})

const LONG = 'y'.repeat(200)
const LONG_ROW = () =>
  board([
    row(8, 'triage', 'crew', '2026-01-01T10:00:00Z', {
      title: LONG,
      last: { at: '2026-01-01T10:00:00Z', text: LONG },
    }),
  ])

test('a text row is exactly the width given, with no second ellipsis', async ($, on) => {
  world(on, LONG_ROW)
  const out = await $.command.run(command(80))
  const line = (out.text ?? '').split('\n').find(l => l.includes('#8')) ?? ''
  // The row is built from the widths alone: the final fit must not cut it.
  expect(line.length).toBe(80)
  expect(line).not.toContain('……')
  // Title 23, last 20 (80 - indent 2 - 30 fixed - 5 gaps = 43 to share): the
  // last cell keeps all of its 19 letters and one ellipsis.
  expect(line.endsWith(`${'y'.repeat(19)}…`)).toBe(true)
})

test('a pane row is exactly bodyColumns wide: cells plus gaps', async ($, on) => {
  world(on, LONG_ROW)
  type Node = {
    props?: { key?: string; gap?: number; width?: number }
    children?: Node[]
  }
  for (const columns of [100, 120]) {
    const ui = await $.ui.mount({
      ...PANE,
      props: { ...PANE.props, bodyColumns: columns },
      surface: 'terminal',
    })
    const root = (await ui.drawn()) as Node
    const line = (root.children ?? []).find(c => c.props?.key === 'o/r#8')
    const cells = line?.children ?? []
    const gaps = (line?.props?.gap ?? 0) * (cells.length - 1)
    const total = cells.reduce((sum, c) => sum + (c.props?.width ?? 0), 0) + gaps
    expect(cells.length).toBe(6)
    expect(total).toBe(columns)
    await ui.unmount()
  }
})
