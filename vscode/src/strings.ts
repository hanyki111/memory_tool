/** Words on the screen, in English or Korean by VS Code's display language. */

const en = {
  tabTitle: "Timeline",
  recordPlaceholder: "Record to the timeline… ([tag] or #tag)",
  record: "Record",
  searchPlaceholder: "Search",
  search: "Search",
  semantic: "Search by meaning",
  semanticTitle: "Hybrid search: finds related wording, but loads a model and takes several seconds",
  clearSearch: "Back to the timeline",
  period: "Period",
  from: "From",
  to: "To",
  go: "Go",
  thisWeek: "This week",
  lastWeek: "Last week",
  thisMonth: "This month",
  latest: "Latest",
  review: "Review",
  reviewTitle: "Opens a terminal and reviews the entries since the last review: mreview",
  reviewFrom: "Review from {date}",
  reviewFromTitle: "Opens a terminal and reviews from this date until now: mreview --since {date}",
  widen: "Open wide",
  loading: "Loading…",
  searching: "Searching…",
  recording: "Recording…",
  noEntries: "No entries in these days.",
  loadingOlder: "Loading older days…",
  loadOlder: "Show the 7 days before {date}",
  timelineHits: "Timeline ({count})",
  documentHits: "Documents ({count})",
  noOlder: "No older entries.",
  resultsFor: "{count} results for “{query}”",
  noResults: "No results for “{query}”.",
  noBaseTitle: "No knowledge base in this folder",
  noBaseBody: "Run minit in a terminal in this folder, then refresh.",
  noFolder: "Open a folder to use its timeline.",
  showing: "{from} – {to}",
  openFile: "Open this day's file",
  pythonNotFound:
    "Python with memory_tool was not found. Set memoryTool.python, or install memory_tool in this folder's .venv.",
};

type Strings = typeof en;

const ko: Strings = {
  tabTitle: "타임라인",
  recordPlaceholder: "타임라인에 기록… ([태그] 또는 #태그)",
  record: "기록",
  searchPlaceholder: "검색",
  search: "검색",
  semantic: "의미로 찾기",
  semanticTitle: "혼합 검색: 표현이 달라도 찾지만, 모델을 불러오느라 몇 초 걸립니다",
  clearSearch: "타임라인으로 돌아가기",
  period: "기간",
  from: "시작",
  to: "끝",
  go: "이동",
  thisWeek: "이번 주",
  lastWeek: "지난주",
  thisMonth: "이번 달",
  latest: "최신",
  review: "리뷰",
  reviewTitle: "터미널을 열고 지난 리뷰 이후의 기록을 리뷰합니다: mreview",
  reviewFrom: "{date}부터 리뷰",
  reviewFromTitle: "터미널을 열고 이 날짜부터 지금까지 리뷰합니다: mreview --since {date}",
  widen: "넓게 보기",
  loading: "불러오는 중…",
  searching: "검색하는 중…",
  recording: "기록하는 중…",
  noEntries: "이 기간에는 기록이 없습니다.",
  loadingOlder: "이전 기록을 불러오는 중…",
  loadOlder: "{date} 이전 7일 더 보기",
  timelineHits: "타임라인 ({count}건)",
  documentHits: "문서 ({count}건)",
  noOlder: "더 이전 기록이 없습니다.",
  resultsFor: "“{query}” 검색 결과 {count}건",
  noResults: "“{query}”에 대한 결과가 없습니다.",
  noBaseTitle: "이 폴더에는 지식 베이스가 없습니다",
  noBaseBody: "이 폴더의 터미널에서 minit을 실행한 뒤 새로 고쳐 주세요.",
  noFolder: "폴더를 열면 그 폴더의 타임라인을 씁니다.",
  showing: "{from} – {to}",
  openFile: "이날의 파일 열기",
  pythonNotFound:
    "memory_tool이 설치된 Python을 찾지 못했습니다. memoryTool.python을 설정하거나, 이 폴더의 .venv에 memory_tool을 설치해 주세요.",
};

export type { Strings };

export function stringsFor(language: string): Strings {
  return language.toLowerCase().startsWith("ko") ? ko : en;
}

/** Fill "{name}" placeholders. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, name) => (name in values ? String(values[name]) : whole));
}
