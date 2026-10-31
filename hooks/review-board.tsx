// The review board: a pane and a status line for the review queue session,
// and the watcher of the queue's sources.
// skills/review-queue/references/board.md owns the schema of the board file
// and of the asks file.
// This module only reads the board file. The queue session writes it. This
// module writes the asks file, and the queue session reads it.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type {
  ReviewBoardAsk,
  ReviewBoardAsksFile,
  ReviewBoardFile,
  ReviewBoardRow,
  ReviewBoardStage,
  ReviewBoardWatch,
} from '../types/index'

type Engine = EngineInterface

const PANE = 'review-board'
const SKILL = 'review-queue'
const POLL_MS = 3000
const WATCH_MS = 60_000
const TITLE_CAP = 60
const LAST_MIN = 20
const MIN_PANE_COLUMNS = 110

const SLACK_API = 'https://slack.com/api'
// One poll reads at most this many history pages, and goes on at the next.
const HISTORY_PAGES = 5
// The channel lookup follows pages to the name. This only stops a loop.
const LIST_PAGES = 100
const NO_TOKEN = 'no token: the queue session polls'
const GH_SEARCH = [
  'gh',
  'search',
  'prs',
  '--review-requested=@me',
  '--state=open',
  '--json',
  'number,repository,url,title,author',
]
const PR_LINK = /https?:\/\/github\.com\/([\w.-]+)\/([\w.-]+)\/pull\/(\d+)/g

const STAGES: ReviewBoardStage[] = [
  'new',
  'triage',
  'reviewing',
  'fixing',
  'rereview',
  'approve',
  'queued',
  'merged',
  'blocked',
  'closed',
]

// Change a tag when the value's meaning changes: it declines what an earlier
// version stored, which outlives a reload.
const armed = atom({ plugin: 'crew', key: 'armed' } as const, false, {
  shape: 'armed-1',
})
const showDone = atom({ plugin: 'crew', key: 'showDone' } as const, false, {
  shape: 'show-done-1',
})

const isDone = (r: ReviewBoardRow) => r.stage === 'merged' || r.stage === 'closed'
const isBlocked = (r: ReviewBoardRow) => r.stage === 'blocked'

// The skill reports as `crew:review-queue` or as `review-queue`.
export const isQueueSkill = (skill: string) =>
  skill === SKILL || skill === `crew:${SKILL}`

export const sortRows = (rows: ReviewBoardRow[]) =>
  [...rows].sort(
    (a, b) =>
      Number(b.next === 'you') - Number(a.next === 'you') ||
      STAGES.indexOf(a.stage) - STAGES.indexOf(b.stage) ||
      b.last.at.localeCompare(a.last.at),
  )

export const statusLine = (board: ReviewBoardFile) => {
  const rows = board.rows
  const count = (f: (r: ReviewBoardRow) => boolean) => rows.filter(f).length
  const watching = board.watches.filter(w => w.status === 'active').length
  return [
    'review board',
    `watching ${watching}`,
    `${count(r => r.next === 'you' && !isDone(r))} need you`,
    `${count(isBlocked)} blocked`,
    `${count(r => !isDone(r) && !isBlocked(r))} active`,
    `${count(r => r.stage === 'merged')} merged`,
  ].join(' · ')
}

// Rows of a board, split the way the pane and the text table show them.
export const sections = (board: ReviewBoardFile) => {
  const sorted = sortRows(board.rows)
  return {
    needsYou: sorted.filter(r => r.next === 'you' && !isDone(r)),
    inFlight: sorted.filter(r => r.next !== 'you' && !isDone(r)),
    done: sorted.filter(isDone),
  }
}

const EMPTY: ReviewBoardFile = {
  version: 1,
  owner: { session_id: '', since: '' },
  updated_at: '',
  asks_through: null,
  watches: [],
  rows: [],
}

const str =(v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)

// A row or watch the file holds in part is made safe here, once, so no other
// code reads a field that may be missing. A row with no known stage or no
// number is dropped: the board cannot place it.
const cleanRow = (raw: unknown): ReviewBoardRow | undefined => {
  if (typeof raw !== 'object' || raw === null) return undefined
  const r = raw as Record<string, unknown>
  if (typeof r.pr !== 'number') return undefined
  if (!STAGES.includes(r.stage as ReviewBoardStage)) return undefined
  const last = (typeof r.last === 'object' && r.last) || {}
  const at = (last as Record<string, unknown>).at
  const text = (last as Record<string, unknown>).text
  return {
    repo: str(r.repo),
    pr: r.pr,
    title: str(r.title),
    author: str(r.author),
    stage: r.stage as ReviewBoardStage,
    next: str(r.next, '-') as ReviewBoardRow['next'],
    head: typeof r.head === 'string' ? r.head : null,
    last: { at: str(at), text: str(text) },
    url: str(r.url),
    watch: typeof r.watch === 'string' ? r.watch : null,
    policy: r.policy === 'assist' ? 'assist' : 'review',
  }
}

const cleanWatch = (raw: unknown): ReviewBoardWatch | undefined => {
  if (typeof raw !== 'object' || raw === null) return undefined
  const w = raw as Record<string, unknown>
  if (typeof w.id !== 'string') return undefined
  return {
    id: w.id,
    source: str(w.source),
    policy: w.policy === 'assist' ? 'assist' : 'review',
    status: w.status === 'active' ? 'active' : 'stopped',
    since: str(w.since),
    last_checked: typeof w.last_checked === 'string' ? w.last_checked : null,
    found: typeof w.found === 'number' ? w.found : 0,
  }
}

export const parseBoard = (text: string | undefined): ReviewBoardFile => {
  if (!text) return EMPTY
  try {
    const raw = JSON.parse(text) as Partial<ReviewBoardFile> | null
    if (typeof raw !== 'object' || raw === null) return EMPTY
    const list = (v: unknown) => (Array.isArray(v) ? v : [])
    return {
      ...EMPTY,
      ...raw,
      asks_through:
        typeof raw.asks_through === 'string' ? raw.asks_through : null,
      watches: list(raw.watches).flatMap(x => cleanWatch(x) ?? []),
      rows: list(raw.rows).flatMap(x => cleanRow(x) ?? []),
    }
  } catch {
    return EMPTY
  }
}

const EMPTY_ASKS: ReviewBoardAsksFile = {
  version: 1,
  updated_at: '',
  watches: {},
  asks: [],
}

const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const obj = (v: unknown): Record<string, unknown> =>
  typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {}
const at = (iso: string) => Date.parse(iso) || 0
const prKey = (x: { repo: string; pr: number }) => `${x.repo}#${x.pr}`

const cleanAsk = (raw: unknown): ReviewBoardAsk | undefined => {
  const a = obj(raw)
  if (typeof a.pr !== 'number' || typeof a.repo !== 'string') return undefined
  if (typeof a.watch !== 'string' || typeof a.found_at !== 'string') {
    return undefined
  }
  const s = obj(a.slack)
  return {
    repo: a.repo,
    pr: a.pr,
    url: str(a.url),
    title: typeof a.title === 'string' ? a.title : null,
    author: typeof a.author === 'string' ? a.author : null,
    watch: a.watch,
    slack:
      typeof s.channel === 'string' && typeof s.ts === 'string'
        ? { channel: s.channel, ts: s.ts }
        : null,
    found_at: a.found_at,
  }
}

export const parseAsks = (text: string | undefined): ReviewBoardAsksFile => {
  if (!text) return EMPTY_ASKS
  try {
    const raw = obj(JSON.parse(text))
    const watches: ReviewBoardAsksFile['watches'] = {}
    for (const [id, v] of Object.entries(obj(raw.watches))) {
      const w = obj(v)
      if (typeof w.last_checked !== 'string') continue
      watches[id] = {
        last_checked: w.last_checked,
        found: typeof w.found === 'number' ? w.found : 0,
      }
    }
    return {
      version: 1,
      updated_at: str(raw.updated_at),
      watches,
      asks: list(raw.asks).flatMap(x => cleanAsk(x) ?? []),
    }
  } catch {
    return EMPTY_ASKS
  }
}

// An entry is untaken until the queue session's asks_through reaches it.
const untaken = (board: ReviewBoardFile, a: ReviewBoardAsk) =>
  board.asks_through === null || at(a.found_at) > at(board.asks_through)

// The board as the pane shows it: each untaken entry whose PR has no row
// draws as a `new` row, one per PR from its earliest entry. A watch takes
// its last_checked and found from the asks file when the file is newer.
export const view = (
  board: ReviewBoardFile,
  asks: ReviewBoardAsksFile,
): ReviewBoardFile => {
  const rows = new Set(board.rows.map(prKey))
  const first = new Map<string, ReviewBoardAsk>()
  for (const a of asks.asks) {
    if (!untaken(board, a) || rows.has(prKey(a))) continue
    const had = first.get(prKey(a))
    if (!had || at(a.found_at) < at(had.found_at)) first.set(prKey(a), a)
  }
  const policy = (id: string) =>
    board.watches.find(w => w.id === id)?.policy ?? 'review'
  const derived = [...first.values()].map(
    (a): ReviewBoardRow => ({
      repo: a.repo,
      pr: a.pr,
      title: a.title ?? '',
      author: a.author ?? '-',
      stage: 'new',
      next: 'crew',
      head: null,
      last: { at: a.found_at, text: `new ask from ${a.watch}` },
      url: a.url,
      watch: a.watch,
      policy: policy(a.watch),
    }),
  )
  const watches = board.watches.map(w => {
    const x = asks.watches[w.id]
    if (!x) return w
    if (w.last_checked !== null && at(x.last_checked) <= at(w.last_checked)) {
      return w
    }
    return { ...w, last_checked: x.last_checked, found: x.found }
  })
  return { ...board, watches, rows: [...board.rows, ...derived] }
}

const fit = (text: string, width: number) =>
  text.length <= width ? text : `${text.slice(0, Math.max(0, width - 1))}…`

const pad = (text: string, width: number) => fit(text, width).padEnd(width)

const when = (iso: string | null) =>
  iso ? iso.replace('T', ' ').slice(0, 16) : '-'

// Fixed cells, in order: pr, stage, next, policy. Title and last event share
// what is left.
const CELLS = [6, 10, 7, 7] as const
const GAP = 1

// A row is the fixed cells, one gap between each of the six cells, then the
// title and the last event. `indent` is what a caller puts before the row.
const widths = (columns: number, indent = 0) => {
  // The four fixed cells, the title and the last event: six cells, five gaps.
  const gaps = GAP * (CELLS.length + 2 - 1)
  const fixed = CELLS.reduce((a, b) => a + b, 0) + gaps
  const left = Math.max(LAST_MIN + 10, columns - indent - fixed)
  const title = Math.min(TITLE_CAP, Math.max(10, left - LAST_MIN))
  return { title, last: left - title }
}

const watchLine = (x: ReviewBoardWatch) =>
  [
    x.id,
    x.source,
    x.policy,
    x.status,
    `since ${when(x.since)}`,
    `checked ${when(x.last_checked)}`,
    `found ${x.found}`,
  ].join(' · ')

export const textTable = (
  board: ReviewBoardFile,
  columns = 120,
  notes: readonly string[] = [],
) => {
  const w = widths(columns, 2)
  const line = (r: ReviewBoardRow) =>
    [
      pad(`#${r.pr}`, CELLS[0]),
      pad(r.stage, CELLS[1]),
      pad(r.next, CELLS[2]),
      pad(r.policy, CELLS[3]),
      pad(r.title, w.title),
      fit(r.last.text, w.last),
    ].join(' '.repeat(GAP))
  const s = sections(board)
  const out = [statusLine(board), '', 'Watching']
  if (board.watches.length === 0) out.push('  none')
  for (const x of board.watches) out.push(`  ${fit(watchLine(x), columns - 2)}`)
  for (const n of notes) out.push(`  ${fit(n, columns - 2)}`)
  out.push('', 'Needs you')
  if (s.needsYou.length === 0) out.push('  none')
  for (const r of s.needsYou) out.push(`  ${line(r)}`)
  out.push('', 'In flight')
  if (s.inFlight.length === 0) out.push('  none')
  for (const r of s.inFlight) out.push(`  ${line(r)}`)
  out.push('', `Done (${s.done.length}, hidden)`)
  return out.map(l => fit(l, columns)).join('\n')
}

// What the poll last saw and whether it opened the pane: both start afresh
// at a reload, and the next tick draws again.
let last: string | undefined
// The board the last tick parsed: the pane of an armed session draws from it.
let current: ReviewBoardFile | undefined
let opened = false
let timer: unknown
// The source poll's timer, whether a poll runs now, and the lines it shows
// in Watching. A reload starts them afresh, and the next arm polls again.
let watcher: unknown
let watching = false
let notes: string[] = []

const queueDir = async ($: Engine) => {
  const root = await $.env.get('CREW_RECORD_ROOT')
  const home = await $.env.get('HOME')
  return `${root || `${home ?? ''}/.claude/crew`}/queue`
}

const readText = async ($: Engine, path: string) => {
  try {
    const text = await $.fs.read(path)
    return typeof text === 'string' ? text : undefined
  } catch {
    return undefined
  }
}

const load = async ($: Engine) =>
  readText($, `${await queueDir($)}/board.json`)

const loadAsks = async ($: Engine) =>
  readText($, `${await queueDir($)}/asks.json`)

// The board the pane shows: the board file and the asks file together.
const loadView = async ($: Engine) =>
  view(parseBoard(await load($)), parseAsks(await loadAsks($)))

const tick = async ($: Engine) => {
  const text = (await load($)) ?? ''
  const asks = (await loadAsks($)) ?? ''
  const seen = [text, asks, ...notes].join('\n')
  if (seen === last) return
  last = seen
  const board = view(parseBoard(text), parseAsks(asks))
  current = board
  const open = board.rows.filter(r => !isDone(r))
  $.ui.status(open.length === 0 ? undefined : statusLine(board))
  if (!opened && open.length > 0) {
    opened = true
    await $.ui.open({ id: PANE, title: 'Review board' })
  }
  $.ui.invalidate('ui.render')
}

// The token never leaves this function's callers: no file, prompt, pane,
// log or store value holds it.
const readToken = async ($: Engine) => {
  const home = await $.env.get('HOME')
  const text = await readText($, `${home ?? ''}/.claude/secrets/slack-token`)
  return (text ?? '').trim() || undefined
}

type Candidate = Omit<ReviewBoardAsk, 'found_at'>

// A Slack ts as seconds and microseconds, so two compare exactly.
const tsParts = (ts: string) => {
  const [s = '0', f = ''] = ts.split('.')
  return [Number(s), Number(f.padEnd(6, '0').slice(0, 6))] as const
}
const tsAfter = (a: string, b: string) => {
  const [as, af] = tsParts(a)
  const [bs, bf] = tsParts(b)
  return as > bs || (as === bs && af > bf)
}
const unixTs = (iso: string) => ((Date.parse(iso) || 0) / 1000).toFixed(6)

const slackGet = async (
  $: Engine,
  token: string,
  method: string,
  params: Record<string, string>,
): Promise<{ body: Record<string, unknown> } | { error: string }> => {
  const query = Object.entries(params)
    .filter(([, v]) => v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&')
  const res = await $.http.fetch(`${SLACK_API}/${method}?${query}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) return { error: `HTTP ${res.status}` }
  let body: Record<string, unknown>
  try {
    body = obj(JSON.parse(res.text))
  } catch {
    return { error: 'an answer that is not JSON' }
  }
  if (body.ok !== true) return { error: str(body.error, 'not ok') }
  return { body }
}

const nextCursor = (body: Record<string, unknown>) =>
  str(obj(body.response_metadata).next_cursor)

const channelId = async ($: Engine, token: string, channel: string) => {
  const key = `slack-channel:${channel}`
  const kept = await $.store.get(key)
  if (typeof kept === 'string') return kept
  let cursor = ''
  for (let page = 0; page < LIST_PAGES; page++) {
    const r = await slackGet($, token, 'conversations.list', {
      types: 'public_channel',
      exclude_archived: 'true',
      limit: '1000',
      cursor,
    })
    if ('error' in r) return r
    const hit = list(r.body.channels)
      .map(obj)
      .find(c => c.name === channel)
    if (hit && typeof hit.id === 'string') {
      await $.store.set(key, hit.id)
      return hit.id
    }
    cursor = nextCursor(r.body)
    if (!cursor) break
  }
  return undefined
}

// The history cursor of a watch: `oldest` moves only after a poll reads the
// last page. `page` is where a poll the page cap stopped goes on.
type SlackCursor = { oldest: string; page: string | null; newest: string | null }

// One Slack watch: its PR messages, or undefined when the poll is skipped.
const pollSlack = async (
  $: Engine,
  token: string,
  w: ReviewBoardWatch,
): Promise<Candidate[] | undefined> => {
  const channel = w.source.slice('slack:#'.length)
  const id = await channelId($, token, channel)
  if (id === undefined) {
    notes.push(`#${channel}: not found`)
    return undefined
  }
  if (typeof id !== 'string') {
    notes.push(`#${channel}: Slack error ${id.error}`)
    return undefined
  }
  const key = `slack-cursor:${w.id}`
  const saved = obj(await $.store.get(key))
  const oldest = typeof saved.oldest === 'string' ? saved.oldest : unixTs(w.since)
  let page = typeof saved.page === 'string' ? saved.page : ''
  let newest = typeof saved.newest === 'string' ? saved.newest : null
  const got: Candidate[] = []
  for (let i = 0; i < HISTORY_PAGES; i++) {
    const r = await slackGet($, token, 'conversations.history', {
      channel: id,
      oldest,
      limit: '200',
      cursor: page,
    })
    if ('error' in r) {
      notes.push(`#${channel}: Slack error ${r.error}`)
      return undefined
    }
    for (const m of list(r.body.messages).map(obj)) {
      const ts = str(m.ts)
      if (!ts) continue
      if (newest === null || tsAfter(ts, newest)) newest = ts
      if (list(m.reactions).some(x => obj(x).name === 'done')) continue
      const prs = new Set<string>()
      for (const [, owner, repo, n] of str(m.text).matchAll(PR_LINK)) {
        const key = `${owner}/${repo}#${n}`
        if (prs.has(key)) continue
        prs.add(key)
        got.push({
          repo: `${owner}/${repo}`,
          pr: Number(n),
          url: `https://github.com/${owner}/${repo}/pull/${n}`,
          title: null,
          author: null,
          watch: w.id,
          slack: { channel: id, ts },
        })
      }
    }
    page = nextCursor(r.body)
    if (!page) break
  }
  const cursor: SlackCursor = page
    ? { oldest, page, newest }
    : { oldest: newest ?? oldest, page: null, newest: null }
  await $.store.set(key, cursor)
  return got
}

// The GitHub review requests: each open PR, or undefined when gh failed.
const pollGithub = async (
  $: Engine,
  w: ReviewBoardWatch,
): Promise<Candidate[] | undefined> => {
  const run = await $.process.run(GH_SEARCH)
  let prs: unknown[] | undefined
  try {
    prs = run.exitCode === 0 ? list(JSON.parse(run.stdout)) : undefined
  } catch {
    prs = undefined
  }
  if (prs === undefined) {
    notes.push(`${w.id}: gh search failed`)
    return undefined
  }
  return prs.map(obj).flatMap(p => {
    const repo = str(obj(p.repository).nameWithOwner)
    if (!repo || typeof p.number !== 'number') return []
    return [
      {
        repo,
        pr: p.number,
        url: str(p.url),
        title: typeof p.title === 'string' ? p.title : null,
        author: str(obj(p.author).login) || null,
        watch: w.id,
        slack: null,
      },
    ]
  })
}

// One poll of every active watch: write the asks file, then hand each new
// ask to this session with one prompt.
const sweep = async ($: Engine) => {
  notes = []
  const token = await readToken($)
  if (!token) {
    notes = [NO_TOKEN]
    return
  }
  const board = parseBoard(await load($))
  const owner = str(obj(board.owner).session_id)
  if (!owner || owner !== (await $.session.id())) return
  const dir = await queueDir($)
  const file = parseAsks(await loadAsks($))
  const rows = new Set(board.rows.map(prKey))
  const kept = file.asks.filter(a => untaken(board, a))
  const added: ReviewBoardAsk[] = []
  const fresh: ReviewBoardAsk[] = []
  const watches = { ...file.watches }
  const now = await $.clock.now()
  // Each new found_at is later than every found_at the file held.
  let latest = Math.max(
    0,
    ...file.asks.map(a => at(a.found_at)),
    board.asks_through === null ? 0 : at(board.asks_through),
  )
  const stamp = () => {
    latest = Math.max(now, latest + 1)
    return new Date(latest).toISOString()
  }
  const slackKey = (a: Candidate) =>
    `${prKey(a)}@${a.slack?.channel ?? ''}/${a.slack?.ts ?? ''}`
  for (const w of board.watches) {
    if (w.status !== 'active') continue
    let got: Candidate[] | undefined
    if (w.source.startsWith('slack:#')) got = await pollSlack($, token, w)
    else if (w.source === 'github:review-requests') got = await pollGithub($, w)
    else continue
    if (got === undefined) continue
    const foundKey = `found:${w.id}`
    const count = obj(await $.store.get(foundKey))
    let found =
      count.since === w.since && typeof count.count === 'number' ? count.count : 0
    for (const c of got) {
      const all = [...kept, ...added]
      if (c.slack) {
        if (all.some(a => a.slack && slackKey(a) === slackKey(c))) continue
      } else if (rows.has(prKey(c)) || all.some(a => prKey(a) === prKey(c))) {
        continue
      }
      const entry = { ...c, found_at: stamp() }
      if (!rows.has(prKey(c)) && !all.some(a => prKey(a) === prKey(c))) {
        fresh.push(entry)
      }
      added.push(entry)
      found += 1
    }
    await $.store.set(foundKey, { since: w.since, count: found })
    watches[w.id] = { last_checked: new Date(now).toISOString(), found }
  }
  const out: ReviewBoardAsksFile = {
    version: 1,
    updated_at: new Date(now).toISOString(),
    watches,
    asks: [...kept, ...added],
  }
  // A reader never sees half a file: write a temp file, then move it.
  const path = `${dir}/asks.json`
  const tmp = `${path}.tmp`
  await $.fs.write(tmp, `${JSON.stringify(out, null, 2)}\n`)
  const moved = await $.process.run(['mv', tmp, path])
  if (moved.exitCode !== 0) {
    notes.push('asks.json: the move failed')
    return
  }
  if (fresh.length === 0) return
  const named = fresh.map(a => `${prKey(a)} from ${a.watch}`).join(', ')
  void $.prompt.submit({
    text: `Crew review-queue ask: ${named}. Run the wakeup loop of crew:review-queue.`,
  })
}

// A throw must not end the interval, so each poll catches its own.
const watch = async ($: Engine) => {
  if (watching) return
  watching = true
  try {
    await sweep($)
  } catch {
    // The next period polls again.
  } finally {
    watching = false
  }
  await tick($)
}

const poll = async ($: Engine) => {
  if (!timer) timer = $.clock.every(POLL_MS, () => void tick($))
  if (!watcher) {
    watcher = $.clock.every(WATCH_MS, () => void watch($))
    await watch($)
  }
  await tick($)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'review-board',
      description: 'Open the review board pane, or print it as text',
    })
    if (await read($, armed)) await poll($)
    return next(e)
  })

  on('skill.prompt', async ($, e, next) => {
    if (isQueueSkill(e.skill)) {
      await update($, armed, () => true)
      await poll($)
    }
    return next(e)
  })

  on('command.run', { command: 'review-board' }, async ($, e) => {
    // A pane a command opens is placed at any width, so the width decides.
    const columns = e.presentation.columns
    if (columns < MIN_PANE_COLUMNS) {
      return { text: textTable(await loadView($), columns, notes) }
    }
    const placed = await $.ui.open({ id: PANE, title: 'Review board' })
    if (placed.isPlaced) return { text: 'Review board pane opened.' }
    return {
      text: placed.reason || 'The review board pane did not open.',
    }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    // Only the timer and the skill prompt run `tick`; a render never does. An
    // armed session draws from the last tick, so a render reads no file. A
    // session that is not armed reads the file once per render.
    const isArmed = await read($, armed)
    if (isArmed && !timer) timer = $.clock.every(POLL_MS, () => void tick($))
    const board = (isArmed && current) || (await loadView($))
    const s = sections(board)
    const shown = await read($, showDone)
    const w = widths(e.props.bodyColumns)

    const cell = (width: number, text: string, color?: string) => (
      <Box width={width} flexShrink={0}>
        <Text color={color} wrap="truncate">
          {fit(text, width)}
        </Text>
      </Box>
    )

    const rowView = (r: ReviewBoardRow) => (
      <Box key={`${r.repo}#${r.pr}`} gap={GAP}>
        {cell(CELLS[0], `#${r.pr}`)}
        {cell(CELLS[1], r.stage)}
        {cell(CELLS[2], r.next)}
        {cell(CELLS[3], r.policy, r.policy === 'assist' ? 'yellow' : undefined)}
        {cell(w.title, r.title)}
        {cell(w.last, r.last.text)}
      </Box>
    )

    // In flight takes what is left of the window. Every other line counts:
    // four headings, the Watching and Needs you rows (or their one empty
    // line), the watcher's notes, the Done button, the Done rows when shown,
    // and the "+N more" line when In flight overflows.
    const used =
      4 +
      Math.max(1, board.watches.length) +
      notes.length +
      Math.max(1, s.needsYou.length) +
      1 +
      (shown ? s.done.length : 0)
    let room = Math.max(1, e.props.scroll.bodyRows - used)
    if (s.inFlight.length > room) room = Math.max(1, room - 1)
    const flight = s.inFlight.slice(0, room)
    const hidden = s.inFlight.length - flight.length

    return (
      <Box flexDirection="column">
        <Text bold>Watching</Text>
        {board.watches.length === 0 && <Text dimColor>No watches.</Text>}
        {board.watches.map(x => (
          <Text
            key={x.id}
            color={x.policy === 'assist' ? 'yellow' : undefined}
            wrap="truncate"
          >
            {fit(watchLine(x), e.props.bodyColumns)}
          </Text>
        ))}
        {notes.map(n => (
          <Text key={`note:${n}`} dimColor wrap="truncate">
            {fit(n, e.props.bodyColumns)}
          </Text>
        ))}
        <Text bold>Needs you</Text>
        {s.needsYou.length === 0 && <Text dimColor>Nothing needs you.</Text>}
        {s.needsYou.map(rowView)}
        <Text bold>In flight</Text>
        {flight.length === 0 && <Text dimColor>Nothing in flight.</Text>}
        {flight.map(rowView)}
        {hidden > 0 && <Text dimColor>{`+${hidden} more`}</Text>}
        <Text bold>Done</Text>
        <Button key="toggle-done" onPress={() => update($, showDone, v => !v)}>
          {`${shown ? 'Hide' : 'Show'} done (${s.done.length})`}
        </Button>
        {shown && s.done.map(rowView)}
      </Box>
    )
  })
}
