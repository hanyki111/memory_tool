# 인수인계: 질문 세션 중 기록 예외와 템플릿의 기본 대상

- 작성일: 2026-11-13
- 출처: `memory_notion` 저장소에서 agent-workbench의 `project-setup`(0.1.4)을 처음 적용한 세션
- 상태: 제안만 정리했으며, 구현은 시작하지 않았습니다. 같은 날의 Goal Loop 쪽 메모는 `goal_loop_tool/docs/handoff/2026-11-13-agents-layout-and-skill-refresh.md`에 있습니다.

> 이 문서와 테스트 데이터에 실제 업무 노트를 넣지 마십시오. 회귀 테스트는 합성 데이터로 작성합니다.

## 1. 배경

agent-workbench(`github.com/hanyki111/agent-workbench`)는 Goal Loop와 Memory Tool을 함께 쓰는 프로젝트를 설정하는 Claude Code plugin입니다. 이 plugin에는 계획을 질문으로 검증하는 스킬이 두 개 들어 있습니다. `grill-me`는 사용자가 입력하는 입구이며 agent-workbench가 직접 작성했고, `grilling`은 `grill-me`가 따르는 질문 방식이며 외부 원본(mattpocock/skills)을 고치지 않고 포함한 스킬입니다. 그리고 Memory Tool의 규칙은 plugin에 복사해 두지 않고, 실행할 때 프로젝트에 설치된 템플릿(`<base>/templates/CLAUDE.md.template`)에서 읽습니다. 이 설치본은 `minit`이 원본(`memory_tool/templates/claude/CLAUDE.md.template`)을 복사해서 만듭니다(`core/init.py`).

## 2. 요청하는 작업

1. **질문 세션 중의 기록 예외를 해석 규칙으로 정하기.** `memory_notion`처럼 "모든 활동을 기록한다"는 규칙이 있는 프로젝트에서는, `grill-me`로 질문하는 라운드마다 기록이 끼어들어 질문의 흐름이 끊깁니다. 그래서 agent-workbench는 지금 이런 프로젝트의 `AGENTS.md`에 관리 절 한 줄을 넣고 있습니다.

   이 예외를 `mt-record`에 "프로젝트 규칙보다 우선한다"는 형태로 넣는 방안은 채택하지 않습니다. `mt-record`는 "기록 시점은 프로젝트가 정하고, 스킬은 방법만 다룬다"고 정하고 있으므로(`SKILL.md` 10번째 줄), 스킬이 프로젝트 규칙을 뒤집으면 이 원칙과 충돌합니다. 또한 프로젝트 지침이 스킬보다 우선하므로 효과도 보장되지 않습니다.

   대신 역할을 두 곳으로 나눕니다.

   - **`mt-record`(이 저장소):** 규칙의 의미를 정하는 해석 규칙을 짧게 넣습니다. 예: "'모든 활동을 기록한다'는 규칙에서, 질문으로 계획을 검증하는 세션은 하나의 활동으로 본다. 합의가 끝나면 정해진 결정을 기록할지 묻는다. 프로젝트가 질문 라운드를 명시적으로 기록 대상으로 정했다면 그 규칙을 따른다." 마지막 단서는 질문 과정 자체를 남기려는 프로젝트의 결정을 덮어쓰지 않기 위해 반드시 넣어야 합니다.
   - **`grill-me`(agent-workbench):** 질문 세션 동안 지킬 동작을 넣습니다. 에이전트는 `AGENTS.md`만 보고도 `m`을 바로 실행할 수 있으므로, 라운드가 끝날 때 `mt-record`가 로드되어 있다고 보장할 수 없습니다. 반면 질문 세션에서는 `grill-me`가 로드되므로, 실제로 동작을 바꾸는 곳은 이 스킬입니다. `grilling`은 외부 원본을 그대로 유지하기 위해 고치지 않습니다.
     agent-workbench 0.1.5에서 반영을 마쳤습니다. 넣은 내용은 "라운드 동안에는 프로젝트가 모든 활동의 기록을 요구하더라도 기록하지 않는다. 질문 세션은 하나의 활동으로 보고 끝에 한 번 기록 여부를 묻는다. 프로젝트 규칙이 질문 라운드를 명시적으로 기록 대상으로 정했다면 그 규칙을 따른다."입니다. 다만 모델이 `grill-me`를 거치지 않고 `grilling`을 직접 호출하면 이 동작이 적용되지 않습니다. 그 경우는 `mt-record`의 해석 규칙이 맡습니다.

   두 곳에 적는 내용은 중복되지 않습니다. `mt-record`는 규칙의 의미를, `grill-me`는 질문 세션에서 할 동작을 다룹니다. agent-workbench는 `mt-record`의 해석 규칙이 들어간 memory_tool 버전이 릴리스된 뒤에 `project-setup`에서 관리 절을 제거합니다. 릴리스하면 그 버전 번호를 agent-workbench 쪽에 알려 주십시오.

2. **템플릿의 기본 대상을 `AGENTS.md`로 바꾸기.** 템플릿은 지금 "Copy this into your project's `CLAUDE.md` (or `AGENTS.md`)"라고 안내합니다. 오늘 두 저장소가 모두 `AGENTS.md`를 원본으로 바꿨습니다(`goal_loop_tool`의 `36c8c4f`, `memory_notion`의 `d576f33`). 그러므로 기본 대상을 `AGENTS.md`로 하고, "`CLAUDE.md`는 `@AGENTS.md`로 가져온다"를 덧붙이는 편이 맞습니다. 같은 표현이 `mt-record`의 `SKILL.md` 10번째 줄에도 있으므로 함께 고쳐 주십시오.
   수정은 원본에서 하고, `minit --update-all`로 설치본을 갱신합니다. agent-workbench가 읽는 경로는 설치본(`<base>/templates/CLAUDE.md.template`)입니다. 따라서 설치본의 이름이나 위치를 바꾼다면 변경 기록에 적어 주십시오. 원본의 경로만 바뀌는 것은 agent-workbench에 영향을 주지 않습니다.

3. **pre-commit hook의 큰 파일 경고 정리.** 2026-11-12에 인수인계 메모(`2715c27`, 파일 한 개)를 커밋할 때 "CRITICAL: Very large files detected! Strongly recommend archiving before commit."이 나왔습니다. 이 경고는 `utils/git_hooks.py`의 document-health hook이 `python -m memory_tool context --check-health-only`를 실행해서 내는 것입니다. 이 검사는 커밋에 들어간 파일이 아니라 지식 베이스 전체를 봅니다. 2026-11-13에 실행했을 때 CRITICAL로 판정된 파일은 다음 다섯 개입니다.

   - `memory-tool/module.md`: 8222줄
   - `memory-tool/project-management/module.md`: 2640줄
   - `memory-tool/knowledge-graph-system/module.md`: 1315줄
   - `memory-tool/core-system/module.md`: 1280줄
   - `memory-tool/project-management/PLAN-document-consolidation/module.md`: 879줄

   해당 파일을 정리하거나, 경고의 기준과 대상(이번 커밋에 들어간 파일만 볼지)을 다시 정해 주십시오. 그리고 hook은 3초나 5초를 기다린 뒤 항상 `exit 0`으로 끝나므로, 경고는 커밋을 막지 못하고 지연시키기만 합니다. 기준을 다시 정할 때 이 동작을 유지할지도 함께 정해 주십시오.

## 3. 참고

- `memory_notion`의 `AGENTS.md`에는 템플릿의 규칙 가운데 "타임라인에는 `m`으로만 기록한다"와 "지난 작업을 물으면 먼저 `ms`로 검색한다"를 넣었습니다. "`mbase show`로 경로를 확인한다"는 넣지 않았습니다. 이 저장소는 지식 폴더가 `.memory/`로 정해져 있고, 다른 지침도 그 경로를 직접 쓰기 때문입니다.
- `memory_notion`의 `.claude/guidelines.md`는 사용자가 직접 지웠습니다. 그래서 백업 파일이 없는 것은 `--update-all`의 결함이 아닙니다.
