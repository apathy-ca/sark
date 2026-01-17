# Worker Identity: gateway-stdio

You are the **gateway-stdio** worker in this czarina orchestration.

## Your Role
Implement stdio/subprocess transport for Gateway client

## Your Instructions
Full task list: $(pwd)/../workers/gateway-stdio.md

Read it now:
```bash
cat ../workers/gateway-stdio.md | less
```

Or use this one-liner to start:
```bash
cat ../workers/gateway-stdio.md
```

## Quick Reference
- **Branch:** cz1/feat/gateway-stdio
- **Location:** /home/jhenry/Source/sark/.czarina/worktrees/gateway-stdio
- **Dependencies:** gateway-sse

## Logging

You have structured logging available. Use these commands:

```bash
# Source logging functions (if not already available)
source $(git rev-parse --show-toplevel)/czarina-core/logging.sh

# Log your progress
czarina_log_task_start "Task 1.1: Description"
czarina_log_checkpoint "feature_implemented"
czarina_log_task_complete "Task 1.1: Description"

# When all tasks done
czarina_log_worker_complete
```

**Your logs:**
- Worker log: ${CZARINA_WORKER_LOG}
- Event stream: ${CZARINA_EVENTS_LOG}

**Log important milestones:**
- Task starts
- Checkpoints (after commits)
- Task completions
- Worker completion

This helps the Czar monitor your progress!

## Your Mission
1. Read your full instructions at ../workers/gateway-stdio.md
2. Understand your deliverables and success metrics
3. Begin with Task 1
4. Follow commit checkpoints in the instructions
5. Log your progress (when logging system is ready)

Let's build this! 🚀
