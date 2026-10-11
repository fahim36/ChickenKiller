# Content health variant research

Fetched **11 October 2026 UTC** in this run; use `sources[].accessed: "2026-10-11"`. Reviewed the release spec, bank rules in `docs/content-format.md`, existing active Questions, and current `v2026-10-10` teaching Lessons/Materials. This file records primary-source claims and new scenario blueprints; it does not change the banks. All targets differ from the previous eight enriched Concepts. MC means one correct choice; MS means at least two correct choices plus a false distractor. Final MS prompts must end “Select all that apply.” Preserve committed Questions and resolve Material IDs against the latest Syllabus.

## Agentic AI Engineer

### `mutable-default-argument` — Lesson `w01-l01`

Sources fetched: Python Software Foundation, [Function definitions](https://docs.python.org/3/reference/compound_stmts.html#function-definitions), [Programming FAQ: default values](https://docs.python.org/3/faq/programming.html#why-are-default-values-shared-between-objects). Defaults are evaluated at definition; supplying an argument bypasses that default. The None sentinel preserves an explicitly supplied empty container when tested with `is None`.

MC: `record(x, bag=[])` appends/returns bag. `first=record('a'); supplied=[]; second=record('b', supplied); third=record('c')`. Correct final values: first/third `['a','c']`, second `['b']`; first is third. Distractors: explicit argument mutates the default; every call gets a fresh list; first is a frozen snapshot.

MS: safe implementation uses `bag=None; if bag is None: bag=[]`. True: omitted calls receive independent lists; a supplied empty list is reused. False: `if not bag` preserves every supplied empty list; a None default forbids explicit lists.

Existing Materials: `fluent-python-2nd-ed`, `facts-and-myths-about-python-names`. No new Material needed. This contrasts omitted/explicit calls instead of repeating the existing two omitted calls.

### `late-binding-closures` — Lesson `w01-l02`

Sources fetched: Python Software Foundation, [FAQ: loop lambdas](https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result), [FAQ: local/nonlocal variables](https://docs.python.org/3/faq/programming.html#what-are-the-rules-for-local-and-global-variables-in-python). Closures read captured bindings when called; defaults capture values at definition. This also applies to ordinary nested functions.

MC: factory creates `value=1`, returns `read()` plus `update()` using `nonlocal value; value=9`. Call update then read. Correct 9; reject 1 frozen at creation, NameError, and update affecting only an unrelated local.

MS: loop creates ordinary functions `def read(i=i): return i`, then sets outer `i=99`. True: results stay `[0,1,2]`; omitting the default would read the final outer binding. False: only lambdas have late binding; parentheses around i capture its old value.

Materials: `fluent-python-2nd-ed`, `python-docs-the-data-model`. No new Material needed. Different from the bank's lambda comprehension output/fix.

### `w02-l03-blocking-calls` — Lesson `w02-l03`

Sources fetched: Python Software Foundation, [Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code), [Coroutines and tasks: to_thread](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread). One blocking loop-thread call delays other tasks; to_thread runs blocking I/O in a worker. It returns a coroutine, not an automatic executor submission at mere construction.

MC: a heartbeat must run while a synchronous file read waits. Correct `await asyncio.to_thread(read_file, path)`; reject adding async to the wrapper, calling read_file before passing its result, or create_task guaranteeing blocking code moves to a thread.

MS: `job = asyncio.to_thread(read_file, path)` is constructed but neither awaited nor scheduled. True: construction alone does not run the function; await/scheduling enables worker execution. False: construction immediately performs the file read; the worker is necessarily the loop thread.

Materials: `python-docs-developing-with-asyncio`, `python-docs-coroutines-and-tasks`, `python-docs-asyncio` exist in the current catalog. No new Material needed. Avoid timing guesses, GIL generalizations, and cancellation of the underlying worker.

### `w02-l04-cancellation-cleanup` — Lesson `w02-l04`

Sources fetched: Python Software Foundation, [Task cancellation](https://docs.python.org/3/library/asyncio-task.html#task-cancellation), [asyncio exceptions](https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.CancelledError). Cancellation raises at an opportunity; caught CancelledError generally propagates after cleanup. It derives from BaseException since Python 3.8. `task.cancelled()` is true when the coroutine actually exits through cancellation.

MC: worker catches CancelledError, records “caught”, reraises, and finally records “released”; caller catches await's cancellation. Correct order caught → released → caller; reject finally skipped, successful normal return, or caller running before finally.

MS: cancellation interrupts an await under try/finally releasing a semaphore. True: release executes; awaiting caller sees CancelledError; task ends cancelled if not suppressed. False: resource release itself clears cancellation; cancel synchronously skips coroutine cleanup.

Materials: `python-docs-coroutines-and-tasks`, `python-docs-asyncio`. No new Material needed. Specify one cancellation and synchronous release to avoid repeated-cancellation complexities.

## Full Stack Web Dev

### `w01-l03-composite-focus` — Lesson `w01-l03`

Source fetched: W3C, [APG keyboard interface, internal focus](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/#keyboard-navigation-inside-components). Roving tabindex has one item at 0, others −1; keyboard movement updates tabindex and calls focus. aria-activedescendant keeps DOM focus on a supporting container while identifying its active item; authors maintain visible focus and scrolling.

MC: three-item toolbar uses roving tabindex; right arrow moves first→second. Correct: first becomes −1, second 0, second receives focus. Reject setting every item 0, changing tabindex without moving focus, or relying on role alone to implement arrows.

MS: listbox container supports aria-activedescendant, remains focused, and changes active ID. True: DOM focus can stay on container; active descendant needs a visible indicator; code must maintain its visibility. False: selected and focused always mean the same thing; every descendant must be a Tab stop.

Material: `web-keyboard-reference`; none missing. This tests implementation strategies instead of restating Tab versus arrows.

### `w02-l02-validation` — Lesson `w02-l02`

Sources fetched: IETF, [RFC 9111 §5.2.2.4](https://www.rfc-editor.org/rfc/rfc9111.html#section-5.2.2.4), [RFC 9110 §13.1.2–13.1.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.2). Unqualified no-cache requires successful validation before reuse. If-None-Match takes precedence over If-Modified-Since; a matching condition returns 304 for GET/HEAD.

MC: stored GET has `Cache-Control: no-cache, max-age=600`, age 10, ETag. Correct: validate before reuse; reject freshness overriding no-cache, no-cache forbidding all storage, or downloading full body regardless of successful validation.

MS: conditional GET sends both matching If-None-Match and a date indicating modification. Assume request otherwise succeeds. True: ignore If-Modified-Since; matching tag leads to 304; existing body can be reused following validation. False: both validators must independently report unchanged; 304 contains a replacement representation.

Material: `web-cache-reference`; new RFC9110 Source is sufficient without a new learning Material. Distinct from the bank's header-identification/304 basics.

### `w02-l03-credential-mode` — Lesson `w02-l03`

Source fetched: WHATWG, [Fetch Standard: credentials](https://fetch.spec.whatwg.org/#concept-request-credentials-mode), [CORS protocol and credentials](https://fetch.spec.whatwg.org/#cors-protocol-and-credentials). Omit excludes credentials and ignores returned credentials; default same-origin includes them only for same-origin URLs. CORS preflight has no credentials even when eventual request uses include.

MC: a same-origin fetch uses credentials omit; server responds Set-Cookie. Correct: existing cookie excluded and returned cookie ignored; reject omit affecting only outgoing cookies, only cross-origin cookies, or CORS forcing inclusion.

MS: cross-origin include request needs preflight; assume matching cookies are otherwise permitted. True: preflight omits cookies; successful actual request may carry cookies; default same-origin would not include cross-origin cookie credentials. False: preflight must authenticate with the session cookie; include disables CORS checks.

Material: `web-fetch-reference`; none missing. Specify allowed cookie policy, no redirects, and standards-conforming Fetch; do not guarantee third-party cookie availability.

### `w02-l04-cookie-flags` — Lesson `w02-l04`

Source fetched: IETF, [RFC6265 §4.1.2.5–6](https://www.rfc-editor.org/rfc/rfc6265.html#section-4.1.2.5), [§5.4 Cookie header](https://www.rfc-editor.org/rfc/rfc6265.html#section-5.4). Secure gates secure transport; HttpOnly excludes non-HTTP APIs. The flags are independent, and HTTP request attachment is separate from script access.

MC: on an ordinary remote host, stored cookies A Secure-only and B HttpOnly-only match path/domain; an HTTP request is actually made (no HSTS upgrade). Correct: B can be sent, A cannot. Reject HttpOnly imposing TLS or Secure permitting HTTP because script cannot read A.

MS: same-origin HTTPS fetch with otherwise permitted Secure+HttpOnly cookie. True: cookie can accompany request; document.cookie does not expose it; Secure-only cookies are not inherently hidden from script. False: HttpOnly prevents authenticated actions initiated by script; Secure replaces domain/path matching.

Materials: `web-cookie-reference`, `web-fetch-reference`; none missing. Exclude localhost special treatment, modern prefix rules, SameSite, and insecure-overwrite claims that RFC6265 alone may not reflect in current browsers.

## Android Developer

All Android links below were fetched by the background research agent in this run on 11 October UTC. Publisher is JetBrains for Kotlin docs/APIs, Google for Android guidance. No new learning Materials are required.

### `kotlin-nullability-platform-types` — Lesson `w01-l01`

Sources: [Java interop](https://kotlinlang.org/docs/java-interop.html), [Null safety](https://kotlinlang.org/docs/null-safety.html). Unannotated Java reference results may infer platform types, permitting calls that fail on null. Recognized nullability annotations constrain Kotlin types; safe calls/Elvis handle null while `!!` throws.

MC: unannotated Java `readLabel()` returns null; Kotlin infers `val label=...` then reads length. Correct: compilation permits platform-type dereference but runtime fails. Reject always String?, val guaranteeing non-null, or Java null becoming empty string. This differs from existing explicit non-null assignment assertion.

MS: migration adds recognized `@Nullable` to readSubtitle, with checking enabled. True: result can be assigned String?; `?.length ?: 0` handles it; annotation communicates nullability. False: direct `.length` remains a permitted platform call; `!!` provides empty fallback.

Materials: `kotlin-docs`, `kotlin-in-action-2`. Avoid unrecognized annotations or compiler-mode ambiguities.

### `coroutinescope-vs-supervisorscope-failure` — Lesson `w02-l02`

Sources: [supervisorScope](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/supervisor-scope.html), [coroutineScope](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/coroutine-scope.html), [Deferred.await](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-deferred/await.html). Supervisor child failure alone leaves siblings running; exceptions escaping its block cancel children. Await rethrows Deferred failure. Caller cancellation still propagates.

MC: supervisor launches failing optional async and a still-suspended sibling, then calls optional.await without catch. Correct: exception escapes scope block and cancels sibling. Reject supervision converting error to null, await suppressing it, or sibling guaranteed immunity.

MS: supervisor catches optional metadata IOException around await, then awaits healthy primary child. True: failure alone does not cancel sibling; local catch supports fallback; caller cancellation still cancels scope. False: automatic retry; scope detached from parent lifetime.

Materials: `android-coroutines`, `android-coroutines-best-practices`, `kotlin-coroutines-guide`. Explicitly state sibling is suspended when failure escapes. Different from existing launch/handler versus regular-scope cases.

### `swallowed-cancellationexception` — Lesson `w02-l03`

Sources: [Android best practices](https://developer.android.com/kotlin/coroutines/coroutines-best-practices), [runCatching](https://kotlinlang.org/api/core/kotlin-stdlib/kotlin/run-catching.html), [ensureActive](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/ensure-active.html), [Job.isActive](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/-job/is-active.html). runCatching catches Throwable, including cancellation. Rethrow CancellationException; cancelled Job stays inactive, and ensureActive checks cooperative cancellation.

MC: refresh throws cancellation inside runCatching/getOrElse cached fallback, then nonsuspending analytics runs. Correct: cancellation became Result failure and synchronous code continued. Reject fallback reactivating Job, cancellation never affecting suspension, or getOrElse automatically rethrowing it.

MS: retry helper catches Exception during cancelled download. True remedies: rethrow CancellationException before broad catch; retry only expected IOException; current-context ensureActive before CPU-only work. False: convert cancellation to retryable IOException; catch Throwable resets Job.

Materials: `kotlin-coroutine-exceptions`, `kotlin-coroutines-deep-dive`, `android-coroutines-best-practices`. Do not claim a cancelled Job becomes active or that every caught cancellation yields normal Job completion.

### `standard-vs-unconfined-test-dispatcher` — Lesson `w02-l04`

Sources: [UnconfinedTestDispatcher](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-test/kotlinx.coroutines.test/-unconfined-test-dispatcher.html), [StandardTestDispatcher](https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-test/kotlinx.coroutines.test/-standard-test-dispatcher.html), [Android coroutine testing](https://developer.android.com/kotlin/coroutines/test). Top-level Unconfined runTest children enter eagerly but can suspend. Standard default launch queues work. runCurrent runs current-time tasks; shared scheduler controls injected dispatchers.

MC: runTest(UnconfinedTestDispatcher), phase=0; top-level default launch sets1, delay100, sets2; immediate assert2. Correct phase1: eager entry stops at delay. Reject phase0, eager completion, or disabling virtual time.

MS: Standard launch appends started, delay100, appends finished; call runCurrent. True: started present; finished absent; advanceUntilIdle runs finite remaining work; shared testScheduler permits unified control. False: runCurrent advances all future delays; Thread.sleep advances virtual time.

Materials: `android-coroutines`, `kotlin-coroutines-guide`. Avoid UNDISPATCHED launch exception, unsupported general scheduling order, and asserting eager entry for every nested launch.

## Full Stack .NET Developer

All .NET links below were fetched by the background research agent this run on 11 October UTC. Publisher: Microsoft Learn or Microsoft .NET Blog. No missing required learning Materials identified.

### `boxing-hidden-interface-conversion` — Lesson `w01-l01`

Sources: [Boxing/unboxing](https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/types/boxing-and-unboxing), [ReferenceEquals (.NET10)](https://learn.microsoft.com/en-us/dotnet/api/system.object.referenceequals?view=net-10.0). Value-type object/interface conversion boxes a copy. ReferenceEquals compares identity, and independent value arguments are independently boxed.

MC: `int n=8; object cached=n;` print ReferenceEquals(n,n) then ReferenceEquals(cached,cached). Correct False then True. Reject numeric equality implying identity, reused object requiring new boxes, or all arguments sharing cached box.

MS: `int n=12; IComparable comparable=n; object alias=comparable; object separate=n;`. True: interface conversion boxes; alias shares comparable's box; separate has a different box. False: alias reference assignment boxes again; equal numeric values imply identity. Different from existing boxing mutation/unboxing cases.

Materials: `csharp-docs`, `csharp-in-depth`. Distinguish object reference assignment from a fresh value-type conversion.

### `linq-deferred-multiple-enumeration` — Lesson `w01-l03`

Source: [Introduction to LINQ Queries](https://learn.microsoft.com/en-us/dotnet/csharp/linq/get-started/introduction-to-linq-queries). Where is deferred streaming; OrderBy deferred nonstreaming; ToList/ToArray evaluate and store results. Re-enumerating the original query repeats execution.

MC: `checks=0; q=new[]{1,2,3}.Where(x=>{checks++;return x>1;}); saved=q.ToArray(); foreach(var x in saved){}; again=q.ToArray();` Correct final checks6. Reject query construction executing, saved enumeration rerunning predicate, or materialization permanently caching q.

MS: deferred OrderBy wraps custom enumerable recording source visits; two foreach loops enumerate it. True: construction makes no visits; source traverses each enumeration; sorting reads all input before first result. False: first traversal caches later results; deferred sorting yields before reading all input.

Materials: `csharp-docs`, `csharp-in-depth`. Use Where/foreach rather than Select().Count(), whose optimization can skip selector work. Distinct from existing network Any/Count/foreach example.

### `sync-over-async-context-deadlock` — Lesson `w02-l01`

Source: [.NET Blog ConfigureAwait FAQ](https://devblogs.microsoft.com/dotnet/configureawait-faq/). Default await may capture context; blocking its execution thread can deadlock. ConfigureAwait(false) affects that await, does not change nested awaits, and does not force completed tasks to switch threads.

MC: WPF UI blocks with `LoadAsync().ConfigureAwait(false).GetAwaiter().GetResult()`; LoadAsync normally awaits incomplete I/O and needs UI continuation. Correct deadlock remains possible. Reject outer configuration changing inner await, GetResult yielding asynchronously, or background I/O guaranteeing continuation progress. Specify blocked UI thread without message pumping.

MS: UI-entered library first awaits Task.CompletedTask.ConfigureAwait(false), then normally awaits incomplete I/O. True: first can stay synchronously on UI; second can capture UI context; awaiting caller avoids blocking that thread. False: first permanently disables later context capture; guarantees thread-pool migration.

Materials: `dotnet-async`, `cleary-blog`, `aspnetcore-diagnostic-scenarios`. Do not generalize WPF deadlock to context-free ASP.NET Core.

### `span-memory-arraypool-ownership` — Lesson `w02-l03`

Sources: [Memory/Span usage](https://learn.microsoft.com/en-us/dotnet/standard/memory-and-spans/memory-t-usage-guidelines), [ArrayPool.Return (.NET10)](https://learn.microsoft.com/en-us/dotnet/api/system.buffers.arraypool-1.return?view=net-10.0), [ArrayPool.Rent (.NET10)](https://learn.microsoft.com/en-us/dotnet/api/system.buffers.arraypool-1.rent?view=net-10.0). Borrowed memory cannot be used by a Task-returning consumer after Task termination. Return relinquishes pool ownership, prohibits subsequent use, and occurs once. Rental can be larger than requested and not zeroed.

MC: rent array; slice Memory; start borrowed-buffer SendAsync; return rental before awaiting. Correct: retain until send finishes, return in finally afterward. Reject Memory slice copying, creating Task ending lease, or managed references making returned rental safe.

MS: asynchronous parser consumes ReadOnlyMemory until its Task completes. True: retain rental during processing; read-only view does not extend lease; return once in finally after await handles cleanup. False: view prevents other renters mutating backing array; borrowed view may be retained after Task completes.

Material: `dotnet-memory-and-spans`. Cancellation request alone is not Task termination. Distinct from simple synchronous Span usage and general ownership rules.

## Execution evidence

Manually evaluated then executed Agentic snippets on installed CPython **3.11.15**, 11 October UTC. Results: default first/third `['a','c']`, supplied `['b']`, identity true; sentinel preserved supplied empty-list identity and independent omitted calls; nonlocal closure returned 9; default-captured ordinary functions returned `[0,1,2]`; cancellation events `['caught','released','caller']`, cancelled true; finally-only release preceded caller cancellation; to_thread executed on a different thread from loop. No timing-based expectations used. Web scenarios were derived from normative algorithms; no browser execution performed.

Executed boxing/interface and Where/ToArray examples using installed **.NET SDK 10.0.201**, target net10.0, in a temporary directory outside the repository. Results: ReferenceEquals on integer arguments False, cached reference True; interface alias identity True, separate box identity False; predicate count 6. Expected CA2013 warnings reinforced the intentional value-type ReferenceEquals trap. WPF context-dependent and buffer-ownership failure scenarios were checked against official contracts rather than executed. No Kotlin compiler was available on PATH; Kotlin outcomes were manually derived from fetched APIs, with scheduler assumptions stated above.

Final inventory check: all **16 Concept sections** present, **34 cited primary-source URLs**, and every recommended Material ID resolves in a current `v2026-10-10` Syllabus. Source dates record this run's original factual research, not link availability or later revalidation.
