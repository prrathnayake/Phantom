# Core Agent Memory Engine

This system exists purely for **the coding agent** to persist its intelligence context securely across sessions without destroying its context window limits.

You are treating this repository as a Graph Data-Structure.
AGENTS.md -> .codex_memories/_agent_rules.md -> .codex_memories/project_state.md -> .codex_memories/system_prompt.md -> .codex_memories/daily_summary.md -> .codex_memories/YYYY-MM-DD/revival_summary.md -> .codex_memories/YYYY-MM-DD/task_log.md

## Start of Task Checklist
1. **Mandatory Load:** Trace from `AGENTS.md` and read `.codex_memories/_agent_rules.md` (this file).
2. **State Load:** Read `.codex_memories/project_state.md` to see stable facts and active threads.
3. **Protocol Load:** Read `.codex_memories/system_prompt.md` and `.codex_memories/daily_summary.md`.
4. **Daily Hub Creation:** If a `.codex_memories/YYYY-MM-DD/` folder for today does not exist, create it.
5. **Session Revival:** On the *first task of a new day*, read yesterday's folder. Write a `revival_summary.md` inside *today's* folder to bootstrap context.

## Navigation & Work Logic
6. **Architectural Guardrails:** Target project architecture is in `/ARCHITECTURE.md` and UI design is in `/DESIGN.md`. Do NOT use these files for your AI engine memory. They are strictly for the application you are building.
7. **Dynamic Discovery:** Whenever you enter a code directory, look for a `folder_map.md`. If missing, generate one so future agents can parse the directory structure without reading every dense codebase file.

## End of Task Checklist
8. **Conversations:** Inside today's `YYYY-MM-DD/` folder, create or append to `message_pairs.md`. Log the exact user prompt and a tight summary of your final response.
9. **Task Log:** Inside today's `YYYY-MM-DD/` folder, create or append to `task_log.md`. Log what specifically you coded, debugged, and any blockers hit during this run.
10. **Final Summarization:** Maintain an `end_of_day_summary.md` in today's folder. When wrapping up your shift, aggregate your task logs into this file so tomorrow's agent can read it quickly.
11. **State Update:** Update your specific agent thread in `.codex_memories/project_state.md`.

## Memory Root
- Write all reusable session memory only under `.codex_memories/`.
- Do not create or use any alternate memory root.
