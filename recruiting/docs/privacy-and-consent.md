# Privacy and consent

You are processing personal data (faces, voices, phone numbers, CVs). Check the law where you and your candidates are (for example Colombia's Ley 1581 de 2012, GDPR in the EU, CCPA in California).

What the code does for you:
- Raw videos and CVs go to a **private** bucket. Reviewers get signed links that expire.
- Local copies used for scoring are deleted after scoring (when live).
- Nobody appears on a public page until they reply YES to an explicit question that says what is shown (first name + initial, video, scores) and that they can ask to be removed.
- Public file names are a salted hash of the phone (`TALENT_REEL_SALT`), never the phone itself.
- Clients see an alias and scores, never phone, email or full name.
- STOP is permanent.

What you still have to do:
- Publish a privacy notice and link it from the apply page and the WhatsApp welcome.
- Set a retention period (e.g. delete rejected candidates' media after 6 months) and run it.
- Handle removal requests within the legal deadline.
- Never commit `state.json`, `events.jsonl`, `media/` or `logs/` (they are in `.gitignore`).
