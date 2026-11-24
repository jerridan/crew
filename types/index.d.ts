// The $.state contract of the board pane mod (hooks/orch-board.tsx).
// skills/orchestrator/references/orchestrator-record.md "The board" owns the
// board JSON. The OrchBoard types below follow it, and a reader ignores a
// field it does not know.

export type OrchBoardLink = { id: string; url: string | null }

export type OrchBoardWindow = {
  key: string
  label: string
  used_pct: number
  meter: string
  resets: string
  full_at: string
}

export type OrchBoardEntry = {
  id: string
  kind: string
  age: string
  item: string
  item_id: string | null
  text: string
  recommend: string | null
}

export type OrchBoardRow = {
  n: number
  id: string
  marks: string
  status: string
  pr: { number: number; label: string; url: string } | null
  ticket: OrchBoardLink | null
  text: string
  age: string
  launch_tab: string | null
  subagent: boolean
}

export type OrchBoardSection = {
  kind: 'group' | 'single'
  id: string | null
  title: string
  ticket: OrchBoardLink | null
  repo: string | null
  merged: number | null
  total: number | null
  rows: OrchBoardRow[]
}

export type OrchBoard = {
  version: number
  orch: string
  plan: { windows: OrchBoardWindow[]; word: string } | null
  needs_you: { count: number; entries: OrchBoardEntry[] }
  sections: OrchBoardSection[]
  done: number
  legend: string
}

// What the pane keeps for the session. It outlives a reload of the mod.
export type OrchBoardView = {
  // The orchestrator name, or null when the command had none.
  name: string | null
  // The last board the command printed.
  board: OrchBoard | null
  // Why the last board command failed, or null.
  error: string | null
  // The line under the board: what the last row number did.
  line: string | null
  // The Needs-you ids the pane has seen.
  seen: string[]
  // False until the first read after the pane opens: that read toasts nothing.
  primed: boolean
}

declare module 'claude-code' {
  interface PluginState {
    crew: {
      orchBoard: Shaped<OrchBoardView>
    }
  }
}
