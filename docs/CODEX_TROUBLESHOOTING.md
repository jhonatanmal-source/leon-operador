# Codex Troubleshooting

## Common Issues

### Skill not loading
- Verify SKILL.md exists with correct name/description
- Check permissions
- Ensure unique skill name

### Command not recognized
- Verify .md file in commands/
- Check frontmatter has description
- Restart TUI

### Validator failing
- Read error message
- Fix the specific issue
- Rerun validator

### Checkpoint corrupted
- Use last valid checkpoint
- Rebuild from progress file
- Verify with git status

## Recovery
1. `/leon-status` to check state
2. `/leon-retomar` to resume
3. If stuck, read checkpoint and continue manually
