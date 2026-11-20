# CLAUDE.md

@AGENTS.md

## Claude Code specifics

- Load the skill that matches the area before you edit it:
  - risk logic: `.claude/skills/risk-engine/SKILL.md`
  - external APIs: `.claude/skills/provider-integration/SKILL.md`
  - map, heatmap, slider: `.claude/skills/map-performance/SKILL.md`
- For any task bigger than one file, write a short plan first (files to touch, tests to add) and follow the milestone order in AGENTS.md section 5.
- Run `make check` before you report a task done. Paste the failing output if it doesn't pass. Never claim it passed without running it.
- Don't run tests that hit the real network. Provider tests use recorded fixtures in `backend/planner/tests/fixtures/`.
- To refresh fixtures, run `uv run python scripts/record_fixtures.py` only when the human asks. It needs real API keys.
- Ask before you add a dependency, change a threshold, or edit anything in `docs/01-SPEC.md`.
