# 인수인계: 사용법을 지침 파일에서 스킬로 옮기기

- 작성일: 2026-11-12
- 출처: `memory_notion` 저장소에서 진행한 프로젝트 설정 점검 세션 (`project-setup` 스킬 시험)
- 상태: memory_tool 쪽 작업 1~3과 5는 구현했습니다(1.9.0에서 `.agents/skills/` 설치, 이후 `mt-record`와 템플릿 정리). 작업 4는 `memory_notion`의 `CLAUDE.md`를 사용자가 직접 정리하도록 안내했습니다. SessionStart hook은 범위에서 뺐습니다. 같은 방향의 Goal Loop 작업은 `goal_loop_tool/docs/handoff/2026-11-12-skills-over-instructions.md`에 있습니다.
- 열린 질문의 결론: 새 스킬은 `mt-record` 하나로 정했습니다. `guidelines.md`는 남기지 않고, `minit --update-all`이 `.backup`으로 이름을 바꿉니다.

> 이 문서와 테스트 데이터에 실제 업무 노트를 넣지 마십시오. 회귀 테스트는 합성 데이터로 작성합니다.

## 1. 배경

`memory_notion`의 `CLAUDE.md`는 129줄입니다. 그런데 "Read First"가 `.claude/guidelines.md`(194줄)를 먼저 읽으라고 지시하므로, 에이전트는 매 세션 320줄 정도를 읽습니다. 그중 대부분은 명령 문법과 절차처럼 필요할 때만 읽으면 되는 내용입니다. 사용자는 `CLAUDE.md`와 `AGENTS.md`를 최소화하고, 도구를 쓰는 방법은 스킬로 옮기기를 원합니다.

## 2. 확정된 결정: 세 가지 층

| 층 | 담는 내용 | 위치 |
| :--- | :--- | :--- |
| 항상 적용되는 원칙과 규칙 | 프로젝트 원칙, "모든 활동은 `m`으로 기록한다" 같은 규칙 (규칙마다 한 줄로 쓰고, 방법은 스킬 이름으로 안내) | `CLAUDE.md` |
| 사용법과 절차 | 명령 문법, 기록하는 방법, 검색, 문서 종류와 작성 절차 | 스킬 (`.claude/skills/`, `.agents/skills/`) |
| 매 세션 반드시 실행할 명령 | `mcontext` 등 | SessionStart hook (검토 단계) |

스킬은 사용자의 요청이 description과 맞을 때 호출됩니다. 그래서 요청이 없어도 해야 하는 행동(예: Micro-Logging)은 스킬에만 두면 실행되지 않습니다. 이런 규칙은 `CLAUDE.md`에 한 줄로 남겨야 합니다.

## 3. 요청하는 작업

1. **`guidelines.md`를 스킬로 바꾸기:** `guidelines.md`의 내용(기록 시점, 검색, 일괄 기록, 맥락 생성)과 `CLAUDE.md.template`의 "Quick Commands"를 스킬 하나(가칭 `mt-record`)로 옮깁니다. description에는 기록, 검색, 맥락 생성 요청을 모두 담습니다.
2. **`CLAUDE.md.template` 줄이기:** 항상 적용할 규칙 몇 줄과, 각 규칙의 방법을 맡은 스킬의 이름만 남깁니다.
3. **Codex용 스킬 설치:** `minit`은 지금 `mt-*` 스킬을 `.claude/skills/`에만 만듭니다. 같은 스킬을 `.agents/skills/`에도 만들게 합니다. `memory_notion`에는 이번 세션에서 손으로 복사해 두었으므로, 구현한 뒤 다시 동기화해야 합니다.
4. **문서 작성 규칙 정리:** `memory_notion`의 `CLAUDE.md`에 있는 "Document Creation Rule"과 "Document Types" 표가 `mt-write`나 `mmodule guide`와 겹치는지 확인합니다. 겹치는 내용은 스킬 쪽으로 모읍니다.
5. **기존 프로젝트로 옮겨 가는 방법:** 사용자가 직접 쓴 `CLAUDE.md`는 덮어쓰지 않습니다. 템플릿만 바꾸고, 기존 프로젝트에서는 무엇을 지울 수 있는지 알려 주는 방식이 적합합니다.

## 4. 열린 질문

- 스킬의 이름과 개수를 정해야 합니다. 기록용 스킬 하나로 충분한지, 검색용 스킬을 따로 둘지 검토해야 합니다.
- 이전 버전과의 호환을 위해 `guidelines.md`를 남길지 정해야 합니다. 남긴다면 스킬을 안내하는 짧은 파일로 둘 수 있습니다.
- `minit`이 SessionStart hook 설정까지 제안할지 정해야 합니다. Codex에 같은 기능이 있는지는 아직 확인하지 않았습니다.
