---
description: Create or checkout branch, stage, commit using Conventional Commits in English, and push to remote repository
---

Execute the procedure to commit and push changes to the remote repository:

> **Requirement**: This workflow MUST be invoked with a `<branch name>` parameter (e.g. `/git-push feat/initial-release`). If no branch name is provided, DO NOT proceed — ask the user to specify the target branch name.

1. **Validate Branch Name**:
   Verify that the `<branch name>` parameter was provided. If missing, ask the user to provide it.

2. **Create / Switch Branch**:
   Check the current branch:
   - If not already on `<branch name>`, check if it exists:
     ```bash
     git checkout -B <branch name>
     ```
     *(or `git checkout -b <branch name>` if creating new, or `git checkout <branch name>` if switching)*.

3. **Formulate Commit Message (Conventional Commits ONLY)**:
   Check modified files using `git status` and read the latest entry from `HISTORY.md`. Formulate a commit message strictly adhering to the **Conventional Commits** specification in English:
   - Structure: `<type>(<scope>): <concise imperative description in English>` (scope is optional, e.g. `<type>: <description>`)
   - Allowed types: `feat`, `fix`, `refactor`, `perf`, `docs`, `test`, `chore`, `ci`, `build` (append `!` for breaking changes, e.g. `feat!: ...`)
   - Examples:
     - `feat(gameover): update victory and defeat poems`
     - `fix(collision): resolve player boundary check`
     - `chore(texts): bump version in scroll.txt`

4. **Stage All Changes**:
   ```bash
   git add .
   ```

5. **Commit the Changes**:
   ```bash
   git commit -m "<type>(<optional-scope>): <concise description in English>"
   ```

6. **Push to Remote with Upstream**:
   ```bash
   git push -u origin <branch name>
   ```

7. **Confirmation**:
   Confirm successful execution to the user, specifying the target branch, commit hash, and commit message.

