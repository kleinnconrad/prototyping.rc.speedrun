# Project Context
This project is a hardware project at a hobbyist level. The target audience consists of technically interested individuals with basic engineering competencies. All communication must strictly adhere to this technical level.

# Documentation Guidelines
* **Language:** The English language must be used for all documentation within the repository.
* **Formatting:** Bullet points (lists for structuring) are permitted and explicitly encouraged to increase readability.
* **Capitalization:** Use upper case in Markdown files only if the word is the first word in a sentence, a proper name, or an acronym (e.g., "ADR"). Apply this sentence case rule to headings, list items, and table entries.
* **Table of Contents:** As soon as a Markdown file contains more than one heading, a Table of Contents is strictly required at the beginning.
* **Emojis:** Emojis are to be avoided throughout the entire repository.

# Language Style
* **Objectivity:** The writing style must be strictly objective, precise, and sober.
* **Adjectives:** The unnecessary enumeration or redundant stringing together of adjectives (e.g., "the beautiful, exciting, great...") is to be strictly avoided.
* **Word Choice:** Filler words and superlatives are to be omitted unless they are absolutely necessary for technical understanding.
* **Phrases:** The use of phrases, idioms, or metaphorical paraphrases is prohibited.

# Version Control & Committing
* **Commits:** Never run `git commit` or `git push`, and never commit or push through GitHub tools or APIs, without the user's explicit approval of that specific commit. Prepare the changes locally, show the diff and the proposed commit message, and wait for approval. Approval of one commit does not extend to later commits.

# CAD rules
* **Inside of the bulkheads:** The inside of the lower and the upper bulkhead is verified with test prints (diff and pinion installed) and must not be changed: gear cavities, floor opening, bearing seats, lips, rib, pinion pocket, all holes, counterbores, the recesses for the bosses and the bosses. Shape changes apply to the outer side only. A change to the inside requires an explicit request of the owner for that specific change.
* **Check:** The generators of the bulkheads compare each part with the verified inside (functional check). A bulkhead change is not committed if this check fails.
