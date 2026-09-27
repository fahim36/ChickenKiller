# Learning App

Daily interview-prep games, modeled on LinkedIn Games. Every Stack releases one numbered Daily Challenge a day, the same for everyone, and Learners keep a Streak by playing it. Past Challenges stay playable in the Archive. Alongside the Challenges, each Stack has a researched Syllabus that Learners work through one Lesson at a time. Every question a Learner misses is explained and can be re-tested.

## Language

### People

**Learner**:
A person with an account, joined by the Admin's invitation, who studies one or more Active Stacks.
_Avoid_: User, student

**Active Stack**:
A Stack a Learner has chosen to study. A Learner can have any number of Active Stacks, picked from every published Stack. Each one has its own Daily Challenges, Lesson path, Streak and progress. Deactivating a Stack keeps its progress.
_Avoid_: Subscription, current course, enrolment

**Admin**:
The person who writes Syllabus Updates and Upcoming Challenges from their own terminal with Claude Code, and who invites Learners. The Admin is a Learner too.
_Avoid_: Owner, maintainer

**Invitation**:
The Admin's permission for one email address to join. It is pending until that person first signs in, which makes them a Learner. Anyone signing in without one is refused.
_Avoid_: Invite code, allowlist entry

### Content

**Stack**:
A named study track, such as "Agentic AI Engineer", that a Learner can activate from the Admin's published list. Each Stack has exactly one current Syllabus, one Question Bank and one run of Daily Challenges.
_Avoid_: Track, course, path

**Stack Request**:
A Learner's request for a Stack that doesn't exist yet. It waits in a queue until the Admin runs a Syllabus Update for it.
_Avoid_: Suggestion, custom stack

**Syllabus**:
The ordered sequence of Weeks and Lessons for one Stack, at a specific version. A new version replaces the old one. The Question Bank is not part of the Syllabus and is never replaced.
_Avoid_: Curriculum, plan, roadmap

**Week**:
A named group of consecutive Lessons and Milestones inside a Syllabus. It is for display only and never controls unlocking.
_Avoid_: Phase, module, unit

**Lesson**:
One topic-sized unit of a Syllabus: its topics, its Materials, and its Lesson Quiz. Lessons unlock one at a time.
_Avoid_: Session, day, module, chapter

**Milestone**:
A hands-on task in a Week, such as a build or a job-hunt action. The Learner ticks it off themselves; it is never quizzed and never blocks unlocking.
_Avoid_: Project, assignment, task

**Updated Lesson**:
A Lesson a Syllabus Update added or changed after the Learner had already passed it: a Completed Lesson that differs from the version it was completed in, or a new Lesson behind the Learner's position. The Learner's progress on it is kept; its new Questions go into the Learner's Review. It never locks anything.
_Avoid_: Changed lesson, outdated lesson

**Material**:
An external learning reference (a course, doc, book, video or paper) attached to a Lesson or a Question, for a Learner who wants to learn more.
_Avoid_: Resource, link, reference

**Source**:
Where a Question's content came from: URL, title, publisher, the date it was accessed, and the claim the Question relies on. Every Question has at least one, and all were accessed in the run that wrote the Question. A Source is for checking a Question; a Material is for learning.
_Avoid_: Citation, reference, Material

**Question**:
A single item a Learner answers: either multiple choice or a written answer. Each Question has a permanent ID, a correct answer, an Explanation, at least one Source, and optionally Materials. Once written it is never edited or deleted, only retired.
_Avoid_: Item, problem, card

**Question Bank**:
Every Question ever written for one Stack. It only grows. Most Questions are also tagged to a Lesson. Daily Challenges, Lesson Quizzes, Retakes and Review all draw from it.
_Avoid_: Pool, question set

**Retired Question**:
A Question taken out of use because it is wrong or out of date, with a reason and optionally the Question that replaces it. It stays in the Question Bank and the Archive but can no longer be answered or drawn.
_Avoid_: Deleted question, archived question, deprecated question

**Concept**:
The single idea a Question tests. Questions that test the same Concept are siblings, and a Retake always uses a sibling rather than the original Question. A new Question that repeats an existing Concept is allowed but flagged when content is checked.
_Avoid_: Topic, skill, tag

**Model Answer**:
The key points a written answer must contain to pass. Grading checks a Learner's answer against it.
_Avoid_: Rubric, reference answer, expected answer

**Explanation**:
Why the correct answer is correct, shown to the Learner after they miss a Question.
_Avoid_: Solution, feedback, hint

**Syllabus Update**:
A research run by the Admin, using Claude Code in a terminal, that produces a new version of a Stack's Syllabus. It can add Questions to the Question Bank, retire them, or re-tag them to a different Lesson, but never edits or deletes one.
_Avoid_: Sync, refresh, regeneration

### Daily Challenges

**Day**:
A calendar day in UTC. Every day boundary in the app, for Daily Challenges and Streaks alike, is 00:00 UTC.
_Avoid_: Local day, calendar day

**Daily Challenge**:
A Stack's set of three Questions (two multiple choice, one written) for one Day, numbered from the Stack's launch: "Agentic AI Engineer #40". Every Learner gets the same one, released at 00:00 UTC. Only a Learner's first try is scored; the Explanation and Sources show after each answer. Replaying it afterwards is for learning only and changes nothing: not the score, the Streak or Missed Questions.
_Avoid_: Drop, daily quiz, puzzle

**Upcoming Challenge**:
A Daily Challenge the Admin has written and committed but that hasn't been released yet. It can still be edited until its Day begins; after that it is frozen. A Day with no Upcoming Challenge written has no Daily Challenge.
_Avoid_: Challenge schedule, draft, queued challenge

**Archive**:
Every released Daily Challenge of a Stack, back to #1. Any Learner with that Active Stack can play any of them. A first play is scored as usual but never counts toward a Streak; a replay is for learning only. Retired Questions appear in it but can't be answered.
_Avoid_: History, backlog, past games

**Catch-up**:
The Daily Challenges in the Archive a Learner hasn't played, across their Active Stacks. Working through it is optional and never blocks anything.
_Avoid_: Backlog, missed challenges, debt

**Result Card**:
A shareable summary of a Learner's score on one Daily Challenge, showing how they did on each Question but not the Questions or answers: "Agentic AI Engineer #40 · 26 Sep · 2/3 ✅❌✅". A Question whose first try couldn't be graded has its own mark.
_Avoid_: Share image, score card

**Streak**:
For one Active Stack, the number of consecutive Days on which the Learner played that Day's Daily Challenge, finishing it on that Day. A Day with no Daily Challenge is skipped, and today's, until played, doesn't break it. Breaking it resets the count and nothing else.
_Avoid_: Chain, run

### Progress

**Lesson Quiz**:
The six Questions (four multiple choice, two written) a Learner answers to complete a Lesson. It can be taken as soon as the Lesson unlocks, with or without studying first. It skips Questions the Learner has already seen.
_Avoid_: Test, exam, lesson test

**Pass Mark**:
The minimum score, 80%, a Lesson Quiz or Placement Quiz needs. Below it, the Learner takes a fresh Lesson Quiz instead of Retakes.
_Avoid_: Threshold, passing grade

**Placement Quiz**:
A quiz covering a whole Week. Meeting the Pass Mark counts every Lesson in that Week as a Completed Lesson.
_Avoid_: Skip test, entrance exam, test-out

**Dispute**:
A Learner's challenge to how a written answer was graded. It waits for the Admin's decision, and until then the answer counts as missed.
_Avoid_: Appeal, report, complaint

**Missed Question**:
A Question the Learner answered wrongly, or left unanswered in a quiz they submitted. A Daily Challenge the Learner never played, or replayed, creates no Missed Questions.
_Avoid_: Mistake, error, wrong answer

**Retake**:
A second attempt at a Missed Question, made after reading its Explanation.
_Avoid_: Retry, redo

**Completed Lesson**:
A Lesson whose Lesson Quiz met the pass mark and whose Missed Questions have all been answered correctly on Retake.
_Avoid_: Finished, passed, done

**Review**:
An optional queue of Questions to practise, in sets of up to 10, whenever the Learner likes. Missed Questions come first, then spaced repeats from Completed Lessons and played Daily Challenges, across all Active Stacks. A Missed Question leaves it once answered correctly on three different Days since it was last missed. It has no rounds or timers and never blocks anything.
_Avoid_: Daily Review, revision, daily quiz

**Weak Concept**:
One of the Concepts the Learner has missed most often, shown with a link to the Lesson that teaches it.
_Avoid_: Gap, weakness, problem area

**Unlocked Lesson**:
The next Lesson after the Learner's last Completed Lesson in a Stack. Only completion sets the pace; nothing else locks it. If a Syllabus Update removes that Completed Lesson, it is the next Lesson after it that is still in the Syllabus.
_Avoid_: Available, open, scheduled

**Locked Lesson**:
Any Lesson after the Unlocked Lesson.
_Avoid_: Unavailable, hidden
