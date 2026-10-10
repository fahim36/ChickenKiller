# Practice guidance variant sources (ticket 07)

Fetched through the web tool during this run beginning at **2026-10-10 18:12 UTC**. All sources below use `source.accessed: "2026-10-10"` (UTC, despite the client displaying 11 October in Asia/Dhaka). These are authoring notes, not bank entries. Scenario outcomes are applications of the cited facts; specify their assumptions in final questions.

Read the active question entries in `w01-l01.json`, `challenge-001.json`, Android `draft-13.json`, PostgreSQL `challenge-065.json`, and .NET `draft-16.json`/`draft-28.json`. Read the corresponding syllabus lessons: names/objects/mutability; processes/lifecycles; intents/tasks; observability; architecture review. Challenge concepts have `lesson: null`; preserve that association.

## Python: `assignment-binds-names`

Sources: [Programming FAQ](https://docs.python.org/3/faq/programming.html#why-did-changing-list-y-also-change-list-x), [copy module](https://docs.python.org/3/library/copy.html). Publisher: Python Software Foundation. Accessed: 2026-10-10.

Facts: assignment binds names rather than copying. Mutating a list is visible through its aliases; list concatenation creates a new list. Function argument names can be rebound without rebinding caller names. A shallow copy creates a new outer container but retains references to nested objects.

- MC application: `queue = ["a"]; backup = queue; queue = queue + ["b"]`. Correct: backup remains `["a"]`, queue becomes `["a", "b"]`. Reject both lists changing, backup clearing, or assignment automatically cloning the initial list.
- MS application: `rows = [[1]]; alias = rows; copied = rows.copy(); copied[0].append(2); copied.append([3])`. Correct: alias is rows; rows becomes `[[1,2]]`; copied has a different outer list. Reject nested independence and the extra outer row appearing in rows.

Pitfall: distinguish mutation, rebinding, shallow copy, and deep copy. Avoid interning or user-defined augmented-assignment semantics.

## LangGraph: `c001-langgraph-thread-id`

Source: [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence). Publisher: LangChain. Accessed: 2026-10-10.

Facts: checkpointer state is thread scoped; `get_state(config)` retrieves that thread's latest snapshot by default. InMemorySaver loses checkpoints on process restart.

- MC application: a diagnostic endpoint requests ticket-43 although ticket-42 owns the desired checkpoints. Use ticket-42 in configurable.thread_id; graph identity, an ordinary user-name field or another saver does not redirect the lookup.
- MS application: separate IDs select separate histories, but stable IDs do not make RAM durable. A durable saver is needed for restart survival.

Pitfall: specify the same live saver when asserting continuation; a thread ID is not authorization.

## Android: `activity-recreation-on-config-change`

Source: [Handle configuration changes](https://developer.android.com/guide/topics/resources/runtime-changes). Publisher: Android Developers. Accessed: 2026-10-10.

Facts: default recreation destroys the old Activity and creates a new one; Activity fields disappear. ViewModel supports retained data and rememberSaveable supports appropriate transient UI state. Declared configChanges suppresses recreation for specified changes, which still happen; embedded Views may need manual updates.

- MC application: default-handled rotation during editing with a draft only in an Activity field. Correct: a new Activity loses that field; preserve suitable state with supported APIs. Reject the same instance, rotation implying permanent finish, or configChanges guaranteeing process-death survival.
- MS application: orientation changes are handled explicitly via configChanges in a mixed Compose/AndroidView screen. Correct: configuration still updates; observing LocalConfiguration enables recomposition; embedded View resources may require manual refresh. Reject freezing device configuration and disabling every possible recreation.

Pitfall: current docs recommend direct handling for modern Compose-only apps and describe Android 17 exceptions for specific changes. Do not claim every configuration change always recreates, or that opting out is universally forbidden. Pin rotation and manifest assumptions.

## Android: `activity-tasks-launch-modes`

Sources: [Tasks and back stack](https://developer.android.com/guide/components/activities/tasks-and-back-stack), [Intent FLAG_ACTIVITY_CLEAR_TOP API](https://developer.android.com/reference/android/content/Intent#FLAG_ACTIVITY_CLEAR_TOP). Publisher: Android Developers. Accessed: 2026-10-10.

Facts: standard creates new instances; singleTop reuses only a top instance through onNewIntent. CLEAR_TOP removes activities above an existing target. With a standard target, CLEAR_TOP also removes that target and creates a fresh instance; combining SINGLE_TOP permits reuse.

- MC application: same-task stack Home → Chat, Chat is singleTop, no flags, another intent targets Chat. Correct: existing Chat receives onNewIntent and stack stays Home → Chat. Reject adding another Chat, clearing Home, or ignoring the intent.
- MS application: same-task stack Home → Detail → Comments, Detail standard; compare CLEAR_TOP alone with CLEAR_TOP | SINGLE_TOP. Correct: Comments removed in both; alone recreates Detail; combined reuses Detail via onNewIntent. Reject retaining Comments or CLEAR_TOP universally guaranteeing instance reuse.

Pitfall: explicitly exclude NEW_TASK, custom navigation, and multiple matching task affinities. Separate stack shape from Activity identity. Existing bank already tests singleTop below the top; use the top-instance or standard/CLEAR_TOP nuance instead.

## PostgreSQL: `c065-advisory-lock-lifetimes`

Source: [Explicit locking, advisory locks](https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS). Publisher: PostgreSQL Global Development Group. Accessed: 2026-10-10.

Facts: advisory locks are cooperative. Session locks persist until explicit release or session end; rollback does not release acquisition or undo unlock. Reentrant session acquisitions require matching unlocks. Transaction locks release at transaction end and have no explicit unlock. Both scopes conflict for the same identifier across sessions.

- MC application: Session A acquires `pg_advisory_lock(42)` twice, unlocks once, then rolls back. Session B requests the same exclusive key. Correct: B remains blocked while A holds its remaining acquisition. Reject rollback release, one unlock releasing all holds, or connection checkout changing ownership.
- MS application: A obtains transaction advisory key 42, B requests a session lock for 42, then A commits. Correct: B waits before commit; commit releases A's hold; noncooperating ordinary writes are not protected by the advisory key. Reject requiring manual transaction unlock and unrelated keys being automatically blocked.

Pitfall: clarify separate sessions and exclusive same-key requests. Pool return is not session termination.

## PostgreSQL: `c065-sequence-allocation-and-rollback`

Source: [Sequence manipulation functions](https://www.postgresql.org/docs/current/functions-sequence.html). Publisher: PostgreSQL Global Development Group. Accessed: 2026-10-10.

Facts: nextval allocates atomically across sessions; aborted transactions do not reclaim values. currval is session-local and requires previous nextval on that sequence. ON CONFLICT may consume an allocation before discovering conflict. Sequences cannot promise gapless numbering.

- MC application: with increment 1, CACHE 1 and no competing callers/resets, A calls setval(s, 100, false), then rolls back. B next receives 100. The false flag returns exactly the assigned value, and setval is not undone by rollback. Reject 101, restoring the previous value, or requiring A to commit. This fact was re-fetched during this run from the same official sequence page.
- MS application: A receives 10; B receives 11; A calls currval; an insert using nextval meets ON CONFLICT DO NOTHING. Correct: A's currval remains 10; conflicting insert can consume a value; missing numbers do not prove deleted rows. Reject currval returning B's 11 and committed rows always having contiguous IDs.

Pitfall: exact numbers require cache/concurrency/reset assumptions. Avoid asserting durable crash state or globally latest currval.

## .NET: `activitysource-trace-propagation`

Sources: [Instrumentation walkthrough](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/distributed-tracing-instrumentation-walkthroughs), [Distributed tracing concepts](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/distributed-tracing-concepts), [OpenTelemetry propagation](https://opentelemetry.io/docs/concepts/context-propagation/). Publishers: Microsoft Learn; OpenTelemetry. Accessed: 2026-10-10.

Facts: StartActivity may return null when no listener is interested. AddSource selects custom source names. Activity.Current flows through ordinary async calls; nested activities use the current parent and stopping restores it. Non-HTTP carriers require injection/extraction support. W3C trace context carries identifiers/flags, not full span data.

- MC application: a broker consumer starts an Activity without a current or extracted parent. It starts a new trace; extract carrier context and supply the parent. ActivityKind, matching source names and message-body matching do not establish parentage.
- MS application: sampled parent A; child B starts inside its scope, awaits normally, then disposes. Correct: B inherits A's trace; has its own span ID; A becomes current again. Reject await automatically starting a new trace and child disposal exporting the whole distributed trace without a collector.

Pitfall: specify interested sampling and unsuppressed normal async context flow. Broker propagation requires explicit library/code support; changing source names is not a propagation fix.

## .NET: `adr-append-only-decision-log`

Source: [Maintain an ADR](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record). Publisher: Microsoft Learn. Accessed: 2026-10-10.

Facts: accepted decisions retain historical context; reversal gets a new linked superseding record. Record context, considered alternatives, outcome, trade-offs, confidence, and status. Architecturally significant decisions affect structure/quality or are hard to reverse. Records should be accessible with workload documentation.

- MC application: an audit finds the old ADR rewritten even though supersession links exist. The historical constraints and rationale are lost; a link cannot reconstruct erased decision content.
- MS application: cross-region constraints replace a former low-throughput local-queue decision. Preserve the original rationale, describe new constraints and trade-offs in the new record, and link supersession. Reject falsifying the original requirements or hiding its changed status.

Pitfall: append-only concerns accepted decision content, not forbidding status/link maintenance. Avoid implying every local refactor requires an ADR or that low confidence invalidates an otherwise recorded decision.
