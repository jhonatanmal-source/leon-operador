# Permissions Matrix

## Agent Permissions
| Role | Read | Edit | Bash | Task | Skill |
|------|------|------|------|------|-------|
| Engineering Director | allow | ask | allow | allow | allow |
| Senior Software Engineer | allow | ask | allow | allow | allow |
| Software Architect | allow | deny | allow | allow | allow |
| QA Test Engineer | allow | ask | allow | allow | allow |
| Security Engineer | allow | deny | ask | allow | allow |
| Engineering Reviewer | allow | deny | allow | allow | allow |
| Release Manager | allow | deny | allow | allow | allow |
| Trading Systems Engineer | allow | deny | allow | allow | allow |
| DevOps Engineer | allow | ask | ask | allow | allow |
| Documentation Engineer | allow | ask | allow | allow | allow |
| Observability Engineer | allow | ask | allow | allow | allow |
| Performance Engineer | allow | ask | allow | allow | allow |
| Refactoring Specialist | allow | ask | allow | allow | allow |
| AI Integration Engineer | allow | ask | allow | allow | allow |

## Default
- Read: allow (all agents)
- Edit: ask (unless read-only role)
- Bash: ask (unless explicitly allowed)
