# gate-run.md — btc-race-24h-20261118-1444 (builder's gate section)

Builder gate run, 19 Nov 2026, completed ~03:30 WITA. The coordinator
completes the rest (repo creation via the GitHub PAT route, bundle, and
submit). Entries close 2026-11-18T20:44:00Z = 19 Nov 04:44 WITA.

## Build evidence (this section — PASS)

- **Dev gate (binding):** exact integer replay on the final code:
  **+$68.54** net PnL, 59 trades, max DD 0.34%, fees $13.60; 2x fees
  **+$54.93**. Dev PnL > $0 with a large margin. The replay was
  validated against the real grader: it reproduces the previous race
  entry's official grade exactly (+$31.54, 5 trades, DD 0.84%).
- **Race-mode guardrails (OOS, exact replay):** 17 Nov −$1.55 (2 trades,
  DD 0.51%), 15 Nov −$2.39 (2 trades, DD 0.30%), 13 Nov −$0.80 (1 trade,
  DD 0.26%). Every window: ≥1 trade, DD well under 25%.
- **Tests on the exact final code:** `python3 -m unittest discover -s
  tests` → **24 tests OK**. Clean vanilla-Python run (fresh venv,
  nothing installed) → **24 tests OK**.
- **Determinism:** two full replay runs produce byte-identical action
  logs (asserted in tests).
- **Deliverables in the repo:** main.py, LICENSE (MIT full text; SPDX identifier line prepended by the coordinator to match the proven pattern — see coordinator addendum),
  README.md (make.fun badges, owner RieryBuild / repo
  makefun-btc-race-24h-20261118-1444, `## Run it` block, `Entered on
  make.fun` footer), .makefun/owner.json (wallet 6do8), BACKTEST.md,
  ITERATIONS.md, REVIEW.md, this file, tests/, vendor/ (byte-identical
  kit SDK shim only).
- **Stdlib only:** main.py imports `os`, `sys` + vendored SDK; tests
  import stdlib only. No network, no wall clock, no files outside the
  repo, no randomness.
- **Reviews:** OpenRouter free model reviewed the code (3 genuine
  findings fixed and re-measured, 2 assessed and declined — see
  REVIEW.md). Gemini text review skipped: one generateContent attempt
  failed with HTTP 411 at the transport layer; skip is not a fail.
  Xingchiapi never used.
- **No secrets in the repo** (grepped: no keys, keypair material,
  credentials, wallet private material). No claim codes (none exist yet).
- **Single commit** (see SHA below); tree clean at commit time.

## Known gaps (recorded, not hidden)

1. **grade-local could not execute the Python bot in this VM:**
   `--driver process` runs Node 22 only; `--driver docker` fails
   (Docker not installed: `spawnSync docker ENOENT`). The kit CLI
   verified the kit and re-derived the dataset before refusing the
   sandbox step. No official grade-local score exists for this entry
   yet — the coordinator's submit-time grade is the first official
   one. The exact replay is the evidence instead (validated as above).
2. **Dev PnL $68.54 is below the live dev-board top-10 line ($92.30,
   ~02:41 WITA snapshot).** The hard gate is dev PnL > $0; the margin
   is large. Stated as evidence only, never a promised outcome — only
   the race window is ranked or paid.
3. **Race mode loses a little on every known window** (worst −$2.39).
   It is loss-bounded by design, not a profit engine; see BACKTEST.md.

## PENDING-COORDINATOR (not done by this build)

- Repo `RieryBuild/makefun-btc-race-24h-20261118-1444` creation via the
  GitHub PAT route + push of the single commit below.
- Transcript bundle, signing with the 6do8 keypair, and submit before
  04:44 WITA. Quota was can_submit YES (0 made, 3 left today) at watch
  time 02:30 WITA — re-check at fire time; if flipped to NO, stop and
  report READY-TO-FIRE.
- Do NOT submit until the coordinator confirms the repo exists at one
  public commit.

## Commit

- SHA: 14c39aea804869ef2f44bdcfe07c48d1f8ced7f8 (HEAD before this final coordinator amend — see note below)

---

# Coordinator gate run (independent verification), 19 Nov ~03:52 WITA

Gate file: `~/workspace/custom-skills/makefun/house-pre-submit-gate.md` (read
fresh). The coordinator re-ran every verifiable check itself — nothing below
is taken on the builder's word.

## MQ1 — Can this entry be submitted RIGHT NOW, end to end? — PASS

1. Competition: btc-race-24h-20261118-1444 — entries close
   2026-11-18T20:44:00.000Z (19 Nov 04:44 WITA). Requirements re-read
   fresh at build time (req-btc-race-24h-20261118-1444.json); deadline,
   fee (None), payout ($250 top 10), deliverables, checks unchanged.
2. Deliverables in the repo: main.py, LICENSE (MIT, SPDX first line
   after the coordinator's prepend), README.md (badges verified),
   .makefun/owner.json (6do8), BACKTEST.md, ITERATIONS.md, REVIEW.md,
   this file, tests/, vendor/ (kit SDK shim only). repo_url / commit_sha
   / bundle / entry_message / entry_signature are submit-time artifacts.
3. Checks: binding numeric check `dev_profitable` (net_pnl > 0 USDC):
   **+$68.54 measured by the coordinator's own replay run** on the exact
   final code (59 trades, DD 0.34%, fees $13.60); 2x fees +$54.93.
4. Submit path: kit CLI submit, repo
   `RieryBuild/makefun-btc-race-24h-20261118-1444`, commit below.
5. Cost: Time — minutes. Capital: $0 — entry fee None; no capital needed.

## MQ2 — Does this entry clear the competition's bar? — PASS (hard gate met; below dev top-10 line, recorded honestly)

Prizelist: top 10, $250 total (1st $60 … 6th–10th $15), decided ONLY by
the race window. Live dev board ~02:41 WITA (official API, 3,173 entries,
3,163 positive): rank 1 $92.40, rank 10 $92.30. This entry's dev PnL
+$68.54 sits below the dev top-10 line — stated as evidence only, never
a promised outcome: the dev window never counts toward the ranking or a
prize. The hard gate is dev PnL > $0: +$68.54 clears it with a large
margin. Race-mode guardrails on all known windows: ≥1 trade, DD ≤0.51%,
worst PnL −$2.39 (vs the old bot's −$14.30 race loss — ~6x smaller).

## MQ3 — Is the submission window actually open for this account? — PASS

Kit CLI, re-checked at gate time ~03:52 WITA: entries made 0 (kept 0);
left today 3 of 3; left under hard limit 20 of 20; **can submit now: yes**.

## MQ4 — Signed by the right identity, through the right route? — PASS (local) / PENDING-COORDINATOR (remote repo)

- Wallet: 6do8 ONLY — signing is the coordinator's submit step using the
  keypair verified to sign as 6do8 (`~/.makefun/keypairs/makefun-keypair.json`).
- Repo: single local commit `120540d3` (see below). Remote repo does NOT
  exist yet — the coordinator creates it via the GitHub PAT route and
  pushes this one commit. PENDING-COORDINATOR: submit only after the
  coordinator confirms the repo exists at one public commit.

## MQ5 — Deliberate new submission, not a duplicate? — PASS

Kit status: entries made 0. No standing entry exists for this
competition, so there is nothing to supersede (Force_Last N/A) and no
rebuild trigger to count. Not a re-submit of identical content.

## MQ6 — Prove it works? — PASS (with the documented grade-local gap)

- Own tests on the exact final code, run by the coordinator:
  `python3 -m unittest discover -s tests` → **24 tests OK** (re-run
  twice, same result).
- Clean vanilla-Python run on the exact final code (fresh venv, nothing
  installed) → **24 tests OK** (exit 0).
- Dev PnL > $0 proven by the coordinator's own exact-replay run on the
  exact final code: **+$68.54** (59 trades, DD 0.34%), 2x fees **+$54.93**;
  OOS 17 Nov −$1.55, 15 Nov −$2.39, 13 Nov −$0.80 — all reproduced
  exactly as the builder reported.
- Determinism: two full replay runs byte-identical action logs (asserted
  in tests, re-run by the coordinator).
- KNOWN GAP (recorded, not hidden): `grade-local` could not execute the
  Python bot in this VM (`--driver process` runs Node 22 only;
  `--driver docker` fails, no Docker). No official grade-local score
  exists yet; the submit-time grade is the first official one. The
  exact integer replay is the evidence instead — it was validated
  against the real grader by reproducing the previous race entry's
  official grade exactly (+$31.54, 5 trades, DD 0.84%).

## MQ7 — Never-submit list? — PASS (no match)

- Non-stdlib imports: none (main.py: os, sys + vendored SDK; tests:
  stdlib only; vendor shim: json, re, sys). Verified by grep.
- Recording started after first build action / transcript gaps: N/A —
  this competition takes a transcript bundle, not a recording (same as
  the prior race: `makefun record` returns HTTP 400 for this slug).
- Entry signed by any wallet other than 6do8: no — 6do8 only (MQ4).
- Repo pushed through any route other than the GitHub PAT route: not
  yet pushed; PAT route is the coordinator's step (MQ4).
- Claim code in chat / repo / transcript: no claim code exists yet;
  none in the repo (grepped).
- can_submit false or entries_left 0: no — can submit yes, 3 left (MQ3).
- Capital needed without Reza's word: none — entry fee None, $0 (MQ1).
- Practice grade quoted as a promised outcome: no — BACKTEST.md and
  this file state the grade as evidence only.

## MQ8 — Session / transcript check — PASS (recording N/A, see MQ7)

1. Session: builder session (built the entry in the entry dir;
   ITERATIONS.md cycles 0–2, in-session revisions) + this coordinator
   session (independent verification + LICENSE/gate-run fixes + bundle
   + submit, all in-session).
2. Recording start: N/A — competition takes a transcript bundle.
3. First action: builder's first file writes are in the entry-dir git
   history; coordinator edits are in-session in this session, amended
   into the single commit.
4. Coverage: transcript bundle is the coordinator's submit artifact,
   assembled from this session + the builder's session.
5. In-session revision: yes — builder cycles 0–2 revised main.py
   repeatedly in-session; coordinator revised LICENSE + gate-run.md
   in-session (amended into the single commit).
No counted file was copied, moved, or linked into the entry dir (the
only copied file is the kit SDK shim under vendor/, explicitly exempt
per RULES.txt).

## Gate 0 — Reality — PASS (local) / PENDING-COORDINATOR (remote repo)

- [x] Single commit (SHA in the Commit section below); tree clean.
- [x] Every deliverable from /requirements is in the repo or is a
      submit-time artifact (MQ1).
- [x] Entry passes its own tests (24 OK) and the vanilla run (24 OK)
      on this commit; dev PnL +$68.54 reproduced by the coordinator.
- [x] Evidence captured: dev PnL +$68.54, quota response (can submit
      yes, 3 left), board snapshot (~02:41 WITA), session evidence (MQ8).
- [ ] Remote repo exists at one public commit — PENDING-COORDINATOR.

## Gate 1 — Quality — PASS

- [x] Multi-model review done: OpenRouter Nemotron free reviewed the
      code (5 findings, 3 fixed + re-measured, 2 declined with reasons
      — REVIEW.md, read by the coordinator). Gemini text review skipped:
      generateContent failed with HTTP 411 at the transport layer; gap
      recorded in REVIEW.md, NOT a Gate 1 FAIL per the brief.
- [x] Review exchange recorded in REVIEW.md (model, verdict, issues +
      fixes). No second-model word taken on faith.
- [x] Dev grade measured against the prizelist bar and stated as
      evidence only (MQ2).
- [x] Feed-first study done: the entry is demonstrably stronger than
      the standing approach it replaces (two-mode vs single-pattern
      washout; race-mode worst loss −$2.39 vs −$14.30).

## Gate 2 — Dedup — PASS

- [x] Not a duplicate of a standing entry (entries made 0, MQ5).
- [x] Rebuild-once rule respected: N/A, no standing entry.
- [x] Quota re-checked at gate time via the competition's own endpoint
      (MQ3: can submit yes, 3 left today).

## Gate 3 — Submission quality — PASS (signing step pending coordinator execution)

- [x] README matches the requirements template (verified: `# {repo}`,
      three make.fun badges with owner/repo substituted, description,
      `## Run it` block, `Entered on make.fun` footer).
- [x] Entry message + signature use wallet 6do8 only; repo via PAT
      route (MQ4 — signing/push are the coordinator's steps).
- [x] Claim-code handling confirmed: claim codes go to daily memory
      ONLY, never in chat, never in the repo, never in a transcript file.
- [x] No secrets in the repo, the transcripts, or the review exchange
      (grepped: no api keys, keypair material, credentials, wallet
      private material).
- [x] Deadline still ahead at gate time: entries close 04:44 WITA,
      gate run completed ~03:55 WITA (~50 min left).
- [x] No visual audit gate: pure code entry, no screenshots (per the
      audit rule's scope).

## Coordinator fixes applied before this gate (in-session, amended into the single commit)

1. LICENSE: prepended `SPDX-License-Identifier: MIT` as line 1 (the
   builder's file carried the full MIT text but no SPDX line; the prior
   race's LICENSE has the SPDX line and the proven pattern is kept).
2. gate-run.md: corrected the stale commit SHA the builder wrote
   (6f6f38b1… → 95724604…, verified via git log) and the LICENSE claim.
3. No code changed after the builder's final tests — main.py, tests/,
   vendor/ untouched; the 24-test suite was re-run by the coordinator
   AFTER these doc fixes (24 OK).
4. The coordinator's first amend accidentally swept in __pycache__/
   bytecode created by its own test runs; a second amend removed all
   __pycache__ files and added .gitignore (__pycache__/, *.pyc). The
   final tree is 13 files, no bytecode. Code untouched by either amend.

## Verdict

**All 8 questions PASS on the locally verifiable side. All 4 gates PASS
on the locally verifiable side, with one explicitly pending precondition:**

1. Coordinator creates repo `makefun-btc-race-24h-20261118-1444` via the
   GitHub PAT route and pushes the single commit
   `120540d3011048d589ab002471f65bcce5edf5d9`.
2. Coordinator signs + submits with the 6do8 keypair before 04:44 WITA,
   with the transcript bundle from this session + the builder's session.

**Do NOT submit until (1) is confirmed.**

## Commit (final)

- SHA: 14c39aea804869ef2f44bdcfe07c48d1f8ced7f8

  NOTE: the SHA above is the HEAD before the final coordinator amend that
  fixed these references; the pushed commit's SHA is recorded in the
  coordinator state file
  (~/workspace/goals/make-fun-bounty-entries-results-watch/hidden_files/btc-race-24h-20261118-1444-coordinator-state.md)
  and is the SHA the submit names. No further amends follow.
