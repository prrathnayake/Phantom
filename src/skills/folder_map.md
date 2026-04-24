# Directory: src/skills (Legacy)

Legacy agent skills. These predate the `src/agent/skills/` framework and are kept for backward compatibility.

| File | Purpose |
| --- | --- |
| `risk_assessment.py` | LLM-powered risk assessment skill |
| `vulnerability_check.py` | LLM-powered vulnerability analysis skill |

## Note

New skills should be added to `src/agent/skills/` instead, which provides `BaseSkill`, `SkillRegistry`, and standardized `SkillResult`/`SkillMetadata` containers.
