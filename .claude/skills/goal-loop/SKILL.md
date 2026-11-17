---
name: goal-loop
description: Inspect and record a user's Goal Loop state through the local goal-loop CLI. Use when the user asks to create, resume, inspect, execute, verify, or explain an Aim, Proposal, Goal, Attempt, Evidence, or Verdict.
---

# Goal Loop

Invoke `goal-loop` (and `goal-loop-judge`) from PATH. When the project's instructions name another way to run
them, such as the project's virtual environment, use that instead; the commands below are written as `goal-loop`.
Inside a project it uses that project's journal; elsewhere it targets the user's shared local SQLite database.
Use `GOAL_LOOP_DATABASE` or `--database <path>` only when the user explicitly wants a separate database.
A project keeps its journal in `<project>/.goal-loop/` (created by `project-init` or the desktop app's
"프로젝트 폴더 열기"); any command run inside the project finds it automatically. Run `goal-loop where` to
see which journal is in use and how it was found. `--workspace "<name>"` selects a desktop workspace by
name when you are outside its folder; `goal-loop workspaces` lists them.
An umbrella journal (one that plans several areas) links its Aims to Aims of other project journals with
`aim-link-add`; the link is a reference on the Aim, the linked journal is only read, and `aim-links` shows the linked
Aim's current state (`broken` with a reason when it cannot be followed; `doctor` lists those). Remove a link with
`reference-remove`. When the linked Aim is achieved there, `aim-link-import <reference-id>` copies its valid evaluation
here as `external-evaluation-N`, which `aim-evaluate` may cite; `aim-links` marks an import `still_valid: false` once the
linked journal invalidates it (this journal's records never change by themselves).

## Safe operating order

1. Start with `goal-loop next`. It is a read-only JSON projection; use its IDs and `command_argv` only as a template, never as authorization to mutate state.
   `goal-loop next --aim <aim-id>` keeps only the actions arising from that Aim and its sub-Aims (a parent's
   `resume_aim` stays when a Goal inside the scope caused it); use it when one journal holds several areas.
   In a journal with Aim links, `next` also returns `linked` (each linked journal's next actions for the linked
   Aim's subtree, with a `source` and `command_argv` pointing at that journal), `skipped` (links whose Aim here is
   paused, abandoned, or achieved), and an `import_linked_evaluation` action when a linked Aim is achieved there.
2. Use `goal-loop status` for a compact inventory and, when history matters, `goal-loop activity`.
3. Explain the current state and the smallest valid next action in plain language.
4. Create or change a durable fact only when the user authorizes that semantic action.
5. Print the returned JSON identity (`aim-*`, `goal-*`, `attempt-*`, `evidence-*`, `verdict-*`, or `decision-*`) in the response.

## Semantic guardrails

- Do not invent an Aim, Proposal, Goal, Attempt, Evidence, Decision, or Verdict from an agent's own assumptions.
- An Attempt `succeeded` records one execution outcome, not Goal success.
- Record Evidence after a completed Attempt. Submit a Verdict only with cited Evidence.
- The executing agent must not silently treat its own output as an independent satisfied Verdict; ask the user or a designated verifier to verify it.
- A verified Goal does not automatically achieve its Aim. Only use `aim-evaluate` when the user authorizes a separate conclusion that cited, valid satisfied Verdicts cover the Aim itself.
- A failed Attempt is not a failed Goal. For the same Contract, use `retry-decide` with an actor and nonempty reason, then pass its returned `decision-*` to `attempt-start --retry-decision` exactly once.
- After an `inconclusive` Verdict, first choose with the user: add new Evidence to the same Attempt and submit a new Verdict with `--supersedes-verdict`, or use `reverification-decide` before one new Attempt. Do not treat either path as automatic.
- If target, scope, criterion, or verification changes, do not retry silently; use the Contract-revision workflow instead.
- A Verdict has only three results (`satisfied`, `not_satisfied`, `inconclusive`); there is no partial result. Write
  criteria as numbered items, and pass `verdict-submit --reason` stating which items were met and on what basis. When
  only part is met, the user picks one path: (A) `not_satisfied`, then a repair Attempt on the same Contract; (B) the
  missing part is too large or different: `contract-revise` to narrow the criterion with a reason, judge the rest, and
  carry the missing part to a new Proposal; (C) the criterion wording is ambiguous: `contract-revise` to clarify it
  before judging; (D) the criterion is met but issues outside it were found: `satisfied` plus a follow-up Proposal.
  Missing grounds for judging are `inconclusive`, not partial.
- When Evidence is corrected, use `reviews` to inspect the resulting `under_review` Verdicts and Impact Reviews. `next` must propose the Verdict review first; only after cited Verdicts are no longer under review may an affected Aim Evaluation review be resolved. Neither `reaffirm` nor `invalidate` is automatic.
- An invalidated Aim Evaluation does not reopen its Aim automatically. Only when no valid Evaluation remains may the user authorize `aim-closure-invalidate`, citing the invalidating record and a reason to resume pursuit.
- A paused Aim, Goal Hold, or unsatisfied/untrusted Verdict dependency blocks a new Attempt. Read `admission` and `next`; do not suggest `attempt-start` until the user authorizes the relevant resume, Hold clear, or dependency recovery.
- A Runtime outbox request is technical delivery state, not authorization to execute. `runtime-attempt-start` creates an Attempt and queues one request only with user authorization. A worker may explicitly claim its assigned request, ack delivery handling, or requeue its own claim; ack never completes the Attempt. Deliver a real execution result separately with its `runtime_delivery_id`.
- `RuntimeOutboxWorker.dispatch` is an application-adapter helper, not a scheduler: it calls a caller-supplied executor once and only a pending request it claimed. On executor, delivery, or ack failure it leaves the request claimed—never silently retry or requeue potentially side-effecting work.
- The built-in outbox executor accepts only `codex_exec.v1` (existing workdir, prompt, safe sandbox) and `claude_print.v1` (existing workdir, prompt, explicit model/positive turn/budget). `runtime-dispatch` is an explicit authorized execution command, never a background scan; rejected payloads remain claimed for inspection.
- When an external process already finished but delivery was interrupted, keep its claim and use `runtime-deliver` with the observed outcome and stable delivery ID. Do not requeue merely to repeat unknown side effects; if delivery succeeded but ack did not, use `runtime-ack` only.

## Useful commands

```powershell
goal-loop where
goal-loop project-init .
goal-loop workspaces
goal-loop --workspace "<name>" next
goal-loop reference-add goal-1 docs/design.md --label "design" --actor "<agent name>"
goal-loop reference-remove reference-1 --actor "owner" --reason "reason"
goal-loop evidence-record attempt-1 "<agent name>" "observation" --attach .\pytest.log
goal-loop ao-import attempt-1 "<agent name>" <ao-workspace>\projects\<project-id> <ao-goal-id>
goal-loop ao-attempt-start goal-1 1 "<agent name>" "run in AO" --ao-project-id <id> --ao-goal-id <slug> --ao-workspace <ao-workspace>
goal-loop ao-links --goal goal-1
goal-loop aim-link-add aim-1 --workspace "<name>" --external-aim aim-3 --actor "<agent name>"
goal-loop aim-links --aim aim-1
goal-loop status
goal-loop next
goal-loop admission
goal-loop guide
goal-loop help --all
goal-loop activity
goal-loop help
goal-loop guided
goal-loop aim-evaluate aim-1 "reviewer" "conclusion" verdict-1
goal-loop aim-create "sub-direction" --parent aim-1
goal-loop aim-parent-add aim-3 aim-1
goal-loop aim-evaluate aim-1 "reviewer" "conclusion" aim-evaluation-2
goal-loop evidence-correct evidence-1 "observer" "corrected observation"
goal-loop reviews
goal-loop verdict-review-resolve impact-review-1 reaffirm "reviewer" "reason"
goal-loop aim-evaluation-review-resolve aim-evaluation-1 impact-review-1 reaffirm "reviewer" "reason"
goal-loop aim-closure-invalidate aim-1 aim-evaluation-1 review-resolution-1 "reviewer" "reason"
goal-loop aim-pause aim-1 "owner" "reason"
goal-loop aim-resume aim-1 "owner" "reason"
goal-loop goal-hold-add goal-1 --actor "owner" --reason "reason"
goal-loop proposal-create aim-1 "direction" --actor "<agent name>"
goal-loop proposal-close proposal-2 --kind declined --actor "owner" --reason "reason"
goal-loop goal-stop goal-1 --actor "owner" --reason "reason"
goal-loop aim-abandon aim-1 --actor "owner" --reason "reason"
goal-loop goal-hold-clear goal-1
goal-loop verdict-dependency-add goal-2 verdict-1 --required-result satisfied
goal-loop retry-decide goal-1 attempt-1 "user" "reason"
goal-loop reverification-decide goal-1 "user" "reason"
goal-loop contract-revise goal-1 --scope "new scope" --criterion "new criterion" --verification "new verification" --actor "owner" --reason "requirements changed"
goal-loop attempt-start goal-1 1 "executor" "operation" --retry-decision decision-1
goal-loop runtime-attempt-start goal-1 1 "runtime" "operation" codex_exec.v1 '{"prompt":"inspect","workdir":"."}' --request-id request-1 --command-id runtime-start-1
goal-loop runtime-requests
goal-loop runtime-request request-1
goal-loop runtime-claim request-1 "worker-a"
goal-loop runtime-requeue request-1 "worker-a"
goal-loop runtime-ack request-1 "worker-a"
goal-loop runtime-dispatch request-1 "worker-a"
goal-loop runtime-deliver request-1 "worker-a" succeeded delivery-1
```

The interactive `guided` command is for a human terminal user. For agent work, prefer precise
scriptable commands and explain each pending semantic choice before issuing it.

## Developing with Goal Loop

Use this protocol when the project has a `.goal-loop/` journal and its instructions say development is
tracked with Goal Loop. The agent works through the CLI from inside the project; the human watches and
decides in the desktop app (opened on the same project folder), which reloads when its window regains
focus. Concurrent sessions may share one journal: a command overtaken by another writer is re-derived
from the newer journal before it is appended. The project's instruction file (`CLAUDE.md`, `AGENTS.md`)
keeps only the rules that always apply (your agent name, never recording as `user`, the judge command);
this section holds the procedure. Before creating or splitting an Aim, writing Aim criteria or a Goal
Contract, and after a `not_satisfied` Verdict, follow the `goal-loop-planning` skill as well.

**Session start.** After the memory context, run `where` (expect `source: project`), then `next` and
`status`, and summarize the open Aims, running Attempts, and pending verifications in a few sentences
before starting work.

**Who does what.**

| Action | Agent alone | With user approval | User only |
|---|---|---|---|
| `proposal-create --actor <agent>` | ✓ | | |
| `aim-create`, `goal-accept` (fixes the Contract) | | ✓ | |
| `attempt-start`, `attempt-complete`, `evidence-record`, `ao-import`, `verification-begin` on an accepted Goal the user asked you to work on | ✓ | | |
| `goal-follow-add` (history only, cites the reason) | ✓ | | |
| `retry-decide`, `reverification-decide`, `contract-revise`, `aim-criteria-revise`, goal tree links | | ✓ | |
| `verdict-submit`, `aim-evaluate` | | delegated judging only (below) | ✓ |
| review resolutions, closures, pause/hold | | | ✓ |

**How much to record and judge.** Match the weight of records and judging to the weight of the change. When
you start a change, say which level you chose; the user may change it.

| Change | Record | Judging |
|---|---|---|
| Easy to undo and confirmed by tests (a typo, a requested style tweak) | the commit only | none |
| Small but worth keeping in the journal | an Attempt on an open Goal that groups such changes | once for the group, later; or the user judges directly |
| Hard to undo, or may break something else | its own Goal | delegated judging before the commit |

- Deferring is not skipping. Leave a Goal at `verification-begin`; `next` and the app keep showing it as waiting,
  and it is judged later (several deferred Goals can be judged one after another).
- A change that is easy to undo may be committed before its Verdict; a `not_satisfied` Verdict is then fixed by a
  repair Attempt and a follow-up commit. Only work that depends on a Goal waits for its Verdict.
- Write only criteria the judge can check itself. The judge works on a copy of the project, so it cannot see Git
  state or a running app's window; attach the observed output as Evidence and write the criterion against that output.

**Mapping development work.**

- Aim: an outcome the user stated. Write what will count as achieved in a Proposal on that Aim and close
  it with `proposal-close --kind criteria`: it leaves the open approaches, the app shows it as the Aim's
  criteria, and `delegated_judging aim` gives it to the judge as the criteria. When the user changes what
  counts as achieved, record it with `aim-criteria-revise <aim> "<new criteria>" --supersedes <criteria proposal>
  --actor <agent> --reason "<the user's decision>"` (with the user's approval) instead of closing a second criteria
  Proposal: the earlier criteria stay as history and only the new ones are judged. When a direction is too large to write a Contract for, split it into sub-Aims
  (`aim-create --parent`, or `aim-parent-add` once for an existing Aim); when the work can be written
  as a Contract, accept a Goal and split it with the Goal tree instead. A parent Aim is evaluated on
  its own, citing its sub-Aims' evaluations; it is never achieved automatically.
- Grouping: Proposals and Goals can never move to another Aim, so group early. When a second Proposal
  on an Aim pursues the same direction as an earlier one (for example, a product idea chosen by a
  research Goal), propose a sub-Aim for that direction first (with user approval) and put that
  Proposal and later ones under it.
- Follow links: when a Goal starts from an earlier Goal's result, or continues a stopped Goal another
  way, record `goal-follow-add <goal> <previous-goal> --actor <agent> --reason "…"`. It may cross Aims and
  link finished Goals, never blocks Attempts, and shows as "이어받음" in the graph and the Goal's
  relations. Use `goal-dependency-add` only when a Goal must wait for another's satisfied Verdict, and
  `goal-parent-add` only when the parent is a real task with its own Contract.
- Proposal: one approach. When the cause is uncertain, write it as `Gap: … / Hypothesis: if we …,
  then … improves` so the Goal tests one intervention against the original gap.
  Make the first line a one-sentence summary: the UI uses it as the title, list label, and default Goal
  target. Put the explanation, achievement criteria, and Gap/Hypothesis on the following lines.
- Contract: `scope` names the area and files; `criterion` states the observable success condition and
  when to stop trying; `verification` lists the exact commands or inspection the verifier will use.
- Attempt: one implementation try. Use your agent name as executor and a short operation.
- Evidence: record after completing the Attempt, including failed ones. State what you ran and what
  you observed (`pytest -q: 114 passed`, changed files, how to reproduce). Never record a result you
  did not observe. Save the output you relied on to a file and pass `--attach <file>` (≤10MB each) so
  the verifier sees exactly that copy; attachments can only be added when the Evidence is recorded.
- References: link the design notes, memory modules, or issue URLs an Aim, Proposal, or Goal depends
  on with `reference-add` (inside the project, paths are stored relative to its root). A referenced
  document can change later, so never let a reference stand in for the Contract's criterion.
- Verification: after `verification-begin`, ask the user to submit the Verdict in the desktop app, or run delegated
  judging (below), or leave it waiting as the level above allows. Do not start work that depends on the Goal until
  the Verdict exists; other work may continue.
- Delegated judging: only when the user has delegated Verdicts or Aim evaluations to a separate agent (one that
  did not execute the work, preferably a different model), run that agent on a copy of the journal, give it
  the Contract or Aim criteria, the Evidence, and the partial-satisfaction rules, and fix its answer with a
  schema. Record its report as Evidence under its name, then record its result unchanged under its name
  with `--reason`. Never judge your own execution, and never record under the user's name.
  `goal-loop-judge` does all of this: after `verification-begin <goal-id> <attempt-id>`, run
  `goal-loop-judge --judge <judge> goal <goal-id>`, and `goal-loop-judge --judge <judge> aim <aim-id>` for an Aim
  (the project's instructions give the `--judge` value for your agent; a judge recorded under your own name is
  refused). `--no-record` shows the judgment without recording it. If you disagree with a judgment, record your
  view as Evidence and tell the user; never re-run it to get a different result.
  A project's `.goal-loop/judging.json` may set `copy_exclude`, `attachments_only`, and `rules` (`code` or
  `notes` for work that is not code); command-line choices override it.

**Session end.** Do not leave an Attempt `running` silently: complete it with its observed outcome, or
tell the user it is still running and why.

**Memory.** Goal Loop holds the working state and verification. The memory timeline records milestones
and decisions and cites Goal Loop IDs (`goal-3 verified`) instead of repeating their content.
When the project uses Memory Tool, a recorded Verdict or Aim evaluation returns a `memory_draft` (also
`goal-loop memory-draft`): adjust that line and record it with `python -m memory_tool record "…"`.

## Closure paths and attribution

When you propose an approach as an agent, always pass `--actor <your agent name>` to `proposal-create` so the
human can tell agent proposals apart. Closing a Proposal (`proposal-close`), stopping a Goal (`goal-stop`), and
abandoning an Aim (`aim-abandon`) are human decisions that cannot be undone: ask for explicit user approval and
the reason before issuing them, and never infer them from inactivity. `goal-hold-add` requires an actor and a
reason. Core rejects depending on an ancestor Goal.

## React / Tauri UI preview

In the Goal Loop source repository, the desktop preview lives in `ui/`. Start it with
`cd ui; npm run tauri dev`; its launcher adds that repository's venv and Rust tool paths and uses Vite port 5174. It consumes only the read-only
`ui-projection` and `next` projections and sends mutations through an allow-listed CLI adapter.
The UI is a human-facing surface, not evidence that an agent has authorization to create facts.
Keep the same semantic guardrails above when describing or operating it.

The desktop UI shows Korean display labels for the same Core concepts: 목표 (Aim), 접근안 (Proposal),
과제 (Goal), 완료 기준 (Contract), 실행 (Attempt), 관찰 근거 (Evidence), 검증 판단 (Verdict), and
목표 달성 평가 (Aim Evaluation). Use the English names in CLI commands; use the Korean labels when
pointing a human to a screen.

The workspace has a 목표 navigator, a graph of 목표 → 접근안 → 과제, and a detail pane. Each detail
screen has one "지금 할 일" box driven by `next`, stage tabs, and collapsible criteria, relations,
hold, and activity sections. Proposal revision is not offered in the UI (the CLI command remains);
an accepted approach routes changes to Contract revision or a new Proposal. After a failed run the UI
records a retry as a retry Decision followed by a new Attempt, exactly as the CLI does. Evidence
cited by a Verdict can be corrected from the UI, which opens the same Impact Review flow; 검토함
shows it, and 실행 대기함 shows only Runtime outbox delivery state. Hiding records is a local display
preference, not a journal fact. `ui-projection` is schema version 19 (v19 adds `criteria_superseded_by_proposal_id` on
Proposals: criteria replaced by `aim-criteria-revise` point at the criteria that replaced them, and the app and
`goal-loop-judge aim` judge against the current criteria only; v18 adds `aim_links`: each Aim link with the linked Aim's state as
`aim-links` reports it, shown in the app's Aim detail "연결된 목표" with a button that opens the linked project, and as a
link summary on graph Aim cards; v17 adds `external_evaluations`: evaluations imported from linked Aims of other
journals with `aim-link-import`, citable by `aim-evaluate` as `external-evaluation-*`, and `external_evaluation_ids` on Aim
Evaluations; v16 adds `follows` edges: a Goal built on or continuing an earlier Goal, with actor and reason, drawn as 이어받음; v15 adds `memory_drafts`: a suggested timeline line and `python -m memory_tool record` command for each valid Verdict or Aim Evaluation the timeline does not cite yet, also printed by `memory-draft` and returned by `delegated_judging` as `memory_draft`; Goal Loop never writes the knowledge folder; v14 adds `memory_mentions` and `memory_documents`: Memory Tool timeline entries citing record IDs and excerpts of referenced `.memory` documents, read-only and empty without Memory Tool content; the knowledge folder is found as Memory Tool finds it — `.memory` by default, renamed by the project's `.memory-tool.yml` (`base:`) or `MEMORY_TOOL_BASE`, or the project root itself (`base: "."`), shown in the details' "메모리 기록" section and reference previews; v13 adds `ao_runs`: each AO Goal linked to a Goal, summarized from the AO snapshots in the journal, shown in the Goal detail's "AO 실행" section, including the `completion:advisory` judgments an `ao_cli.v1` run (always started with `--external-verdict`) recorded instead of blocking completion; v12 adds Verdict reasons; v11 and earlier add `contract_history`,
`decisions`, `evidence_corrections`, `impact_reviews`, closure/attribution facts, `project_root`,
references, Evidence attachments, the Aim tree, and sub-Aim evaluation citations). Runtime dispatch remains an explicit
CLI/operator action.
