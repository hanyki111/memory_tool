<!-- goal-loop:begin (project-init --agents가 관리하는 절입니다. 표지 안을 고치면 다시 실행할 때 바뀝니다) -->
## Goal Loop

이 프로젝트의 작업은 Goal Loop 기록(`.goal-loop/`)으로 추적한다. 명령과 절차는 `goal-loop` 스킬과 `goal-loop guide`에 있다.
Aim을 만들거나 나누기 전, 기준과 Contract를 쓰기 전, 불합격이 나온 뒤에는 `goal-loop-planning` 스킬을 따른다.

- 세션 시작: `python -m memory_tool context`를 실행하고 `.claude/memory-context.md`를 읽은 뒤 `goal-loop where`(`source: project` 확인), `goal-loop next`, `goal-loop status`로 열린 Aim, 실행 중인 Attempt, 검증 대기를 요약한다.
- 이 에이전트의 이름은 `codex`이다. Proposal과 참고 문서의 `--actor`, Attempt의 실행자, Evidence의 관찰자로 이 이름을 쓴다.
- `user` 이름으로는 아무것도 기록하지 않는다. 종료, 일시 중지와 재개, 보류, 검토 해소는 사용자가 정한다.
- Verdict와 Aim 평가는 직접 기록하지 않고 실행하지 않은 판정자에게 맡긴다: `goal-loop verification-begin <goal-id> <attempt-id>` 뒤
  `goal-loop-judge --judge claude goal <goal-id>`, Aim은 `goal-loop-judge --judge claude aim <aim-id>`.
- 판정에 동의하지 않으면 의견을 Evidence로 남기고 사용자에게 알린다. 다른 결과를 얻으려고 판정을 다시 실행하지 않는다.
<!-- goal-loop:end -->
