# Czarina Orchestration - sark

## Quick Start

### For Workers

**Claude Code / Desktop:**
```bash
./.czarina/.worker-init worker1
```

**Claude Code Web (auto-discovery):**
Just say: "You are worker1"

### For Orchestrators

**Launch all workers:**
```bash
czarina launch
```

**Start daemon (auto-approval):**
```bash
czarina daemon start
```

**Check status:**
```bash
czarina status
```

## Configuration

Edit `.czarina/config.json` to:
- Add/remove workers
- Configure agent types
- Set daemon behavior

Edit `.czarina/workers/*.md` to define worker roles and tasks.

## Workers

- **worker1**: Worker 1

## Project

**Repository:** /home/jhenry/Source/sark
**Orchestration:** .czarina/

Created: 2025-12-09
