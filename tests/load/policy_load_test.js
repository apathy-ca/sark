/**
 * K6 load test for SARK policy evaluation.
 *
 * This script tests policy evaluation performance under various load patterns.
 *
 * Usage:
 *   # Run with default settings (10 VUs for 30s)
 *   k6 run tests/load/policy_load_test.js
 *
 *   # Run with custom load (100 VUs for 5 minutes)
 *   k6 run --vus 100 --duration 5m tests/load/policy_load_test.js
 *
 *   # Run with staged load
 *   k6 run tests/load/policy_load_test.js -e SCENARIO=staged
 *
 *   # Generate HTML report (requires k6-reporter)
 *   k6 run --out json=test_results.json tests/load/policy_load_test.js
 *   k6-reporter test_results.json
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const policyEvaluationRate = new Rate('policy_evaluation_success');
const policyLatency = new Trend('policy_evaluation_duration');
const cacheHits = new Counter('cache_hits');
const cacheMisses = new Counter('cache_misses');
const policyDenials = new Counter('policy_denials');

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const SCENARIO = __ENV.SCENARIO || 'default';

// Load test scenarios
export const options = getScenario(SCENARIO);

function getScenario(scenario) {
  const scenarios = {
    // Default scenario: constant load
    default: {
      vus: 10,
      duration: '30s',
      thresholds: {
        http_req_duration: ['p(95)<50'], // 95% of requests should be below 50ms
        policy_evaluation_success: ['rate>0.95'], // 95% success rate
        http_req_failed: ['rate<0.05'], // Error rate below 5%
      },
    },

    // Staged load: gradually increase load
    staged: {
      stages: [
        { duration: '1m', target: 10 },   // Ramp up to 10 users
        { duration: '2m', target: 50 },   // Ramp up to 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '2m', target: 200 },  // Ramp up to 200 users
        { duration: '1m', target: 0 },    // Ramp down to 0 users
      ],
      thresholds: {
        http_req_duration: ['p(95)<50', 'p(99)<100'],
        policy_evaluation_success: ['rate>0.95'],
      },
    },

    // Spike test: sudden load spikes
    spike: {
      stages: [
        { duration: '30s', target: 20 },   // Baseline
        { duration: '30s', target: 200 },  // Spike!
        { duration: '1m', target: 20 },    // Back to baseline
        { duration: '30s', target: 500 },  // Bigger spike!
        { duration: '1m', target: 20 },    // Back to baseline
      ],
      thresholds: {
        http_req_duration: ['p(95)<100'], // More lenient for spike test
        policy_evaluation_success: ['rate>0.90'],
      },
    },

    // Stress test: push to the limits
    stress: {
      stages: [
        { duration: '2m', target: 100 },
        { duration: '3m', target: 200 },
        { duration: '3m', target: 300 },
        { duration: '3m', target: 400 },
        { duration: '2m', target: 0 },
      ],
      thresholds: {
        http_req_duration: ['p(95)<200'],
      },
    },

    // Soak test: sustained load over time
    soak: {
      stages: [
        { duration: '2m', target: 100 },
        { duration: '30m', target: 100 }, // Sustained load
        { duration: '2m', target: 0 },
      ],
      thresholds: {
        http_req_duration: ['p(95)<50'],
        policy_evaluation_success: ['rate>0.95'],
      },
    },
  };

  return scenarios[scenario] || scenarios.default;
}

// Test data generators
function randomChoice(array) {
  return array[Math.floor(Math.random() * array.length)];
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

const roles = ['developer', 'developer', 'developer', 'admin', 'viewer'];
const sensitivityLevels = ['low', 'medium', 'high', 'critical'];

// ============================================================================
// TEST SCENARIOS
// ============================================================================

export default function () {
  // Simulate realistic traffic distribution
  const scenario = Math.random();

  if (scenario < 0.5) {
    // 50% - Cached policy evaluation (common tools)
    evaluateCachedPolicy();
  } else if (scenario < 0.8) {
    // 30% - Unique policy evaluation (cache miss)
    evaluateUniquePolicy();
  } else if (scenario < 0.95) {
    // 15% - Critical tool evaluation
    evaluateCriticalTool();
  } else {
    // 5% - Server registration
    evaluateServerRegistration();
  }

  sleep(randomInt(1, 5) / 10); // 100-500ms between requests
}

function evaluateCachedPolicy() {
  const userId = `user-${randomInt(1, 1000)}`;
  const toolId = `tool-${randomInt(1, 10)}`; // Limited set for cache hits

  const payload = JSON.stringify({
    user: {
      id: userId,
      role: randomChoice(roles),
      teams: [`team-${randomInt(1, 20)}`],
    },
    action: 'tool:invoke',
    tool: {
      id: toolId,
      name: `common_tool_${randomInt(1, 10)}`,
      sensitivity_level: randomChoice(['low', 'medium']),
    },
    context: {
      client_ip: '10.0.0.100',
      timestamp: Math.floor(Date.now() / 1000),
    },
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'cached_policy' },
  };

  const response = http.post(`${BASE_URL}/api/v1/policy/evaluate`, payload, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has allow field': (r) => JSON.parse(r.body).allow !== undefined,
    'latency < 50ms': (r) => r.timings.duration < 50,
  });

  policyEvaluationRate.add(success);
  policyLatency.add(response.timings.duration);

  if (success) {
    cacheHits.add(1);
    const result = JSON.parse(response.body);
    if (!result.allow) {
      policyDenials.add(1);
    }
  }
}

function evaluateUniquePolicy() {
  const userId = `user-${randomInt(1, 1000)}`;
  const toolId = `tool-${randomInt(1, 10000)}`; // Large set for cache misses

  const payload = JSON.stringify({
    user: {
      id: userId,
      role: randomChoice(roles),
      teams: [`team-${randomInt(1, 20)}`],
    },
    action: 'tool:invoke',
    tool: {
      id: toolId,
      name: `unique_tool_${randomInt(1, 10000)}`,
      sensitivity_level: randomChoice(['low', 'medium', 'high']),
    },
    context: {
      client_ip: '10.0.0.100',
      timestamp: Math.floor(Date.now() / 1000),
    },
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'unique_policy' },
  };

  const response = http.post(`${BASE_URL}/api/v1/policy/evaluate`, payload, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has allow field': (r) => JSON.parse(r.body).allow !== undefined,
  });

  policyEvaluationRate.add(success);
  policyLatency.add(response.timings.duration);

  if (success) {
    cacheMisses.add(1);
    const result = JSON.parse(response.body);
    if (!result.allow) {
      policyDenials.add(1);
    }
  }
}

function evaluateCriticalTool() {
  const userId = `user-${randomInt(1, 1000)}`;
  const currentTime = Date.now() * 1000000; // nanoseconds
  const mfaTime = currentTime - (5 * 60 * 1000000000); // 5 minutes ago

  const payload = JSON.stringify({
    user: {
      id: userId,
      role: randomChoice(['developer', 'admin']),
      teams: [`team-${randomInt(1, 20)}`],
      mfa_verified: true,
      mfa_timestamp: mfaTime,
      mfa_methods: ['totp'],
    },
    action: 'tool:invoke',
    tool: {
      id: `critical-tool-${randomInt(1, 5)}`,
      name: `critical_tool_${randomInt(1, 5)}`,
      sensitivity_level: 'critical',
    },
    context: {
      client_ip: '10.0.0.100',
      timestamp: Math.floor(Date.now() / 1000),
    },
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'critical_tool' },
  };

  const response = http.post(`${BASE_URL}/api/v1/policy/evaluate`, payload, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has allow field': (r) => JSON.parse(r.body).allow !== undefined,
  });

  policyEvaluationRate.add(success);
  policyLatency.add(response.timings.duration);

  if (success) {
    const result = JSON.parse(response.body);
    if (!result.allow) {
      policyDenials.add(1);
    }
  }
}

function evaluateServerRegistration() {
  const userId = `user-${randomInt(1, 1000)}`;

  const payload = JSON.stringify({
    user: {
      id: userId,
      role: randomChoice(['developer', 'admin']),
      teams: [`team-${randomInt(1, 20)}`],
    },
    action: 'server:register',
    server: {
      name: `server-${userId}-${Date.now()}`,
      teams: [`team-${randomInt(1, 20)}`],
    },
    context: {
      client_ip: '10.0.0.100',
      timestamp: Math.floor(Date.now() / 1000),
    },
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    tags: { scenario: 'server_register' },
  };

  const response = http.post(`${BASE_URL}/api/v1/policy/evaluate`, payload, params);

  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'has allow field': (r) => JSON.parse(r.body).allow !== undefined,
  });

  policyEvaluationRate.add(success);
  policyLatency.add(response.timings.duration);
}

// ============================================================================
// SUMMARY HANDLER
// ============================================================================

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  const p99 = data.metrics.http_req_duration.values['p(99)'];
  const successRate = data.metrics.policy_evaluation_success.values.rate * 100;

  console.log('\n' + '='.repeat(60));
  console.log('POLICY EVALUATION PERFORMANCE TEST SUMMARY');
  console.log('='.repeat(60));
  console.log(`Scenario: ${SCENARIO}`);
  console.log(`Total Requests: ${data.metrics.http_reqs.values.count}`);
  console.log(`Success Rate: ${successRate.toFixed(2)}%`);
  console.log('\nLatency:');
  console.log(`  P50: ${data.metrics.http_req_duration.values['p(50)'].toFixed(2)}ms`);
  console.log(`  P95: ${p95.toFixed(2)}ms`);
  console.log(`  P99: ${p99.toFixed(2)}ms`);
  console.log(`  Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms`);
  console.log('\nCache Performance:');
  console.log(`  Cache Hits: ${data.metrics.cache_hits?.values.count || 0}`);
  console.log(`  Cache Misses: ${data.metrics.cache_misses?.values.count || 0}`);
  console.log('\nPolicy Decisions:');
  console.log(`  Denials: ${data.metrics.policy_denials?.values.count || 0}`);

  // Check targets
  console.log('\nPerformance Targets:');
  if (p95 < 50) {
    console.log(`  ✅ P95 latency target MET: ${p95.toFixed(2)}ms < 50ms`);
  } else {
    console.log(`  ❌ P95 latency target MISSED: ${p95.toFixed(2)}ms >= 50ms`);
  }

  if (successRate > 95) {
    console.log(`  ✅ Success rate target MET: ${successRate.toFixed(2)}% > 95%`);
  } else {
    console.log(`  ❌ Success rate target MISSED: ${successRate.toFixed(2)}% <= 95%`);
  }

  console.log('='.repeat(60));

  return {
    'stdout': '', // Don't print built-in summary
    'summary.json': JSON.stringify(data, null, 2),
  };
}
