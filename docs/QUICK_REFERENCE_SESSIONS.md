# Quick Reference - Team Sessions

## Team Workload Distribution

| Role | Sessions | Hours | Avg/Week |
|------|----------|-------|----------|
| **Engineer 1** (Frontend) | 24 | 90h | 11.25h |
| **Engineer 2** (Backend/API) | 19 | 71h | 8.88h |
| **Engineer 3** (Full-Stack) | 24 | 90h | 11.25h |
| **Engineer 4** (DevOps) | 18 | 68h | 8.5h |
| **QA Engineer** | 16 | 61h | 7.63h |
| **Documenter** | 15 | 56h | 7h |
| **All-hands** | 8 | 18h | 2.25h |
| **TOTAL** | 124 | 454h | 56.75h |

**Note:** Total sessions include 8 all-hands sessions (weekly reviews)

## Week-by-Week Snapshot

### Week 1: MCP Definition & Foundation
**Focus:** Documentation
**Key Person:** Documenter (5 sessions)
**Deliverable:** MCP documentation complete

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 3 sessions |

### Week 2: Simplified Onboarding
**Focus:** Tutorials & Examples
**Key Person:** Engineer 3 (4 sessions)
**Deliverable:** 5-min quickstart + tutorials

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 3: UI Planning & Design
**Focus:** Architecture & Setup
**Key Persons:** Engineer 1, Engineer 3
**Deliverable:** React project ready

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 4: UI Foundation
**Focus:** Core components
**Key Persons:** Engineer 1, Engineer 3
**Deliverable:** Auth + layouts working

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 5: UI Core Features
**Focus:** Main pages
**Key Persons:** Engineer 1, Engineer 3
**Deliverable:** Dashboard, servers, policies

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 6: UI Advanced Features
**Focus:** Policy editor, exports
**Key Persons:** Engineer 1, Engineer 3
**Deliverable:** Full feature set

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 7: UI Polish & Accessibility
**Focus:** UX improvements
**Key Persons:** Engineer 1, QA
**Deliverable:** Production-quality UI

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

### Week 8: Integration & Launch
**Focus:** Testing & deployment
**Key Person:** Engineer 4 (5 sessions)
**Deliverable:** 🚀 LAUNCH

| Mon | Tue | Wed | Thu | Fri |
|-----|-----|-----|-----|-----|
| 4 sessions | 4 sessions | 4 sessions | 4 sessions | 4 sessions |

## Critical Sessions (Don't Miss These!)

### 🔴 P0 - Blocking Sessions

| Week | Session | Owner | Why Critical |
|------|---------|-------|--------------|
| W1 | DOC-01 | DOC | Blocks all W1 doc work |
| W2 | E3-01 | E3 | Blocks quickstart testing |
| W3 | E3-02 | E3 | Blocks all UI development |
| W4 | E3-01 | E3 | Blocks UI feature work |
| W8 | E4-01 | E4 | Blocks integration testing |

### 🟡 P1 - Important Sessions

| Week | Session | Owner | Impact |
|------|---------|-------|--------|
| W1 | E3-02 | E3 | Needed for documentation diagrams |
| W2 | QA-01 | QA | Validates quickstart works |
| W4 | E1-01 | E1 | Sets UI layout pattern |
| W6 | E1-01 | E1 | Policy editor is key feature |
| W7 | QA-01 | QA | Accessibility is non-negotiable |
| W8 | QA-03 | QA | Security must pass |

## Session Templates

### Standard Session Structure

```markdown
## Session: [ID] - [Title]

**Owner:** [Role]
**Duration:** [Hours]
**Week:** [Number]
**Day:** [Day of week]

### Prerequisites
- [ ] Dependency 1
- [ ] Dependency 2

### Deliverables
- [ ] Output 1
- [ ] Output 2

### Acceptance Criteria
- Meets requirement X
- Passes test Y
- Documented in Z

### Notes
[Space for session notes]
```

### Session Handoff Template

```markdown
## Handoff: [From Session] → [To Session]

**From:** [Owner 1]
**To:** [Owner 2]
**Handoff Date:** [Date]

### Completed Work
- ✅ Item 1
- ✅ Item 2

### Files/Artifacts
- `path/to/file1.md`
- `path/to/file2.tsx`

### Next Steps
- [ ] Task for next owner
- [ ] Task for next owner

### Questions/Blockers
- Question 1?
- Blocker 1?
```

## Collaboration Patterns

### Pair Programming Sessions

When to pair:
- **W4-E3-01** (Auth) - E2 can help
- **W6-E1-01** (Monaco) - E3 can assist
- **W8-E4-01** (Integration) - E3 should pair

### Review Sessions

| What | Who Reviews | When |
|------|-------------|------|
| UI Components | E1 or E3 | Same day |
| API Changes | E2 | Next day |
| Docker/K8s | E4 | Same day |
| Documentation | DOC + 1 Engineer | End of week |
| Tests | QA + Feature owner | Same day |

## Session Scheduling Tips

### Morning Sessions (Best for)
- Complex problem-solving (E1, E3 new features)
- Deep focus work (DOC writing)
- Architecture decisions (E4 planning)

### Afternoon Sessions (Best for)
- Testing and QA (QA sessions)
- Code reviews (All)
- Integration work (E3, E4)
- Documentation reviews (DOC)

### Friday Sessions
- Keep lighter (polish, docs, reviews)
- Schedule all-hands at end of day
- Reserve time for cleanup

## Progress Tracking

### Daily Updates in Slack

```
#sark-improvements-[area]

[ROLE] - [SESSION-ID] - [STATUS]
✅ Completed: [what you finished]
🔄 In Progress: [what you're working on]
🚫 Blocked: [any blockers]
📋 Next: [what's next]
```

**Example:**
```
E1 - W4-E1-02 - IN PROGRESS
✅ Completed: Header and Sidebar components
🔄 In Progress: Button and Input components
🚫 Blocked: None
📋 Next: Form components tomorrow
```

### Weekly Status Board

| Role | Sessions Done | Sessions Remaining | % Complete |
|------|---------------|-------------------|------------|
| E1 | 3/24 | 21 | 12.5% |
| E2 | 2/19 | 17 | 10.5% |
| E3 | 4/24 | 20 | 16.7% |
| E4 | 2/18 | 16 | 11.1% |
| QA | 2/16 | 14 | 12.5% |
| DOC | 5/15 | 10 | 33.3% |

## Emergency Protocols

### Session Owner Unavailable

**Backup Plan:**
1. Check session dependencies
2. If blocking, escalate immediately
3. Find backup from same specialty:
   - E1 ↔ E3 (UI work)
   - E2 ↔ E3 (API work)
   - E4 solo (notify team of delay)
   - QA solo (engineers can help)
   - DOC solo (E2 can help)

### Session Running Over

**Protocol:**
1. Assess % complete
2. If >80%: extend 1 hour
3. If <80%: split into 2 sessions
4. Update dependent sessions
5. Communicate in all-hands

### Blocker Encountered

**Escalation:**
1. Post in relevant Slack channel immediately
2. Tag dependent session owners
3. Propose solutions or alternatives
4. If not resolved in 2 hours, escalate to all-hands
5. Consider parallel track if critical

## Tools & Resources

### Essential Tools

| Tool | Purpose | Access |
|------|---------|--------|
| **GitHub** | Code repository | https://github.com/apathy-ca/sark |
| **Slack** | Communication | #sark-improvements-* |
| **Figma** | UI Design | [Link to project] |
| **Jira/Linear** | Issue tracking | [Link to board] |
| **Notion/Confluence** | Wiki/Docs | [Link to space] |

### Useful Commands

```bash
# Check your current sessions
grep "W[0-9]-$(whoami)" WORK_BREAKDOWN_SESSIONS.md

# Create session branch
git checkout -b session/W1-E1-01-layout-components

# Session complete checklist
git add .
git commit -m "feat: complete W1-E1-01 - layout components"
git push origin session/W1-E1-01-layout-components
# Create PR with session ID in title
```

### Session Branch Naming

```
session/[WEEK]-[ROLE]-[NUM]-[short-description]

Examples:
session/W1-DOC-01-mcp-definition
session/W4-E1-02-base-components
session/W8-QA-03-security-testing
```

## Celebration Checklist

### End of Week 1 ✅
- [ ] All MCP documentation merged
- [ ] Demo in all-hands
- [ ] Team lunch scheduled

### End of Week 3 ✅
- [ ] UI design approved
- [ ] Onboarding docs live
- [ ] Happy hour planned

### End of Week 5 ✅
- [ ] Core UI features working demo
- [ ] External stakeholder demo
- [ ] Team dinner booked

### End of Week 7 ✅
- [ ] Feature-complete demo
- [ ] Code freeze announced
- [ ] Game night organized

### End of Week 8 🚀
- [ ] Production deployment complete
- [ ] All tests passing
- [ ] Launch announcement sent
- [ ] LAUNCH PARTY! 🎉

---

**Keep this reference handy throughout the 8 weeks!**

Print it out, bookmark it, or pin in Slack 📌
