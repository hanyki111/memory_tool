# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.8.0] - 2026-11-09

### 🔄 변경

- **`mreview`를 회고 중심으로 바꿈:** 남길 것을 정리하는 일이 곧 회고이므로 옮기기와 돌아보기를 나누지 않습니다. 먼저 회고 방법(CLI와 회고, 혼자 회고, AI 후보만 보기)을 고르고, 그 결과로 남길 것을 정한 뒤 항목마다 지금 쓰기(직접 또는 AI와), 나중에 쓰기, 남기지 않기를 고릅니다.
- **후보가 회고 글을 읽음:** 혼자 회고하면 AI가 쓴 글과 기록을 함께 읽고 후보를 냅니다.
- **`--with`:** 쓰기뿐 아니라 회고 방법도 고릅니다.
- **리뷰 파일의 제목:** 새 파일은 `## 남길 것`과 `## 회고`를 씁니다. `## 옮기기`와 `## 돌아보기`로 된 기존 파일도 그대로 읽습니다.
- **후보를 내지 못했을 때:** 대화형 `mreview`는 리뷰를 진행 중으로 남기고 다시 시도하거나 후보 없이 계속할 수 있습니다. `mreview --json`은 지금처럼 바로 후보를 냅니다.

### ✨ Added

- **`mreview add`:** 남길 것을 추가합니다. 대화 중인 AI와 사용자가 모두 쓸 수 있고, 항목 메뉴에서는 `a`로 추가합니다. `--heading "열린 질문"`으로 결론이 없는 질문을 기존 문서에 남길 수 있습니다.

## [1.7.1] - 2026-11-09

### 🐛 Fixed

- **VS Code 리뷰 버튼(확장 0.2.0):** 버튼이 화면에 불러온 가장 오래된 날짜부터 리뷰하여, 이미 리뷰한 기록을 다시 다루거나 그 사이의 기록을 건너뛰었습니다. 이제 **리뷰** 버튼은 지난 리뷰 이후를 다룹니다. 다른 날짜부터 리뷰하려면 **기간**을 펼쳐 **{날짜}부터 리뷰**를 누릅니다.
- **VS Code 화면의 겹침:** 타임라인을 내리면 위쪽 입력 영역이 투명하여 기록과 글자가 겹쳤습니다.
- **돌아보기의 기록:** CLI나 편집기를 닫기만 해도 돌아보기를 쓴 것으로 기록했습니다. 이제 실제로 글이 바뀌었는지 확인하고, 그대로이면 다시 묻습니다. 종료 메시지에도 돌아보기 결과를 표시합니다. 옮길 항목이 없으면 그렇다고 알립니다.
- **돌아보기와 문서 작성의 말투:** AI가 채팅 답변을 그대로 파일에 붙여 넣었습니다. 이제 글말로 다듬어 보여 주고 확인을 받은 뒤 적습니다.

### ✨ Added

- **`mreview --since`의 경고:** 지난 리뷰보다 늦은 날짜를 주면 그 사이의 기록이 리뷰되지 않는다고 알립니다.

## [1.7.0] - 2026-11-07

### 🔄 변경

- **임베딩 모델을 다국어 모델로 교체:** `all-MiniLM-L6-v2`를 `paraphrase-multilingual-MiniLM-L12-v2`로 바꿨습니다. 이전 모델은 영어 전용이어서 한국어 문장의 의미를 잘 구분하지 못했습니다. 처음 실행할 때 모델 파일(약 470MB)을 내려받습니다. 벡터 검색 캐시는 이제 모델별 폴더(`.embeddings/<모델>/`)에 저장하므로, 첫 의미 검색에서 색인을 새로 만듭니다. `mmodule audit`과 연결 제안이 쓰는 캐시도 모델 이름을 키에 포함해서, 다른 모델의 벡터와 섞이지 않습니다.
- **의미 검색의 기본 기준값을 0.5에서 0.35로 조정:** 새 모델은 점수가 전반적으로 낮게 나옵니다. 한국어와 영어를 섞은 표본에서 0.35일 때 관련 기록 14건 중 12건을 찾았고, 무관한 기록은 86건 중 5건만 걸렸습니다. **기존 프로젝트의 `config.yaml`에 `search.semantic_threshold: 0.5`가 적혀 있다면 그 값이 계속 적용되므로, 0.35로 직접 바꿔 주십시오.**

### 🐛 수정

- **`mmodule check-links`가 파일 이름으로 쓴 링크를 깨진 링크로 보고하던 문제:** 링크를 모듈 전체 경로와만 비교했기 때문에, 같은 폴더의 `[[core-principles]]`도 깨진 링크로 판정했습니다. 이제 Obsidian과 같은 순서로 찾습니다: 전체 경로, `./`·`../` 상대 경로, 경로의 끝부분이 일치하는 모듈. 끝부분이 일치하는 모듈이 여럿이면 링크한 모듈과 가장 가까운 모듈을 고르고, 똑같이 가까우면 "모호한 링크"로 따로 보고합니다. 그래프에도 해석한 모듈을 저장하므로 `connections`와 고립 문서 판정도 같은 기준을 따릅니다. `mmodule relink`도 같은 규칙을 써서, 정상적으로 해석되는 짧은 링크를 전체 경로로 고쳐 쓰지 않습니다.
- **`mmodule check-links`가 삭제된 문서의 링크까지 보고하던 문제:** 마지막 `rebuild-graph`의 결과를 그대로 읽었기 때문입니다. 이제 검사할 때마다 문서를 다시 읽습니다.
- **코드와 HTML 주석 안의 링크를 링크로 읽던 문제:** Obsidian처럼 이제 링크로 취급하지 않습니다. 템플릿의 `[[모듈명]]` 예시는 주석이나 인라인 코드로 옮겨서, 새 문서마다 깨진 링크가 하나씩 생기지 않습니다. 이전 템플릿으로 만든 문서에 남은 `[[모듈명]]`은 "채우지 않은 자리 표시"로 안내합니다.
- **`mcheck`가 Related Files 절이 없는 문서마다 경고하던 문제:** 경로는 이제 frontmatter의 `sources`에 적고 Related Files 절은 선택 사항이므로, 경고와 종료 코드 1을 없앴습니다. `sources`와 Related Files에 적힌 경로는 지금처럼 검사합니다.
- **`mmodule audit`이 관계없는 문서끼리 90% 이상 유사하다고 표시하던 문제:** 모델은 앞부분 256토큰만 읽는데, 한국어는 토큰을 빨리 소모해서 두 문서에 똑같이 들어 있는 frontmatter와 템플릿 안내 문구만 비교되었습니다. 이제 frontmatter, 주석, 템플릿 문구(이전 템플릿의 문구와 여러 모듈에 공통으로 나오는 줄 포함)를 제외하고, 본문 전체를 200자 단위로 나누어 임베딩한 뒤 평균을 냅니다. 내용이 없는 문서는 비교하지 않습니다. 한국어 소형 문서 여덟 개로 측정했을 때, 관계없는 쌍 26개 중 기준(0.65)을 넘은 쌍이 10개에서 0개로 줄었습니다.

## [1.6.2] - 2026-11-07

### 🐛 수정

- **연달아 쓴 기록이 검색 결과에서 빠지던 문제:** 같은 파일에서 세 줄 이내에 있는 결과를 하나로 합쳤는데, 화면에는 앞뒤 한 줄만 보여 주므로 두세 줄 떨어진 기록은 어디에도 나오지 않았습니다. 이제 화면에서는 앞뒤 줄로 이미 보이는 결과만 합치고, `--json`은 합치지 않고 기록마다 하나씩 냅니다. 혼합 검색의 캐시도 합치기 전의 결과를 저장하므로, `--json`은 캐시에서도 모든 기록을 받습니다. 앱의 검색 결과도 여기에 해당합니다.

## [1.6.1] - 2026-11-07

### 🐛 수정

- **기록 직후의 검색이 오래된 결과를 내던 문제:** 검색 결과 캐시는 한 시간 동안 같은 검색어에 같은 결과를 냈고, 그사이 기록하거나 고친 내용은 반영하지 않았습니다. `m`, `medit`, 앱, Obsidian에서 고친 경우가 모두 해당합니다. 키워드 검색은 색인을 쓰므로 검색 자체에 0.1초 정도밖에 걸리지 않아서, 캐시가 줄이는 시간이 거의 없었습니다. 이제 키워드 검색은 캐시를 쓰지 않습니다. 혼합 검색(`--hybrid`)은 캐시를 유지하되, 검색 대상 폴더의 마크다운 파일 정보(경로, 크기, 수정 시각)를 캐시 키에 넣어서 파일이 하나라도 바뀌면 새로 계산합니다. 파일 내용은 읽지 않습니다.

## [1.6.0] - 2026-11-07

### ✨ 추가

- **`entry find`, `entry edit`, `entry delete`:** 날짜, 시각, 글로 기록 하나를 찾고, 고치고, 지웁니다. 목록을 받아 온 뒤 기록을 고치는 프로그램(휴대폰 앱)을 위한 명령입니다. 그사이 PC에서 그 기록이 바뀌었다면 아무것도 고치지 않고 `not_found`를 냅니다. `entry find`는 태그를 `record`와 같은 규칙으로 정리한 뒤 비교하므로, `fix #bug`로 `[bug] fix`를 찾습니다. `entry edit`는 날짜를 바꾸면 새 날짜의 파일에 먼저 추가한 뒤 원래 파일에서 지우고, 바꾼 날짜와 시각은 `record`와 같은 규칙(`future_time`, `distant_past`)으로 검사합니다. 기록 아래에 손으로 적은 줄은 보존합니다. 사람이 고칠 때는 지금처럼 `medit`을 씁니다.

### 🐛 수정

- **`ms --type`이 아무것도 찾지 못하던 문제:** 형식 필터가 지식 베이스 폴더를 기준으로 경로를 비교하는데, 검색은 그 위의 프로젝트 폴더를 넘겼습니다. 그래서 `--type timeline` 등이 언제나 빈 결과를 냈습니다.
- **검색 캐시가 지식 베이스를 구분하지 않던 문제:** 캐시는 홈 폴더에 하나뿐인데 키에 지식 베이스가 없어서, 한 시간 안에 다른 지식 베이스에서 같은 검색어를 쓰면 앞서 검색한 지식 베이스의 결과가 나왔습니다.

## 안드로이드 앱 Memory Capture 0.6.0 - 2026-11-07

### ✨ 추가

- **큰 위젯의 태그 칩:** 기록 앞의 `[태그]`를 앱처럼 연한 강조색 칩으로 보여 줍니다. 위젯 글자에는 둥근 모서리를 그릴 수 없어서 각진 칩입니다. 화면 모드가 "휴대폰 설정 따르기"이면, 휴대폰이 다크로 바뀔 때 함께 바뀌지 않는 글자 색 대신 반투명 강조색 바탕만 씁니다.
- **받아쓰기 뒤의 태그 칩:** 작은 입력 창과 앱의 하단 입력란에서 음성으로 입력하면, 최근 쓴 태그(최대 8개)를 칩으로 보여 줍니다. 칩을 누르면 글 앞에 태그가 붙고, 다시 누르면 빠집니다. 보내기 전 카운트다운 중에 누르면 카운트다운이 처음부터 다시 시작합니다. 태그는 휴대폰에서 보낸 기록, 앱이 불러온 타임라인, 큰 위젯의 기록에서 가져옵니다.
- **받아쓰기 방식 설정:** 설정 › 음성에서 "구글 받아쓰기 창"(지금까지의 방식, 기본값)과 "앱 안에서 받아쓰기" 중에서 고릅니다. 앱 안에서 받아쓰면 휴대폰의 기본 음성 입력 서비스가 듣고, 들은 내용을 입력 창에 바로 보여 준 뒤 지금처럼 몇 초 뒤에 보냅니다. 처음 한 번 마이크 권한을 묻고, 서비스가 없거나 실패하면 구글 받아쓰기 창으로 넘어갑니다.

### ⚠️ 알아 둘 점

- 삼성 키보드의 마이크는 다른 앱이 켤 수 없고, 받아쓰기가 끝났는지도 다른 앱에 알려 주지 않습니다. 그래서 "삼성 키보드로 받아쓰고 바로 보내기"는 만들 수 없으며, 대신 휴대폰의 기본 음성 입력 서비스를 쓰는 방식을 넣었습니다.

## 안드로이드 앱 Memory Capture 0.5.0 - 2026-11-07

### ✨ 추가

- **macOS·Linux PC:** 설정의 "PC 종류"에서 macOS · Linux를 고르면, 앱이 sh 명령(`cd -- '폴더' && export PYTHONIOENCODING=utf-8 && exec python3 -m memory_tool …`)을 만듭니다. 인수는 모두 작은따옴표로 감싸서 글에 있는 `$`, 따옴표, 백틱이 그대로 전달되고, 폴더가 틀리면 `cd`에서 멈춥니다. 로그인 셸은 sh, bash, zsh를 지원합니다. 키를 넣을 파일과 지문 확인 명령도 PC 종류에 맞게 안내합니다.
- **위젯 설정:** 설정에 "위젯" 묶음을 만들었습니다. 큰 위젯에 보일 기록 수(5, 10, 20, 30건, 기본 10건)와, 긴 기록을 한 줄로 줄일지 여러 줄로 모두 보일지를 고릅니다.

### 🔄 변경

- **큰 위젯은 크기만큼 채웁니다:** 고정된 3줄 대신 스크롤되는 목록입니다. 위젯의 높이만큼 기록을 보여 주고 나머지는 스크롤해서 봅니다. 위젯을 키우면 더 많이 보입니다. "갱신" 시각은 목록 위의 머리줄("최근 기록 · 14:30 갱신")로 옮겼습니다.
- **받아 오는 범위:** 최근 7일에서 30일로 넓혔습니다. 앱이 타임라인을 불러올 때에도 앱이 불러온 기록 대신 PC에 30일 치를 따로 묻습니다.

## 안드로이드 앱 Memory Capture 0.4.2 - 2026-11-07

### 🔄 변경

- **큰 위젯의 순서:** 최근 기록을 위에, 입력란을 아래에 둡니다.
- **위젯의 강조색:** 마이크 아이콘과 큰 위젯의 시각을 강조색으로 칠해서, 설정의 강조색이 위젯에도 보입니다.

### 🐛 수정

- **휴대폰이 다크로 바뀌어도 위젯이 그대로이던 문제:** 화면 모드가 "휴대폰 설정 따르기"일 때, 앱이 꺼져 있으면 위젯을 다시 그리지 않아 이전 색이 남았습니다. 이제 위젯에 라이트와 다크의 색을 모두 넘겨서, 런처가 그릴 때마다 휴대폰 설정에 맞는 쪽을 고릅니다(Android 12 이상).

## 안드로이드 앱 Memory Capture 0.4.1 - 2026-11-07

### 🐛 수정

- **큰 위젯을 추가할 수 없던 문제:** 구분선을 일반 `View`로 만들었는데, 홈 화면 위젯에는 정해진 뷰만 쓸 수 있어서 런처가 "위젯을 추가할 수 없습니다"를 냈습니다. 구분선을 `FrameLayout`으로 바꿨습니다.

## 안드로이드 앱 Memory Capture 0.4.0 - 2026-11-07

### ✨ 추가

- **위젯 세 종류:** 위젯 목록에서 골라 놓습니다.
  - **기록 (작게)**, 1×1: 동그란 버튼 하나이며, 누르면 입력 창이 열립니다.
  - **기록**, 4×1: 지금까지의 위젯입니다.
  - **기록과 최근 타임라인**, 4×2: 같은 입력란 아래에 PC 타임라인의 최근 기록 3건을 보여 줍니다. 오늘이 아닌 기록에는 "어제"나 날짜가 붙고, 기록을 누르면 앱의 타임라인이 열립니다. 맨 아래에 마지막으로 받아 온 시각을 표시합니다.
- **최근 기록 받아 오기:** 30분마다(네트워크가 있을 때), 앱이 타임라인을 불러올 때, 보낸 기록이 PC에 들어간 직후에 받아 옵니다. 최근 7일에서 최신 3건을 고릅니다.

### 🔒 휴대폰에 남는 것

- 큰 위젯이 홈 화면에 있는 동안에만 최근 기록 3건과 받아 온 시각을 앱 전용 저장소에 둡니다. 백업과 기기 이전에서는 빠집니다. 큰 위젯을 모두 치우면 지우고, 30분마다 받는 작업도 멈춥니다. 0.2부터 지켜 온 "PC 타임라인을 휴대폰에 남기지 않는다"의 예외이며, 사용자가 업무 기록이 홈 화면에 보이는 것을 감안하고 고른 것입니다.

## 안드로이드 앱 Memory Capture 0.3.1 - 2026-11-07

### ✨ 추가

- **앱 바로가기 "기록하기"와 "음성으로 기록하기":** 앱 아이콘을 길게 누르면 나옵니다. 삼성 "모드 및 루틴"은 앱 바로가기를 앱 액션으로 보여 주므로, 루틴에서 작은 입력 창을 열거나 받아쓰기로 바로 시작할 수 있습니다. 입력 창이 이미 열려 있을 때 "음성으로 기록하기"가 실행되어도 받아쓰기가 시작됩니다.

## 안드로이드 앱 Memory Capture 0.3.0 - 2026-11-07

### 🎨 화면

- **글 중심의 차분한 화면:** 색을 거의 쓰지 않고 여백과 글자 크기·굵기로 구분합니다. 날짜는 크게, 요일은 옆에 작게 씁니다. 하루의 기록은 세로 시간선 위의 점으로 이어지고, 그날의 최신 기록만 점에 강조색을 칠합니다. 시각은 숫자 폭을 맞춰 세로로 줄이 맞습니다.
- **태그 칩:** 기록 앞의 `[태그]`를 연한 강조색 칩으로 보여 줍니다. 저장된 글은 바뀌지 않습니다.
- **검색창과 입력란:** 테두리 없이 아이콘과 글자만 둡니다. 입력란의 안내 문구는 "무슨 일이 있었나요?"이고, 보내기는 둥근 강조색 버튼입니다. 검색 결과에는 날짜와 시각을 글 위에 씁니다.
- **설정 화면:** 모양, PC, 음성, 이 휴대폰의 키, 배터리의 다섯 묶음으로 나눴습니다.

### ✨ 추가

- **화면 모드:** 휴대폰 설정 따르기, 라이트, 다크 중에서 고릅니다. 상태 표시줄 아이콘도 함께 바뀝니다.
- **강조색:** 배경화면 색(Android 12 이상)과 고정색 여섯 가지(남색, 청록, 초록, 호박색, 장밋빛, 먹색) 중에서 고릅니다. 고정색은 라이트와 다크에서 각각 바탕과 4.5:1 이상의 대비를 지킵니다.
- **위젯과 작은 입력 창:** 앱의 화면 모드와 강조색을 따릅니다. 위젯의 글자 크기는 지금처럼 휴대폰 설정을 따릅니다.

### 🔄 변경

- **"명령" 대신 "지식 베이스 폴더":** PC에서 `m`을 실행하는 폴더만 적으면, 앱이 `Set-Location -LiteralPath '폴더' -ErrorAction Stop; python -m memory_tool …`을 만듭니다. 0.2 이하에서 저장한 명령은 폴더를 뽑아 옮깁니다. 이제 `python`은 PC의 SSH 세션 PATH에 있어야 합니다.
- **연결 시험:** 버전에 더해 `base show`로 그 폴더의 지식 베이스를 보여 줍니다.

### 🐛 수정

- **폴더가 틀리면 다른 곳에서 실행되던 문제:** 예전 명령은 `Set-Location`이 실패해도 다음 명령으로 넘어가서, memory_tool이 SSH 세션의 홈 폴더에서 실행될 수 있었습니다. 이제 거기서 멈추고 오류를 냅니다.

## 안드로이드 앱 Memory Capture 0.2.1 - 2026-11-07

### 🔄 변경

- **편집은 길게 눌러서:** 고칠 일이 드물어서, 기록을 길게 눌러야 진동과 함께 편집 창이 열립니다. 짧게 누르면 "기록을 길게 누르면 고칠 수 있습니다"가 잠깐 뜹니다.
- **보내지 않은 기록은 입력란 바로 위에:** 타임라인 맨 위에 있던 목록을 입력란 위의 한 줄로 옮겼습니다. 건수와 마지막 기록이 보이고, 누르면 펼쳐집니다. 타임라인을 스크롤해 둔 상태에서도 방금 보낸 기록이 보입니다.
- **글자 크기 범위:** 80~150%에서 70~200%로 넓혔습니다.

### 🐛 수정

- **첫 화면이 목록 끝에서 열리던 문제:** 처음에 목록에 있던 "불러오는 중" 표시가 제자리에 머물러서, 기록이 그 위에 채워지면 화면이 목록 끝으로 갔습니다. 이제 최신 기록이 맨 위에 보입니다. 오늘의 첫 기록이 새 날짜로 들어올 때에도, 맨 위를 보고 있었다면 그 날짜가 보입니다.

## 안드로이드 앱 Memory Capture 0.2.0 - 2026-11-07

### ✨ 추가

- **타임라인이 첫 화면:** 앱을 열면 PC의 타임라인이 최신순으로 나옵니다(하루 안에서도 최신 기록이 위). 처음에 최근 7일을 불러오고, 끝까지 스크롤하면 이전 7일을 더 불러옵니다. 기록이 없는 주가 나오면 자동으로 더 불러오지 않고 버튼을 보여 줍니다. 아래로 당기면 새로 고칩니다.
- **하단 입력란:** 화면 아래의 입력란에서 바로 쓰고 보냅니다. 마이크 버튼은 받아쓴 글을 입력란에 채웁니다. 보낸 기록이 PC에 들어가면 그날을 다시 불러옵니다.
- **검색:** 위쪽 검색창에서 타임라인을 키워드로 찾습니다(`ms --type timeline`).
- **고치기와 삭제:** 기록을 누르면 편집 창이 열리고, 글, 날짜, 시각을 고치거나 삭제합니다. 그사이 PC에서 그 기록이 바뀌었다면 고치지 않고 다시 불러옵니다.
- **설정 화면:** 톱니바퀴로 엽니다. 글자 크기(80~150%, 0.2.1부터 70~200%)를 고를 수 있으며, 휴대폰의 글자 크기 위에 곱해집니다. 홈 화면 위젯에는 적용되지 않습니다.

### 🐛 수정

- **태그가 붙은 기록이 두 번 기록될 수 있던 문제(0.1.2):** 보낸 뒤 연결이 끊긴 기록을 확인할 때, PC가 태그를 정리해 다시 쓴 글(`[버그] [긴급] …`, `[idea] …`)을 적은 글과 그대로 비교해서 "없음"으로 판단하고 다시 보냈습니다. 이제 `entry find`로 PC에 묻습니다. PC의 memory_tool이 1.6.0보다 오래되었으면 다시 보내지 않고 "확인할 기록"으로 남깁니다.

### ⚠️ 필요한 것

- PC의 memory_tool 1.6.0 이상이 필요합니다. 오래된 버전에서는 기록은 되지만, 타임라인 보기의 수정과 끊긴 기록의 확인이 동작하지 않습니다.

## 안드로이드 앱 Memory Capture 0.1.2 - 2026-11-07

### 🐛 수정

- **연결 직후의 실패:** 비행기 모드를 끈 직후에는 DDNS 주소 조회가 실패할 수 있고, 배터리 최적화가 켜져 있으면 다음 재시도가 오래 미뤄졌습니다. 이제 주소 조회나 연결에 실패하면 같은 작업 안에서 5초, 10초, 20초를 기다리며 세 번 더 시도합니다.
- **보낸 뒤 연결이 끊긴 기록:** 모바일 데이터에서 Wi-Fi로 바뀌는 등의 이유로 보낸 뒤 연결이 끊기면, 지금까지는 사람이 확인해야 했습니다. 이제 앱이 다시 연결한 뒤 PC에서 `memory_tool day <날짜> --json`을 실행해 그날 타임라인을 확인합니다. 같은 시각, 같은 글의 기록이 있으면 보낸 것으로 처리하고, 없으면 다시 보냅니다. 확인하지 못한 경우에만 사람에게 맡깁니다.
- 확인할 기록에 실패 이유를 함께 보여 줍니다.

## 안드로이드 앱 Memory Capture 0.1.1 - 2026-11-07

### 🐛 수정

- **연결이 돌아와도 보내지 않던 문제:** 비행기 모드를 끄는 것만으로는 보내지 않고, 앱을 열어야 보냈습니다. 이제 보낼 기록이 있으면 Android에 네트워크 연결 알림을 등록해서, 실제로 인터넷이 되는 네트워크가 생기는 즉시 앱이 깨어나 보냅니다. 전송 작업은 백그라운드에서도 바로 실행되도록(expedited work) 바꿨습니다.
- **재시도 간격:** PC에 닿지 못했을 때 재시도 간격이 2배씩 늘어나던 것을 15초씩 늘어나고 5분을 넘지 않도록 바꿨습니다.
- **같은 기록이 두 번 보내질 수 있던 문제:** 한 기록을 보내는 동안 새 기록을 쓰면, 새 전송 작업이 같은 기록을 다시 보낼 수 있었습니다. 이제 전송은 한 번에 하나씩만 실행됩니다.

### ✨ 추가

- 보낼 기록마다 마지막 시도 시각과 실패 이유를 보여 줍니다.
- 설정 화면에 배터리 항목을 넣었습니다. 배터리 최적화 상태를 보여 주고, 앱 설정을 여는 버튼을 둡니다. 배터리 최적화가 켜져 있으면 '제한 없음'으로 바꾸도록 안내합니다.

## 안드로이드 앱 Memory Capture 0.1.0 - 2026-11-07

### ✨ 추가

- **휴대폰 기록 앱 (`android/`):** 앱 아이콘, 빠른 설정 타일, 홈 화면 위젯, 공유하기로 작은 입력 창을 열어 기록합니다. 음성 입력은 받아쓴 글을 잠깐 보여 준 뒤 보냅니다. 기록은 SSH로 PC에 보내고 PC의 `memory_tool record --json`이 씁니다. 연결되지 않을 때는 휴대폰에 보관했다가 적은 시각으로 보냅니다. 휴대폰 전용 Ed25519 키를 쓰고, 사람이 확인한 PC 지문만 신뢰합니다.

## [1.5.1] - 2026-11-07

### 🐛 수정

- **Windows에서 인수가 펼쳐지던 문제:** Click이 Windows에서 명령줄 인수의 `$변수`, `%변수%`, `*.py` 같은 패턴을 펼쳐서, `m "*.py 정리"`가 현재 폴더의 파일 이름으로 기록되고 `$HOME`이 경로로 바뀌었습니다. 이제 모든 명령이 인수를 적은 그대로 받습니다.

## [1.5.0] - 2026-11-06

### ⚠️ 호환 없이 바뀐 동작

- **`mcontext --update-interfaces`(`-i`), `--include-archived`, `mmap --interface` 제거:** 모듈 옆에 `interface.md`를 따로 만드는 기능이었습니다. 문서가 `주제.md` 하나인 새 형식에서는 예전 형식의 파일을 다시 만들게 되고, 문서 본문에 써 넣으면 사람이 쓴 문서를 도구가 고치게 되어 없앴습니다. 코드 구조는 `mmap`과 `mcontext --with-map`으로 볼 수 있고, 문서에 적은 소스 경로는 `mcheck`가 확인합니다. 이미 만들어진 `interface.md`는 그대로 둡니다.

### 🐛 수정

- **`msummary`의 최근 결정:** `modules/` 바로 아래의 `decisions.md`만 읽어서, 새 형식에서는 요약에 넣는 최근 결정이 늘 비어 있었습니다. 이제 기간 안에 만든 `판단` 문서(`generated.at` 기준)와, 하위 모듈까지 포함한 예전 결정 기록을 읽습니다.

### 🧹 정리

- 아무 데서도 쓰지 않던 `core/warnings.py`(`FileSizeWarning`)를 지웠습니다.

## [1.4.1] - 2026-11-06

### 🐛 수정

- **`~/.memory`를 지식 베이스로 착각하던 문제:** 검색 캐시가 만드는 `~/.memory`를 CLI가 예전 방식의 지식 베이스로 받아들였습니다. 그래서 지식 베이스가 없는 폴더에서 `m`을 실행하면 `~/.memory/timeline`에 기록되었습니다. 이제 `.memory` 폴더에 `config.yaml`, `timeline/`, `modules/` 중 하나가 있어야 지식 베이스로 인정합니다. 지식 베이스가 없는 폴더에서 `m`을 실행하면, 홈 폴더 밖에서와 같이 그 폴더에 `.memory`를 만듭니다.
- **`medit`이 손으로 적은 줄을 지우던 문제:** 저장할 때 파일 전체를 기록 줄만으로 다시 써서, 제목이 바뀌고 손으로 적은 줄이 사라졌습니다. 이제 고친 기록만 바뀝니다. 손으로 적은 줄은 바로 위 기록과 함께 움직이고, 그 기록을 지우면 바로 앞 기록 아래로 옮겨집니다.

### Obsidian 플러그인 1.2.1

- 명령을 셸을 거치지 않고 인수 배열로 실행합니다. 따옴표, `%`, `$`, 역슬래시가 든 기록도 적은 그대로 저장됩니다. Python 설정은 `py -3` 같은 런처나 큰따옴표로 감싼 경로도 그대로 받습니다.

## VS Code 확장 0.1.0 - 2026-11-06

### ✨ 추가

- **Memory Tool Timeline (`vscode/`):** VS Code에서 타임라인에 기록하고, 7일씩 이어 보고, 기간을 골라 보고, 검색합니다. 사이드바와 편집기 탭에 같은 화면을 띄우며, 어디서 기록하든 열린 화면이 모두 새로 고쳐집니다. 검색은 키워드가 기본이고 "의미로 찾기"를 누르면 혼합 검색을 합니다. 리뷰 버튼은 화면에 보이는 가장 오래된 날짜로 `mreview --since`를 터미널에서 실행합니다. memory_tool 1.4 이상이 필요합니다.

## [1.4.0] - 2026-11-06

### ✨ 추가

- **JSON 출력:** 기록, 조회, 검색, AI 명령에 `--json`을 추가했습니다. 편집기와 스크립트가 터미널 출력을 해석하지 않고 결과를 받을 수 있습니다. 형식은 `docs/USER_GUIDE.md`의 "JSON Output"에 정리했습니다.
  - 대상: `m`, `mtoday`, `mday`, `mweek`, `mmonth`, `mdays`, `ms`, `msummary`, `mmodule suggest-links --ai`, `mmodule from-text`
  - 결과는 표준 출력에 UTF-8 JSON 한 줄로만 나옵니다. 실패에는 `code`가 붙고, 리뷰 알림 같은 안내는 `notices`에 담깁니다.
  - 조회와 검색은 기록마다 시각, 원문, 태그를 담습니다. 조회는 파일 원문도 함께 담습니다.
- **기간 조회:** `mdays --from 날짜 --to 날짜`로 원하는 기간의 기록을 봅니다.
- **`mday` 명령 등록:** 도움말에 있었지만 실행 명령으로 등록되어 있지 않았습니다.

### 🔧 변경

- `mask --json`, `mreview --json`의 실패에 `code`를 추가했습니다. 기존 항목은 그대로입니다.

### 🐛 수정

- **의미 검색이 바뀐 파일만 검색하던 문제:** 한 번 색인한 타임라인 파일은 바뀌지 않는 한 검색 대상에서 빠졌습니다. 그래서 두 번째 검색부터는 그사이에 바뀐 파일의 기록만 찾았습니다. `ms --semantic`, 혼합 검색, `mask`의 의미 검색이 영향을 받았습니다. 이제 검색할 때는 모든 파일을 읽고, 바뀌지 않은 파일을 건너뛰는 동작은 미리 색인하기에만 남겼습니다.
- **의미 검색 결과의 날짜:** `daily/` 구조에서 `daily-2026-11`처럼 잘못된 날짜가 나왔습니다.
- `mhelp days`가 기본값을 7일로 안내했지만 실제 기본값은 14일입니다.
- `mhelp today`와 사용자 안내서에 있던, 실제로는 없는 옵션(`--yesterday`, `--reverse`, `--limit`)을 지웠습니다.

## [1.3.0] - 2026-11-05

### ⚠️ 호환 없이 바뀐 동작

- **`mreview weekly`, `monthly` 제거:** 회고 양식을 만들던 기존 기능을 호환 기간 없이 제거했습니다. 이미 만들어진 `reviews/weekly/`, `reviews/monthly/`의 파일은 그대로 두며, `ms`로 검색할 수 있습니다. `mreview`는 패키지 설치 명령에 등록되어 있지 않았으므로, 이제 `pip install -e .` 등으로 다시 설치해야 명령이 생깁니다.

### ✨ 추가

- **`mreview`:** 타임라인에서 남길 내용을 문서로 옮기는 리뷰입니다.
  - 지난 리뷰 이후의 기록을 설정된 LLM 제공자로 보내 제안을 다섯 건까지 받습니다. 첫 리뷰는 최근 14일을 읽고, `--since`로 시작일을 정할 수 있습니다.
  - 제안마다 지금 쓰기, 나중에 쓰기, 거절 중에서 고릅니다. 남은 항목이 다섯 건을 넘는 동안에는 미룰 수 없습니다.
  - 선택은 바로 저장되므로 멈춘 곳부터 이어 갈 수 있고, 이때 LLM을 다시 호출하지 않습니다.
  - 쓰기를 시작할 때 Claude Code, Codex, Antigravity와 혼자 쓰기를 메뉴로 고릅니다. 고르는 것만으로는 문서가 생기지 않습니다.
  - 마지막에 그 기간을 돌아보거나 건너뜁니다.
  - `mreview list`, `write`, `done`과 `--json`, `set`, `reflection`을 제공합니다.
- **리뷰 알림:** 지난 리뷰 후 7일이 지나고 기록이 10건 쌓이면, 그날의 첫 `m`과 `mcontext`에서 한 줄로 알립니다. `review.notice`로 값을 바꾸거나 끌 수 있습니다.
- **편집 가능한 리뷰 가이드:** 제안 기준과 돌아보기 절차는 `guides/review-proposals.md`, `guides/review-reflection.md`로 바꿀 수 있습니다.

### 알려진 제한

- `--date`로 지난 날짜에 추가한 기록은 다음 리뷰 범위에서 빠질 수 있습니다.
- AI는 문서 본문을 받지 않으므로, 이미 반영된 내용을 다시 제안할 수 있습니다.
- Obsidian 플러그인에서 기록하면 알림 문구가 플러그인 쪽 결과에 함께 나타날 수 있습니다. 확인하지 않았습니다.

## [1.2.0] - 2026-11-05

### ⚠️ 호환 없이 바뀐 동작

- **`module auto-tag` 제거:** 대체 기능은 없습니다.
- **`gemini-cli` 제공자 제거:** Gemini CLI가 개인용 Code Assist 계정을 더 이상 지원하지 않습니다. `antigravity-cli`를 사용하십시오. 설정에 `gemini-cli`가 남아 있으면 이 내용을 안내합니다.
- **`mplan module`과 `PLAN.md` 제거:** `mplan`의 나머지 기능은 그대로입니다. 기존 `PLAN.md`는 삭제되지 않으며, 모듈 목록에 더는 나타나지 않습니다.
- **옵션 없는 `mmodule create`의 결과 변경:** 범용 골격 대신 frontmatter와 제목만 있는 파일 하나(`topic.md`)를 만듭니다. `modules.default_kind`를 설정한 프로젝트는 이전처럼 동작합니다.
- **`mmodule from-text`의 결과 변경:** 파일 3개 대신 문서 하나로 저장하며, `generated.by`에 AI 작성으로 표시합니다. `--structure`는 더 이상 효과가 없습니다.
- **Obsidian 플러그인 1.2.0의 `grow` 메뉴 제거:** 생성 화면은 Kind와 Nature 대신 종류를 묻습니다. 이 플러그인은 `--type`을 쓰므로 memory_tool 1.2 이상이 필요합니다. 이전 플러그인은 1.2에서 경고와 함께 계속 작동합니다.
- **LLM 제공자 기본값 변경:** `llm.provider`가 없으면 `anthropic`으로 고정하지 않고, `anthropic`, `claude-cli`, `codex-cli`, `antigravity-cli`, `ollama` 순서로 사용 가능한 제공자를 고릅니다.
- **CLI 제공자의 실행 위치 변경:** `claude-cli`를 포함한 CLI 제공자는 빈 임시 폴더에서 실행합니다. 프로젝트 파일을 건드리지 않고 프로젝트 지침도 읽지 않습니다.
- **`mmodule rename`의 대상 제한:** 대상 폴더가 이미 있으면 합치지 않고 거부합니다.

### 🗑️ Deprecated

다음 기능은 경고와 함께 계속 작동하며, 이후 버전에서 제거될 수 있습니다. 이 기능으로 만든 문서는 계속 읽을 수 있습니다.

- `--kind`, `--nature`, `--draft`, `mmodule grow`, `--part`, `merge-templates`, `modules.default_kind`
- `mmodule ai-organize` (`mmodule audit`으로 대체)
- `mmodule suggest-ai` (`mmodule suggest-links --ai`로 대체)

### ✨ Added

- **LLM 제공자 추가:** `codex-cli`(별칭 `codex`), `antigravity-cli`(별칭 `agy`, `antigravity`), `glm`. Codex는 `read-only`, Antigravity는 `plan` 모드로 실행합니다.
- **`glm`:** Claude CLI를 GLM에 연결합니다. `llm.glm.env_from_ps1` 또는 `llm.glm.env_from_env`로 연결 값이 있는 곳을 지정하며, 값은 설정 파일에 적지 않습니다. 자동으로 선택되지 않습니다.
- **새 문서 형식:** `mmodule create --type <종류>`. 종류는 참고, 이해, 방법, 판단이며 선택 사항입니다. 첫 하위 문서를 만들면 `topic.md`가 `topic/topic.md`로 옮겨지고, `[[topic]]` 링크는 유지됩니다.
- **작성 지원:** `mmodule guide [종류]`와 `mt-write` 스킬. 기본적으로 AI는 질문하고 지적하며, 요청할 때만 본문을 씁니다. `<기반폴더>/guides/`의 파일이 번들 가이드보다 우선합니다.
- **`mmodule audit`:** 분리와 병합 후보를 보여 줍니다. LLM을 쓰지 않으며 문서를 바꾸지 않습니다.
- **`mmodule suggest-links --ai`:** 내용을 읽고 관련 문서를 제안합니다.
- **`mask`의 기간 조회:** 시작일과 종료일을 지정해 타임라인을 읽습니다.
- **연결 그래프의 Markdown 링크:** 위키 링크와 함께 읽습니다.
- **`mcheck`의 `sources` 검증:** frontmatter의 로컬 경로를 확인합니다.

### 🐛 Fixed

- **`mask`:** 날짜형 파일명의 타임라인과 단일 문서 모듈을 읽지 못하던 문제를 고쳤습니다. 읽을 수 없는 날짜를 오늘로 처리해 다른 날의 기록으로 답하던 문제도 고쳤습니다.
- **`msummary`:** 타임라인과 모듈 요약이 `AttributeError`로 중단되던 문제를 고쳤습니다. `--decisions`는 단일 문서의 결정 절도 읽습니다. 도움말의 없는 옵션(`--week`, `--days`)도 바로잡았습니다.
- **`claude-cli`:** 긴 프롬프트가 Windows 명령줄 길이 제한에 걸리지 않도록 표준 입력으로 전달합니다.
- **`PLAN.md`:** CLI가 모듈로 나열하던 문제를 고쳤습니다.
- **플러그인 모듈 목록:** `AI.md`, `MIGRATION-PLAN.md`처럼 대문자로 된 파일명을 숨기던 문제를 고쳤습니다.
- **`mmodule rename`:** 하위 문서를 남겨 두거나 잘못된 위치로 옮기던 문제를 고쳤습니다.
- **`mmodule archive`, `unarchive`, 연결 그래프, `mpublish`:** 단일 파일 모듈을 처리합니다. 하위 문서를 남겨 두거나, 하위 문서의 링크를 상위 문서의 것으로 집계하던 문제도 고쳤습니다.
- **`suggest-links`, `check-links`:** 문서 이름이 빈 괄호로 출력되던 문제를 고쳤습니다.

### 📚 Documentation

- 도움말, README, 사용자 가이드, 튜토리얼, 스킬을 새 문서 형식 기준으로 수정했습니다.
- `minit`은 `MODULE-ORGANIZATION-PRINCIPLES.md`와 `QUICK-REFERENCE-MODULE-ORGANIZATION.md`를 더 이상 만들지 않습니다.

### ⚠️ 알려진 제한

- `mcontext -i`는 단일 문서 모듈에서 동작하지 않습니다.
- 플러그인 1.2.0은 빌드와 단위 테스트만 거쳤고, Obsidian 안에서 화면을 직접 확인하지 않았습니다.

## [1.1.0] - 2026-02-25

### ✨ 추가

- **Primary-Secondary 다중 Notion 동기화:** Notion 워크스페이스 여러 곳에 동기화합니다.
  - Primary 백엔드는 지금까지처럼 양방향으로 동기화합니다(Local ↔ Notion A).
  - Secondary 백엔드는 내보내기만 하는 사본입니다(Local → Notion B, C, …).
  - config의 `additional-backends` 절에 추가 백엔드를 적습니다.
  - `nsync --backend <name>`은 그 백엔드만, `nsync --secondary-only`는 secondary 백엔드만 동기화합니다. `nwatch --no-secondary`는 secondary로 내보내지 않습니다.
  - 백엔드마다 state와 cache 파일을 따로 둡니다(`notion_sync_state_{name}.json`).
  - Secondary가 실패해도 primary에는 영향이 없습니다.
  - 백엔드가 하나인 기존 config는 그대로 동작합니다.

### 🐛 수정

- `mupdate`가 PEP 668(externally-managed-environment) 환경에서 실패하던 문제
- `mupdate` 별칭이 등록되지 않던 문제
- editable 설치에서 버전을 `pyproject.toml`에서 읽도록 수정

## [1.0.0] - 2026-02-10

1.0.0-alpha 이후 커밋 187개(기능 76개, 수정 34개)의 기록에서 정리한 절입니다. 커밋 메시지를 바탕으로 영역별로 묶었으며, 기능을 하나씩 다시 실행해 확인한 것은 아닙니다.

### ✨ 추가

- **Timeline, Review, Plan 체계(Phase 1~5):** 타임라인 구조를 정리하고, 리뷰와 계획(daily, weekly, monthly)을 더했습니다.
  - `mplan daily/weekly/monthly done`을 실행하면 타임라인에 자동으로 기록하고, 계획과 타임라인이 서로를 가리킵니다. 기록에는 작업 유형(Daily Plan, Weekly Plan, Monthly Plan)이 표시됩니다.
  - `mplan done`은 할 일을 비슷한 이름으로도 찾고, 진행률을 자동으로 갱신합니다. `mplan daily`는 `recurring.md`도 보여 줍니다.
  - `mcontext`에 Current Plans 절이 생겨서, 오늘·이번 주·이번 달 계획의 진행률과 남은 할 일·목표(최대 3개)를 보여 줍니다.
  - `mstatus`에 계획 통계가 생겨서, Daily·Weekly·Monthly 계획 수와 오늘·이번 주 진행률을 보여 줍니다.
- **타임라인 보기와 편집:** `mday`, `mmonth`, `mdays`로 날짜별 타임라인을 봅니다. `medit`은 기록을 화면에서 고치는 편집기이며, 시각도 바꿀 수 있습니다.
- **태그:** `record --tags`와 글 안의 태그(`[tag]`, `#tag`)를 인식합니다. 태그의 대소문자를 보존하고, 괄호 태그 안의 공백을 허용합니다. `mtags`(`mtag`)는 사용 횟수와 최근 31일 활동을 보여 주고, 태그 바꾸기·지우기·찾기 명령이 있습니다.
- **보관(archive):** 날짜 기준 보관(`marchive --older-than`), 보관 제안(`--suggest`), 대화형 선택을 지원합니다.
- **요약과 문서 상태:** `msummary`가 결과를 캐시하고, `--decisions`로 결정 사항을 분석합니다. 문서 상태 점검이 `mcontext`에 들어갔습니다.
- **모듈:** 모듈 그래프의 JSON 출력과 부모·자식 관계, 모듈 이름 바꾸기, 유니코드 경로, Feature 기반과 Topic 기반 구조를 지원합니다. `ai-organize`와 글에서 모듈을 만드는 AI 기능이 생겼습니다.
- **Context Graph와 codemap:** `mcheck`(경로 확인, 보관 모듈 제외)와 `mcontext --structure`, `--update-interfaces`, Python 코드 구조를 분석하는 codemap(`mmap`)을 더했습니다.
- **Notion 연동:** 타임라인 미러링, 검색과 캐시, 모듈의 양방향 동기화, `nsync --discover`, 파일 변경을 따라가는 `nwatch`, 프록시와 PAT 모드, 할 일을 더하는 `np`, 한국어 별칭(노, 노검 등)을 지원합니다. `nwatch`는 중복 실행을 막고 캐시를 스스로 복구합니다.
- **Knowledge Federation:** 프로젝트 사이에서 모듈을 공유하고, `mimport --preview`로 KB 모듈의 내용을 미리 봅니다.
- **검색:** `mcache`로 검색 캐시와 Notion 캐시를 관리합니다. 겹치는 검색 결과를 합칩니다(1.6.2에서 고친 문제가 여기서 시작되었습니다).
- **도움말과 설정:** 이중 언어 도움말(`mhelp --guide`), 튜토리얼, `mconfig`와 config 안내, USAGE.md를 더했습니다. `minit`은 `.claude/` 구조와 모듈 구성 문서를 만들고, `--update-docs`와 `--update-all`로 갱신합니다. 별칭은 Linux 셸(Bash, Zsh)에서도 동작합니다.
- **버전 관리:** `m --version`과 `mupdate`를 더했습니다.

### 🐛 수정

- Typer 0.12 이상에서 선택 인수(`Optional`)를 다루는 문제
- `pyproject.toml`이 하위 패키지를 모두 포함하지 않던 문제
- Notion 동기화의 중복 페이지·중복 기록 생성, 시각 순서, 잠자기 뒤의 중복 기록
- 그 밖에 경로 정규화, 문서 상태의 줄 수 계산, AI 응답 해석 등

## [1.0.0-alpha] - 2025-11-15

### 🎉 Initial Alpha Release

**Core Philosophy:**
"0.5초로 포착하고, 주말에 정리하며, 평생 활용한다."

### ✨ Features

#### Timeline System (시간축)
- **m** - Record messages to timeline in 0.5 seconds
- **mtoday** - View today's timeline
- **mweek** - View this week's timeline
- **msort** - Sort timeline entries by time

#### Module System (공간축)
- **module create** - Create hierarchical modules
- **module list/tree** - View module structure
- **module archive/unarchive** - Archive management
- **module connections** - Wiki-style [[links]]
- **module graph** - Visualize connections (Mermaid/Graphviz)
- **module rebuild-graph** - Rebuild connection graph
- **module check-links** - Validate links
- **module suggest-links** - Manual connection suggestions
- **module suggest-ai** - AI-based connection suggestions
- **module auto-tag** - Automatic tagging
- **module graph-history/diff/snapshot** - Graph version management

#### Search System (검색)
- **ms** - Search with multiple backends
  - Text search (BM25 ranking)
  - Semantic search (vector embeddings)
  - Hybrid search (text + semantic)
- Advanced filters (date, type, tags, exclude)
- Result caching for performance
- SQLite FTS5 indexing

#### LLM Integration
- **msummary** - Summarize timeline or modules
- Dual provider support (Anthropic API + Ollama)
- Local-first with Ollama
- Vector embeddings for semantic search
- AI connection suggestions
- Auto-tagging

#### UI/UX
- **CLI** - 16 commands with rich output
- **malias** - Alias management (batch + PowerShell)
- **mbrowse** - Interactive TUI browser
  - Multi-mode: Search/Timeline/Modules/Graph
  - Vim-style navigation
  - Filter toggles
- **mcompletion** - Shell completion support
- **mtutorial** - Interactive tutorial

#### Project Management
- **mstatus** - Project statistics
- **marchive** - Archive completed documentation
- **mplan** - Plan management
- **mcontext** - Generate Claude Code context
- **mhooks** - Git hooks for auto-sync

#### Performance
- Batch embeddings (10-50x improvement)
- Incremental indexing
- Result caching (TTL-based)
- Parallel search processing

### 📦 Architecture

- **6 Feature-Based Modules:**
  - core-system - Timeline, initialization, basic data
  - search-system - Text, vector, hybrid search
  - module-system - Hierarchical modules, wiki links, graph
  - ui-system - CLI, TUI, aliases
  - llm-integration - LLM features, embeddings
  - project-management - Architecture, roadmap, decisions

### 🎯 Design Principles

1. **Time First** - Capture first, organize later
2. **Lossless** - Record everything, lose nothing
3. **Minimal Friction** - 0.5 second capture
4. **Loose Coupling** - Modular architecture
5. **Local First** - Local by default, explicit expansion

### 📚 Documentation

- README.md - Project overview
- INSTALLATION.md - Installation guide
- QUICKSTART.md - 5-minute start guide
- USER_GUIDE.md - Complete user guide
- FAQ.md - Frequently asked questions
- CLAUDE.md - Claude Code integration guide
- 시간-공간-통합-지식-체계-v2.0.md - Full design document (Korean)

### 🧪 Testing

This is an alpha release. The software has been extensively dogfooded during development (200+ timeline entries, 30+ decisions) but lacks formal test coverage. Use with caution and report issues.

### 🔧 Requirements

- Python 3.10+
- Optional: sentence-transformers (vector search)
- Optional: anthropic/ollama (LLM features)
- Optional: textual (TUI browser)

### 📝 Known Limitations

- No automated tests (manual testing only)
- Windows console encoding issues (workaround available)
- Large datasets (10,000+ entries) not extensively tested
- MCP server support postponed (may revisit)

### 🙏 Acknowledgments

This project practices what it preaches - it was built using its own system for knowledge management. All development is recorded in `.memory/timeline/` and decisions in module-specific `decisions.md` files.

