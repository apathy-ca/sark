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
 * Class ServiceController
 * API controller for SARK service management (start/stop/status)
 * @package OPNsense\SARK\Api
 */
class ServiceController extends ApiControllerBase
{
    /**
     * Start SARK service
     * @return array status response
     */
    public function startAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = trim($backend->configdRun('sark start'));
            return [
                'status' => 'ok',
                'message' => $response
            ];
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Stop SARK service
     * @return array status response
     */
    public function stopAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = trim($backend->configdRun('sark stop'));
            return [
                'status' => 'ok',
                'message' => $response
            ];
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Restart SARK service
     * @return array status response
     */
    public function restartAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            $response = trim($backend->configdRun('sark restart'));
            return [
                'status' => 'ok',
                'message' => $response
            ];
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Get SARK service status
     * @return array status response with running state
     */
    public function statusAction()
    {
        $backend = new Backend();
        $response = trim($backend->configdRun('sark status'));
        $isRunning = strpos($response, 'running') !== false ||
                     strpos($response, 'is running') !== false;
        return [
            'status' => $isRunning ? 'running' : 'stopped',
            'message' => $response
        ];
    }

    /**
     * Reconfigure SARK service (reload configuration)
     * @return array status response
     */
    public function reconfigureAction()
    {
        if ($this->request->isPost()) {
            $backend = new Backend();
            // First template the configuration
            $backend->configdRun('template reload OPNsense/SARK');
            // Then restart the service
            $response = trim($backend->configdRun('sark restart'));
            return [
                'status' => 'ok',
                'message' => $response
            ];
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }
}
