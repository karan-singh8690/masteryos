# Question Flow

> How questions are rendered, answered, and evaluated.

## Question Types

| Type | Component | Answer Format | Notes |
|---|---|---|---|
| `multiple_choice` | MultipleChoice | `{ choice: "id" }` | Single answer radio |
| `multiple_select` | MultipleSelect | `{ choices: ["id1", "id2"] }` | Multiple checkboxes |
| `true_false` | TrueFalse | `{ answer: true/false }` | Radio buttons |
| `ordering` | Ordering | `{ order: ["id1", "id2", ...] }` | Up/down buttons |
| `fill_blank` | FillBlank | `{ blank_0: "text" }` | Inline input |
| `code_output` | CodeOutput | `{ output: "text" }` | Textarea |
| `short_answer` | ShortAnswer | `{ text: "..." }` | Textarea |
| `numerical` | NumericalAnswer | `{ value: "123.45" }` | Number input |

## QuestionRenderer

The `QuestionRenderer` component dispatches to the correct question type component based on `question.question_type`:

```tsx
<QuestionRenderer
  question={question}
  answer={answer}
  onAnswerChange={setAnswer}
  submitted={submitted}
  correctAnswer={submitResult?.correctAnswer}
/>
```

## Never Expose Correct Answers

The backend NEVER returns correct answers in the question response (`GET /questions/{id}`). Correct answers are only revealed after submission, in the `SubmitAnswerResponse`.

## Hints

Questions can have tiered hints (stored in `question.metadata.hint_tiers`):
- Each tier reveals progressively more information
- Using hints reduces mastery gain
- The `HintDisplay` component manages hint state
- Keyboard shortcut: `H` to reveal next hint

## Confidence Slider

The `ConfidenceSlider` component lets learners rate their confidence (0-100%):
- 0-20%: Very low
- 20-40%: Low
- 40-60%: Medium
- 60-80%: High
- 80-100%: Very high

Confidence is sent with the submission and used by the mastery algorithm.

## Accessibility

- All question types use semantic HTML (`<fieldset>`, `<legend>`, `<input>`)
- Radio/checkbox inputs have proper labels
- ARIA labels for screen readers
- Keyboard navigation (Tab, Space, Enter)
- Correct/incorrect feedback has `role="status"` with `aria-live="polite"`
