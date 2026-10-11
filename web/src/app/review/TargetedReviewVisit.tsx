"use client";

import { useEffect } from "react";
import { recordTargetedReviewVisit } from "./actions";

/** Instrument a loaded targeted queue; failures never prevent practice. */
export function TargetedReviewVisit({
  stack,
  concept,
}: {
  stack: string;
  concept: string;
}) {
  useEffect(() => {
    void recordTargetedReviewVisit(stack, concept).catch(() => {});
  }, [stack, concept]);
  return null;
}
