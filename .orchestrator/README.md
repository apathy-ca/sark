# SARK v2.0 Orchestrator

This directory contains orchestrator coordination files for SARK v2.0 development.

## Files
- `status.json` - Current project status and engineer assignments
- `daily_report_template.md` - Template for daily status reports
- `daily_reports/` - Generated daily status reports

## Usage

### Check Current Status
```bash
cat .orchestrator/status.json
```

### Generate Daily Report
```bash
python ../claude-orchestrator/generate_daily_report.py
```

### Update Engineer Status
```bash
python ../claude-orchestrator/update_status.py engineer-1 --status in_progress --task "Implementing MCPAdapter"
```

## Orchestrator Commands

See `../claude-orchestrator/README.md` for full orchestrator command reference.
