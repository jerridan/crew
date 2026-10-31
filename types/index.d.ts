// The $.state contract of the review-board mod (hooks/review-board.tsx).
// The board file's own schema lives in skills/review-queue/references/board.md.

export type ReviewBoardStage =
  | 'new'
  | 'triage'
  | 'reviewing'
  | 'fixing'
  | 'rereview'
  | 'approve'
  | 'queued'
  | 'merged'
  | 'blocked'
  | 'closed'

export type ReviewBoardNext = 'you' | 'crew' | 'author' | 'ci' | 'queue' | '-'

export type ReviewBoardWatch = {
  id: string
  source: string
  policy: 'assist' | 'review'
  status: 'active' | 'stopped'
  since: string
  last_checked: string | null
  found: number
}

export type ReviewBoardRow = {
  repo: string
  pr: number
  title: string
  author: string
  stage: ReviewBoardStage
  next: ReviewBoardNext
  head: string | null
  last: { at: string; text: string }
  url: string
  watch: string | null
  policy: 'assist' | 'review'
}

export type ReviewBoardFile = {
  version: number
  owner: { session_id: string; since: string }
  updated_at: string
  // The found_at of the newest asks.json entry the queue session took.
  asks_through: string | null
  watches: ReviewBoardWatch[]
  rows: ReviewBoardRow[]
}

// One PR in one Slack message, or one GitHub review request.
export type ReviewBoardAsk = {
  repo: string
  pr: number
  url: string
  title: string | null
  author: string | null
  watch: string
  slack: { channel: string; ts: string } | null
  found_at: string
}

// The asks file the mod writes and the queue session reads.
export type ReviewBoardAsksFile = {
  version: number
  updated_at: string
  watches: Record<string, { last_checked: string; found: number }>
  asks: ReviewBoardAsk[]
}

declare module 'claude-code' {
  interface PluginState {
    crew: {
      // True once a `review-queue` skill prompt armed this session.
      armed: Shaped<boolean>
      // True while the Done section shows its rows.
      showDone: Shaped<boolean>
    }
  }
}
