<?php

/**
 *    Copyright (C) 2024 SARK Project
 *
 *    All rights reserved.
 *
 *    Redistribution and use in source and binary forms, with or without
 *    modification, are permitted provided that the following conditions are met:
 *
 *    1. Redistributions of source code must retain the above copyright notice,
 *       this list of conditions and the following disclaimer.
 *
 *    2. Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *
 *    THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES,
 *    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
 *    AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *    AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
 *    OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *    SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *    CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *    ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *    POSSIBILITY OF SUCH DAMAGE.
 */

namespace OPNsense\SARK\Api;

use OPNsense\Base\ApiControllerBase;
use OPNsense\Core\Backend;

/**
 * Class AnalyticsController
 * API controller for SARK usage statistics and analytics
 * @package OPNsense\SARK\Api
 */
class AnalyticsController extends ApiControllerBase
{
    /**
     * Get usage summary for the dashboard
     * @return array usage summary
     */
    public function summaryAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics summary');
        $data = json_decode($response, true);

        if ($data === null) {
            return [
                'status' => 'ok',
                'summary' => [
                    'requests_today' => 0,
                    'tokens_today' => 0,
                    'cost_today' => 0.00,
                    'active_users' => 0,
                    'policy_violations' => 0
                ]
            ];
        }

        return [
            'status' => 'ok',
            'summary' => $data
        ];
    }

    /**
     * Get usage data for charts (hourly breakdown)
     * @return array hourly usage data
     */
    public function hourlyAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics hourly');
        $data = json_decode($response, true);

        if ($data === null) {
            // Return empty data structure for chart
            $hours = [];
            for ($i = 0; $i < 24; $i++) {
                $hours[] = [
                    'hour' => $i,
                    'requests' => 0,
                    'tokens' => 0
                ];
            }
            $data = ['hours' => $hours];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get daily usage for the past N days
     * @return array daily usage data
     */
    public function dailyAction()
    {
        $days = $this->request->get('days', 'int', 7);
        $days = min(max($days, 1), 90); // Clamp to 1-90 days

        $backend = new Backend();
        $response = $backend->configdRun("sark analytics daily {$days}");
        $data = json_decode($response, true);

        if ($data === null) {
            $data = ['days' => []];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get per-user usage statistics
     * @return array user usage data
     */
    public function usersAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics users');
        $data = json_decode($response, true);

        if ($data === null) {
            $data = ['users' => []];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get per-model usage statistics
     * @return array model usage data
     */
    public function modelsAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics models');
        $data = json_decode($response, true);

        if ($data === null) {
            $data = ['models' => []];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get cost breakdown by provider
     * @return array cost data
     */
    public function costsAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics costs');
        $data = json_decode($response, true);

        if ($data === null) {
            $data = [
                'total' => 0.00,
                'by_provider' => [],
                'by_user' => [],
                'by_model' => []
            ];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get policy violation statistics
     * @return array violation data
     */
    public function violationsAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics violations');
        $data = json_decode($response, true);

        if ($data === null) {
            $data = [
                'total' => 0,
                'by_policy' => [],
                'by_user' => [],
                'recent' => []
            ];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Get real-time statistics (for live dashboard updates)
     * @return array real-time stats
     */
    public function realtimeAction()
    {
        $backend = new Backend();
        $response = $backend->configdRun('sark analytics realtime');
        $data = json_decode($response, true);

        if ($data === null) {
            $data = [
                'active_sessions' => 0,
                'requests_per_minute' => 0,
                'tokens_per_minute' => 0,
                'queue_depth' => 0,
                'latency_ms' => 0
            ];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }

    /**
     * Export analytics data in various formats
     * @return array export data or file download
     */
    public function exportAction()
    {
        $format = $this->request->get('format', 'string', 'json');
        $period = $this->request->get('period', 'string', 'day');

        $backend = new Backend();
        $response = $backend->configdRun("sark analytics export {$format} {$period}");

        if ($format === 'csv') {
            $this->response->setContentType('text/csv');
            $this->response->setHeader('Content-Disposition', 'attachment; filename="sark-analytics.csv"');
            $this->response->setContent($response);
            return $this->response;
        }

        $data = json_decode($response, true);
        return [
            'status' => 'ok',
            'data' => $data ?: []
        ];
    }

    /**
     * Get logs with optional filtering
     * @return array log entries
     */
    public function logsAction()
    {
        $limit = $this->request->get('limit', 'int', 100);
        $offset = $this->request->get('offset', 'int', 0);
        $level = $this->request->get('level', 'string', '');
        $user = $this->request->get('user', 'string', '');

        $limit = min(max($limit, 1), 1000);
        $offset = max($offset, 0);

        $args = "limit={$limit} offset={$offset}";
        if (!empty($level)) {
            $args .= " level=" . escapeshellarg($level);
        }
        if (!empty($user)) {
            $args .= " user=" . escapeshellarg($user);
        }

        $backend = new Backend();
        $response = $backend->configdRun("sark analytics logs {$args}");
        $data = json_decode($response, true);

        if ($data === null) {
            $data = [
                'logs' => [],
                'total' => 0
            ];
        }

        return [
            'status' => 'ok',
            'data' => $data
        ];
    }
}
