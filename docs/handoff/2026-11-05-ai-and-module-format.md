# 인수인계: AI 기능 정비와 모듈 형식 개편

- 작성일: 2026-11-05
- 출처: `memory_notion` 저장소에서 진행한 노트 체계 점검 세션
- 상태: 쟁점 1~3의 논의를 마쳤고, 6절의 구현 계획을 승인받아 1단계부터 진행합니다(2026-11-05).

> 이 문서와 테스트 데이터에 실제 업무 노트를 넣지 마십시오. `memory_notion`의 타임라인에는 회사 업무 내용이 있습니다. 회귀 테스트는 합성 데이터로 작성합니다.

## 1. 배경

사용자는 `memory_tool`을 개인 노트(`memory_notion/.memory`)에 쓰고 있으며, 체계가 무겁고 모듈화 방법을 정하기 어렵다고 느낍니다. 점검에서 확인한 원인은 다음과 같습니다.

- 도구가 코딩 에이전트의 프로젝트 맥락 관리를 중심으로 설계되어, 개발용 구조가 개인 노트에도 그대로 적용되었습니다.
- 타임라인 기록은 쌓이지만 모듈로 옮기는 절차가 작동하지 않습니다.
- Obsidian 플러그인 패널은 오늘 기록만 보여 줍니다. 태블릿에서는 지난주와 이번 주의 기록을 이어 보기 어려웠습니다.
- 파일명과 모듈 구조를 바꿀 때 AI 코드가 함께 갱신되지 않았고, 이를 잡아 줄 테스트도 없습니다.

## 2. 확정된 결정

1. **도구 경계:** Goal Loop는 사전 계획, Memory Tool은 사후 기록입니다. 타임라인과 AI 상담 화면을 Goal Loop 앱에 넣지 않습니다.
2. **시작 환경:** 노트북과 데스크톱의 VS Code부터 시작합니다. Obsidian에서 전체 AI 지원을 받는 일은 추후 서버 접속 방식으로 검토합니다. 동기화에는 Obsidian Sync를 쓰고 있습니다.
3. **문서 작성:** 사용자와 AI가 모두 씁니다. 사용자는 문해력과 문장력을 유지하기 위해 직접 쓰는 것을 목표로 하고, 어려울 때 AI에게 의지합니다. 따라서 AI 초안을 기본값으로 삼지 않습니다.
4. **OKF:** 전체 규격이 아니라 부분 도입합니다.
5. **`auto-tag`:** 제거합니다.
6. **`ai-organize`, `suggest-ai`:** 아이디어만 참고하여 AI 기능 정비와 함께 처리합니다.
7. **Notion 키:** 사용자에 따르면 이미 폐기된 키이므로 우선순위가 낮습니다. 사용자는 현재 Notion 동기화를 쓰지 않습니다.
8. **주간 리뷰 스킬:** 논의가 끝나기 전에는 만들지 않습니다.
9. **문서 종류:** 참고, 이해, 방법, 판단의 4종으로 시작합니다. `type`은 선택 항목이며, 도구는 알 수 없는 값도 거부하지 않습니다. 새 문서 20개 정도를 쓴 뒤 둘 사이에서 자주 망설이면 `방법`을 `참고`에 합칩니다.

   | 종류 | 답하는 질문 | 갱신 계기 | 기존 분류 |
   |:---|:---|:---|:---|
   | 참고 | 그 값이나 사실이 무엇이었지? | 대상이 바뀔 때 | `reference`, `implementation`, `tracker`, 진행 중인 `inquiry` |
   | 이해 | 왜 이렇게 작동하지? | 이해가 깊어질 때 | `concept` |
   | 방법 | 어떻게 하지? | 적용하다 실패했을 때 | `method` |
   | 판단 | 왜 그렇게 보았거나 정했지? | 고쳐 쓰지 않고 새 판단으로 대체 | `analysis`, 끝난 `inquiry` |

10. **문서 밖으로 보내는 내용:** 일상 기록과 `idea`, 작은 결정은 타임라인에 남기고, `plan`은 Goal Loop로 보냅니다. 미결 질문은 `참고` 문서의 `## 열린 질문` 제목 아래에 적고, 결론이 나면 `판단` 문서를 만들어 링크합니다.
11. **문서 모양:** 템플릿을 완전히 제거합니다. `mmodule create`는 frontmatter와 제목만 만들며, 필수 절과 안내 주석은 없습니다. 필드는 `type`, `description`, `tags`, `generated`로 시작하고, `sources`와 `stale_after`는 해당될 때만 씁니다.
12. **작성 지원:** 종류별 AI 가이드(질문과 점검 항목)를 두고 `mmodule guide <종류>`와 `mt-write` 스킬로 전달합니다. CLI에 대화 화면을 만들지 않습니다. 임시 기본 동작은 질문, 작성 후 지적, 막힐 때 개요, 요청 시 대신 작성의 순서입니다.
13. **코드 프로젝트:** 문서 종류가 아니라 지식 베이스가 놓인 장소와 코드 연결로 봅니다. `--project`를 만들지 않으며, 코드 연결은 어떤 문서든 `sources`에 적을 수 있습니다. 기존 `Related Files`도 계속 읽습니다.
14. **현황:** 별도의 종류나 문서로 두지 않습니다. 코드 작업을 재개할 때는 타임라인과 Git을 읽고, Goal Loop가 있으면 함께 읽습니다. Goal Loop는 별도의 프로그램이므로 도구와 안내문이 그 존재를 전제하면 안 됩니다. 계속 변하는 상황을 추적하는 문서는 `참고`와 `stale_after`로 처리합니다.
15. **기존 구조:** Kind, Nature, `grow`, `--part`, `--draft`, 번들 템플릿은 호환 기간을 거쳐 제거합니다. 쓰기 기능은 경고와 함께 한 버전 유지하고, 기존 문서를 읽는 기능은 제거하지 않습니다.
16. **`PLAN.md`:** `mplan module`과 함께 호환 기간 없이 제거합니다. `mplan`의 나머지 기능과 `PLAN-*.md` 처리는 유지합니다.
17. **하위 문서:** 도구로 하위 문서를 만들면 `topic.md`를 `topic/topic.md`로 옮기고, 하위 문서는 `topic/child.md`로 만듭니다. 상위 문서의 내용은 건드리지 않습니다. 상위 문서가 없는 폴더와, Obsidian에서 직접 만든 `topic.md`, `topic/child.md` 형태도 정상으로 처리합니다.
18. **AI 명령:** `ai-organize`를 `mmodule audit`으로 바꾸고, 이동, 계층, 네임스페이스 제안은 버립니다. 분리와 병합 후보 계산은 리뷰의 입력으로 재사용합니다. `suggest-ai`는 `suggest-links --ai`로 합칩니다. 모든 기능은 제안만 하며, 문서는 승인 후에 바꿉니다.
19. **OKF 방향 수정:** `title`은 파일명과 다를 때만 씁니다. `index.md`는 자동으로 만들지 않고, 있을 때만 읽습니다.

## 3. AI 기능 점검 결과

임시 사본과 `claude-cli` 설정으로 시험한 결과입니다. 경로는 저장소 기준입니다.

| 기능 | 상태 | 원인과 위치 |
|:---|:---|:---|
| `mask` | 오답 위험 | `memory_tool/core/memory_agent.py:360-363`, `:379-383`이 `{day:02d}.md`만 찾아 날짜형 파일명을 읽지 못합니다. `:527`, `:552`는 `current.md`만 찾습니다. 계획 도구(`:497`)도 같은 형식을 씁니다. |
| `msummary` | 고장 | `summary week`가 `memory_tool/summary/timeline_summarizer.py:139`에서 `AttributeError: 'str' object has no attribute 'as_posix'`로 중단됩니다. 도움말의 `--week`, `--days`는 실제 옵션이 아닙니다. 실제 범위는 인수(`today`, `week`, 날짜)로 받습니다. |
| `module suggest-ai` | 고장 | `memory_tool/commands/modules.py:563` 이후의 경로 검사에서 시험한 이름이 `Module not found`로 실패했습니다. `memory_tool/core/ai_suggester.py:268`도 예전 파일 이름만 읽습니다. |
| `module auto-tag` | 고장 | `memory_tool/commands/modules.py:651` 이후에서 같은 오류가 납니다. 제거 대상입니다. |
| `module ai-organize` | 잘못된 결과 | `memory_tool/core/ai_organizer.py:92`가 예전 파일 이름만 읽어, 544KB 문서가 있어도 문제가 없다고 답합니다. `find_namespace_issues`는 `projects/` 밖의 최상위 모듈을 문제로 봅니다. |
| `module from-text` | 일부 정상 | 미리보기는 작동합니다. `memory_tool/core/ai_module_generator.py:627-629`는 예전 3개 파일 형식으로 저장하고, 프롬프트도 구 분류(Feature/Topic)를 씁니다. 저장은 실행해 보지 않았습니다. |
| `mcontext` | 작동, 무거움 | 날짜형 파일을 인식합니다. 결과가 약 43KB이고 `PLAN.md`까지 모듈로 나열합니다. |
| `ms --semantic`, `--hybrid` | 정상 | 실행에 8~9초가 걸립니다. |

**공통 문제**

- AI 코드를 참조하는 테스트가 없습니다. 테스트 파일 13개 중 해당 파일이 없습니다.
- `memory_tool/commands/modules.py:571`, `:659`, `:844`, `memory_tool/commands/planning.py:77`의 오류 메시지는 `claude-cli`를 쓸 수 있어도 API 키 설정을 안내합니다.
- `minit`의 기본 제공자가 `anthropic`이라, 키가 없으면 `claude-cli`가 있어도 기본 설정에서 AI 기능이 실패합니다.
- `memory_tool/llm/claude_cli_client.py:80-100`은 프롬프트를 명령줄 인수로 넘깁니다. 긴 기간을 다루면 Windows의 명령줄 길이 제한에 걸릴 수 있습니다. 코드만 보고 판단했으며 재현하지는 않았습니다.
- `core/timeline.py`에 `timeline_filename`(`:36`), `date_from_timeline_path`(`:51`)가 이미 있으니 경로 처리를 여기로 모으는 것을 먼저 검토하십시오.

## 4. OKF 부분 도입 방향

참고: [OKF SPEC v0.2](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)

**가져오는 것:** frontmatter의 `type`, `title`, `description`, `tags`, `generated`, `sources`, `stale_after`와 폴더별 `index.md`

**가져오지 않는 것:** Attested Computation과 관련 필드, 규격 전체 준수 의무

**유의 사항**

- OKF는 형식 규격이며 언제 어떤 단위로 문서를 만들지는 정하지 않습니다. 모듈화 기준은 따로 정해야 합니다.
- v0.1에서 v0.2로 바뀌며 하위 호환이 깨진 변경이 있었습니다. 도구가 규격 버전에 강하게 묶이지 않게 합니다.
- `index.md`와 `log.md`는 OKF의 예약 파일명입니다.
- OKF의 링크는 일반 Markdown 형식입니다. 노트에는 위키 링크가 266개, Markdown 링크가 39개 있습니다. 제안은 위키 링크를 당분간 유지하는 것이며, 도구는 두 형식을 모두 읽어야 합니다.
- 기존 문서를 한꺼번에 바꾸지 않습니다. `type`이 없는 문서도 계속 정상 처리해야 합니다.
- `generated.by`로 사람과 AI의 작성을 구분합니다(`human:<id>`, `<producer>/<version>`). 직접 쓰기 목표를 확인하는 데 씁니다.

**예시 (합성 데이터)**

```markdown
---
type: 결정
title: 예시 규칙
description: 표시 항목과 그 결정 경위
tags: [예시]
generated: { by: human:example, at: 2026-11-05T10:00:00+09:00 }
sources:
  - id: tl-1
    resource: timeline/daily/2026-09/2026-09-03.md
---

본문은 자유 형식으로 씁니다.
```

## 5. 미결 쟁점

구현 전에 사용자와 논의할 사항입니다.

1. **문서 종류:** 2026-11-05에 결정했습니다(2절 9~14번). 4종이 실제 문서에 맞는지는 파일명으로만 대조했으므로, 쓰면서 검증합니다.
2. **기존 구조의 처리:** 2026-11-05에 결정했습니다(2절 15~17번).
3. **`ai-organize`, `suggest-ai`의 처리:** 2026-11-05에 결정했습니다(2절 18번).
4. **타임라인 기반 제안(리뷰):** 사용자 논의가 먼저입니다. `memory_tool/review/`에 주간·월간 리뷰 코드가 약 640줄 있으므로, 재사용 여부도 함께 판단합니다. 초안은 다음과 같습니다.
   - 지난 리뷰 이후의 기록을 원할 때 실행합니다.
   - 새 문서, 기존 문서 갱신, Goal Loop 후보, 그대로 둘 기록으로 나눕니다.
   - 한 번에 다섯 건 이하로 제안합니다.
   - 마지막 리뷰 날짜와 승인·거절 결과를 남깁니다.
5. **글쓰기 지원 단계:** 2절 12번의 순서를 임시 기본값으로 두고, 써 보면서 조정합니다. 이 순서는 가이드 파일에 적으므로 코드를 바꾸지 않고 수정할 수 있습니다.
6. **모듈 생성 기준 초안:** 같은 주제가 3일 이상 나오고 다시 찾을 내용인 경우, 실제로 다시 찾아본 경우, 나중에 "왜 이렇게 정했지?"에 답해야 하는 결정인 경우입니다. 새 문서보다 기존 문서 갱신을 먼저 검토합니다.
7. **기존 노트의 처리:** 도구 쪽 형식이 정해진 뒤 노트 세션에서 별도로 논의합니다. 쟁점은 `Projects/` 사본(모듈 용량의 42%), 300줄을 넘는 문서 37개, 비어 있는 `PLAN.md` 53개입니다.

## 6. 구현 계획

브랜치는 `feature/module-format-and-ai`입니다. 시작 시점의 테스트는 454개가 모두 통과합니다. 각 단계는 별도의 커밋으로 나누고, 단계마다 테스트를 통과시킵니다.

**버전 1.2.0**

1. **읽기 경로와 파일 구조**
   - `core/timeline.py`로 타임라인 경로 처리를 모읍니다.
   - 모듈 문서 찾기를 `resolve_module_doc`으로 모읍니다. 대상은 예전 파일명을 직접 읽는 파일 중 `memory_agent`, `ai_organizer`, `ai_suggester`, `module_summarizer`, `context/builder`, `warnings`, `health_checker`, `tui/modules_mode`입니다. 사용하지 않는 `notion/`은 제외합니다.
   - `discover_all_modules`가 `PLAN.md`를 제외하게 고칩니다. `"PLAN.md".isupper()`가 거짓이라 지금은 모듈로 나열됩니다.
   - `mmodule rename`이 단일 파일과 하위 문서를 올바로 옮기게 고칩니다. 현재는 `topic.md`, `topic/child/child.md`의 이름을 바꾸면 `subject/topic/child/child.md`가 되고 `topic.md`는 남습니다.
2. **`mask`, `msummary`:** 오류를 고치고, 아래의 회귀 테스트를 합성 데이터로 작성합니다.
3. **제거와 정리**
   - `auto-tag`, `planner/module_plan.py`, `mplan module`을 제거합니다.
   - 도움말의 없는 옵션과 API 키만 안내하는 오류 메시지를 고칩니다.
   - `minit`의 기본 제공자를 사용 가능한 쪽으로 정하게 바꿉니다.
   - `mcontext`가 출력하는 예전 모듈 기준 안내를 고칩니다.
4. **AI 명령**
   - `mmodule audit`을 추가하고 `ai-organize`는 경고를 내는 별칭으로 둡니다. 이동, 계층, 네임스페이스 제안은 제거합니다.
   - `suggest-links --ai`를 추가하고 `suggest-ai`는 별칭으로 둡니다.
5. **새 문서 형식**
   - `mmodule create [--type 종류]`가 frontmatter와 제목만 만들게 합니다. 새 문서는 `주제.md` 하나이며, 하위 문서를 만들 때 2절 17번처럼 동작합니다.
   - `--kind`, `--nature`, `--draft`, `grow`, `merge-templates`는 기존 동작을 유지하되 경고를 출력합니다.
   - `mcheck`가 `sources`의 코드 경로도 검증하게 합니다. `Related Files`, `Decisions`, `Current` 제목은 있으면 읽고 없어도 정상으로 처리합니다.
   - 위키 링크와 Markdown 링크를 모두 읽는지 확인하고, 읽지 못하면 고칩니다.
6. **AI 가이드**
   - 종류별 가이드 4개를 추가합니다. 기존 템플릿의 갱신 계기, 실패 사례, 반대 논거를 질문으로 옮깁니다.
   - `mmodule guide <종류>`와 `mt-write` 스킬을 추가하고, `minit`의 스킬 복사 목록에 넣습니다.
   - `from-text`가 같은 가이드를 읽고 단일 문서로 저장하게 합니다.
7. **플러그인과 문서**
   - 플러그인의 생성 화면을 `--type` 기준으로 바꾸고, `grow` 버튼과 명령을 제거합니다. CLI와 함께 1.2.0으로 올립니다.
   - `mhelp`, `README.md`, `guidelines.md`, `MODULE-ORGANIZATION.md`와 번들 사본을 새 기준으로 고칩니다. 코드 재개 시 타임라인과 Git을 읽고, Goal Loop가 있으면 함께 읽으라는 안내도 여기에 넣습니다.

**버전 1.3.0 (모든 기기의 플러그인을 1.2.0으로 바꾼 뒤)**

8. 호환 기능을 제거합니다. 대상은 `--kind`, `--nature`, `--draft`, `grow`, `--part`, `merge-templates`, `modules.default_kind`, `ai-organize`, `suggest-ai`, `module_templates.py`, 번들 템플릿과 그 테스트입니다. `archiver.py:474`의 `plan` 판별은 기존 문서를 읽기 위해 유지합니다.

**1.2.0 이후에 이어서 진행할 작업**

이 작업들은 취소한 것이 아니며, 다음 순서로 진행합니다. 구현 전에 각각 사용자와 논의합니다. 리뷰 논의는 컨텍스트가 섞이지 않도록 1.2.0 구현을 마친 뒤 시작합니다.

9. **리뷰 설계와 구현(5절 4번, 6번):** 타임라인 기록이 모듈로 옮겨지지 않는 문제를 해결하는 작업이므로 가장 먼저 합니다. `audit` 결과를 입력으로 연결합니다.
10. **AI 기능의 JSON 출력:** 이후의 VS Code 화면과 서버 접속에서 재사용하기 위해 CLI에서 호출할 수 있게 합니다. 명령이 정리된 뒤에 해야 다시 만들지 않습니다.
11. **VS Code용 타임라인 화면:** 10번을 사용합니다. 첫 버전 후보는 입력창, 기간별 이어 보기와 검색, Goal Loop 읽기 전용 표시, 선택 기간의 리뷰 요청입니다.

**별도로 진행할 작업**

- **기존 노트의 정리(5절 7번):** 1.2.0의 형식이 정해진 뒤 `memory_notion` 세션에서 진행합니다. `PLAN.md` 53개의 삭제, 약 49개 문서에 합쳐진 계획 제목, `memory_notion/.memory/templates/`의 사본이 여기에 포함됩니다.

**회귀 테스트 필수 사례**

- 날짜형 파일명(`2026-09-03.md`)과 예전 파일명(`03.md`)의 타임라인을 모두 읽습니다.
- 특정 날짜의 기록을 물으면 그 날짜의 기록을 근거로 답하는 도구 경로를 탑니다.
- 기간 조회에서 실제 파일이 있으면 "항목 없음"을 반환하지 않습니다.
- 단일 파일 모듈과 `[Folder]/[Folder].md` 형식의 모듈을 모두 읽습니다.
- `type`이 없는 문서와 알 수 없는 frontmatter 키를 거부하지 않습니다.
- 발행 정보(`version`, `source_hash` 등)가 있는 frontmatter에 새 필드가 함께 있어도 깨지지 않습니다.
- `PLAN.md`를 모듈로 나열하지 않습니다.
- 단일 파일에 하위 문서를 만들면 `topic/topic.md`와 `topic/child.md`가 되고, 상위 문서의 내용과 `[[topic]]` 링크가 유지됩니다.
- `topic.md`와 `topic/child.md`가 나란히 있는 문서의 이름을 바꾸면 둘 다 옮겨집니다.
