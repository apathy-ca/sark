# SARK Improvement Plan - Task Files

**Welcome to the SARK Improvement Project!**

This directory contains individual task files for each team member working on the 8-week repository improvement plan.

---

## Team Members - Find Your Tasks

| Role | Task File | Tasks | Days |
|------|-----------|-------|------|
| **Documenter** | [DOCUMENTER.md](DOCUMENTER.md) | 4 tasks | 9 days |
| **Engineer 1** (Frontend) | [ENGINEER1_FRONTEND.md](ENGINEER1_FRONTEND.md) | 8 tasks | 17 days |
| **Engineer 2** (Backend) | [ENGINEER2_BACKEND.md](ENGINEER2_BACKEND.md) | 3 tasks | 6 days |
| **Engineer 3** (Full-Stack) | [ENGINEER3_FULLSTACK.md](ENGINEER3_FULLSTACK.md) | 8 tasks | 17 days |
| **Engineer 4** (DevOps) | [ENGINEER4_DEVOPS.md](ENGINEER4_DEVOPS.md) | 2 tasks | 5 days |
| **QA Engineer** | [QA_ENGINEER.md](QA_ENGINEER.md) | 3 tasks | 7 days |

**👉 Click your role above to see your tasks!**

---

## Quick Start

### 1. Read Your Task File
Open your task file and read through all your tasks for the 8 weeks.

### 2. Start with Week 1
Each task has:
- **What you're building** - Clear description
- **Deliverables** - Specific outputs expected
- **Acceptance Criteria** - How to know you're done
- **Dependencies** - What must be done first
- **Claude Code Prompt** - Copy/paste prompt to get started

### 3. Use Claude Code for Help
Each task includes a "Claude Code Prompt" you can use:

```bash
# Example: Starting Documenter's first task
# Copy the prompt from DOCUMENTER.md Task T1.1 and paste it into Claude Code
```

The prompts are designed to give Claude Code the right context to help you complete the task.

### 4. Track Progress
As you complete tasks, update the weekly status in your standup or team chat.

---

## How to Work on a Task

### Step 1: Read the Task
- Understand what you're building
- Check the deliverables
- Note any dependencies

### Step 2: Check Dependencies
Some tasks depend on others completing first:
- ✅ **Green to go** - Dependencies complete
- ⏳ **Wait** - Dependencies in progress
- ❌ **Blocked** - Dependencies not started

Example:
```
T2.1 (Documenter - 5-min guide) depends on:
- T2.4 (Engineer 4 - Docker profiles) ← Wait for this first!
- T1.3 (Engineer 2 - MCP examples) ← Wait for this first!
```

### Step 3: Create a Branch
```bash
git checkout -b task/T1.1-mcp-documentation
```

Branch naming: `task/[TASK-ID]-[short-description]`

### Step 4: Do the Work
- Use the Claude Code prompt to get started
- Follow the deliverables checklist
- Test as you go

### Step 5: Test Against Acceptance Criteria
Before marking complete, verify:
- [ ] All deliverables created
- [ ] All acceptance criteria met
- [ ] Tests pass
- [ ] Documentation updated

### Step 6: Create Pull Request
```bash
git add .
git commit -m "feat: complete T1.1 - MCP documentation package

- Added MCP definition to README
- Created MCP_INTRODUCTION.md
- Updated GLOSSARY.md
- Updated FAQ.md
"

git push origin task/T1.1-mcp-documentation
gh pr create --title "[T1.1] MCP Documentation Package"
```

### Step 7: Code Review
- Get 1+ approvals
- Address feedback
- Merge when approved

---

## Task Priorities

### P0 - Critical (Must complete on time)
These tasks block other work:
- T1.1 - MCP Documentation (Documenter)
- T2.4 - Docker Profiles (Engineer 4)
- T3.2 - React Setup (Engineer 3)
- T4.3 - Authentication (Engineer 3)
- T8.1 - Docker/K8s Integration (Engineer 4)
- T8.2 - Final QA (QA)

### P1 - High (Important but some flexibility)
All other tasks are P1.

---

## Working with Claude Code

### What is Claude Code?
Claude Code is an AI coding assistant that can help you complete tasks autonomously.

### How to Use Claude Code for These Tasks

**Option 1: Copy the Prompt**
Each task has a "Claude Code Prompt" section. Copy and paste it:

```
Example from DOCUMENTER.md Task T1.1:

Read the SARK repository and create comprehensive MCP documentation.

Tasks:
1. Add MCP definition to README.md (first 100 lines)
2. Create docs/MCP_INTRODUCTION.md with full explanation
3. Update docs/GLOSSARY.md with MCP terms
4. Update docs/FAQ.md with MCP questions

Requirements:
- No assumptions of prior MCP knowledge
- Include real-world examples
- Link to MCP specification at https://modelcontextprotocol.io
- Make it accessible to non-technical readers

Context: SARK is a governance system for MCP deployments, but we've never clearly explained what MCP is. Fix this.
```

**Option 2: Interactive Approach**
Start a conversation with Claude Code:
```
"I'm working on Task T1.1 from DOCUMENTER.md. Can you help me understand what MCP is and how to explain it in the SARK documentation?"
```

**Option 3: Ask for a Plan**
```
"I need to complete Task T5.2 (MCP Servers Management UI). Can you create a plan for building this feature?"
```

### Claude Code Best Practices

✅ **DO:**
- Give context about SARK and the task
- Be specific about what you need
- Ask for code examples
- Ask Claude to test its own work
- Iterate and refine

❌ **DON'T:**
- Assume Claude knows the codebase (give context)
- Accept first draft without testing
- Skip the acceptance criteria
- Forget to ask for tests

---

## Weekly Schedule

### Week 1: MCP Definition
- **Documenter:** T1.1 (3 days)
- **Engineer 2:** T1.3 (1 day)
- **Engineer 3:** T1.2 (2 days)
- **QA:** T1.4 (1 day)

### Week 2: Simplified Onboarding
- **Documenter:** T2.1, T2.2 (4 days)
- **Engineer 3:** T2.3 (3 days)
- **Engineer 4:** T2.4 (2 days)

### Week 3: UI Planning
- **Engineer 1:** T3.1 (3 days)
- **Engineer 2:** T3.3 (2 days)
- **Engineer 3:** T3.2 (2 days)

### Week 4: UI Foundation
- **Engineer 1:** T4.1, T4.2 (5 days)
- **Engineer 3:** T4.3, T4.4 (4 days)

### Week 5: UI Core Features
- **Engineer 1:** T5.1, T5.3 (4 days)
- **Engineer 3:** T5.2, T5.4 (5 days)

### Week 6: UI Advanced Features
- **Engineer 1:** T6.1 (3 days)
- **Engineer 2:** T6.3 (2 days)
- **Engineer 3:** T6.2 (2 days)

### Week 7: Polish & Accessibility
- **Engineer 1:** T7.1, T7.2 (5 days)
- **QA:** T7.3 (3 days)

### Week 8: Integration & Launch
- **Documenter:** T8.2 part 1 (3 days)
- **Engineer 4:** T8.1 (4 days)
- **QA:** T8.2 part 2 (3 days)

---

## Getting Help

### Stuck on a Task?
1. Review the task deliverables again
2. Check if dependencies are complete
3. Use Claude Code with the provided prompt
4. Ask in team chat
5. Pair with another engineer

### Need Clarification?
- See [WORK_TASKS.md](../WORK_TASKS.md) for full context
- Ask in daily standup
- Message the project lead

### Found a Problem?
- Create a GitHub issue
- Tag it with the task ID (e.g., `task:T1.1`)
- Discuss in team chat

---

## Success Metrics

### Individual Task Success
- [ ] All deliverables complete
- [ ] All acceptance criteria met
- [ ] Tests passing
- [ ] Code reviewed and merged
- [ ] Documentation updated

### Weekly Success
- [ ] All week's tasks completed
- [ ] Demo prepared for Friday
- [ ] No blocking issues for next week

### Project Success (Week 8)
- [ ] All 27 tasks complete
- [ ] MCP clearly defined
- [ ] Onboarding simplified (5-min quickstart)
- [ ] UI launched and working
- [ ] All tests passing
- [ ] QA sign-off
- [ ] 🚀 **PRODUCTION LAUNCH**

---

## Communication

### Daily Standups (9:00 AM)
Share:
- What I completed yesterday
- What I'm working on today
- Any blockers
- Dependencies on others

### Weekly Demos (Friday 3:00 PM)
- Show your week's work
- Get feedback
- Celebrate progress

### Slack Channels
- `#sark-improvements-general` - General discussion
- `#sark-improvements-ui` - UI development
- `#sark-improvements-docs` - Documentation
- `#sark-improvements-qa` - Testing

---

## Tools & Resources

### Development
- **Git:** Version control
- **GitHub:** Code repository
- **Docker:** Containers
- **Node.js:** UI development
- **Python:** Backend development

### Documentation
- **Markdown:** All docs
- **Mermaid:** Diagrams
- **GitHub:** Doc hosting

### Testing
- **Playwright:** E2E tests
- **Vitest:** Unit tests
- **Lighthouse:** Performance
- **axe:** Accessibility

### Communication
- **Slack:** Team chat
- **Zoom:** Standups & demos
- **GitHub:** Code reviews

---

## Tips for Success

### Time Management
- Don't wait until the last day of the week
- Start with the hardest task first
- Break large tasks into smaller chunks
- Ask for help early if blocked

### Quality
- Test your work before PR
- Follow acceptance criteria
- Write clear commit messages
- Document as you go

### Collaboration
- Help teammates when you can
- Share knowledge and learnings
- Review others' PRs
- Celebrate wins together

### Using AI Assistance
- Claude Code is your pair programmer
- Give it context about SARK
- Ask it to explain its suggestions
- Always review and test its code

---

## Let's Build Something Great! 🚀

You have:
- ✅ Clear tasks
- ✅ Detailed deliverables
- ✅ Claude Code prompts
- ✅ 8-week timeline
- ✅ Supportive team

**Now let's make SARK accessible to the world!**

Questions? Check [WORK_TASKS.md](../WORK_TASKS.md) or ask in Slack.

---

**Last Updated:** 2025-11-27
**Project Timeline:** 8 weeks
**Team Size:** 6 people
**Goal:** Make SARK the best MCP governance platform
