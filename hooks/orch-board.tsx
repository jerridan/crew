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

// ---------------------------------------------------------------- wrapping

const graphemes = (text: string): string[] =>
  typeof Intl.Segmenter === 'function'
    ? Array.from(new Intl.Segmenter().segment(text), part => part.segment)
    : Array.from(text)

const WIDE =
  /\p{Extended_Pictographic}|\p{Emoji_Presentation}|[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE30-\uFE6F\uFF00-\uFF60\uFFE0-\uFFE6]|[\u{20000}-\u{3FFFD}]/u

// The terminal cells of one grapheme: a wide East Asian character or an
// emoji takes 2.
const graphemeCells = (g: string) => (WIDE.test(g) ? 2 : 1)

export const cellCount = (text: string) => graphemes(text).reduce((sum, g) => sum + graphemeCells(g), 0)

// Break a text into lines of at most `width` cells. A line breaks at the last
// space that fits. A word longer than the room breaks at a grapheme boundary
// at the column. Runs of white space count as one space.
export const wrap = (text: string, width: number): string[] => {
  const room = Math.max(1, width)
  const lines: string[] = []
  let cur = ''
  let curCells = 0
  const flush = () => {
    if (cur) lines.push(cur)
    cur = ''
    curCells = 0
  }
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const size = cellCount(word)
    if (cur && curCells + 1 + size <= room) {
      cur += ` ${word}`
      curCells += 1 + size
    } else if (size <= room) {
      flush()
      cur = word
      curCells = size
    } else {
      flush()
      for (const g of graphemes(word)) {
        const gc = graphemeCells(g)
        if (cur && curCells + gc > room) flush()
        cur += g
        curCells += gc
      }
    }
  }
  flush()
  return lines.length > 0 ? lines : ['']
}

// The window over the content lines. `n` lines, `rows` rows to draw in. With
// at least 3 rows, a mark takes a row at each edge that has lines beyond it.
// The window is at least one line.
export type Win = { start: number; end: number; up: boolean; down: boolean }

export const windowAt = (n: number, rows: number, from: number): Win => {
  const start = Math.min(Math.max(0, from), Math.max(0, n - 1))
  const marks = rows >= 3
  if (!marks) return { start, end: Math.min(n, start + rows), up: false, down: false }
  const up = start > 0
  const room = rows - (up ? 1 : 0)
  // The last page has no mark below it, so it uses that row for a line.
  if (start + room >= n) return { start, end: n, up, down: false }
  const below = room - 1
  return { start, end: start + below, up, down: true }
}

// The start of the window that ends at or after `at` and shows the most lines
// above it: no line falls between that page and the one below.
export const pageUp = (n: number, rows: number, at: number): number => {
  for (let s = 0; s < at; s++) if (windowAt(n, rows, s).end >= at) return s
  return 0
}

// The first start whose window reaches the last line.
export const lastStart = (n: number, rows: number): number => {
  for (let s = 0; s < n; s++) if (windowAt(n, rows, s).end >= n) return s
  return 0
}

// Hold a window start between 0 and the last start.
export const clampTop = (n: number, rows: number, top: number): number =>
  Math.min(Math.max(0, top), lastStart(n, rows))

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
type Load = {
  timer: { cancel: () => void } | undefined
  busy: boolean
  // The first content line of the window, and the window of the last draw.
  // They live in this load only, so a reload starts at the top.
  top: number
  shown: { n: number; rows: number } | undefined
}

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

// ---------------------------------------------------------------- the scroll words

const SCROLL_WORDS = ['u', 'd', 't', 'b']

// Move the window by a word, from the window of the last draw.
const scrollBy = (load: Load, word: string) => {
  const shown = load.shown
  if (!shown) return
  const win = windowAt(shown.n, shown.rows, load.top)
  if (word === 't') load.top = 0
  else if (word === 'b') load.top = lastStart(shown.n, shown.rows)
  else if (word === 'd') load.top = win.down ? win.end : win.start
  else load.top = win.start > 0 ? pageUp(shown.n, shown.rows, win.start) : 0
}

// ---------------------------------------------------------------- register

export const register: Register = on => {
  // The timer of this load. A reload runs `register` again, with none.
  const load: Load = { timer: undefined, busy: false, top: 0, shown: undefined }

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

  // The pane draws its own window, so a wheel tick or a page key moves it
  // here, and the engine's window does not move.
  on('ui.scroll', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const shown = load.shown
    load.top = shown ? clampTop(shown.n, shown.rows, load.top + e.by) : Math.max(0, load.top + e.by)
    await $.ui.invalidate('ui.render')
    return {}
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
            <Text color="yellow" wrap="truncate">{fit(MISSING, columns)}</Text>
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
      if (!v.error) parts.push(<Box key="wait"><Text dimColor wrap="truncate">{fit('Reading the board…', columns)}</Text></Box>)
      return <Box flexDirection="column">{parts}</Box>
    }

    // A text line: one row, cut to its width.
    const textLine = (key: string, pad: number, text: string, style: { dim?: boolean; color?: string } = {}) => (
      <Box key={key} paddingLeft={pad}>
        <Text wrap="truncate" dimColor={style.dim} color={style.color}>
          {text}
        </Text>
      </Box>
    )
    // A wrapped text: the first line keeps `key`, the next lines get `-k`.
    const wrapped = (key: string, pad: number, text: string, style: { dim?: boolean; color?: string } = {}) =>
      wrap(text, columns - pad).map((line, k) => textLine(k === 0 ? key : `${key}-${k}`, pad, line, style))

    // The Plan block.
    if (b.plan && b.plan.windows.length === 0 && b.plan.word) {
      parts.push(...wrapped('plan-word', 0, b.plan.word, { color: 'yellow' }))
    }
    for (const [i, w] of (b.plan?.windows ?? []).entries()) {
      const notes = [w.resets && `resets ${w.resets}`, w.full_at && `full at about ${w.full_at}`]
        .filter(Boolean)
        .join(' · ')
      const word = i === 0 && b.plan?.word ? b.plan.word : ''
      const head = ['Plan', w.label, w.meter, `${w.used_pct}%`.padStart(4)]
      const whole = [...head, ...(notes ? [notes] : []), ...(word ? [word] : [])]
      const fits = whole.reduce((sum, x) => sum + cellCount(x) + 1, -1) <= columns
      parts.push(
        <Box key={`plan-${w.key}`} gap={1}>
          <Text bold wrap="truncate">{i === 0 ? 'Plan' : '    '}</Text>
          <Text wrap="truncate">{w.label}</Text>
          <Text color="cyan" wrap="truncate">{w.meter}</Text>
          <Text wrap="truncate">{`${w.used_pct}%`.padStart(4)}</Text>
          {fits && notes ? <Text dimColor wrap="truncate">{notes}</Text> : null}
          {fits && word ? <Text color="yellow" wrap="truncate">{word}</Text> : null}
        </Box>,
      )
      // A Plan row wider than the pane gives its notes and its pace word
      // lines of their own.
      if (!fits) {
        if (notes) parts.push(...wrapped(`plan-${w.key}-notes`, INDENT * 2, notes, { dim: true }))
        if (word) parts.push(...wrapped(`plan-${w.key}-word`, INDENT * 2, word, { color: 'yellow' }))
      }
    }
    if (b.plan) parts.push(<Box key="gap-plan"><Text wrap="truncate"> </Text></Box>)

    // Needs you.
    const entries = b.needs_you.entries
    parts.push(
      <Box key="needs">
        <Text bold wrap="truncate" color={b.needs_you.count > 0 ? 'magenta' : undefined}>
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
        // Where the text column has too little room, the text starts on the
        // next line, indented, and wraps there.
        const below = room < MIN_QUESTION && cellCount(e.text) > room
        const lines = e.text === '' ? [] : wrap(e.text, below ? columns - 2 * INDENT : room)
        parts.push(
          <Box key={`need-${e.id}`} paddingLeft={INDENT} gap={GAP}>
            {cell(n.id, e.id, { color: 'magenta' })}
            {n.kind > 0 ? cell(n.kind, e.kind) : null}
            {n.age > 0 ? cell(n.age, e.age, { dim: true }) : null}
            {cell(n.item, e.item)}
            {!below && lines[0] && room > 0 ? (
              <Box width={Math.min(room, cellCount(lines[0]))} flexShrink={0}>
                <Text wrap="truncate">{lines[0]}</Text>
              </Box>
            ) : null}
          </Box>,
        )
        const rest = below ? lines : lines.slice(1)
        const restPad = below ? 2 * INDENT : textAt()
        rest.forEach((line, k) => parts.push(textLine(`need-${e.id}-${k + 1}`, restPad, line)))
        if (e.recommend !== null) {
          const recBelow = room < MIN_QUESTION && cellCount(`Recommended: ${e.recommend}`) > room
          parts.push(
            ...wrapped(`recommend-${e.id}`, recBelow ? 2 * INDENT : textAt(), `Recommended: ${e.recommend}`, {
              dim: true,
            }),
          )
        }
      }
    }
    parts.push(<Box key="gap-needs"><Text wrap="truncate"> </Text></Box>)

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
            <Box width={Math.min(columns, cellCount(s.ticket.id))} flexShrink={0}>
              {s.ticket.url ? (
                <Link href={s.ticket.url}>{fit(s.ticket.id, columns)}</Link>
              ) : (
                <Text wrap="truncate">{fit(s.ticket.id, columns)}</Text>
              )}
            </Box>
          ) : null}
          {s.repo ? <Text dimColor wrap="truncate">{`· ${s.repo}`}</Text> : null}
          {s.kind === 'group' ? (
            <Text dimColor wrap="truncate">{`· ${s.merged} of ${s.total} merged`}</Text>
          ) : null}
        </Box>,
      )
      for (const r of s.rows) parts.push(rowView(s, r))
      parts.push(<Box key={`gap-${key}`}><Text wrap="truncate"> </Text></Box>)
    }

    // The routine events: the bounded `events` list of the board JSON. An older
    // board has no such key, and then the pane draws no block.
    const events = b.events ?? []
    if (events.length > 0) {
      parts.push(<Box key="recent"><Text bold wrap="truncate">Recent</Text></Box>)
      events.forEach((ev, k) =>
        parts.push(...wrapped(`event-${k}`, INDENT, `${ev.age} ${ev.item} ${ev.text}`, { dim: true })),
      )
      parts.push(<Box key="gap-recent"><Text wrap="truncate"> </Text></Box>)
    }

    // The result line and the footer.
    const extras: RenderChildren[] = []
    if (v.line) extras.push(textLine('line', 0, fit(v.line, columns), { color: 'yellow' }))
    extras.push(
      ...wrapped('footer', 0, `Done ${b.done} · type a number and Enter to go to the tab, or u d t b to scroll · stages: ${b.legend}`, {
        dim: true,
      }),
    )
    const input = (
      <Input
        key="go"
        label="Row"
        placeholder="type a number and Enter"
        submitLabel="go to tab"
        value=""
        autoFocus
        onSubmit={async value => {
          const word = value.trim().toLowerCase()
          if (SCROLL_WORDS.includes(word)) {
            scrollBy(load, word)
            await $.ui.invalidate('ui.render')
            return
          }
          await focusRow($, value)
        }}
      />
    )

    // The window. The Row input is always pinned. The result line and the
    // footer are pinned only where the pane has room left for a window of 5
    // lines; in a shorter pane they end the scrollable content.
    const rows = e.props.scroll.bodyRows
    const roomy = rows - 1 - extras.length >= 5
    const content = roomy ? parts : [...parts, ...extras]
    const pinned = roomy ? [input, ...extras] : [input]
    const room = Math.max(1, rows - pinned.length)
    load.shown = { n: content.length, rows: room }
    load.top = clampTop(content.length, room, load.top)
    if (content.length <= room) return <Box flexDirection="column">{[...content, ...pinned]}</Box>
    const win = windowAt(content.length, room, load.top)
    const drawn: RenderChildren[] = []
    if (win.up) {
      drawn.push(textLine('mark-up', 0, fit(`↑ ${win.start} more · u`, columns), { dim: true }))
    }
    drawn.push(...content.slice(win.start, win.end))
    if (win.down) {
      drawn.push(textLine('mark-down', 0, fit(`↓ ${content.length - win.end} more · d`, columns), { dim: true }))
    }
    return <Box flexDirection="column">{[...drawn, ...pinned]}</Box>
  })
}
