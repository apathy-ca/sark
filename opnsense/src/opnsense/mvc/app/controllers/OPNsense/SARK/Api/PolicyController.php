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

use OPNsense\Base\ApiMutableModelControllerBase;
use OPNsense\Core\Backend;

/**
 * Class PolicyController
 * API controller for SARK policy management (enable/disable governance policies)
 * @package OPNsense\SARK\Api
 */
class PolicyController extends ApiMutableModelControllerBase
{
    protected static $internalModelClass = '\OPNsense\SARK\Policy';
    protected static $internalModelName = 'policy';

    /**
     * Get all policies configuration
     * @return array policies data
     */
    public function getAction()
    {
        return $this->getBase('policy', 'policy');
    }

    /**
     * Set policies configuration
     * @return array validation result
     */
    public function setAction()
    {
        $result = $this->setBase('policy', 'policy');
        if ($result['result'] !== 'failed') {
            // Notify backend to reload policies
            $backend = new Backend();
            $backend->configdRun('sark reload-policies');
        }
        return $result;
    }

    /**
     * Get list of available built-in policies
     * @return array available policies
     */
    public function getAvailableAction()
    {
        return [
            'policies' => [
                'token_limits' => [
                    'name' => gettext('Token Limits'),
                    'description' => gettext('Enforce daily token usage limits per user'),
                    'category' => 'budgetary'
                ],
                'cost_caps' => [
                    'name' => gettext('Cost Caps'),
                    'description' => gettext('Set maximum daily/monthly spending limits'),
                    'category' => 'budgetary'
                ],
                'bedtime_hours' => [
                    'name' => gettext('Bedtime Hours'),
                    'description' => gettext('Block AI access during specified hours'),
                    'category' => 'temporal'
                ],
                'homework_mode' => [
                    'name' => gettext('Homework Mode'),
                    'description' => gettext('Restrict to educational assistance only'),
                    'category' => 'educational'
                ],
                'age_appropriate' => [
                    'name' => gettext('Age-Appropriate Content'),
                    'description' => gettext('Filter responses based on user age'),
                    'category' => 'safety'
                ],
                'pii_protection' => [
                    'name' => gettext('PII Protection'),
                    'description' => gettext('Redact personal information from requests'),
                    'category' => 'privacy'
                ],
                'model_allowlist' => [
                    'name' => gettext('Model Allowlist'),
                    'description' => gettext('Restrict which AI models can be used'),
                    'category' => 'access'
                ],
                'rate_limiting' => [
                    'name' => gettext('Rate Limiting'),
                    'description' => gettext('Limit requests per minute per user'),
                    'category' => 'budgetary'
                ]
            ]
        ];
    }

    /**
     * Get policy rules (custom rules)
     * @return array rules
     */
    public function getRulesAction()
    {
        $mdl = $this->getModel();
        $result = [];
        foreach ($mdl->rules->rule->iterateItems() as $uuid => $rule) {
            $result[$uuid] = [
                'name' => (string)$rule->name,
                'type' => (string)$rule->type,
                'pattern' => (string)$rule->pattern,
                'action' => (string)$rule->action,
                'priority' => (string)$rule->priority,
                'enabled' => (string)$rule->enabled
            ];
        }
        return ['rules' => $result];
    }

    /**
     * Get a specific rule by UUID
     * @param string $uuid rule UUID
     * @return array rule data
     */
    public function getRuleAction($uuid = null)
    {
        return $this->getBase('rule', 'rules.rule', $uuid);
    }

    /**
     * Add a new policy rule
     * @return array result with UUID
     */
    public function addRuleAction()
    {
        if ($this->request->isPost()) {
            return $this->addBase('rule', 'rules.rule');
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Update a rule by UUID
     * @param string $uuid rule UUID
     * @return array validation result
     */
    public function setRuleAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->setBase('rule', 'rules.rule', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Delete a rule by UUID
     * @param string $uuid rule UUID
     * @return array result
     */
    public function delRuleAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->delBase('rules.rule', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Search policy rules
     * @return array search results
     */
    public function searchRulesAction()
    {
        return $this->searchBase('rules.rule', ['name', 'type', 'action', 'priority', 'enabled']);
    }

    /**
     * Toggle a built-in policy on/off
     * @return array result
     */
    public function toggleAction()
    {
        if ($this->request->isPost()) {
            $policyId = $this->request->getPost('policy_id');
            $enabled = $this->request->getPost('enabled');

            $mdl = $this->getModel();
            if (property_exists($mdl->builtIn, $policyId)) {
                $mdl->builtIn->$policyId->enabled = $enabled ? '1' : '0';
                $validationMessages = $mdl->performValidation();
                if (count($validationMessages) === 0) {
                    $mdl->serializeToConfig();
                    \OPNsense\Core\Config::getInstance()->save();

                    // Notify backend
                    $backend = new Backend();
                    $backend->configdRun('sark reload-policies');

                    return ['status' => 'ok'];
                }
                return ['status' => 'error', 'validations' => $validationMessages];
            }
            return ['status' => 'error', 'message' => 'Unknown policy'];
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Get policy status summary
     * @return array status of all policies
     */
    public function statusAction()
    {
        $mdl = $this->getModel();
        $backend = new Backend();

        // Get real-time policy status from backend
        $statusJson = $backend->configdRun('sark policy-status');
        $backendStatus = json_decode($statusJson, true) ?: [];

        return [
            'enabled_policies' => $backendStatus['enabled'] ?? [],
            'active_rules' => $backendStatus['rules_count'] ?? 0,
            'last_evaluation' => $backendStatus['last_evaluation'] ?? null,
            'violations_today' => $backendStatus['violations_today'] ?? 0
        ];
    }
}
