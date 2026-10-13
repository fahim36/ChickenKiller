"use client";

import { useSyncExternalStore } from "react";

const subscribe = () => () => {};
const browser = () => true;
const server = () => false;

export function formatLocalTime(
  value: string,
  dateOnly = false,
  timeZone?: string,
) {
  const instant = new Date(value.length === 10 ? `${value}T00:00:00Z` : value);
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    ...(dateOnly ? {} : { timeStyle: "short" as const }),
    ...(timeZone ? { timeZone } : {}),
  }).format(instant);
}

/** Browser-local formatting with the same initial markup on server and client. */
export function LocalTime({
  value,
  dateOnly = false,
}: {
  value: string;
  dateOnly?: boolean;
}) {
  const ready = useLocalClockReady();
  return (
    <time dateTime={value}>
      {ready ? formatLocalTime(value, dateOnly) : "…"}
    </time>
  );
}

export function useLocalClockReady() {
  return useSyncExternalStore(subscribe, browser, server);
}

export function ChallengeLabel({ label, day }: { label: string; day: string }) {
  return (
    <>
      {label.split(" · ")[0]} · <LocalTime value={day} dateOnly />
    </>
  );
}
