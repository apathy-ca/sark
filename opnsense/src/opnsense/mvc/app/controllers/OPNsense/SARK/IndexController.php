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

namespace OPNsense\SARK;

/**
 * Class IndexController
 * Main dashboard controller for SARK Home Gateway plugin
 * @package OPNsense\SARK
 */
class IndexController extends \OPNsense\Base\IndexController
{
    /**
     * Dashboard page - shows usage statistics and service status
     */
    public function indexAction()
    {
        $this->view->pick('OPNsense/SARK/index');
        $this->view->title = gettext('SARK Home Gateway');
        $this->view->formGeneralSettings = $this->getForm('general');
    }

    /**
     * Settings page - configure SARK home deployment
     */
    public function settingsAction()
    {
        $this->view->pick('OPNsense/SARK/settings');
        $this->view->title = gettext('SARK Settings');
        $this->view->formGeneralSettings = $this->getForm('general');
    }

    /**
     * Policies page - manage governance policies
     */
    public function policiesAction()
    {
        $this->view->pick('OPNsense/SARK/policies');
        $this->view->title = gettext('SARK Policies');
        $this->view->formPolicies = $this->getForm('policies');
    }

    /**
     * Logs page - view audit logs and events
     */
    public function logsAction()
    {
        $this->view->pick('OPNsense/SARK/logs');
        $this->view->title = gettext('SARK Logs');
    }
}
