# Study Session

> Complete study session workflow from start to summary.

## Flow

```
Start Session → Adaptive Queue → Open Question → Answer → Submit
                                                              ↓
                                                        Explanation
                                                        Mastery Update
                                                        Review Schedule
                                                        Recommendation
                                                              ↓
                                                        Next Question
                                                              ↓
                                                        Session Summary
```

## Start Session Page (`/study/start`)

- Select enrollment (if multiple active)
- Choose session intent:
  - Mixed practice (new + reviews)
  - Review session (due reviews only)
  - Learn new concepts
  - Practice weak areas
- Choose question count (5, 10, 15, 20)
- Calls `POST /study-sessions` to create session

## Study Session Page (`/study/[sessionId]`)

### Features

- **Adaptive queue**: Loaded from `GET /study-sessions/{id}/adaptive-queue`
- **Question rendering**: Dispatches to the correct component by `question_type`
- **Confidence slider**: 0-100% with labels (Very low → Very high)
- **Hints**: Tiered hints that reduce mastery gain when used
- **Timer**: Tracks time per question, can pause/resume
- **Progress bar**: Current question / total questions
- **Keyboard shortcuts**:
  - `1-4`: Quick answer for multiple choice
  - `Enter`: Submit answer (or go to next question after submission)
  - `H`: Reveal next hint
- **Abandon**: Confirmation dialog before abandoning

### Submission

Calls `POST /questions/{id}/submit` with:
- Answer (format depends on question type)
- Answer type (multiple_choice, code, free_response)
- Confidence (0.0-1.0)
- Time spent (seconds)
- Hint used (boolean)
- Hint tiers used (array)

### Result Display

After submission, shows:
- Correctness banner (correct, partially correct, incorrect)
- Explanation text
- Mastery score update (combined, memory, durable)
- Evidence count
- Review schedule (interval, priority)
- Recommendation

## Session Summary (`/study/[sessionId]/summary`)

Calls `GET /study-sessions/{id}/summary` and displays:
- Questions answered
- Accuracy
- Time spent
- Mastery gained
- Weak/strong concepts
- Recommendations
- Review schedule
- Achievements unlocked
- "Start another session" + "Back to dashboard" buttons
