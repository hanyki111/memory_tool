<!-- Single-file module template.
     Each part below becomes one section of the assembled module,
     joined in this order and separated by a horizontal rule.
     Parts: module, current, decisions, dependencies, interface
     The 'natures' part is a menu: one outline is spliced into the
     body of 'current' and the rest are never emitted. -->
<!-- part: module -->

# Module: [경로]

**Created:** YYYY-MM-DD | **Updated:** YYYY-MM-DD
**Kind:** implementation | **Role:** leaf | root
**Status:** planning | dev | stable | frozen
**Tags:** 

## 목적과 목표

<!-- 이 모듈이 구현하는 기능은 무엇인가. 한 문장. -->

## 책임과 범위 (Single Responsibility Principle 적용)

- **책임:** <!-- 하나의 명확한 책임 -->
- **범위:**
  - **포함** — 
  - **제외** — <!-- 어느 모듈로 위임하는지 명시 -->

## Architecture

<!-- 구성요소와 데이터 흐름. 코드를 읽으면 알 수 있는 것은 쓰지 않는다.
     여기 담을 것은 코드에 '없는 것' — 왜 이렇게 만들었고 무엇을 시도했다 버렸는가. -->

## Source of Truth

> ⚠️ **코드가 정본이고 이 모듈은 그 요약이다. 충돌하면 코드가 이긴다.**

- **저장소:** 
- **주요 경로:** 
- **기준 커밋:** 

## 관련 모듈

- 상위: 
- 형제: 
- 의존: 

---

<!-- part: current -->

# Current Status: [모듈]

> **기준:** YYYY-MM-DD | **Phase:** planning | dev | stable | frozen | **버전/커밋:** —

<!-- 기준 커밋이 없으면 이 문서가 언제 기준 요약인지 알 수 없고,
     낡았다는 사실 자체가 드러나지 않는다. 구현 모듈의 고유 실패 모드는 '틀림'이 아니라 '낡음'이다. -->

## 1. Overview

<!-- 3줄. 이 컴포넌트가 무엇을 하는가. -->

## 2. Architecture

<!-- 구조와 데이터 흐름. 코드 복제 금지 — 쓰지 않은 것은 썩지 않는다. -->

## 3. 📂 Related Files

<!-- 코드 앵커. 모듈에서 코드로 가는 유일한 다리이자, 가장 먼저 썩는 부분.
     mcheck의 검증 대상. -->

| 경로 | 역할 |
| :--- | :--- |
| `src/...` | |

## 4. 상태 (Status)

**완료**
- [x] 

**진행 중**
- [ ] 

**차단**
- <!-- 무엇에 막혀 있는가. 없으면 "없음" -->

## 5. 할 일 (Todos)

- [ ] 

## 6. 기술 부채 & Known Issues

<!-- 알면서 남긴 것과 모르고 생긴 것을 구분해 적는다 -->

| 항목 | 내용 | 영향 | 대응 시점 |
| :--- | :--- | :--- | :--- |

## 7. 검증 (테스트 / 재현 절차)

<!-- 선택이 아니다. 이 Kind의 검증 질문이 "동작하는가?"인데
     확인 방법이 없으면 그 질문에 답할 수 없다. 명령 한 줄이라도 남긴다. -->

```bash
# 테스트
# 수동 재현
```

## 8. Next Steps

1. 

---

<!-- part: decisions -->

# 기술 결정 (Decisions)

<!-- 왜 그 라이브러리를 안 썼는지, 왜 그 구조를 버렸는지가 본체다.
     Alternatives 없는 decisions는 결정 기록이 아니라 결과 기록이다. -->

## Decision 1: [제목] (YYYY-MM-DD)

**Context:**
<!-- 어떤 기술적 문제 또는 요구사항이었는가 -->

**Alternatives (기각 이유):**
- **[대안 A]** → 기각 이유 (성능/의존성/유지보수 비용 등 구체적으로)
- **[대안 B]** → 기각 이유

**Decision:**

**Rationale:**

**Consequences:**
- 기술적 영향:
- 감수한 트레이드오프:
- 발생한 부채:

**Status:** Accepted | Superseded by Decision N | Deprecated

---

<!-- part: dependencies -->

# Dependencies

## 계층

- **상위:** 
- **형제:** 
- **하위:** 

## 참조 (이 모듈이 의존하는 것)

- [[모듈명]] — 무엇을 가져다 쓰는가

## 피참조 (이 모듈에 의존하는 것)

<!-- 이 모듈의 인터페이스를 바꿀 때 무엇이 깨지는가 -->

- [[모듈명]] — 무엇을 가져가는가

## 외부 패키지

| 패키지 | 버전 | 용도 | 필수/선택 |
| :--- | :--- | :--- | :--- |

## 런타임 전제

<!-- 언어 버전, OS, 외부 서비스, 환경 변수 등 -->

- 

## 미해결 결합

<!-- 알고 있지만 아직 못 끊은 의존. 순환 참조가 있다면 반드시 여기에 -->

- 

---

<!-- part: interface -->

# Interface

<!-- 구현 모듈에서만 이 양식이 유효하다.
     지식 모듈은 Glossary + 인용 가능한 결론 양식을 쓴다. -->

## Public API

<!-- 다른 모듈·사용자가 호출하는 진입점. CLI라면 명령과 옵션, 라이브러리라면 함수 시그니처 -->

### Usage
```bash
```

### Options
- `--flag <value>`: 설명 (Default: —)

## Data Structures

<!-- 입출력 스키마. 실제 예시 값을 포함한다 -->

```json
{
}
```

## Output Artifacts

<!-- 이 모듈이 만들어내는 산출물. 파일이라면 경로와 형식 -->

| 산출물 | 경로 | 내용 |
| :--- | :--- | :--- |

## Examples

<!-- 복사해서 바로 돌릴 수 있는 최소 예제 -->

```bash
```

## 하위 호환성

<!-- 선택. 변경 시 깨지는 것이 무엇인지 -->

- 
