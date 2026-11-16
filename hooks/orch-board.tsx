// The board pane: the orchestrator's board in a pane of its session.
//
// The pane gets the board only from `crew-orch.py --orch <name> board
// --json`. skills/orchestrator/references/orchestrator-record.md "The board"
// owns that JSON: every section, order and value in it. This module draws it
// and computes no board value. It sets column widths, truncation, colour,
// links and keys, and nothing else. It reads no record file and writes no
// file: what it keeps is in $.state.
//
// A row number and Enter runs `launcher.py focus <launch_tab>`.
// skills/orchestrator/references/launcher.md owns that command.
import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, RenderChildren } from 'claude-code'

import type {
  OrchBoard,
  OrchBoardEntry,
  OrchBoardRow,
  OrchBoardSection,
  OrchBoardView,
} from '../types/index'

type Engine = EngineInterface

const PANE = 'orch-board'
const POLL_MS = 5000
const BOARD_PY = 'skills/orchestrator/scripts/crew-orch.py'
const LAUNCHER_PY = 'skills/orchestrator/scripts/launcher.py'
// The board JSON version this pane reads. orchestrator-record.md says when
// it changes.
const VERSION = 1
// The breakpoint: below this many columns, a row drops the marks, the ticket
// and the age, and a Needs-you row drops the kind and the age. At any width
// the row text truncates first.
export const NARROW = 60
const INDENT = 2
const GAP = 2
const MIN_TICKET = 4
// A Needs-you question keeps this many characters before its other columns
// shrink.
const MIN_QUESTION = 15
const SEEN_CAP = 500
const MISSING =
  'No orchestrator name. Type /orch-board <name>, or set CREW_ORCH.'

const EMPTY: OrchBoardView = {
  name: null,
  board: null,
  error: null,
  line: null,
  seen: [],
  primed: false,
}

// Change the tag when the value's meaning changes: it declines what an
// earlier version stored, which outlives a reload.
const view = atom({ plugin: 'crew', key: 'orchBoard' } as const, EMPTY, {
  shape: 'orch-board-1',
})

const lastLine = (text: string) =>
  text
    .split('\n')
    .map(l => l.trim())
    .filter(Boolean)
    .at(-1) ?? ''

// Cut a text to a width, with an ellipsis where it cuts.
const fit = (text: string, width: number) =>
  text.length <= width
    ? text
    : width <= 1
      ? text.slice(0, Math.max(0, width))
      : `${text.slice(0, width - 1)}…`

const allRows = (board: OrchBoard) => board.sections.flatMap(s => s.rows)

// ---------------------------------------------------------------- layout

export type Widths = {
  n: number
  id: number
  marks: number
  status: number
  pr: number
  ticket: number
  text: number
  age: number
}

// The column widths for a width of `columns`. A width of 0 drops the column.
export const layout = (board: OrchBoard, columns: number): Widths => {
  const rows = allRows(board)
  const most = (f: (r: OrchBoardRow) => number) => Math.max(0, ...rows.map(f))
  const singles = board.sections
    .filter(s => s.kind === 'single')
    .flatMap(s => s.rows)
  const narrow = columns < NARROW
  const w: Widths = {
    n: most(r => String(r.n).length),
    id: most(r => r.id.length),
    marks: narrow ? 0 : 5,
    status: most(r => r.status.length),
    pr: most(r => (r.pr ? r.pr.label.length : 0)),
    ticket: narrow
      ? 0
      : Math.max(0, ...singles.map(r => (r.ticket ? r.ticket.id.length : 0))),
    text: most(r => r.text.length),
    age: narrow ? 0 : most(r => r.age.length),
  }
  const used = () =>
    INDENT +
    [w.n, w.id, w.marks, w.status, w.pr, w.ticket, w.age]
      .filter(x => x > 0)
      .reduce((sum, x) => sum + x + GAP, -GAP)
  // The row text truncates first: it takes the room that is left, down to 0.
  const full = w.text
  const room = () => columns - used() - GAP
  const over = () => used() - columns
  w.text = Math.max(0, Math.min(full, room()))
  // Only a row that is still wider than the pane shrinks the ticket, then
  // drops the age, the marks and the ticket, then shrinks the status and the
  // id. The row number stays whole.
  if (over() > 0 && w.ticket > MIN_TICKET) w.ticket = Math.max(MIN_TICKET, w.ticket - over())
  for (const drop of ['age', 'marks', 'ticket'] as const) {
    if (over() <= 0) break
    w[drop] = 0
  }
  for (const shrink of ['status', 'id'] as const) {
    if (over() > 0) w[shrink] = Math.max(1, w[shrink] - over())
  }
  // A dropped column can give the text room again.
  w.text = Math.max(0, Math.min(full, room()))
  return w
}

// ---------------------------------------------------------------- the board command

const parse = (stdout: string): OrchBoard | string => {
  try {
    const data = JSON.parse(stdout) as OrchBoard
    if (typeof data !== 'object' || data === null) return 'board --json printed no board'
    if (data.version !== VERSION) {
      return `The board has version ${String(data.version)}; this pane reads version ${VERSION}. Update the crew plugin.`
    }
    return data
  } catch {
    return 'board --json printed no board'
  }
}

const toastText = (e: OrchBoardEntry) =>
  `Needs you: ${e.id} ${e.kind} ${e.item}: ${e.text}`

// Run the board command once, and keep what it printed. A new Needs-you id
// shows one toast, except on the first read after the pane opens.
const refresh = async ($: Engine) => {
  const old = await read($, view)
  if (!old.name) return
  const run = await $.process.run([
    'python3',
    `${$.plugin.root}/${BOARD_PY}`,
    '--orch',
    old.name,
    'board',
    '--json',
  ])
  // A read for a name that is no longer the pane's name writes nothing.
  if ((await read($, view)).name !== old.name) return
  let board = old.board
  let error: string | null = null
  let { seen, primed } = old
  if (run.exitCode !== 0) {
    error = `crew-orch.py board --json exited ${run.exitCode}: ${lastLine(run.stderr)}`
  } else {
    const got = parse(run.stdout)
    if (typeof got === 'string') {
      error = got
      board = null
    } else {
      board = got
      const entries = got.needs_you.entries
      if (primed) {
        for (const e of entries) if (!seen.includes(e.id)) $.ui.toast(toastText(e))
      }
      seen = [...seen, ...entries.map(e => e.id).filter(id => !seen.includes(id))].slice(-SEEN_CAP)
      primed = true
    }
  }
  const next: OrchBoardView = { ...old, board, error, seen, primed }
  // Write only a change, so the pane redraws only when a value differs.
  if (JSON.stringify(next) !== JSON.stringify(old)) {
    await update($, view, current =>
      current.name === old.name ? { ...current, board, error, seen, primed } : current,
    )
  }
}

// ---------------------------------------------------------------- the timer

// The timer of one load of this module. Each `register` makes its own, so
// a reload starts with none.
type Load = { timer: { cancel: () => void } | undefined; busy: boolean }

const stop = (load: Load) => {
  load.timer?.cancel()
  load.timer = undefined
}

// One read each POLL_MS while the pane is open. A closed pane stops it.
const tick = async ($: Engine, load: Load) => {
  if (load.busy) return
  load.busy = true
  try {
    const panes = await $.ui.panes()
    if (!panes.some(p => p.id === PANE)) {
      stop(load)
      return
    }
    await refresh($)
  } catch {
    // A failed read leaves the pane as it was. The next tick reads again.
  } finally {
    load.busy = false
  }
}

const ensureTimer = ($: Engine, load: Load) => {
  if (!load.timer) load.timer = $.clock.every(POLL_MS, () => void tick($, load))
}

// ---------------------------------------------------------------- the focus key

const focusRow = async ($: Engine, typed: string) => {
  const text = typed.trim()
  const { board, name } = await read($, view)
  const rows = board ? allRows(board) : []
  let line: string
  const row = /^\d+$/.test(text) ? rows.find(r => r.n === Number(text)) : undefined
  if (!/^\d+$/.test(text)) {
    line = 'Type a row number, then Enter.'
  } else if (!row) {
    line = `No row ${text} on the board.`
  } else if (!row.launch_tab) {
    line = `Row ${row.n} (${row.id}) has no tab.`
  } else {
    const run = await $.process.run([
      'python3',
      `${$.plugin.root}/${LAUNCHER_PY}`,
      'focus',
      row.launch_tab,
    ])
    line =
      run.exitCode === 0
        ? `Row ${row.n} (${row.id}): its tab is in front.`
        : `launcher.py focus exited ${run.exitCode}: ${lastLine(run.stderr)}`
  }
  // A result for a name that is no longer the pane's name writes nothing.
  await update($, view, current => (current.name === name ? { ...current, line } : current))
}

// ---------------------------------------------------------------- register

export const register: Register = on => {
  // The timer of this load. A reload runs `register` again, with none.
  const load: Load = { timer: undefined, busy: false }

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'orch-board',
      description: "Open the orchestrator's board in a pane",
      argumentHint: '[orchestrator name]',
    })
    return next(e)
  })

  on('command.run', { command: 'orch-board' }, async ($, e) => {
    const typed = e.args.trim()
    const name = typed || (await $.env.get('CREW_ORCH'))?.trim() || null
    await update($, view, current => ({
      ...current,
      name,
      board: name === current.name ? current.board : null,
      error: null,
      line: name ? null : MISSING,
      // The first read after the pane opens toasts nothing.
      primed: false,
    }))
    const placed = await $.ui.open({
      id: PANE,
      title: name ? `Board: ${name}` : 'Board',
      focus: true,
    })
    if (name) {
      await refresh($)
      ensureTimer($, load)
    }
    if (!placed.isPlaced) return { text: placed.reason || 'The board pane did not open.' }
    return { text: name ? `Board pane opened for ${name}.` : MISSING }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) stop(load)
    return next(e)
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Link, Input } = $.ui.resolve(e)
    // A reload stops the timer. An open pane starts it again here.
    ensureTimer($, load)
    const v = await read($, view)
    const columns = e.props.bodyColumns

    if (!v.name) {
      return (
        <Box flexDirection="column">
          <Box key="line">
            <Text color="yellow">{MISSING}</Text>
          </Box>
        </Box>
      )
    }

    const cell = (width: number, text: string, style: { dim?: boolean; color?: string; right?: boolean } = {}) => (
      <Box width={width} flexShrink={0}>
        <Text wrap="truncate" dimColor={style.dim} color={style.color}>
          {style.right ? fit(text, width).padStart(width) : fit(text, width)}
        </Text>
      </Box>
    )
    const linkCell = (width: number, label: string, url: string | null) => (
      <Box width={width} flexShrink={0}>
        {url ? (
          <Link href={url}>{fit(label, width)}</Link>
        ) : (
          <Text wrap="truncate">{fit(label, width)}</Text>
        )}
      </Box>
    )

    const b = v.board
    const parts: RenderChildren[] = []
    if (v.error) {
      parts.push(
        <Box key="error">
          <Text color="red" wrap="truncate">
            {fit(v.error, columns)}
          </Text>
        </Box>,
      )
    }
    if (!b) {
      if (!v.error) parts.push(<Box key="wait"><Text dimColor>Reading the board…</Text></Box>)
      return <Box flexDirection="column">{parts}</Box>
    }

    // The Plan block.
    if (b.plan && b.plan.windows.length === 0 && b.plan.word) {
      parts.push(
        <Box key="plan-word">
          <Text color="yellow">{b.plan.word}</Text>
        </Box>,
      )
    }
    for (const [i, w] of (b.plan?.windows ?? []).entries()) {
      const notes = [w.resets && `resets ${w.resets}`, w.full_at && `full at about ${w.full_at}`]
        .filter(Boolean)
        .join(' · ')
      parts.push(
        <Box key={`plan-${w.key}`} gap={1}>
          <Text bold>{i === 0 ? 'Plan' : '    '}</Text>
          <Text>{w.label}</Text>
          <Text color="cyan">{w.meter}</Text>
          <Text>{`${w.used_pct}%`.padStart(4)}</Text>
          {notes ? <Text dimColor>{notes}</Text> : null}
          {i === 0 && b.plan?.word ? <Text color="yellow">{b.plan.word}</Text> : null}
        </Box>,
      )
    }
    if (b.plan) parts.push(<Box key="gap-plan"><Text> </Text></Box>)

    // Needs you.
    const entries = b.needs_you.entries
    parts.push(
      <Box key="needs">
        <Text bold color={b.needs_you.count > 0 ? 'magenta' : undefined}>
          {`Needs you ${b.needs_you.count}`}
        </Text>
      </Box>,
    )
    if (entries.length > 0) {
      const most = (f: (e: OrchBoardEntry) => string) => Math.max(...entries.map(e => f(e).length))
      const narrow = columns < NARROW
      const n = {
        id: most(e => e.id),
        kind: narrow ? 0 : most(e => e.kind),
        age: narrow ? 0 : most(e => e.age),
        item: most(e => e.item),
      }
      const textAt = () =>
        INDENT + [n.id, n.kind, n.age, n.item].filter(x => x > 0).reduce((sum, x) => sum + x + GAP, 0)
      // The question keeps MIN_QUESTION characters: the item, then the id
      // shrink first, so no row is wider than the pane.
      const want = Math.min(MIN_QUESTION, most(e => e.text))
      for (const shrink of ['item', 'id'] as const) {
        const short = want - (columns - textAt())
        if (short > 0) n[shrink] = Math.max(1, n[shrink] - short)
      }
      const room = Math.max(0, columns - textAt())
      for (const e of entries) {
        const textWidth = Math.min(room, e.text.length)
        parts.push(
          <Box key={`need-${e.id}`} paddingLeft={INDENT} gap={GAP}>
            {cell(n.id, e.id, { color: 'magenta' })}
            {n.kind > 0 ? cell(n.kind, e.kind) : null}
            {n.age > 0 ? cell(n.age, e.age, { dim: true }) : null}
            {cell(n.item, e.item)}
            {textWidth > 0 ? cell(textWidth, e.text) : null}
          </Box>,
        )
        if (e.recommend !== null) {
          parts.push(
            <Box key={`recommend-${e.id}`} paddingLeft={textAt()}>
              <Text dimColor wrap="truncate">
                {fit(`Recommended: ${e.recommend}`, room)}
              </Text>
            </Box>,
          )
        }
      }
    }
    parts.push(<Box key="gap-needs"><Text> </Text></Box>)

    // The groups, then the single items, in the order of the data.
    const w = layout(b, columns)
    const rowView = (s: OrchBoardSection, r: OrchBoardRow) => {
      const ticket = s.kind === 'single' && w.ticket > 0
      return (
        <Box key={`row-${r.n}`} paddingLeft={INDENT} gap={GAP}>
          {cell(w.n, String(r.n), { right: true })}
          {cell(w.id, r.id)}
          {w.marks > 0 ? cell(w.marks, r.marks, { dim: true }) : null}
          {cell(w.status, r.status)}
          {w.pr > 0 ? linkCell(w.pr, r.pr?.label ?? '', r.pr?.url ?? null) : null}
          {ticket ? linkCell(w.ticket, r.ticket?.id ?? '', r.ticket?.url ?? null) : null}
          {w.text > 0 ? cell(w.text, r.text) : null}
          {w.age > 0 ? cell(w.age, r.age, { dim: true }) : null}
        </Box>
      )
    }
    for (const s of b.sections) {
      const key = s.kind === 'group' ? `group-${s.id ?? ''}` : 'singles'
      parts.push(
        <Box key={key} gap={GAP}>
          <Text bold wrap="truncate">
            {s.title}
          </Text>
          {s.ticket ? (
            s.ticket.url ? (
              <Link href={s.ticket.url}>{s.ticket.id}</Link>
            ) : (
              <Text>{s.ticket.id}</Text>
            )
          ) : null}
          {s.repo ? <Text dimColor>{`· ${s.repo}`}</Text> : null}
          {s.kind === 'group' ? <Text dimColor>{`· ${s.merged} of ${s.total} merged`}</Text> : null}
        </Box>,
      )
      for (const r of s.rows) parts.push(rowView(s, r))
      parts.push(<Box key={`gap-${key}`}><Text> </Text></Box>)
    }

    // The key, its last result, and the footer.
    parts.push(
      <Input
        key="go"
        label="Row"
        placeholder="type a number and Enter"
        submitLabel="go to tab"
        value=""
        autoFocus
        onSubmit={value => focusRow($, value)}
      />,
    )
    if (v.line) {
      parts.push(
        <Box key="line">
          <Text color="yellow" wrap="truncate">
            {fit(v.line, columns)}
          </Text>
        </Box>,
      )
    }
    parts.push(
      <Box key="footer">
        <Text dimColor>
          {`Done ${b.done} · type a number and Enter to go to the tab · stages: ${b.legend}`}
        </Text>
      </Box>,
    )
    return <Box flexDirection="column">{parts}</Box>
  })
}
