# Mock interviews use learner-confirmed free-tier Gemini keys

Mock Interview AI feedback uses only the learner's own Gemini key, explicitly enabled for interviews and confirmed as belonging to a Free Tier project with billing disabled. Unlike legacy grading, interviews do not fall back to an Admin key or CLI: shared quota and hidden fallback consumption conflict with the agreed free-quota constraint. The confirmation is attestation, not a machine-enforced billing guarantee; exhausted quota preserves the response and offers reviewed self-review, with AI feedback retried later.
