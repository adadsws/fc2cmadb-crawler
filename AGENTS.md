# AGENTS.md

## Project-Specific Rules

- Treat the current contents of the whole project as the latest correct state.
- Do not restore or revert any project file to an older version unless the user explicitly asks for it.
- Do not revert, overwrite, or discard files changed by the user or by another process.
- If unrelated user changes are present, leave them untouched.
- If committing is requested and unrelated user changes are present, commit those changes separately from Codex-authored changes.
- If user changes affect the current task, work with them instead of undoing them. Ask only when the task cannot be completed safely without clarification.
