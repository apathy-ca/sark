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
use OPNsense\Core\Config;

/**
 * Class SettingsController
 * API controller for SARK configuration management
 * @package OPNsense\SARK\Api
 */
class SettingsController extends ApiMutableModelControllerBase
{
    protected static $internalModelClass = '\OPNsense\SARK\General';
    protected static $internalModelName = 'general';

    /**
     * Get general settings
     * @return array settings data
     */
    public function getAction()
    {
        return $this->getBase('general', 'general');
    }

    /**
     * Set general settings
     * @return array validation result
     */
    public function setAction()
    {
        return $this->setBase('general', 'general');
    }

    /**
     * Get user/household configuration
     * @return array user settings
     */
    public function getUsersAction()
    {
        $mdl = $this->getModel();
        $result = [];
        foreach ($mdl->users->user->iterateItems() as $uuid => $user) {
            $result[$uuid] = [
                'name' => (string)$user->name,
                'role' => (string)$user->role,
                'dailyLimit' => (string)$user->dailyLimit,
                'enabled' => (string)$user->enabled
            ];
        }
        return ['users' => $result];
    }

    /**
     * Add a new user
     * @return array result with UUID
     */
    public function addUserAction()
    {
        if ($this->request->isPost()) {
            $result = $this->addBase('user', 'users.user');
            return $result;
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Update a user by UUID
     * @param string $uuid user UUID
     * @return array validation result
     */
    public function setUserAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->setBase('user', 'users.user', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Delete a user by UUID
     * @param string $uuid user UUID
     * @return array result
     */
    public function delUserAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->delBase('users.user', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Search users
     * @return array search results
     */
    public function searchUsersAction()
    {
        return $this->searchBase('users.user', ['name', 'role', 'dailyLimit', 'enabled']);
    }

    /**
     * Get API provider configuration
     * @return array provider settings
     */
    public function getProvidersAction()
    {
        $mdl = $this->getModel();
        $result = [];
        foreach ($mdl->providers->provider->iterateItems() as $uuid => $provider) {
            $result[$uuid] = [
                'name' => (string)$provider->name,
                'type' => (string)$provider->type,
                'enabled' => (string)$provider->enabled,
                'rateLimit' => (string)$provider->rateLimit
            ];
        }
        return ['providers' => $result];
    }

    /**
     * Get a specific provider by UUID
     * @param string $uuid provider UUID
     * @return array provider data
     */
    public function getProviderAction($uuid = null)
    {
        return $this->getBase('provider', 'providers.provider', $uuid);
    }

    /**
     * Add a new API provider
     * @return array result with UUID
     */
    public function addProviderAction()
    {
        if ($this->request->isPost()) {
            return $this->addBase('provider', 'providers.provider');
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Update a provider by UUID
     * @param string $uuid provider UUID
     * @return array validation result
     */
    public function setProviderAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->setBase('provider', 'providers.provider', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Delete a provider by UUID
     * @param string $uuid provider UUID
     * @return array result
     */
    public function delProviderAction($uuid)
    {
        if ($this->request->isPost()) {
            return $this->delBase('providers.provider', $uuid);
        }
        return ['status' => 'error', 'message' => 'POST request required'];
    }

    /**
     * Search providers
     * @return array search results
     */
    public function searchProvidersAction()
    {
        return $this->searchBase('providers.provider', ['name', 'type', 'enabled', 'rateLimit']);
    }
}
