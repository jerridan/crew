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
// A session the skill prompt armed has this long to see the board name it.
const ARM_WINDOW_MS = 120_000
// A Slack call that has not answered by then fails, so the poll ends.
const FETCH_MS = 30_000
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
  '--limit',
  '100',
  '--json',
  'number,repository,url,title,author',
]
const PR_LINK = /https?:\/\/github\.com\/([\w.-]+)\/([\w.-]+)\/pull\/(\d+)/g
// A Slack message with one of these reactions holds no new ask: someone
// already approved (✅) or handled (`done`) its PR.
const DONE_REACTIONS = new Set(['white_check_mark', 'done'])

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
// When this session armed, in ms. A later owner than that disarms it.
const armedAt = atom({ plugin: 'crew', key: 'armedAt' } as const, 0, {
  shape: 'armed-at-1',
})

// When a skill prompt armed this session, in ms, until the board names it.
// 0 holds no time. It is an atom so a reload keeps the arming window.
const skillArmedAt = atom(
  { plugin: 'crew', key: 'skillArmedAt' } as const,
  0,
  { shape: 'skill-armed-at-1' },
)

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
    done: sorted
      .filter(isDone)
      .sort((a, b) => b.last.at.localeCompare(a.last.at)),
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

const str = (v: unknown, fallback = '') => (typeof v === 'string' ? v : fallback)
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : [])
const obj = (v: unknown): Record<string, unknown> =>
  typeof v === 'object' && v !== null ? (v as Record<string, unknown>) : {}

// A row or watch the file holds in part is made safe here, once, so no other
// code reads a field that may be missing. A row with no known stage or no
// number is dropped: the board cannot place it.
const cleanRow = (raw: unknown): ReviewBoardRow | undefined => {
  const r = obj(raw)
  if (typeof r.pr !== 'number') return undefined
  if (!STAGES.includes(r.stage as ReviewBoardStage)) return undefined
  const last = obj(r.last)
  return {
    repo: str(r.repo),
    pr: r.pr,
    title: str(r.title),
    author: str(r.author),
    stage: r.stage as ReviewBoardStage,
    next: str(r.next, '-') as ReviewBoardRow['next'],
    head: typeof r.head === 'string' ? r.head : null,
    last: { at: str(last.at), text: str(last.text) },
    url: str(r.url),
    watch: typeof r.watch === 'string' ? r.watch : null,
    policy: r.policy === 'assist' ? 'assist' : 'review',
  }
}

const cleanWatch = (raw: unknown): ReviewBoardWatch | undefined => {
  const w = obj(raw)
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

// Fixed cells, in order: pr, stage, next, author, then title, the age, and the
// last event. Title and last event share what is left.
const CELLS = [6, 10, 7, 8] as const
const AGE = 5
const GAP = 1
const COUNT = CELLS.length + 3
const HEAD = ['PR', 'stage', 'next', 'author', 'title', 'age', 'last event']

// A row is the fixed cells, one gap between each of the seven cells, then the
// title, the age and the last event. `indent` is what a caller puts before
// the row.
const widths = (columns: number, indent = 0) => {
  const gaps = GAP * (COUNT - 1)
  const fixed = CELLS.reduce((a, b) => a + b, 0) + AGE + gaps
  const left = Math.max(LAST_MIN + 10, columns - indent - fixed)
  const title = Math.min(TITLE_CAP, Math.max(10, left - LAST_MIN))
  return { title, last: left - title }
}

// The short age of a time: 15m, 20h, 3d. A time that does not parse is `-`.
export const ago = (iso: string | null, now: number) => {
  const t = at(iso ?? '')
  if (!t) return '-'
  const min = Math.max(0, Math.floor((now - t) / 60_000))
  if (min < 60) return `${min}m`
  if (min < 24 * 60) return `${Math.floor(min / 60)}h`
  return `${Math.floor(min / (24 * 60))}d`
}

const sourceName = (source: string) => {
  if (source.startsWith('slack:')) return source.slice('slack:'.length)
  if (source === 'github:review-requests') return 'review requests'
  if (source === 'direct') return 'direct asks'
  return source
}

const active = (board: ReviewBoardFile) =>
  board.watches.filter(w => w.status === 'active')

export const topLine = (board: ReviewBoardFile, now: number) => {
  const sources = active(board).map(w => sourceName(w.source))
  const where = sources.length === 0 ? '' : `${sources.join(' + ')}  `
  const updated = board.updated_at
    ? `updated ${ago(board.updated_at, now)} ago`
    : 'updated -'
  return `Review board  ${where}·  ${updated}`
}

const checkedText = (x: ReviewBoardWatch, now: number) =>
  x.last_checked ? `checked ${ago(x.last_checked, now)} ago` : 'not checked yet'

// The policy of a row, when it differs from the policy of its watch.
const marker = (board: ReviewBoardFile, r: ReviewBoardRow) => {
  const w = board.watches.find(x => x.id === r.watch)
  return w && w.policy !== r.policy ? `[${r.policy}] ` : ''
}

const STAGE_COLOR: Partial<Record<ReviewBoardStage, string>> = {
  approve: 'magenta',
  blocked: 'red',
  fixing: 'yellow',
  reviewing: 'cyan',
  rereview: 'cyan',
  queued: 'blue',
}

export const textTable = (
  board: ReviewBoardFile,
  columns = 120,
  notes: readonly string[] = [],
  now = Date.now(),
) => {
  const w = widths(columns, 2)
  const cells = (c: string[]) =>
    [
      pad(c[0], CELLS[0]),
      pad(c[1], CELLS[1]),
      pad(c[2], CELLS[2]),
      pad(c[3], CELLS[3]),
      pad(c[4], w.title),
      pad(c[5], AGE),
      fit(c[6], w.last),
    ].join(' '.repeat(GAP))
  const line = (r: ReviewBoardRow) =>
    cells([
      `#${r.pr}`,
      r.stage,
      r.next,
      r.author || '-',
      r.title,
      ago(r.last.at, now),
      `${marker(board, r)}${r.last.text}`,
    ])
  const s = sections(board)
  const out = [topLine(board, now), `Watching ${active(board).length}`]
  for (const x of active(board)) {
    out.push(
      `  ${fit(`${sourceName(x.source)}  ${x.policy}  ${checkedText(x, now)}`, columns - 2)}`,
    )
  }
  for (const n of notes) out.push(`  ${fit(n, columns - 2)}`)
  out.push('', `  ${cells(HEAD)}`, '')
  out.push(`Needs you ${s.needsYou.length}`)
  if (s.needsYou.length === 0) out.push('  Nothing needs you.')
  for (const r of s.needsYou) out.push(`  ${line(r)}`)
  out.push('', `In flight ${s.inFlight.length}`)
  for (const r of s.inFlight) out.push(`  ${line(r)}`)
  out.push('', `Done ${s.done.length}`)
  for (const r of s.done) out.push(`  ${line(r)}`)
  return out.map(l => fit(l, columns)).join('\n')
}

// What the poll last saw and whether it opened the pane: both start afresh
// at a reload, and the next tick draws again.
let last: string | undefined
// The minute of the last redraw: the clock alone redraws the pane each minute.
let lastMinute = -1
// The board the last tick parsed: the pane of an armed session draws from it.
let current: ReviewBoardFile | undefined
let opened = false
let timer: unknown
// The slow timer of a session with no pane and no arm: it checks the owner.
let idle: unknown
// True from an invalidate until the next render: a render that does not come
// means the pane is closed.
let awaitingRender = false
// The source poll's timer, whether a poll runs now, and the lines it shows
// in Watching. A reload starts them afresh, and the next arm polls again.
let watcher: unknown
let watching = false
let notes: string[] = []
// The PRs of a prompt the engine refused, each with its words in the prompt.
// The next poll names each one again while it has an untaken entry and no
// row, or a row at next: author.
let unsent = new Map<string, string>()

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

// True once a render drew the pane: its reload runs for any session.
let paneShown = false

// An armed session leaves when the board names another non-empty session
// that took it after this session armed. An equal time goes to the greater
// session id, so exactly one of two sessions stays. A session the skill just
// armed has an earlier armedAt than its own Start writes, so it stays.
const superseded = async ($: Engine, board: ReviewBoardFile) => {
  const owner = str(obj(board.owner).session_id)
  const me = await $.session.id()
  if (!owner || owner === me) return false
  const since = at(str(obj(board.owner).since))
  const armTime = await read($, armedAt)
  return since > armTime || (since === armTime && owner > me)
}

// The skill path arms at the clock. The owner path arms at the board's
// owner.since, so the mod orders owners by the value the skill orders by.
const arm = async ($: Engine, since?: number) => {
  const armTime = since ?? (await $.clock.now())
  await update($, skillArmedAt, () => (since === undefined ? armTime : 0))
  await update($, armed, () => true)
  await update($, armedAt, () => armTime)
  last = undefined
  await poll($)
}

const disarm = async ($: Engine) => {
  await update($, armed, () => false)
  if (watcher) (watcher as { cancel: () => void }).cancel()
  watcher = undefined
  opened = false
  last = undefined
  lastMinute = -1
  await update($, skillArmedAt, () => 0)
  notes = []
  unsent = new Map()
  current = undefined
  $.ui.status(undefined)
}

// One read of the board each POLL_MS. An armed session sets the status line
// and opens the pane. A session the board names as owner arms. An open pane
// of any session redraws on a change.
const tick = async ($: Engine) => {
  const text = (await load($)) ?? ''
  const parsed = parseBoard(text)
  // A pane that was told to draw and did not is closed.
  if (awaitingRender) {
    paneShown = false
    awaitingRender = false
    // A pane opened again draws from a fresh read, not from this one.
    current = undefined
    last = undefined
  }
  let isArmed = await read($, armed)
  const owner = str(obj(parsed.owner).session_id)
  const me = await $.session.id()
  if (isArmed && owner === me) {
    // The board names this session: its own since orders it from here on.
    if ((await read($, skillArmedAt)) > 0) {
      await update($, armedAt, () => at(str(obj(parsed.owner).since)))
    }
    await update($, skillArmedAt, () => 0)
  }
  const skillTime = isArmed ? await read($, skillArmedAt) : 0
  if (
    isArmed &&
    ((await superseded($, parsed)) ||
      (skillTime > 0 && (await $.clock.now()) - skillTime > ARM_WINDOW_MS))
  ) {
    await disarm($)
    isArmed = false
  }
  if (!isArmed) {
    if (owner && owner === me) {
      await arm($, at(str(obj(parsed.owner).since)))
      return
    }
    if (!paneShown) {
      if (timer) (timer as { cancel: () => void }).cancel()
      timer = undefined
      return
    }
  }
  const asks = (await loadAsks($)) ?? ''
  const seen = [text, asks, ...notes].join('\n')
  // Every age in the pane is read at render time, so a new minute redraws the
  // pane when no file moved. The status line holds no age: it sets on a change.
  const minute = Math.floor((await $.clock.now()) / 60_000)
  if (seen === last) {
    if (minute === lastMinute) return
    lastMinute = minute
    awaitingRender = paneShown
    $.ui.invalidate('ui.render')
    return
  }
  last = seen
  lastMinute = minute
  const board = view(parsed, parseAsks(asks))
  current = board
  if (isArmed) {
    const open = board.rows.filter(r => !isDone(r))
    $.ui.status(open.length === 0 ? undefined : statusLine(board))
    if (!opened && open.length > 0) {
      opened = true
      await $.ui.open({ id: PANE, title: 'Review board' })
    }
  }
  awaitingRender = paneShown
  $.ui.invalidate('ui.render')
}

// The 3 s timer runs for an armed session or an open pane. Any other session
// checks the owner on the slow timer, within the 60 s arming bound.
const ensureTimer = ($: Engine) => {
  if (!timer) timer = $.clock.every(POLL_MS, () => void tick($))
}

const ensureIdle = ($: Engine) => {
  if (!idle) idle = $.clock.every(WATCH_MS, () => void tick($))
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
const unixTs = (ms: number) => (ms / 1000).toFixed(6)

// The fetch, or a rejection when it has not answered in FETCH_MS.
const bounded = <T,>($: Engine, work: Promise<T>) =>
  new Promise<T>((resolve, reject) => {
    const alarm = $.clock.after(FETCH_MS, () =>
      reject(new Error('no answer in time')),
    )
    work.then(
      v => {
        alarm.cancel()
        resolve(v)
      },
      (err: unknown) => {
        alarm.cancel()
        reject(err)
      },
    )
  })

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
  const res = await bounded(
    $,
    $.http.fetch(`${SLACK_API}/${method}?${query}`, {
      method: 'GET',
      headers: { Authorization: `Bearer ${token}` },
    }),
  )
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
// last page. `page` is where a poll the page cap stopped goes on. `since` is
// the watch's since: a watch added again with a new since starts afresh.
type SlackCursor = {
  since: string
  oldest: string
  page: string | null
  newest: string | null
}

// A store value the sweep writes only after the asks file is in place.
type Kept = { key: string; value: unknown }

// One Slack watch: its PR messages and its new cursor, or undefined when the
// poll is skipped. `now` is the time of this poll. `outage` is true when the
// board's last_checked is the queue session's own poll, not the mod's.
const pollSlack = async (
  $: Engine,
  token: string,
  w: ReviewBoardWatch,
  now: number,
  outage: boolean,
): Promise<{ got: Candidate[]; cursor: Kept } | undefined> => {
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
  const kept = obj(await $.store.get(key))
  // After an outage, a board last_checked later than the kept oldest is
  // where the queue session's own poll stopped: the poll starts there, and
  // the kept page and newest, which belong to the old oldest, go.
  const checked = at(w.last_checked ?? '')
  const behind =
    outage &&
    typeof kept.oldest === 'string' &&
    checked > 0 &&
    tsAfter(unixTs(checked), kept.oldest)
  const saved = kept.since === w.since && !behind ? kept : {}
  // With no cursor, the poll starts at the later of since and the board's
  // last_checked, which the queue session's own poll moved. With neither a
  // time, it starts now, so it never reads the channel's whole history.
  const start = Math.max(at(w.since), checked) || now
  const oldest = typeof saved.oldest === 'string' ? saved.oldest : unixTs(start)
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
      // A person who approved the PR marks its message with ✅, and a person
      // who handled it marks it with `done`. Either way it needs no review.
      if (list(m.reactions).some(x => DONE_REACTIONS.has(str(obj(x).name)))) continue
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
    ? { since: w.since, oldest, page, newest }
    : { since: w.since, oldest: newest ?? oldest, page: null, newest: null }
  return { got, cursor: { key, value: cursor } }
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
  // A Slack message for a row at next: author re-triages it, so it prompts.
  const author = new Set(
    board.rows.filter(r => r.next === 'author').map(prKey),
  )
  const kept = file.asks.filter(a => untaken(board, a))
  const slackKey = (a: Candidate) =>
    `${prKey(a)}@${a.slack?.channel ?? ''}/${a.slack?.ts ?? ''}`
  // The PRs and the Slack messages the asks file holds an entry for.
  const keys = new Set(kept.map(prKey))
  const slackKeys = new Set(kept.filter(a => a.slack).map(slackKey))
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
  // The cursors and found counts: written only after the asks file is in
  // place, so a failed write reads the same messages again at the next poll.
  const later: Kept[] = []
  for (const w of board.watches) {
    if (w.status !== 'active') continue
    let got: Candidate[] | undefined
    // The wakeup loop copies the mod's last_checked to the board, so only a
    // board last_checked later than the asks file's is the queue session's
    // own poll, during an outage.
    const outage =
      at(w.last_checked ?? '') > at(file.watches[w.id]?.last_checked ?? '')
    // A watch whose source throws is skipped, and the others still poll.
    try {
      if (w.source.startsWith('slack:#')) {
        const r = await pollSlack($, token, w, now, outage)
        if (r) later.push(r.cursor)
        got = r?.got
      } else if (w.source === 'github:review-requests') {
        got = await pollGithub($, w)
      } else continue
    } catch {
      notes.push(`${w.id}: poll failed`)
      continue
    }
    if (got === undefined) continue
    const foundKey = `found:${w.id}`
    const count = obj(await $.store.get(foundKey))
    // After an outage, or with no count for this since, the count goes on
    // from the board's, which the queue session's own poll kept.
    let found =
      !outage && count.since === w.since && typeof count.count === 'number'
        ? count.count
        : w.found
    for (const c of got) {
      const key = prKey(c)
      if (c.slack) {
        if (slackKeys.has(slackKey(c))) continue
      } else if (rows.has(key) || keys.has(key)) {
        continue
      }
      const entry = { ...c, found_at: stamp() }
      const isNew = !rows.has(key) || author.has(key)
      if (isNew && !keys.has(key)) fresh.push(entry)
      added.push(entry)
      keys.add(key)
      if (c.slack) slackKeys.add(slackKey(c))
      found += 1
    }
    later.push({ key: foundKey, value: { since: w.since, count: found } })
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
  try {
    await $.fs.write(tmp, `${JSON.stringify(out, null, 2)}\n`)
  } catch {
    notes.push('asks.json: the write failed')
    return
  }
  const moved = await $.process.run(['mv', tmp, path])
  if (moved.exitCode !== 0) {
    notes.push('asks.json: the move failed')
    return
  }
  // A failed store write reads the same messages again at the next poll, and
  // the dedupe drops them. The prompt still goes.
  try {
    for (const k of later) await $.store.set(k.key, k.value)
  } catch {
    notes.push('store: a cursor write failed')
  }
  // A refused PR that was taken or has a row now is not named again.
  const named = new Map<string, string>()
  for (const [k, words] of unsent) {
    if (keys.has(k) && (!rows.has(k) || author.has(k))) named.set(k, words)
  }
  for (const a of fresh) {
    if (!named.has(prKey(a))) named.set(prKey(a), `${prKey(a)} from ${a.watch}`)
  }
  unsent = new Map()
  if (named.size === 0) return
  const refused = () => {
    for (const [k, words] of named) unsent.set(k, words)
  }
  // The poll does not wait for the session's turn. A refused submit, as a
  // drop or a rejection, names its PRs again at the next poll.
  $.prompt
    .submit({
      text: `Crew review-queue ask: ${[...named.values()].join(', ')}. Run the wakeup loop of crew:review-queue.`,
    })
    .then(r => {
      if (r.drop !== undefined) refused()
    }, refused)
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
  try {
    await tick($)
  } catch {
    // The next tick draws again.
  }
}

const poll = async ($: Engine) => {
  ensureIdle($)
  ensureTimer($)
  if (!watcher) {
    watcher = $.clock.every(WATCH_MS, () => void watch($))
    // The first poll may take as long as a fetch, so arming does not wait.
    void watch($)
  }
  await tick($)
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'review-board',
      description: 'Open the review board pane, or print it as text',
    })
    ensureIdle($)
    if (await read($, armed)) await poll($)
    return next(e)
  })

  on('skill.prompt', async ($, e, next) => {
    if (isQueueSkill(e.skill)) await arm($)
    return next(e)
  })

  on('command.run', { command: 'review-board' }, async ($, e) => {
    // A pane a command opens is placed at any width, so the width decides.
    const columns = e.presentation.columns
    if (columns < MIN_PANE_COLUMNS) {
      return { text: textTable(
          await loadView($),
          columns,
          notes,
          await $.clock.now(),
        ) }
    }
    const placed = await $.ui.open({ id: PANE, title: 'Review board' })
    if (placed.isPlaced) return { text: 'Review board pane opened.' }
    return {
      text: placed.reason || 'The review board pane did not open.',
    }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    // Only the timer and the skill prompt run `tick`; a render never does. The
    // timer reloads the board for an open pane, armed or not, so a render
    // draws from the last tick and reads a file only before the first tick.
    paneShown = true
    awaitingRender = false
    ensureTimer($)
    const board = current ?? (await loadView($))
    const now = await $.clock.now()
    const s = sections(board)
    const w = widths(e.props.bodyColumns)

    type Style = { color?: string; dimColor?: boolean }
    const cell = (width: number, text: string, style: Style = {}) => (
      <Box width={width} flexShrink={0}>
        <Text color={style.color} dimColor={style.dimColor} wrap="truncate">
          {fit(text, width)}
        </Text>
      </Box>
    )

    const rowView = (r: ReviewBoardRow) => {
      const done = isDone(r)
      const grey: Style = { dimColor: true }
      const stage: Style = done
        ? grey
        : STAGE_COLOR[r.stage]
          ? { color: STAGE_COLOR[r.stage] }
          : grey
      const flag = marker(board, r)
      return (
        <Box key={`${r.repo}#${r.pr}`} gap={GAP}>
          {cell(CELLS[0], `#${r.pr}`, done ? grey : {})}
          {cell(CELLS[1], r.stage, stage)}
          {cell(
            CELLS[2],
            r.next,
            done ? grey : r.next === 'you' ? { color: 'magenta' } : {},
          )}
          {cell(CELLS[3], r.author || '-', done ? grey : {})}
          {cell(w.title, r.title, done ? grey : {})}
          {cell(AGE, ago(r.last.at, now), done ? grey : {})}
          <Box width={w.last} flexShrink={0}>
            {flag && (
              <Text
                color={!done && r.policy === 'assist' ? 'yellow' : undefined}
                dimColor={done}
              >
                {flag}
              </Text>
            )}
            <Text dimColor={done} wrap="truncate">
              {fit(r.last.text, Math.max(1, w.last - flag.length))}
            </Text>
          </Box>
        </Box>
      )
    }

    const blank = (key: string) => <Text key={key}>{' '}</Text>
    const more = (key: string, n: number) => (
      <Text key={key} dimColor>{`+${n} more`}</Text>
    )

    // The room for In flight and Done: the height less every line that is
    // never cut. In flight takes what it needs first, and Done keeps room for
    // one row (and its "+N more" line) when it has more than it can show. A
    // list that does not fit shows the rows that fit, down to none, then
    // "+N more". With no room at all it shows neither: its heading has the
    // count.
    const watches = active(board)
    const fixed =
      1 + // top line
      1 + watches.length + // Watching
      notes.length +
      3 + // blank, header, blank
      1 + Math.max(1, s.needsYou.length) + // Needs you
      1 + 1 + // blank, In flight heading
      1 + 1 // blank, Done heading
    const room = Math.max(0, e.props.scroll.bodyRows - fixed)
    const f = s.inFlight.length
    const d = s.done.length
    const share = (n: number, space: number) =>
      n <= space
        ? { rows: n, more: false }
        : space <= 0
          ? { rows: 0, more: false }
          : { rows: space - 1, more: true }
    const reserve = d === 0 ? 0 : d === 1 ? 1 : 2
    const inFlight = share(f, Math.max(0, room - reserve))
    const done = share(
      d,
      Math.max(0, room - inFlight.rows - (inFlight.more ? 1 : 0)),
    )
    const flightRows = inFlight.rows
    const doneRows = done.rows
    const flight = s.inFlight.slice(0, flightRows)
    const doneShown = s.done.slice(0, doneRows)

    return (
      <Box flexDirection="column">
        <Text bold wrap="truncate">
          {fit(topLine(board, now), e.props.bodyColumns)}
        </Text>
        <Text bold>{`Watching ${watches.length}`}</Text>
        {watches.map(x => (
          <Box key={x.id} gap={2}>
            <Text>{sourceName(x.source)}</Text>
            <Text color={x.policy === 'assist' ? 'yellow' : undefined}>
              {x.policy}
            </Text>
            <Text dimColor>{checkedText(x, now)}</Text>
          </Box>
        ))}
        {notes.map((n, i) => (
          <Text key={`note:${i}`} dimColor wrap="truncate">
            {fit(n, e.props.bodyColumns)}
          </Text>
        ))}
        {blank('b1')}
        <Box gap={GAP}>
          {cell(CELLS[0], HEAD[0], { dimColor: true })}
          {cell(CELLS[1], HEAD[1], { dimColor: true })}
          {cell(CELLS[2], HEAD[2], { dimColor: true })}
          {cell(CELLS[3], HEAD[3], { dimColor: true })}
          {cell(w.title, HEAD[4], { dimColor: true })}
          {cell(AGE, HEAD[5], { dimColor: true })}
          {cell(w.last, HEAD[6], { dimColor: true })}
        </Box>
        {blank('b2')}
        <Text bold>{`Needs you ${s.needsYou.length}`}</Text>
        {s.needsYou.length === 0 && <Text dimColor>Nothing needs you.</Text>}
        {s.needsYou.map(rowView)}
        {blank('b3')}
        <Text bold>{`In flight ${f}`}</Text>
        {flight.map(rowView)}
        {inFlight.more && more('more-flight', f - flightRows)}
        {blank('b4')}
        <Text bold>{`Done ${d}`}</Text>
        {doneShown.map(rowView)}
        {done.more && more('more-done', d - doneRows)}
      </Box>
    )
  })
}
