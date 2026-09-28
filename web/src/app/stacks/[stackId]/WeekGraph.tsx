"use client";

import "@xyflow/react/dist/style.css";
import {
  Background,
  Controls,
  type Edge,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from "@xyflow/react";
import {
  Briefcase,
  CircleCheck,
  Hammer,
  Lock,
  LockOpen,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { Inline } from "@/components/Inline";
import type {
  LessonState,
  LessonSummary,
  Milestone,
  Syllabus,
  Week,
} from "@/lib/api";
import { formatMinutes, weekMinutes } from "@/lib/format";
import { cn } from "@/lib/utils";

const ROW_HEIGHT = 150;
const HUB_WIDTH = 200;
const NODE_GAP = 150;

const isDone = (state: LessonState) =>
  state === "completed" || state === "updated";

type WeekNode = Node<
  { week: Week; status: "done" | "current" | "ahead" },
  "week"
>;
type LessonNode = Node<{ lesson: LessonSummary; href: string }, "lesson">;
type MilestoneNode = Node<{ milestone: Milestone }, "milestone">;
export type WeekGraphNode = WeekNode | LessonNode | MilestoneNode;

/**
 * Lays the Week map out as a graph: one row per Week, in Syllabus order. Each row starts with a
 * Week hub, then its Lessons joined in order, then its Milestones. The hubs are joined top to
 * bottom. An edge is green once the node it leaves is done, and animated into the Unlocked Lesson.
 * `focus` is where the graph opens: the current Week's hub and the Lessons around its Unlocked one
 * (the first Week when nothing is Unlocked), so the Learner starts at readable size.
 */
export function weekGraphLayout(syllabus: Syllabus): {
  nodes: WeekGraphNode[];
  edges: Edge[];
  focus: string[];
} {
  const nodes: WeekGraphNode[] = [];
  const edges: Edge[] = [];
  const edge = (
    source: string,
    target: string,
    done: boolean,
    animated = false,
  ): Edge => ({
    id: `${source}->${target}`,
    source,
    target,
    animated,
    style: {
      stroke: done ? "var(--success)" : "var(--border)",
      strokeWidth: 2,
    },
  });

  syllabus.weeks.forEach((week, row) => {
    const weekDone = week.lessons.every((l) => isDone(l.state));
    const current = week.lessons.some((l) => l.state === "unlocked");
    const hubId = `week:${week.id}`;
    const y = row * ROW_HEIGHT;
    nodes.push({
      id: hubId,
      type: "week",
      position: { x: 0, y },
      data: { week, status: weekDone ? "done" : current ? "current" : "ahead" },
    });
    if (row > 0) {
      const previous = syllabus.weeks[row - 1];
      const previousDone = previous.lessons.every((l) => isDone(l.state));
      edges.push({
        ...edge(`week:${previous.id}`, hubId, previousDone),
        sourceHandle: "bottom",
        targetHandle: "top",
      });
    }

    let previousId = hubId;
    let previousDone = week.lessons[0]?.state !== "locked";
    let x = HUB_WIDTH + 40;
    for (const lesson of week.lessons) {
      const id = `lesson:${lesson.id}`;
      nodes.push({
        id,
        type: "lesson",
        position: { x, y },
        data: { lesson, href: `/stacks/${syllabus.id}/lessons/${lesson.id}` },
        // React Flow turns pointer events off on non-interactive nodes; Lesson nodes are links.
        style: { pointerEvents: "all" },
      });
      edges.push(
        edge(previousId, id, previousDone, lesson.state === "unlocked"),
      );
      previousId = id;
      previousDone = isDone(lesson.state);
      x += NODE_GAP;
    }
    for (const milestone of week.milestones) {
      const id = `milestone:${milestone.id}`;
      nodes.push({
        id,
        type: "milestone",
        position: { x, y },
        data: { milestone },
      });
      edges.push(edge(previousId, id, previousDone));
      previousId = id;
      previousDone = milestone.ticked;
      x += NODE_GAP;
    }
  });

  const focusWeek = syllabus.weeks.find((w) =>
    w.lessons.some((l) => l.state === "unlocked"),
  );
  const week = focusWeek ?? syllabus.weeks[0];
  const unlocked = week
    ? Math.max(
        0,
        week.lessons.findIndex((l) => l.state === "unlocked"),
      )
    : 0;
  const focus = week
    ? [
        `week:${week.id}`,
        ...week.lessons
          .slice(Math.max(0, unlocked - 1), unlocked + 3)
          .map((l) => `lesson:${l.id}`),
      ]
    : [];

  return { nodes, edges, focus };
}

const LABELS: Record<LessonState, string> = {
  completed: "Completed",
  updated: "Updated",
  unlocked: "Unlocked",
  locked: "Locked",
};

const LESSON_STYLES: Record<LessonState, string> = {
  completed: "bg-success/15 text-success-foreground ring-success",
  updated: "bg-warning/20 text-warning-foreground ring-warning",
  unlocked: "bg-primary text-primary-foreground ring-primary/30 ring-4",
  locked: "bg-muted text-muted-foreground ring-border",
};

const ICONS = {
  completed: CircleCheck,
  updated: Sparkles,
  unlocked: LockOpen,
  locked: Lock,
};

const hidden = "!size-1 !min-w-0 !border-0 !bg-transparent";

function WeekHub({ data: { week, status } }: NodeProps<WeekNode>) {
  return (
    <div
      className={cn(
        "flex w-[200px] items-center gap-3 rounded-2xl border bg-card p-3 shadow-xs",
        status === "current" && "border-primary/50 ring-2 ring-primary/20",
      )}
    >
      <Handle
        type="target"
        position={Position.Top}
        id="top"
        className={hidden}
      />
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-full font-heading text-sm font-semibold",
          status === "done" && "bg-success text-background",
          status === "current" && "bg-primary text-primary-foreground",
          status === "ahead" && "bg-muted text-muted-foreground",
        )}
      >
        {week.number}
      </span>
      <span className="min-w-0 space-y-0.5">
        <span className="line-clamp-2 block text-sm leading-tight font-semibold">
          {week.title}
        </span>
        <span className="block text-xs text-muted-foreground">
          {formatMinutes(weekMinutes(week))}
        </span>
      </span>
      <Handle type="source" position={Position.Right} className={hidden} />
      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom"
        className={hidden}
      />
    </div>
  );
}

function LessonDot({ data: { lesson, href } }: NodeProps<LessonNode>) {
  const Icon = ICONS[lesson.state];
  return (
    <Link
      href={href}
      className="group flex w-28 flex-col items-center gap-2 text-center"
    >
      <span
        className={cn(
          "relative flex size-11 items-center justify-center rounded-full ring-2 transition-transform group-hover:scale-110",
          LESSON_STYLES[lesson.state],
        )}
      >
        <Handle type="target" position={Position.Left} className={hidden} />
        <Icon aria-hidden className="size-5" />
        <span className="sr-only">{LABELS[lesson.state]} </span>
        <Handle type="source" position={Position.Right} className={hidden} />
      </span>
      <span
        className={cn(
          "line-clamp-3 text-xs font-medium group-hover:text-primary",
          lesson.state === "locked" && "text-muted-foreground",
        )}
      >
        <Inline text={lesson.title} />
      </span>
    </Link>
  );
}

function MilestoneDiamond({ data: { milestone } }: NodeProps<MilestoneNode>) {
  const Icon = milestone.kind === "build" ? Hammer : Briefcase;
  return (
    <div className="flex w-28 flex-col items-center gap-2 text-center">
      <span
        className={cn(
          "relative flex size-10 rotate-45 items-center justify-center rounded-lg ring-2",
          milestone.ticked
            ? "bg-success/15 text-success-foreground ring-success"
            : "bg-card text-muted-foreground ring-border",
        )}
      >
        <Handle type="target" position={Position.Left} className={hidden} />
        <Icon aria-hidden className="size-4 -rotate-45" />
        <span className="sr-only">
          {milestone.ticked ? "Ticked Milestone " : "Milestone "}
        </span>
        <Handle type="source" position={Position.Right} className={hidden} />
      </span>
      <span className="line-clamp-3 text-xs text-muted-foreground">
        {milestone.title}
      </span>
    </div>
  );
}

const nodeTypes = {
  week: WeekHub,
  lesson: LessonDot,
  milestone: MilestoneDiamond,
};

/**
 * The Week map as a pannable, zoomable graph (React Flow). Every Lesson node, Locked ones too,
 * links to its page;
 * Milestones are ticked in the list view.
 */
export function WeekGraph({ syllabus }: { syllabus: Syllabus }) {
  const { nodes, edges, focus } = weekGraphLayout(syllabus);
  return (
    <div
      className="h-[70vh] min-h-[28rem] overflow-hidden rounded-2xl border bg-card shadow-xs [--xy-background-color:var(--card)] [--xy-background-pattern-dots-color:var(--border)] [--xy-controls-button-background-color-hover:var(--muted)] [--xy-controls-button-background-color:var(--card)] [--xy-controls-button-border-color:var(--border)] [--xy-controls-button-color-hover:var(--foreground)] [--xy-controls-button-color:var(--foreground)] [--xy-attribution-background-color:transparent]"
      aria-label="Week graph"
      role="figure"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{
          nodes: focus.map((id) => ({ id })),
          maxZoom: 1,
          padding: 0.2,
        }}
        minZoom={0.3}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        preventScrolling={false}
      >
        <Background gap={24} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
