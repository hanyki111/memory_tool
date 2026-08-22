/**
 * The MOP Kind/Nature decision tables, as UI copy.
 *
 * This is presentation only — the wording of the two questions and their
 * options. Template resolution and assembly belong to memory_tool
 * (`memory_tool/core/module_templates.py`), which the plugin drives by passing
 * `--kind` / `--nature` through to `mmodule create`. Keeping a second assembler
 * here meant two template sources producing two different documents for the
 * same choice.
 */

export type ModuleKind = "knowledge" | "implementation" | "intent";

export type ModuleNature =
  | "concept"
  | "reference"
  | "analysis"
  | "tracker"
  | "method"
  | "idea"
  | "inquiry"
  | "plan";

/** "Does the subject of this document exist yet, and what is its source of truth?" */
export const KINDS: { id: ModuleKind; answer: string }[] = [
  { id: "intent", answer: "아직 없다. 앞으로 하려는 것" },
  { id: "knowledge", answer: "있다. 지식이 틀린 것" },
  { id: "implementation", answer: "있다. 코드는 맞는데 문서만 낡은 것" },
];

type NatureOption = {
  id: ModuleNature;
  label: string;
  trigger: string;
  answers: string;
  lifetime: string;
};

/** "What makes this module need updating?" — knowledge modules. */
export const KNOWLEDGE_NATURES: NatureOption[] = [
  {
    id: "concept",
    label: "concept (개념)",
    trigger: "내 이해가 깊어질 때",
    answers: "이게 뭔가?",
    lifetime: "반영구",
  },
  {
    id: "reference",
    label: "reference (레퍼런스)",
    trigger: "대상이 패치·개정될 때",
    answers: "값이 얼마인가?",
    lifetime: "버전 종속",
  },
  {
    id: "analysis",
    label: "analysis (분석)",
    trigger: "새 증거가 나올 때",
    answers: "그래서 어떻게 판단하나?",
    lifetime: "수개월",
  },
  {
    id: "tracker",
    label: "tracker (추적)",
    trigger: "시간이 흐를 때",
    answers: "지금 상태가 뭔가?",
    lifetime: "수일~수주",
  },
  {
    id: "method",
    label: "method (방법론)",
    trigger: "적용 피드백이 올 때",
    answers: "어떻게 하는가?",
    lifetime: "반영구",
  },
];

/** "What makes this module need updating?" — intent modules. */
export const INTENT_NATURES: NatureOption[] = [
  {
    id: "idea",
    label: "idea (착상)",
    trigger: "새 자극이 붙을 때",
    answers: "이거 뭔가 될까?",
    lifetime: "넓히기",
  },
  {
    id: "inquiry",
    label: "inquiry (논의)",
    trigger: "논의가 한 바퀴 돌 때",
    answers: "무엇을 골라야 하나?",
    lifetime: "고르기",
  },
  {
    id: "plan",
    label: "plan (실행 계획)",
    trigger: "현실이 계획을 어길 때",
    answers: "무엇을 언제 하는가?",
    lifetime: "옮기기",
  },
];

/** Natures a kind offers. implementation modules carry none. */
export const NATURES_BY_KIND: Record<ModuleKind, NatureOption[]> = {
  knowledge: KNOWLEDGE_NATURES,
  implementation: [],
  intent: INTENT_NATURES,
};
