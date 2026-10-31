import type { On } from 'claude-code'

type UiOpenResult = { isPlaced: true } | { isPlaced: false; reason: string }
import { expect, mock, test } from 'claude-code/testing'

import * as mod from '../hooks/review-board'

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

const board = (rows: unknown[]) =>
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

test('a malformed row is dropped or made safe, and the good row still draws', async ($, on) => {
  const bad = [
    { ...row(20, 'triage', 'crew', '2026-01-01T10:00:00Z'), last: undefined },
    { ...row(21, 'triage', 'crew', '2026-01-01T10:00:00Z'), last: null },
    { ...row(22, 'triage', 'crew', '2026-01-01T10:00:00Z'), stage: undefined },
    null,
    'text',
  ]
  const w = world(on, () =>
    board([...bad, row(30, 'reviewing', 'crew', '2026-01-01T11:00:00Z')]),
  )
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(order(words(await ui.drawn()))).toContain(30)
  await ui.unmount()
  const out = await $.command.run(command(80))
  expect(order(out.text ?? '')).toContain(30)
  await $.skill.prompt({ skill: 'review-queue', text: 'go' })
  await w.clock.settle()
  expect(w.seen.status.at(-1)).toContain('review board')
})

test('a mounted armed pane costs one board read per change, and a render reads none', async ($, on) => {
  let rows: object[] = ROWS
  const w = world(on, () => board(rows))
  await $.skill.prompt({ skill: 'review-queue', text: 'go' })
  await w.clock.settle()
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  rows = ROWS.filter(r => r.pr !== 7)
  const before = w.seen.reads
  await w.clock.advance(3000)
  // The timer's tick reads once. The render it causes draws from that read.
  expect(w.seen.reads - before).toBe(1)
  expect(order(words(await ui.drawn()))).not.toContain(7)
  await ui.unmount()
})

// The watcher: the mod polls the queue's sources, writes the asks file, and
// hands each new ask to the queue session.

const ASKS = '/rec/queue/asks.json'
const TOKEN_FILE = '/home/me/.claude/secrets/slack-token'
const TOKEN = 'xoxp-test-token-4242'
const T0 = Date.parse('2026-01-02T00:00:00Z')
const SINCE = '2026-01-01T00:00:00Z'
const MINUTE = 60_000

const SLACK_WATCH = {
  id: '#dev',
  source: 'slack:#dev',
  policy: 'assist',
  status: 'active',
  since: SINCE,
  last_checked: null,
  found: 0,
}
const GH_WATCH = {
  id: 'review-requests',
  source: 'github:review-requests',
  policy: 'review',
  status: 'active',
  since: SINCE,
  last_checked: null,
  found: 0,
}

const watchBoard = (
  opts: {
    watches?: object[]
    rows?: object[]
    asks_through?: string | null
    owner?: string
  } = {},
) =>
  JSON.stringify({
    version: 1,
    owner: { session_id: opts.owner ?? 's1', since: SINCE },
    updated_at: SINCE,
    asks_through: opts.asks_through ?? null,
    watches: opts.watches ?? [SLACK_WATCH],
    rows: opts.rows ?? [],
  })

type Msg = { ts: string; text: string; reactions?: { name: string }[] }

// A Slack message with one PR link per number given.
const msg = (ts: string, prs: number[], done = false): Msg => ({
  ts,
  text: prs.map(n => `see <https://github.com/o/r/pull/${n}>`).join(' and '),
  ...(done ? { reactions: [{ name: 'done' }] } : {}),
})

// A Slack ts after SINCE, in order of `i`.
const ts = (i: number) => `${1767230000 + i}.000100`

const ghPr = (n: number, repo = 'o/g') => ({
  number: n,
  repository: { nameWithOwner: repo, name: repo.split('/')[1] },
  url: `https://github.com/${repo}/pull/${n}`,
  title: `gh title ${n}`,
  author: { login: 'bob' },
})

type Ask = {
  repo: string
  pr: number
  url: string
  title: string | null
  author: string | null
  watch: string
  slack: { channel: string; ts: string } | null
  found_at: string
}

const ask = (pr: number, found_at: string, extra: Partial<Ask> = {}): Ask => ({
  repo: 'o/r',
  pr,
  url: `https://github.com/o/r/pull/${pr}`,
  title: null,
  author: null,
  watch: '#dev',
  slack: { channel: 'C1', ts: ts(0) },
  found_at,
  ...extra,
})

const asksFile = (asks: Ask[]) =>
  JSON.stringify({ version: 1, updated_at: SINCE, watches: {}, asks })

// Stands for the engine, Slack and gh beneath the plugin: files in a map, a
// Slack Web API in memory, and a `gh` that prints what the test sets.
const watcher = (
  on: On,
  opts: {
    board: () => string
    token?: string | null
    store?: Record<string, unknown>
    session?: string
    files?: Record<string, string>
  },
) => {
  const files = new Map<string, string>(Object.entries(opts.files ?? {}))
  if (opts.token !== null) files.set(TOKEN_FILE, opts.token ?? TOKEN)
  const store: Record<string, unknown> = { ...(opts.store ?? {}) }
  const slack = {
    channels: [[{ id: 'C1', name: 'dev' }]] as { id: string; name: string }[][],
    history: [] as Msg[],
    pageSize: 100,
    fail: 0,
    // History fetches that never resolve.
    hang: 0,
  }
  const gh = { prs: [] as object[], fail: false, throws: false }
  // The next `mv` runs that exit 1, and temp-file writes the engine refuses.
  const faults = { mv: 0, write: 0 }
  const seen = {
    fetches: [] as string[],
    lists: [] as string[],
    history: [] as { oldest: string | null; cursor: string | null }[],
    runs: [] as string[][],
    writes: [] as { path: string; text: string }[],
    prompts: [] as string[],
    status: [] as unknown[],
    opens: 0,
  }
  mock.env(on, { CREW_RECORD_ROOT: '/rec', HOME: '/home/me' })
  const clock = mock.clock(on, { now: T0 })
  on('session.id', () => ({ value: opts.session ?? 's1' }))
  on('store.get', (_, e) => ({ value: store[e.key] }))
  on('store.set', (_, e) => {
    store[e.key] = e.value
    return { value: undefined }
  })
  on('store.delete', (_, e) => {
    delete store[e.key]
    return { value: undefined }
  })
  on('fs.read', (_, e) => {
    if (e.path === BOARD) return { value: opts.board() }
    const text = files.get(e.path)
    return text === undefined ? { deny: `no ${e.path}` } : { value: text }
  })
  on('fs.exists', (_, e) => ({ value: e.path === BOARD || files.has(e.path) }))
  on('fs.write', (_, e) => {
    if (e.path !== ASKS && faults.write > 0) {
      faults.write -= 1
      return { deny: 'disk full' }
    }
    seen.writes.push({ path: e.path, text: e.text })
    files.set(e.path, e.text)
    return { value: undefined }
  })
  const ran = (exitCode: number, stdout = '') => ({
    value: { exitCode, stdout, stderr: '' } as never,
  })
  on('process.run', (_, e) => {
    const argv = [...e.argv]
    seen.runs.push(argv)
    if (argv[0] === 'mv') {
      if (faults.mv > 0) {
        faults.mv -= 1
        return ran(1)
      }
      const text = files.get(argv[1])
      if (text === undefined) return ran(1)
      files.set(argv[2], text)
      files.delete(argv[1])
      return ran(0)
    }
    if (argv[0] === 'gh' && gh.throws) return { deny: 'gh: command not found' }
    if (argv[0] === 'gh') return gh.fail ? ran(1) : ran(0, JSON.stringify(gh.prs))
    return ran(127)
  })
  const reply = (body: object, status = 200) => ({
    value: { status, ok: status < 300, headers: {}, text: JSON.stringify(body) } as never,
  })
  on('http.fetch', (_, e) => {
    seen.fetches.push(e.url)
    const [base, query = ''] = e.url.split('?')
    const params = new URLSearchParams(query)
    const cursor = params.get('cursor') || null
    if (base.endsWith('/conversations.list')) {
      seen.lists.push(cursor ?? '')
      const page = Number(cursor ?? 0)
      const more = page + 1 < slack.channels.length
      return reply({
        ok: true,
        channels: slack.channels[page] ?? [],
        response_metadata: { next_cursor: more ? String(page + 1) : '' },
      })
    }
    if (base.endsWith('/conversations.history')) {
      const oldest = params.get('oldest')
      seen.history.push({ oldest, cursor })
      if (slack.hang > 0) {
        slack.hang -= 1
        return new Promise<never>(() => undefined)
      }
      if (slack.fail > 0) {
        slack.fail -= 1
        return reply({ ok: false, error: 'ratelimited' })
      }
      const after = slack.history
        .filter(m => oldest === null || Number(m.ts) > Number(oldest))
        .sort((a, b) => Number(b.ts) - Number(a.ts))
      const from = Number(cursor ?? 0)
      const messages = after.slice(from, from + slack.pageSize)
      const more = from + slack.pageSize < after.length
      return reply({
        ok: true,
        messages,
        has_more: more,
        response_metadata: { next_cursor: more ? String(from + slack.pageSize) : '' },
      })
    }
    return reply({ ok: false, error: 'unknown_method' }, 404)
  })
  on('prompt.submit', (_, e) => {
    seen.prompts.push(e.text)
    return { text: e.text }
  })
  on('ui.open', () => {
    seen.opens += 1
    return { value: { isPlaced: true } }
  })
  on('ui.close', () => ({ value: undefined }))
  on('ui.status', (_, e) => {
    seen.status.push(e.text)
    return { value: undefined }
  })
  on('command.register', () => ({ value: { command: 'review-board' } }))
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('skill.prompt', (_, e) => ({ text: e.text }))
  on('command.run', () => ({ text: 'engine' }))
  const asks = (): {
    watches: Record<string, { last_checked: string; found: number }>
    asks: Ask[]
  } => JSON.parse(files.get(ASKS) ?? '{"watches":{},"asks":[]}')
  const ghRuns = () => seen.runs.filter(a => a[0] === 'gh')
  const asksWrites = () =>
    seen.runs.filter(a => a[0] === 'mv' && a[2] === ASKS).length +
    seen.writes.filter(x => x.path === ASKS).length
  return { seen, clock, files, store, slack, gh, faults, asks, ghRuns, asksWrites }
}

type Kit = Parameters<Parameters<typeof test>[1]>[0]

const arm = async ($: Kit, w: { clock: { settle: () => Promise<void> } }) => {
  await $.skill.prompt({ skill: 'review-queue', text: 'go' })
  await w.clock.settle()
}

const drawn = async ($: Kit) => {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const text = words(await ui.drawn())
  await ui.unmount()
  return text
}

const PROMPT = (asks: string) =>
  `Crew review-queue ask: ${asks}. Run the wakeup loop of crew:review-queue.`

test('A1: a Slack PR message gives an entry, a prompt and a new row; a done message gives none', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [11])]
  await arm($, w)
  expect(w.asks().asks.map(a => a.pr)).toEqual([11])
  expect(w.asks().asks[0].slack).toEqual({ channel: 'C1', ts: ts(1) })
  expect(w.seen.prompts).toEqual([PROMPT('o/r#11 from #dev')])
  const pane = await drawn($)
  expect(order(pane)).toEqual([11])
  expect(pane).toContain('new ask from #dev')
  // Two links give two entries. A message with the done reaction gives none.
  w.slack.history.push(msg(ts(2), [12, 13]), msg(ts(3), [14], true))
  await w.clock.advance(MINUTE)
  expect(w.asks().asks.map(a => a.pr).sort()).toEqual([11, 12, 13])
})

test('A2: the gh review-request poll gives an entry with slack null', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [GH_WATCH] }) })
  w.gh.prs = [ghPr(5)]
  await arm($, w)
  expect(w.ghRuns()).toEqual([
    ['gh', 'search', 'prs', '--review-requested=@me', '--state=open', '--json', 'number,repository,url,title,author'],
  ])
  const [entry] = w.asks().asks
  expect(entry).toMatchObject({
    repo: 'o/g',
    pr: 5,
    url: 'https://github.com/o/g/pull/5',
    title: 'gh title 5',
    author: 'bob',
    watch: 'review-requests',
    slack: null,
  })
  expect(w.seen.prompts).toEqual([PROMPT('o/g#5 from review-requests')])
})

test('A3: a gh candidate with a row or an entry gives no second entry and no prompt', async ($, on) => {
  const w = watcher(on, {
    board: () =>
      watchBoard({
        watches: [GH_WATCH],
        rows: [row(5, 'reviewing', 'crew', '2026-01-01T10:00:00Z', { repo: 'o/g' })],
      }),
    files: {
      [ASKS]: asksFile([
        ask(6, '2026-01-01T10:00:00.000Z', { repo: 'o/g', watch: 'review-requests', slack: null }),
      ]),
    },
  })
  w.gh.prs = [ghPr(5), ghPr(6)]
  await arm($, w)
  expect(w.ghRuns().length).toBe(1)
  expect(w.asks().asks.map(a => a.pr)).toEqual([6])
  expect(w.seen.prompts).toEqual([])
})

test('A4: an unarmed session polls no source, writes nothing and prompts nothing', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }) })
  w.slack.history = [msg(ts(1), [11])]
  w.gh.prs = [ghPr(5)]
  await $.session.start({ cwd: '/', surface: 'terminal', isInteractive: true })
  await w.clock.advance(3 * MINUTE)
  expect(w.seen.fetches).toEqual([])
  expect(w.ghRuns()).toEqual([])
  expect(w.seen.writes).toEqual([])
  expect(w.seen.prompts).toEqual([])
})

for (const [name, token] of [
  ['no token file', null],
  ['a token file of only whitespace', '  \n\t '],
] as const) {
  test(`A5: with ${name}, the mod polls nothing and says the queue session polls`, async ($, on) => {
    const w = watcher(on, {
      board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }),
      token,
    })
    w.slack.history = [msg(ts(1), [11])]
    w.gh.prs = [ghPr(5)]
    await arm($, w)
    await w.clock.advance(2 * MINUTE)
    expect(w.seen.fetches).toEqual([])
    expect(w.ghRuns()).toEqual([])
    expect(w.asksWrites()).toBe(0)
    expect(w.seen.prompts).toEqual([])
    expect(await drawn($)).toContain('no token: the queue session polls')
  })
}

test('A6: a stopped watch is not polled', async ($, on) => {
  const w = watcher(on, {
    board: () =>
      watchBoard({
        watches: [
          { ...SLACK_WATCH, status: 'stopped' },
          { ...GH_WATCH, status: 'stopped' },
        ],
      }),
  })
  w.slack.history = [msg(ts(1), [11])]
  w.gh.prs = [ghPr(5)]
  await arm($, w)
  await w.clock.advance(2 * MINUTE)
  expect(w.seen.fetches).toEqual([])
  expect(w.ghRuns()).toEqual([])
  expect(w.seen.prompts).toEqual([])
})

test('A7: the token is in no written file, prompt, pane text or store value', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }) })
  w.slack.history = [msg(ts(1), [11])]
  w.gh.prs = [ghPr(5)]
  w.slack.fail = 1
  await arm($, w)
  await w.clock.advance(MINUTE)
  expect(w.seen.writes.length).toBeGreaterThan(0)
  expect(w.seen.prompts.length).toBeGreaterThan(0)
  expect(Object.keys(w.store).length).toBeGreaterThan(0)
  for (const x of w.seen.writes) expect(x.text).not.toContain(TOKEN)
  for (const p of w.seen.prompts) expect(p).not.toContain(TOKEN)
  for (const u of w.seen.fetches) expect(u).not.toContain(TOKEN)
  expect(JSON.stringify(w.store)).not.toContain(TOKEN)
  expect(await drawn($)).not.toContain(TOKEN)
  const out = await $.command.run(command(80))
  expect(out.text).not.toContain(TOKEN)
  for (const s of w.seen.status) expect(String(s)).not.toContain(TOKEN)
})

test('A8: an untaken entry with no row draws as a new row and counts as active; one with a row draws none', async ($, on) => {
  const w = watcher(on, {
    board: () =>
      watchBoard({ rows: [row(2, 'reviewing', 'crew', '2026-01-01T12:00:00Z')] }),
    token: null,
    files: {
      [ASKS]: asksFile([
        ask(40, '2026-01-01T13:00:00.000Z'),
        ask(2, '2026-01-01T13:00:01.000Z'),
      ]),
    },
  })
  await arm($, w)
  const pane = await drawn($)
  expect(order(pane).sort((a, b) => a - b)).toEqual([2, 40])
  expect(w.seen.status.at(-1)).toBe(
    'review board · watching 1 · 0 need you · 0 blocked · 2 active · 0 merged',
  )
})

test('A9: a Slack ok:false answer leaves the timer running, and the next period polls again', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [11])]
  w.slack.fail = 1
  await arm($, w)
  expect(w.seen.history.length).toBe(1)
  expect(w.asks().asks).toEqual([])
  expect(await drawn($)).toContain('#dev: Slack error')
  await w.clock.advance(MINUTE)
  expect(w.seen.history.length).toBe(2)
  expect(w.asks().asks.map(a => a.pr)).toEqual([11])
})

test('A10: the mod writes asks.json through a temp file and a move', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [11])]
  await arm($, w)
  expect(w.seen.writes.filter(x => x.path === ASKS)).toEqual([])
  const moves = w.seen.runs.filter(a => a[0] === 'mv')
  expect(moves.length).toBe(1)
  const [, from, to] = moves[0]
  expect(to).toBe(ASKS)
  expect(from).not.toBe(ASKS)
  expect(from.startsWith('/rec/queue/')).toBe(true)
  expect(w.seen.writes.map(x => x.path)).toContain(from)
  const file = JSON.parse(w.files.get(ASKS) ?? '')
  expect(file.version).toBe(1)
  expect(file.asks.length).toBe(1)
  expect(w.files.has(from)).toBe(false)
})

test('A11: two new asks in one poll give one prompt that names both; no new ask gives no prompt', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [50]), msg(ts(2), [51])]
  await arm($, w)
  expect(w.seen.prompts.length).toBe(1)
  expect(w.seen.prompts[0]).toContain('o/r#50 from #dev')
  expect(w.seen.prompts[0]).toContain('o/r#51 from #dev')
  expect(w.seen.prompts[0]).toContain('Run the wakeup loop of crew:review-queue.')
  await w.clock.advance(MINUTE)
  expect(w.seen.history.length).toBe(2)
  expect(w.seen.prompts.length).toBe(1)
})

test('A12: an armed session reads each source at arm, then once each 60 seconds', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }) })
  await arm($, w)
  expect(w.seen.history.length).toBe(1)
  expect(w.ghRuns().length).toBe(1)
  await w.clock.advance(MINUTE - 1)
  expect(w.seen.history.length).toBe(1)
  expect(w.ghRuns().length).toBe(1)
  await w.clock.advance(1)
  expect(w.seen.history.length).toBe(2)
  expect(w.ghRuns().length).toBe(2)
  await w.clock.advance(MINUTE)
  expect(w.seen.history.length).toBe(3)
  expect(w.ghRuns().length).toBe(3)
})

test('A18: two polls with one new ask each give two prompts', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [61])]
  await arm($, w)
  w.slack.history.push(msg(ts(2), [62]))
  await w.clock.advance(MINUTE)
  expect(w.seen.prompts).toEqual([PROMPT('o/r#61 from #dev'), PROMPT('o/r#62 from #dev')])
})

test('A19: a later Slack message for a PR with a row gives an entry; a prompt only at next: author', async ($, on) => {
  const w = watcher(on, {
    board: () =>
      watchBoard({
        rows: [
          row(60, 'reviewing', 'crew', '2026-01-01T10:00:00Z'),
          row(61, 'reviewing', 'author', '2026-01-01T10:00:00Z'),
        ],
      }),
  })
  w.slack.history = [msg(ts(5), [60]), msg(ts(6), [61])]
  await arm($, w)
  expect(w.asks().asks.map(a => [a.pr, a.slack?.ts]).sort()).toEqual([
    [60, ts(5)],
    [61, ts(6)],
  ])
  // A row at next: author is a re-triage the queue session must see now.
  expect(w.seen.prompts).toEqual([PROMPT('o/r#61 from #dev')])
})

test('A20: a poll prunes every entry at or before asks_through and keeps the later ones', async ($, on) => {
  const w = watcher(on, {
    board: () => watchBoard({ watches: [GH_WATCH], asks_through: '2026-01-01T11:00:00.000Z' }),
    files: {
      [ASKS]: asksFile([
        ask(70, '2026-01-01T10:00:00.000Z'),
        ask(71, '2026-01-01T11:00:00.000Z'),
        ask(72, '2026-01-01T12:00:00.000Z'),
      ]),
    },
  })
  await arm($, w)
  expect(w.asks().asks.map(a => a.pr)).toEqual([72])
})

test('A21: after a reload the mod reads the channel id and the cursor from the store', async ($, on) => {
  const w = watcher(on, {
    board: () => watchBoard(),
    store: {
      'slack-channel:dev': 'C1',
      'slack-cursor:#dev': { since: SINCE, oldest: ts(3), page: null, newest: null },
    },
  })
  await arm($, w)
  expect(w.seen.lists).toEqual([])
  expect(w.seen.history[0].oldest).toBe(ts(3))
})

test('A21: a watch added again with a new since reads from the new since, not the old cursor', async ($, on) => {
  const since = '2026-01-01T18:00:00Z'
  const w = watcher(on, {
    board: () => watchBoard({ watches: [{ ...SLACK_WATCH, since }] }),
    store: {
      'slack-channel:dev': 'C1',
      'slack-cursor:#dev': { since: SINCE, oldest: ts(3), page: '4', newest: ts(9) },
    },
  })
  await arm($, w)
  expect(w.seen.history[0]).toEqual({
    oldest: (Date.parse(since) / 1000).toFixed(6),
    cursor: null,
  })
})

test('A21: with no cursor, oldest is the watch since as a Unix ts', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  await arm($, w)
  const oldest = w.seen.history[0].oldest ?? ''
  expect(oldest).toContain('.')
  expect(Number(oldest)).toBe(Date.parse(SINCE) / 1000)
  // The channel id is kept for the next reload.
  expect(w.store['slack-channel:dev']).toBe('C1')
})

test('A22: history follows up to 5 pages, and the lookup follows pages to the name', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.channels = [
    [{ id: 'C7', name: 'ops' }],
    [{ id: 'C8', name: 'random' }],
    [{ id: 'C1', name: 'dev' }],
  ]
  w.slack.pageSize = 2
  w.slack.history = Array.from({ length: 14 }, (_, i) => msg(ts(i + 1), [100 + i]))
  await arm($, w)
  expect(w.seen.lists).toEqual(['', '1', '2'])
  expect(w.seen.history.length).toBe(5)
})

test('A22: a channel the lookup cannot find shows not found and polls no history', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.channels = [[{ id: 'C7', name: 'ops' }], [{ id: 'C8', name: 'random' }]]
  await arm($, w)
  expect(w.seen.lists).toEqual(['', '1'])
  expect(w.seen.history).toEqual([])
  expect(await drawn($)).toContain('#dev: not found')
})

test('A23: found counts the entries written since since, and a dedupe hit does not raise it', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [GH_WATCH] }) })
  w.gh.prs = [ghPr(5)]
  await arm($, w)
  expect(w.asks().watches['review-requests'].found).toBe(1)
  w.gh.prs = [ghPr(5), ghPr(6)]
  await w.clock.advance(MINUTE)
  expect(w.asks().watches['review-requests'].found).toBe(2)
  expect(w.asks().watches['review-requests'].last_checked).toBe(
    new Date(T0 + MINUTE).toISOString(),
  )
})

test('A24: a session that does not own the board polls nothing', async ($, on) => {
  const w = watcher(on, {
    board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }),
    session: 's2',
  })
  w.slack.history = [msg(ts(1), [11])]
  w.gh.prs = [ghPr(5)]
  await arm($, w)
  await w.clock.advance(2 * MINUTE)
  expect(w.seen.fetches).toEqual([])
  expect(w.ghRuns()).toEqual([])
  expect(w.asksWrites()).toBe(0)
  expect(w.seen.prompts).toEqual([])
})

test('A25: past 5 pages the next poll goes on from the page cursor with the same oldest', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.pageSize = 2
  w.slack.history = Array.from({ length: 12 }, (_, i) => msg(ts(i + 1), [200 + i]))
  await arm($, w)
  expect(w.seen.history.length).toBe(5)
  expect(w.asks().asks.length).toBe(10)
  await w.clock.advance(MINUTE)
  expect(w.seen.history.length).toBe(6)
  const first = w.seen.history[0]
  const sixth = w.seen.history[5]
  expect(sixth.oldest).toBe(first.oldest)
  expect(sixth.cursor).toBe('10')
  expect(w.asks().asks.map(a => a.pr).sort((a, b) => a - b)).toEqual(
    Array.from({ length: 12 }, (_, i) => 200 + i),
  )
  // The last page is read, so the next poll starts after the newest ts seen.
  await w.clock.advance(MINUTE)
  expect(w.seen.history[6]).toEqual({ oldest: ts(12), cursor: null })
})

test('A26: two writes in the same clock millisecond give strictly increasing found_at', async ($, on) => {
  const now = new Date(T0).toISOString()
  const w = watcher(on, {
    board: () => watchBoard({ watches: [GH_WATCH] }),
    files: { [ASKS]: asksFile([ask(80, now, { watch: 'review-requests', slack: null })]) },
  })
  w.gh.prs = [ghPr(81), ghPr(82)]
  await arm($, w)
  const at = w.asks().asks.map(a => Date.parse(a.found_at))
  expect(at.length).toBe(3)
  expect(at[1]).toBeGreaterThan(at[0])
  expect(at[2]).toBeGreaterThan(at[1])
})

test('A27: two untaken entries for one PR draw one derived row, and it alone opens the pane', async ($, on) => {
  const w = watcher(on, {
    board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }),
    token: null,
    files: {
      [ASKS]: asksFile([
        ask(41, '2026-01-01T14:00:00.000Z', {
          watch: 'review-requests',
          title: 'later',
          author: 'zed',
          slack: null,
        }),
        ask(41, '2026-01-01T13:00:00.000Z'),
      ]),
    },
  })
  await arm($, w)
  expect(w.seen.opens).toBe(1)
  expect(w.seen.status.at(-1)).toBe(
    'review board · watching 2 · 0 need you · 0 blocked · 1 active · 0 merged',
  )
  const out = await $.command.run(command(100))
  const lines = (out.text ?? '').split('\n').filter(l => l.includes('#41'))
  expect(lines.length).toBe(1)
  // The row comes from the earliest entry: watch #dev, its policy assist, no
  // title, and the last event names the watch.
  expect(lines[0]).toMatch(/#41\s+new\s+crew\s+assist\s/)
  expect(lines[0]).toContain('new ask from #dev')
  expect(lines[0]).not.toContain('later')
})

test('A27: a derived row has the fields of the spec table', async () => {
  const { view, parseBoard } = mod
  const b = parseBoard(watchBoard({ watches: [SLACK_WATCH] }))
  const v = view(b, {
    version: 1,
    updated_at: SINCE,
    watches: {},
    asks: [
      ask(41, '2026-01-01T14:00:00.000Z', { title: 'later', author: 'zed' }),
      ask(41, '2026-01-01T13:00:00.000Z'),
      ask(42, '2026-01-01T13:00:00.000Z', { watch: 'gone', title: 'T', author: 'amy' }),
    ],
  })
  expect(v.rows).toEqual([
    {
      repo: 'o/r',
      pr: 41,
      url: 'https://github.com/o/r/pull/41',
      watch: '#dev',
      title: '',
      author: '-',
      stage: 'new',
      next: 'crew',
      head: null,
      last: { at: '2026-01-01T13:00:00.000Z', text: 'new ask from #dev' },
      policy: 'assist',
    },
    {
      repo: 'o/r',
      pr: 42,
      url: 'https://github.com/o/r/pull/42',
      watch: 'gone',
      title: 'T',
      author: 'amy',
      stage: 'new',
      next: 'crew',
      head: null,
      last: { at: '2026-01-01T13:00:00.000Z', text: 'new ask from gone' },
      policy: 'review',
    },
  ])
})

test('R8: a later last_checked in asks.json shows in Watching', async ($, on) => {
  const w = watcher(on, {
    board: () => watchBoard(),
    token: null,
    files: {
      [ASKS]: JSON.stringify({
        version: 1,
        updated_at: '2026-01-01T20:00:00.000Z',
        watches: { '#dev': { last_checked: '2026-01-01T20:00:00.000Z', found: 9 } },
        asks: [],
      }),
    },
  })
  await arm($, w)
  const pane = await drawn($)
  expect(pane).toContain('checked 2026-01-01 20:00')
  expect(pane).toContain('found 9')
})

for (const fault of ['mv', 'write'] as const) {
  test(`A28: a Slack ask read in a poll whose ${fault} of asks.json failed reaches asks.json at the next poll`, async ($, on) => {
    const w = watcher(on, { board: () => watchBoard() })
    w.slack.history = [msg(ts(1), [11])]
    w.faults[fault] = 1
    await arm($, w)
    expect(w.asks().asks).toEqual([])
    expect(w.seen.prompts).toEqual([])
    await w.clock.advance(MINUTE)
    expect(w.asks().asks.map(a => a.pr)).toEqual([11])
    expect(w.asks().watches['#dev'].found).toBe(1)
    expect(w.seen.prompts).toEqual([PROMPT('o/r#11 from #dev')])
  })
}

test('A29: a gh run that rejects skips its watch with a note, and the Slack watch still writes', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard({ watches: [SLACK_WATCH, GH_WATCH] }) })
  w.slack.history = [msg(ts(1), [11])]
  w.gh.throws = true
  await arm($, w)
  expect(w.asks().asks.map(a => a.pr)).toEqual([11])
  expect(w.seen.prompts).toEqual([PROMPT('o/r#11 from #dev')])
  expect(await drawn($)).toContain('review-requests: poll failed')
  w.gh.throws = false
  w.gh.prs = [ghPr(5)]
  await w.clock.advance(MINUTE)
  expect(w.asks().asks.map(a => a.pr)).toEqual([11, 5])
})

test('A30: a Slack fetch that never resolves times out at 30 seconds, and the next poll polls again', async ($, on) => {
  const w = watcher(on, { board: () => watchBoard() })
  w.slack.history = [msg(ts(1), [11])]
  w.slack.hang = 1
  await arm($, w)
  expect(w.seen.history.length).toBe(1)
  await w.clock.advance(30_000)
  expect(await drawn($)).toContain('#dev: poll failed')
  await w.clock.advance(MINUTE - 30_000)
  expect(w.seen.history.length).toBe(2)
  expect(w.asks().asks.map(a => a.pr)).toEqual([11])
})
