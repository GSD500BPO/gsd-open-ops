# Quizzes

Multiple-choice question banks, one key per module slug (the same slugs as [`../curriculum/modules.json`](../curriculum/modules.json)).

| File | Modules | Questions |
|---|---|---|
| `_quiz-ops.json` | welcome, role-and-kpis, scrum-trello, crm-process, qa-scorecard | 20 |
| `_quiz-calls.json` | the 9 call modules + graduation-333 | 35 |
| `_quiz-zoho.json` | the 8 Zoho modules | 26 |

Each question: `q`, `type` (`multiple_choice`), `options`, `correct` (the exact option text) and `explanation` (shown after answering: the *why* is the teaching).

## How to use
- **Zoho Learn / LMS:** import each module's array as a question bank; use the pass marks from `modules.json`.
- **Google Forms / Typeform:** one form per module; paste `explanation` as answer feedback.
- **Your own app:** load the JSON, shuffle `options`, compare against `correct`.

## How to adapt
Write questions about decisions, not definitions ("A prospect says X. What do you do?"). Every wrong option should be a mistake a real new hire makes.
