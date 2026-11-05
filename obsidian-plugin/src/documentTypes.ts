/**
 * Document types, as UI copy.
 *
 * Presentation only: the wording of the options. memory_tool writes the document
 * and accepts any type, so this list needs no version check against the CLI.
 */

export type DocumentTypeOption = {
  id: string;
  answers: string;
  updatedWhen: string;
};

export const DOCUMENT_TYPES: DocumentTypeOption[] = [
  { id: "참고", answers: "그 값이나 사실이 무엇이었지?", updatedWhen: "대상이 바뀔 때" },
  { id: "이해", answers: "왜 이렇게 작동하지?", updatedWhen: "이해가 깊어질 때" },
  { id: "방법", answers: "어떻게 하지?", updatedWhen: "적용하다 실패했을 때" },
  {
    id: "판단",
    answers: "왜 그렇게 보았거나 정했지?",
    updatedWhen: "고쳐 쓰지 않고 새 판단으로 대체할 때",
  },
];
