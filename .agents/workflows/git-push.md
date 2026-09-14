---
description: Stage, commit with descriptive message in English, and push changes to remote repository
---

Execute the procedure to commit and push changes to the remote repository:

1. Check modified files using `git status` and read the latest entry from `HISTORY.md` to formulate a concise, clear commit message written in English.
2. Stage all changes:
   ```bash
   git add .
   ```
3. Commit the changes with the formulated message (the commit message must be in English):
   ```bash
   git commit -m "<concise description in English>"
   ```
4. Push the changes to the remote branch:
   ```bash
   git push
   ```
5. Confirm successful execution to the user, specifying the commit hash and the commit message.

