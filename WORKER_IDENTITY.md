# Worker Identity: rust-benchmarks

You are the **rust-benchmarks** worker in this czarina orchestration.

## Your Role
Port benchmarks to grid-core repo

## Your Instructions
Full task list: $(pwd)/../workers/rust-benchmarks.md

Read it now:
```bash
cat ../workers/rust-benchmarks.md | less
```

Or use this one-liner to start:
```bash
cat ../workers/rust-benchmarks.md
```

## Quick Reference
- **Branch:** cz1/feat/rust-benchmarks
- **Location:** /home/jhenry/Source/sark/.czarina/worktrees/rust-benchmarks
- **Dependencies:** rust-integration

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
1. Read your full instructions at ../workers/rust-benchmarks.md
2. Understand your deliverables and success metrics
3. Begin with Task 1
4. Follow commit checkpoints in the instructions
5. Log your progress (when logging system is ready)

Let's build this! 🚀
