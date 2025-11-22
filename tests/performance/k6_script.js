/**
 * k6 Load Testing Scripts for SARK API
 *
 * This script provides comprehensive load testing scenarios using k6 (https://k6.io/).
 * k6 is a modern load testing tool with excellent performance and developer experience.
 *
 * Performance Targets:
 * - API response time (p95): < 100ms
 * - Server registration (p95): < 200ms
 * - Policy evaluation (p95): < 50ms
 * - Database queries: < 20ms
 *
 * Installation:
 *   # macOS
 *   brew install k6
 *
 *   # Linux
 *   sudo gpg -k
 *   sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
 *   echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
 *   sudo apt-get update
 *   sudo apt-get install k6
 *
 * Usage Examples:
 *   # Basic smoke test
 *   k6 run k6_script.js
 *
 *   # Load test with 100 virtual users for 5 minutes
 *   k6 run --vus 100 --duration 5m k6_script.js
 *
 *   # Stress test with ramping users
 *   k6 run --stage 1m:100,3m:500,1m:100,1m:0 k6_script.js
 *
 *   # Specific scenario
 *   k6 run --env SCENARIO=server_registration k6_script.js
 *
 *   # Generate HTML report
 *   k6 run --out json=reports/k6_results.json k6_script.js
 *   k6 convert -O html reports/k6_results.json > reports/k6_report.html
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomIntBetween, randomItem } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// ============================================================================
// Configuration
// ============================================================================

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'sk_test_1234567890abcdefghijklmnop';
const SCENARIO = __ENV.SCENARIO || 'mixed'; // mixed, server_registration, policy_evaluation, stress

// ============================================================================
// Custom Metrics
// ============================================================================

const serverRegistrationDuration = new Trend('server_registration_duration');
const policyEvaluationDuration = new Trend('policy_evaluation_duration');
const serverListDuration = new Trend('server_list_duration');
const errorRate = new Rate('error_rate');
const rateLimitHits = new Counter('rate_limit_hits');
const successfulRegistrations = new Counter('successful_registrations');
const policyDecisions = new Counter('policy_decisions');

// ============================================================================
// Test Configuration
// ============================================================================

export const options = {
  scenarios: {
    // Smoke test - verify basic functionality
    smoke_test: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { test_type: 'smoke' },
      exec: 'smokeTest',
    },

    // Load test - sustained load
    load_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },   // Ramp up to 50 users
        { duration: '5m', target: 50 },   // Stay at 50 users
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '5m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 0 },    // Ramp down to 0 users
      ],
      gracefulRampDown: '30s',
      tags: { test_type: 'load' },
      exec: 'loadTest',
    },

    // Stress test - push beyond normal capacity
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '5m', target: 200 },  // Ramp up to 200 users
        { duration: '5m', target: 300 },  // Ramp up to 300 users
        { duration: '2m', target: 400 },  // Spike to 400 users
        { duration: '10m', target: 0 },   // Ramp down to 0 users
      ],
      gracefulRampDown: '30s',
      tags: { test_type: 'stress' },
      exec: 'stressTest',
    },

    // Spike test - sudden traffic spike
    spike_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },   // Normal load
        { duration: '30s', target: 500 }, // Sudden spike
        { duration: '3m', target: 500 },  // Maintain spike
        { duration: '1m', target: 50 },   // Return to normal
        { duration: '1m', target: 0 },    // Ramp down
      ],
      tags: { test_type: 'spike' },
      exec: 'spikeTest',
    },

    // Soak test - extended duration at moderate load
    soak_test: {
      executor: 'constant-vus',
      vus: 50,
      duration: '30m',
      tags: { test_type: 'soak' },
      exec: 'soakTest',
    },
  },

  thresholds: {
    // Global thresholds
    'http_req_duration': ['p(95)<100'],         // 95% of requests under 100ms
    'http_req_duration{type:api}': ['p(95)<100'], // API requests under 100ms
    'http_req_failed': ['rate<0.01'],           // Error rate under 1%

    // Specific endpoint thresholds
    'server_registration_duration': ['p(95)<200'], // Server registration under 200ms
    'policy_evaluation_duration': ['p(95)<50'],   // Policy evaluation under 50ms
    'server_list_duration': ['p(95)<100'],        // Server list under 100ms

    // Error rate thresholds
    'error_rate': ['rate<0.05'],                  // Overall error rate under 5%
    'http_req_duration{expected_response:true}': ['p(95)<100'],
  },

  // Don't run all scenarios by default (use --scenario flag to select)
  // Comment out scenarios you don't want to run
  // scenarios: ['smoke_test', 'load_test'], // Uncomment to run only specific scenarios
};

// ============================================================================
// Helper Functions
// ============================================================================

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  };
}

function generateServerRegistration() {
  const transport = randomItem(['http', 'stdio', 'sse']);
  const toolCount = randomIntBetween(1, 10);
  const tools = [];

  for (let i = 0; i < toolCount; i++) {
    tools.push({
      name: `tool_${randomString(8)}`,
      description: `Test tool ${i}`,
      parameters: {
        type: 'object',
        properties: {
          param1: { type: 'string', description: 'Test parameter' },
          param2: { type: 'number', description: 'Test number' },
        },
      },
      sensitivity_level: randomItem(['low', 'medium', 'high', 'critical']),
      requires_approval: randomItem([true, false]),
    });
  }

  const server = {
    name: `mcp-server-${randomString(10)}`,
    transport: transport,
    version: '2025-06-18',
    capabilities: randomItem([
      ['tools'],
      ['tools', 'prompts'],
      ['tools', 'prompts', 'resources'],
      ['tools', 'prompts', 'resources', 'sampling'],
    ]),
    tools: tools,
    description: `Test server ${randomString(5)}`,
    sensitivity_level: randomItem(['low', 'medium', 'high', 'critical']),
    metadata: {
      environment: randomItem(['dev', 'staging', 'production']),
      team: `Team ${randomString(5)}`,
      owner: `test_${randomString(5)}@example.com`,
    },
  };

  if (transport === 'http') {
    server.endpoint = `http://192.168.1.${randomIntBetween(1, 255)}:${randomIntBetween(8000, 9000)}`;
  } else if (transport === 'stdio') {
    server.command = `/usr/local/bin/${randomString(8)}`;
  }

  return server;
}

function generatePolicyEvaluation(serverId = null) {
  const actions = [
    'tool:invoke',
    'tool:read',
    'server:read',
    'server:update',
    'server:delete',
    'policy:evaluate',
  ];

  return {
    action: randomItem(actions),
    tool: Math.random() > 0.3 ? `tool_${randomString(6)}` : null,
    server_id: serverId || `00000000-0000-0000-0000-${randomString(12, '0123456789abcdef')}`,
    parameters: {
      arg1: randomString(8),
      arg2: randomIntBetween(1, 100),
      arg3: randomItem([true, false]),
    },
  };
}

// ============================================================================
// Test Scenarios
// ============================================================================

export function smokeTest() {
  group('Health Checks', () => {
    const healthRes = http.get(`${BASE_URL}/health/`);
    check(healthRes, {
      'health check status is 200': (r) => r.status === 200,
    });

    const readyRes = http.get(`${BASE_URL}/health/ready`);
    check(readyRes, {
      'ready check status is 200': (r) => r.status === 200,
    });
  });

  group('Basic API Operations', () => {
    // List servers
    const listRes = http.get(`${BASE_URL}/api/v1/servers/`, {
      headers: getHeaders(),
      tags: { type: 'api' },
    });

    const listOk = check(listRes, {
      'list servers status is 200': (r) => r.status === 200,
      'list servers has array response': (r) => Array.isArray(r.json()),
    });

    errorRate.add(!listOk);
    serverListDuration.add(listRes.timings.duration);

    // Evaluate policy
    const policyRes = http.post(
      `${BASE_URL}/api/v1/policy/evaluate`,
      JSON.stringify(generatePolicyEvaluation()),
      {
        headers: getHeaders(),
        tags: { type: 'api' },
      }
    );

    const policyOk = check(policyRes, {
      'policy evaluation status is 200': (r) => r.status === 200,
      'policy has decision field': (r) => r.json('decision') !== undefined,
    });

    errorRate.add(!policyOk);
    policyEvaluationDuration.add(policyRes.timings.duration);

    if (policyOk) {
      policyDecisions.add(1);
    }
  });

  sleep(1);
}

export function loadTest() {
  const actions = ['server_registration', 'server_list', 'policy_evaluation', 'server_get'];
  const action = randomItem(actions);

  switch (action) {
    case 'server_registration':
      registerServer();
      break;
    case 'server_list':
      listServers();
      break;
    case 'policy_evaluation':
      evaluatePolicy();
      break;
    case 'server_get':
      getServer();
      break;
  }

  sleep(randomIntBetween(1, 3));
}

export function stressTest() {
  // More aggressive - less sleep time
  const actions = ['server_registration', 'server_list', 'policy_evaluation', 'server_get'];
  const action = randomItem(actions);

  switch (action) {
    case 'server_registration':
      registerServer();
      break;
    case 'server_list':
      listServers();
      break;
    case 'policy_evaluation':
      // Do multiple policy evaluations in stress test
      for (let i = 0; i < randomIntBetween(2, 5); i++) {
        evaluatePolicy();
      }
      break;
    case 'server_get':
      getServer();
      break;
  }

  sleep(randomIntBetween(0, 1));
}

export function spikeTest() {
  // Rapid requests during spike
  for (let i = 0; i < randomIntBetween(3, 10); i++) {
    evaluatePolicy();
  }

  sleep(0.1);
}

export function soakTest() {
  // Sustained moderate load
  loadTest();
}

// ============================================================================
// Core Operations
// ============================================================================

function registerServer() {
  const serverData = generateServerRegistration();

  const res = http.post(
    `${BASE_URL}/api/v1/servers/`,
    JSON.stringify(serverData),
    {
      headers: getHeaders(),
      tags: { type: 'api', operation: 'server_registration' },
    }
  );

  const success = check(res, {
    'server registration status is 201 or 403': (r) => r.status === 201 || r.status === 403,
    'server registration response time < 200ms': (r) => r.timings.duration < 200,
  });

  errorRate.add(!success && res.status !== 403);
  serverRegistrationDuration.add(res.timings.duration);

  if (res.status === 201) {
    successfulRegistrations.add(1);
  }

  if (res.status === 429) {
    rateLimitHits.add(1);
  }
}

function listServers() {
  const res = http.get(`${BASE_URL}/api/v1/servers/`, {
    headers: getHeaders(),
    tags: { type: 'api', operation: 'server_list' },
  });

  const success = check(res, {
    'list servers status is 200': (r) => r.status === 200,
    'list servers response time < 100ms': (r) => r.timings.duration < 100,
  });

  errorRate.add(!success);
  serverListDuration.add(res.timings.duration);

  if (res.status === 429) {
    rateLimitHits.add(1);
  }
}

function evaluatePolicy() {
  const policyData = generatePolicyEvaluation();

  const res = http.post(
    `${BASE_URL}/api/v1/policy/evaluate`,
    JSON.stringify(policyData),
    {
      headers: getHeaders(),
      tags: { type: 'api', operation: 'policy_evaluation' },
    }
  );

  const success = check(res, {
    'policy evaluation status is 200': (r) => r.status === 200,
    'policy evaluation response time < 50ms': (r) => r.timings.duration < 50,
    'policy has valid decision': (r) => {
      const decision = r.json('decision');
      return decision === 'allow' || decision === 'deny';
    },
  });

  errorRate.add(!success);
  policyEvaluationDuration.add(res.timings.duration);

  if (success) {
    policyDecisions.add(1);
  }

  if (res.status === 429) {
    rateLimitHits.add(1);
  }
}

function getServer() {
  // Use a random UUID since we don't track registered servers in k6
  const serverId = `00000000-0000-0000-0000-${randomString(12, '0123456789abcdef')}`;

  const res = http.get(`${BASE_URL}/api/v1/servers/${serverId}`, {
    headers: getHeaders(),
    tags: { type: 'api', operation: 'server_get' },
  });

  // 404 is acceptable for random UUIDs
  const success = check(res, {
    'get server status is 200 or 404': (r) => r.status === 200 || r.status === 404,
    'get server response time < 100ms': (r) => r.timings.duration < 100,
  });

  errorRate.add(!success && res.status !== 404);

  if (res.status === 429) {
    rateLimitHits.add(1);
  }
}

// ============================================================================
// Test Lifecycle
// ============================================================================

export function setup() {
  console.log('Starting k6 load tests for SARK API');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Scenario: ${SCENARIO}`);

  // Verify API is accessible
  const healthRes = http.get(`${BASE_URL}/health/`);
  if (healthRes.status !== 200) {
    throw new Error(`API health check failed: ${healthRes.status}`);
  }

  return { startTime: new Date() };
}

export function teardown(data) {
  const endTime = new Date();
  const duration = (endTime - data.startTime) / 1000;

  console.log(`\nTest completed in ${duration.toFixed(2)} seconds`);
  console.log('Check the k6 summary above for detailed metrics');
}
