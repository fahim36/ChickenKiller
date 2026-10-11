import Link from "next/link";

export function QuestionReportLink({
  stackId,
  questionId,
}: {
  stackId: string;
  questionId: string;
}) {
  return (
    <Link
      aria-label={`Report Question ${questionId}`}
      className="text-sm underline"
      href={`/question-reports/new?stack_id=${encodeURIComponent(stackId)}&question_id=${encodeURIComponent(questionId)}`}
    >
      Report this Question
    </Link>
  );
}
