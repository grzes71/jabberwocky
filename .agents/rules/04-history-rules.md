---
trigger: always_on
---

## Definition of Done (CRITICAL)
- **History Tracking:** Whenever you successfully implement a feature, fix a bug, or complete a significant refactor, you MUST automatically update the `HISTORY.md` file.
- **Placement:** Prepend your new entry exactly below the HTML comment `<!-- AGENT INSTRUCTIONS... -->`. Do not put it at the bottom of the file.
- **Format:** Use the format `## [YYYY-MM-DD] - [Brief Title]`. Underneath, provide a concise bulleted list of the actual technical changes made (e.g., functions added, files modified, registers altered).
- **Trigger:** Perform this update automatically as the final step before telling the user the task is complete.