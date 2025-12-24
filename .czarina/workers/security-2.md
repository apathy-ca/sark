# Worker: SECURITY-2
## Anomaly Detection System

**Stream:** 2
**Duration:** Weeks 3-4 (2 weeks)
**Branch:** `feat/anomaly-detection`
**Agent:** Aider (recommended)
**Dependencies:** None

---

## Mission

Build behavioral anomaly detection to identify unusual access patterns and potential account compromise through baseline comparison and statistical analysis.

## Goals

- Build 30-day behavioral baselines per user
- Detect 6+ anomaly types (unusual tool, time, data volume, sensitivity)
- Alert on critical anomalies (auto-suspend option)
- 80%+ detection rate on simulated attacks
- <10% false positive rate

## Week 3: Behavioral Baseline

### Tasks

1. **Baseline Builder** (3 days)
   - File: `src/sark/security/behavioral_analyzer.py` (NEW)
   - Build user profiles from 30-day audit history
   - Track: most_common_tools, typical_hours, typical_days, data_volume, sensitivity_levels
   - Store baselines in database with versioning

2. **Anomaly Detection** (2 days)
   - Implement 6 detection rules:
     * Unusual tool (not in top 10)
     * Unusual time (outside typical hours)
     * Unusual day (weekend when user typically weekday)
     * Excessive data (>2x max baseline)
     * Sensitivity escalation (above max baseline)
     * Rapid fire requests (rate spike)
   - Return list of Anomaly objects with severity

## Week 4: Alerting & Integration

### Tasks

1. **Alert Manager** (2 days)
   - File: `src/sark/security/anomaly_alerts.py` (NEW)
   - Process anomalies and send alerts
   - Critical: 2+ high severity → PagerDuty + auto-suspend
   - Warning: 1 high or 3+ medium → Slack
   - Always log to audit

2. **Gateway Integration** (2 days)
   - File: `src/sark/api/routers/gateway.py` (UPDATE)
   - Run anomaly detection post-execution
   - Async processing (don't block response)
   - Feature flag: `ANOMALY_DETECTION_ENABLED`

3. **Baseline Management** (1 day)
   - File: `src/sark/services/baseline_manager.py` (NEW)
   - Background task: rebuild baselines daily
   - API endpoint: POST /api/v1/security/baselines/rebuild
   - Baseline versioning and rollback

4. **Tests** (1 day)
   - File: `tests/unit/security/test_anomaly_detector.py` (NEW)
   - Test all 6 anomaly types
   - Test alert triggering logic
   - Test baseline building and updates

## Deliverables

- ✅ `src/sark/security/behavioral_analyzer.py` (~250 lines)
- ✅ `src/sark/security/anomaly_alerts.py` (~150 lines)
- ✅ `src/sark/services/baseline_manager.py` (~100 lines)
- ✅ `tests/unit/security/test_anomaly_detector.py` (~300 lines)
- ✅ `docs/security/ANOMALY_DETECTION.md`

## Success Metrics

- [ ] 80%+ detection rate on simulated attacks
- [ ] <10% false positive rate
- [ ] Baselines update automatically
- [ ] Alerts delivered to all configured channels
- [ ] All tests passing, coverage ≥90%

## References

- Implementation Plan: `docs/v1.3.0/IMPLEMENTATION_PLAN.md` (Stream 2)
