# Learning App

A self-paced study app. Learners work through a researched, regularly updated Syllabus one Lesson at a time. Each Lesson ends with a quiz, and every question a Learner misses is explained and re-tested.

## Language

### People

**Learner**:
A person with an account, joined by the Admin's invitation, who studies one Active Stack at a time.
_Avoid_: User, student

**Active Stack**:
The one Stack a Learner is currently studying. Switching to another Stack keeps the progress on each one separately.
_Avoid_: Current course, enrolment

**Admin**:
The person who runs Syllabus Updates from their own terminal with Claude Code, and who invites Learners. The Admin is a Learner too.
_Avoid_: Owner, maintainer

**Invitation**:
The Admin's permission for one email address to join. It is pending until that person first signs in, which makes them a Learner. Anyone signing in without one is refused.
_Avoid_: Invite code, allowlist entry

### Content

**Stack**:
A named study track, such as "Agentic AI Engineer", that a Learner picks during onboarding from the Admin's published list. Each Stack has exactly one current Syllabus.
_Avoid_: Track, course, path

**Stack Request**:
A Learner's request for a Stack that doesn't exist yet. It waits in a queue until the Admin runs a Syllabus Update for it.
_Avoid_: Suggestion, custom stack

**Syllabus**:
The ordered sequence of Weeks and Lessons for one Stack, at a specific version.
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
A Lesson a Syllabus Update added or changed after the Learner had already passed it. The Learner's progress on it is kept; its new Questions go into the Learner's Daily Review.
_Avoid_: Changed lesson, outdated lesson

**Material**:
An external learning reference (a course, doc, book, video or paper) attached to a Lesson or a Question.
_Avoid_: Resource, link, reference

**Question**:
A single item a Learner answers: either multiple choice or a written answer. Each Question has a correct answer, an Explanation and Materials.
_Avoid_: Item, problem, card

**Question Bank**:
All the pre-written Questions for one Lesson, produced by a Syllabus Update. Lesson Quizzes, Retakes and Review Rounds all draw from it.
_Avoid_: Pool, question set

**Concept**:
The single idea a Question tests. Questions that test the same Concept are siblings, and a Retake always uses a sibling rather than the original Question.
_Avoid_: Topic, skill, tag

**Model Answer**:
The key points a written answer must contain to pass. Grading checks a Learner's answer against it.
_Avoid_: Rubric, reference answer, expected answer

**Explanation**:
Why the correct answer is correct, shown to the Learner after they miss a Question.
_Avoid_: Solution, feedback, hint

**Syllabus Update**:
A research run by the Admin, using Claude Code in a terminal, that produces a new version of a Stack's Syllabus.
_Avoid_: Sync, refresh, regeneration

### Progress

**Lesson Quiz**:
The six Questions (four multiple choice, two written) a Learner answers to complete a Lesson. It can be taken as soon as the Lesson unlocks, with or without studying first.
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
A Question the Learner answered wrongly or left unanswered.
_Avoid_: Mistake, error, wrong answer

**Retake**:
A second attempt at a Missed Question, made after reading its Explanation.
_Avoid_: Retry, redo

**Completed Lesson**:
A Lesson whose Lesson Quiz met the pass mark and whose Missed Questions have all been answered correctly on Retake.
_Avoid_: Finished, passed, done

**Daily Review**:
The up-to-three Review Rounds a Learner owes on one calendar day in their own time zone. Missed Questions come first, and Questions from Completed Lessons fill the rest. Rounds not done by the end of the day are dropped, but their Questions go first into the next day's rounds.
_Avoid_: Daily quiz, revision, streak quiz

**Review Round**:
One sitting of a Daily Review: up to 10 Questions. Round 1 opens the first time the Learner uses the app that day. Each later round opens four hours after the previous one is finished and becomes pending two hours after that.
_Avoid_: Session, review session, sitting

**Pending Review Round**:
A Review Round whose two-hour optional period has run out. While one exists, no new Lesson unlocks.
_Avoid_: Overdue round, due round, late round

**Locked Lesson**:
Any Lesson after the Unlocked Lesson. While a Pending Review Round exists, the Unlocked Lesson is locked too.
_Avoid_: Unavailable, hidden

**Streak**:
The number of consecutive days on which the Learner finished their whole Daily Review. Breaking it resets the count and nothing else.
_Avoid_: Chain, run

**Weak Concept**:
One of the Concepts the Learner has missed most often, shown with a link to the Lesson that teaches it.
_Avoid_: Gap, weakness, problem area

**Unlocked Lesson**:
The next Lesson after the Learner's last Completed Lesson, available when there is no Pending Review Round. Pacing is set only by completion, never by the calendar.
_Avoid_: Available, open, scheduled
