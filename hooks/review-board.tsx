// The review board: a pane and a status line for the review queue session.
// The board file's schema is owned by skills/review-queue/references/board.md.
// This module only reads the file. The queue session writes it.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type {
  ReviewBoardFile,
  ReviewBoardRow,
  ReviewBoardStage,
  ReviewBoardWatch,
} from '../types/index'

type Engine = EngineInterface

const PANE = 'review-board'
const SKILL = 'review-queue'
const POLL_MS = 3000
const TITLE_CAP = 60
const LAST_MIN = 20
const MIN_PANE_COLUMNS = 110

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
  watches: [],
  rows: [],
}

export const parseBoard = (text: string | undefined): ReviewBoardFile => {
  if (!text) return EMPTY
  try {
    const raw = JSON.parse(text) as Partial<ReviewBoardFile>
    return {
      ...EMPTY,
      ...raw,
      watches: Array.isArray(raw.watches) ? raw.watches : [],
      rows: Array.isArray(raw.rows) ? raw.rows : [],
    }
  } catch {
    return EMPTY
  }
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
  const fixed = CELLS.reduce((a, b) => a + b, 0) + GAP * CELLS.length
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

export const textTable = (board: ReviewBoardFile, columns = 120) => {
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
let opened = false
let timer: { cancel: () => void } | undefined

const load = async ($: Engine) => {
  const root = await $.env.get('CREW_RECORD_ROOT')
  const home = await $.env.get('HOME')
  try {
    return await $.fs.read(
      `${root || `${home ?? ''}/.claude/crew`}/queue/board.json`,
    )
  } catch {
    return undefined
  }
}

const tick = async ($: Engine) => {
  const text = (await load($)) ?? ''
  if (text === last) return
  last = text
  const board = parseBoard(text)
  const open = board.rows.filter(r => !isDone(r))
  $.ui.status(open.length === 0 ? undefined : statusLine(board))
  if (!opened && open.length > 0) {
    opened = true
    await $.ui.open({ id: PANE, title: 'Review board' })
  }
  $.ui.invalidate('ui.render')
}

const poll = async ($: Engine) => {
  if (!timer) timer = $.clock.every(POLL_MS, () => void tick($))
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
      return { text: textTable(parseBoard(await load($)), columns) }
    }
    const placed = await $.ui.open({ id: PANE, title: 'Review board' })
    if (placed.isPlaced) return { text: 'Review board pane opened.' }
    return {
      text: placed.reason || 'The review board pane did not open.',
    }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    if (await read($, armed)) await poll($)
    const board = parseBoard(await load($))
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
    // line), the Done button, the Done rows when shown, and the "+N more"
    // line when In flight overflows.
    const used =
      4 +
      Math.max(1, board.watches.length) +
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
