{#
    Copyright (C) 2024 SARK Project
    All rights reserved.

    SARK Home Gateway - Policies View
#}

<div class="content-box">
    <div class="content-box-header">
        <h3>{{ lang._('SARK Policies') }}</h3>
    </div>
    <div class="content-box-main">
        <ul class="nav nav-tabs" role="tablist">
            <li class="active">
                <a data-toggle="tab" href="#builtin">
                    <i class="fa fa-shield"></i> {{ lang._('Built-in Policies') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#custom">
                    <i class="fa fa-code"></i> {{ lang._('Custom Rules') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#homework">
                    <i class="fa fa-book"></i> {{ lang._('Homework Mode') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#pii">
                    <i class="fa fa-user-secret"></i> {{ lang._('PII Protection') }}
                </a>
            </li>
        </ul>

        <div class="tab-content">
            {# Built-in Policies Tab #}
            <div id="builtin" class="tab-pane fade in active">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-shield"></i> {{ lang._('Built-in Governance Policies') }}
                    </div>
                    <div class="panel-body">
                        <p class="text-muted">{{ lang._('Toggle built-in policies to control AI usage in your home.') }}</p>

                        <div class="row" id="policyToggles">
                            {# Policies will be loaded dynamically #}
                        </div>
                    </div>
                </div>

                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-list"></i> {{ lang._('Model Allowlist') }}
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <div class="checkbox">
                                <label>
                                    <input type="checkbox" id="policy_modelAllowlist">
                                    {{ lang._('Enable model allowlist (restrict to approved models only)') }}
                                </label>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="policy_allowedModels">{{ lang._('Allowed Models') }}</label>
                            <input type="text" class="form-control" id="policy_allowedModels"
                                   placeholder="gpt-4o,gpt-4o-mini,claude-3-5-sonnet,claude-3-haiku">
                            <span class="help-block">{{ lang._('Comma-separated list of allowed model identifiers') }}</span>
                        </div>
                    </div>
                </div>
            </div>

            {# Custom Rules Tab #}
            <div id="custom" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-code"></i> {{ lang._('Custom Policy Rules') }}
                        <button class="btn btn-primary btn-xs pull-right" id="addRule">
                            <i class="fa fa-plus"></i> {{ lang._('Add Rule') }}
                        </button>
                    </div>
                    <div class="panel-body">
                        <table class="table table-striped table-condensed" id="rulesTable">
                            <thead>
                                <tr>
                                    <th>{{ lang._('Name') }}</th>
                                    <th>{{ lang._('Type') }}</th>
                                    <th>{{ lang._('Pattern') }}</th>
                                    <th>{{ lang._('Action') }}</th>
                                    <th>{{ lang._('Priority') }}</th>
                                    <th>{{ lang._('Enabled') }}</th>
                                    <th>{{ lang._('Actions') }}</th>
                                </tr>
                            </thead>
                            <tbody id="rulesTableBody">
                                <tr><td colspan="7" class="text-center">{{ lang._('Loading...') }}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {# Homework Mode Tab #}
            <div id="homework" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-book"></i> {{ lang._('Homework Mode Settings') }}
                    </div>
                    <div class="panel-body">
                        <p class="text-muted">{{ lang._('When homework mode is enabled, AI assistance is limited to educational topics and encourages learning rather than providing direct answers.') }}</p>

                        <div class="form-group">
                            <div class="checkbox">
                                <label>
                                    <input type="checkbox" id="policy_homeworkMode">
                                    {{ lang._('Enable Homework Mode') }}
                                </label>
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="homework_subjects">{{ lang._('Allowed Subjects') }}</label>
                            <input type="text" class="form-control" id="homework_subjects"
                                   value="math,science,history,english,programming">
                            <span class="help-block">{{ lang._('Comma-separated list of allowed subject areas') }}</span>
                        </div>

                        <div class="form-group">
                            <div class="checkbox">
                                <label>
                                    <input type="checkbox" id="homework_noDirectAnswers" checked>
                                    {{ lang._('Discourage direct answers (encourage explanation)') }}
                                </label>
                            </div>
                        </div>

                        <div class="form-group">
                            <div class="checkbox">
                                <label>
                                    <input type="checkbox" id="homework_requireExplanation" checked>
                                    {{ lang._('Require step-by-step explanations') }}
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {# PII Protection Tab #}
            <div id="pii" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-user-secret"></i> {{ lang._('PII Protection Settings') }}
                    </div>
                    <div class="panel-body">
                        <p class="text-muted">{{ lang._('Automatically detect and redact personal information from AI requests to protect family privacy.') }}</p>

                        <div class="form-group">
                            <div class="checkbox">
                                <label>
                                    <input type="checkbox" id="policy_piiProtection" checked>
                                    {{ lang._('Enable PII Protection') }}
                                </label>
                            </div>
                        </div>

                        <h4>{{ lang._('Information Types to Redact') }}</h4>
                        <div class="row">
                            <div class="col-md-6">
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_names" checked>
                                        {{ lang._('Full Names') }}
                                    </label>
                                </div>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_addresses" checked>
                                        {{ lang._('Street Addresses') }}
                                    </label>
                                </div>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_phones" checked>
                                        {{ lang._('Phone Numbers') }}
                                    </label>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_emails" checked>
                                        {{ lang._('Email Addresses') }}
                                    </label>
                                </div>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_ssn" checked>
                                        {{ lang._('Social Security Numbers') }}
                                    </label>
                                </div>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="pii_creditCards" checked>
                                        {{ lang._('Credit Card Numbers') }}
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {# Save Button #}
        <div class="row">
            <div class="col-md-12">
                <hr>
                <button class="btn btn-primary" id="savePolicies">
                    <i class="fa fa-save"></i> {{ lang._('Save') }}
                </button>
                <button class="btn btn-default" id="applyPolicies">
                    <i class="fa fa-check"></i> {{ lang._('Save & Apply') }}
                </button>
            </div>
        </div>
    </div>
</div>

{# Rule Modal #}
<div class="modal fade" id="ruleModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title" id="ruleModalTitle">{{ lang._('Add Rule') }}</h4>
            </div>
            <div class="modal-body">
                <form id="ruleForm">
                    <input type="hidden" id="rule_uuid">
                    <div class="form-group">
                        <label for="rule_name">{{ lang._('Rule Name') }}</label>
                        <input type="text" class="form-control" id="rule_name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="rule_type">{{ lang._('Rule Type') }}</label>
                        <select class="form-control" id="rule_type" name="type">
                            <option value="block_keyword">{{ lang._('Block Keyword') }}</option>
                            <option value="block_pattern">{{ lang._('Block Pattern (Regex)') }}</option>
                            <option value="allow_keyword">{{ lang._('Allow Keyword') }}</option>
                            <option value="rate_limit">{{ lang._('Rate Limit') }}</option>
                            <option value="transform">{{ lang._('Transform Content') }}</option>
                            <option value="alert">{{ lang._('Alert Only') }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="rule_pattern">{{ lang._('Pattern / Keyword') }}</label>
                        <input type="text" class="form-control" id="rule_pattern" name="pattern" required>
                        <span class="help-block">{{ lang._('Enter keyword or regex pattern to match') }}</span>
                    </div>
                    <div class="form-group">
                        <label for="rule_action">{{ lang._('Action') }}</label>
                        <select class="form-control" id="rule_action" name="action">
                            <option value="block">{{ lang._('Block Request') }}</option>
                            <option value="warn">{{ lang._('Warn User') }}</option>
                            <option value="log">{{ lang._('Log Only') }}</option>
                            <option value="redact">{{ lang._('Redact Content') }}</option>
                            <option value="notify">{{ lang._('Notify Parent') }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="rule_priority">{{ lang._('Priority') }}</label>
                        <input type="number" class="form-control" id="rule_priority" name="priority" value="50" min="1" max="100">
                        <span class="help-block">{{ lang._('1-100, higher = more important') }}</span>
                    </div>
                    <div class="form-group">
                        <label for="rule_appliesToUsers">{{ lang._('Apply to Users') }}</label>
                        <input type="text" class="form-control" id="rule_appliesToUsers" name="appliesToUsers" placeholder="user1,user2">
                        <span class="help-block">{{ lang._('Leave empty to apply to all users') }}</span>
                    </div>
                    <div class="form-group">
                        <div class="checkbox">
                            <label>
                                <input type="checkbox" id="rule_enabled" name="enabled" checked>
                                {{ lang._('Enabled') }}
                            </label>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">{{ lang._('Cancel') }}</button>
                <button type="button" class="btn btn-primary" id="saveRule">{{ lang._('Save') }}</button>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Load available policies
    function loadAvailablePolicies() {
        $.ajax({
            url: '/api/sark/policy/getAvailable',
            success: function(data) {
                if (data.policies) {
                    var container = $('#policyToggles');
                    container.empty();

                    $.each(data.policies, function(id, policy) {
                        var categoryColors = {
                            'budgetary': 'label-success',
                            'temporal': 'label-info',
                            'educational': 'label-primary',
                            'safety': 'label-danger',
                            'privacy': 'label-warning',
                            'access': 'label-default'
                        };

                        var html = '<div class="col-md-6">' +
                            '<div class="panel panel-default">' +
                                '<div class="panel-body">' +
                                    '<div class="checkbox">' +
                                        '<label>' +
                                            '<input type="checkbox" class="policy-toggle" data-policy="' + id + '"> ' +
                                            '<strong>' + policy.name + '</strong>' +
                                        '</label>' +
                                        '<span class="label ' + (categoryColors[policy.category] || 'label-default') + ' pull-right">' +
                                            policy.category +
                                        '</span>' +
                                    '</div>' +
                                    '<p class="text-muted small">' + policy.description + '</p>' +
                                '</div>' +
                            '</div>' +
                        '</div>';
                        container.append(html);
                    });
                }
            }
        });
    }

    // Load current policy configuration
    function loadPolicies() {
        $.ajax({
            url: '/api/sark/policy/get',
            success: function(data) {
                if (data.policy) {
                    var p = data.policy;
                    // Set built-in toggles
                    if (p.builtIn) {
                        $('.policy-toggle[data-policy="token_limits"]').prop('checked', p.builtIn.tokenLimits === '1');
                        $('.policy-toggle[data-policy="cost_caps"]').prop('checked', p.builtIn.costCaps === '1');
                        $('.policy-toggle[data-policy="bedtime_hours"]').prop('checked', p.builtIn.bedtimeHours === '1');
                        $('.policy-toggle[data-policy="homework_mode"]').prop('checked', p.builtIn.homeworkMode === '1');
                        $('.policy-toggle[data-policy="age_appropriate"]').prop('checked', p.builtIn.ageAppropriate === '1');
                        $('.policy-toggle[data-policy="pii_protection"]').prop('checked', p.builtIn.piiProtection === '1');
                        $('.policy-toggle[data-policy="model_allowlist"]').prop('checked', p.builtIn.modelAllowlist === '1');
                        $('.policy-toggle[data-policy="rate_limiting"]').prop('checked', p.builtIn.rateLimiting === '1');
                    }

                    // Model allowlist
                    $('#policy_modelAllowlist').prop('checked', p.builtIn && p.builtIn.modelAllowlist === '1');
                    $('#policy_allowedModels').val(p.allowedModels);

                    // Homework settings
                    $('#policy_homeworkMode').prop('checked', p.builtIn && p.builtIn.homeworkMode === '1');
                    if (p.homeworkSettings) {
                        $('#homework_subjects').val(p.homeworkSettings.subjectsAllowed);
                        $('#homework_noDirectAnswers').prop('checked', p.homeworkSettings.noDirectAnswers === '1');
                        $('#homework_requireExplanation').prop('checked', p.homeworkSettings.requireExplanation === '1');
                    }

                    // PII settings
                    $('#policy_piiProtection').prop('checked', p.builtIn && p.builtIn.piiProtection === '1');
                    if (p.piiSettings) {
                        $('#pii_names').prop('checked', p.piiSettings.redactNames === '1');
                        $('#pii_addresses').prop('checked', p.piiSettings.redactAddresses === '1');
                        $('#pii_phones').prop('checked', p.piiSettings.redactPhones === '1');
                        $('#pii_emails').prop('checked', p.piiSettings.redactEmails === '1');
                        $('#pii_ssn').prop('checked', p.piiSettings.redactSSN === '1');
                        $('#pii_creditCards').prop('checked', p.piiSettings.redactCreditCards === '1');
                    }
                }
            }
        });
    }

    // Load custom rules
    function loadRules() {
        $.ajax({
            url: '/api/sark/policy/getRules',
            success: function(data) {
                var tbody = $('#rulesTableBody');
                tbody.empty();
                if (data.rules && Object.keys(data.rules).length > 0) {
                    $.each(data.rules, function(uuid, rule) {
                        var row = '<tr data-uuid="' + uuid + '">' +
                            '<td>' + rule.name + '</td>' +
                            '<td>' + rule.type + '</td>' +
                            '<td><code>' + rule.pattern.substring(0, 30) + (rule.pattern.length > 30 ? '...' : '') + '</code></td>' +
                            '<td>' + rule.action + '</td>' +
                            '<td>' + rule.priority + '</td>' +
                            '<td>' + (rule.enabled === '1' ? '<i class="fa fa-check text-success"></i>' : '<i class="fa fa-times text-danger"></i>') + '</td>' +
                            '<td>' +
                                '<button class="btn btn-xs btn-default editRule"><i class="fa fa-pencil"></i></button> ' +
                                '<button class="btn btn-xs btn-danger deleteRule"><i class="fa fa-trash"></i></button>' +
                            '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                } else {
                    tbody.html('<tr><td colspan="7" class="text-center">{{ lang._("No custom rules configured") }}</td></tr>');
                }
            }
        });
    }

    // Save policies
    $('#savePolicies').click(function() {
        var data = {
            policy: {
                builtIn: {
                    tokenLimits: $('.policy-toggle[data-policy="token_limits"]').is(':checked') ? '1' : '0',
                    costCaps: $('.policy-toggle[data-policy="cost_caps"]').is(':checked') ? '1' : '0',
                    bedtimeHours: $('.policy-toggle[data-policy="bedtime_hours"]').is(':checked') ? '1' : '0',
                    homeworkMode: $('#policy_homeworkMode').is(':checked') ? '1' : '0',
                    ageAppropriate: $('.policy-toggle[data-policy="age_appropriate"]').is(':checked') ? '1' : '0',
                    piiProtection: $('#policy_piiProtection').is(':checked') ? '1' : '0',
                    modelAllowlist: $('#policy_modelAllowlist').is(':checked') ? '1' : '0',
                    rateLimiting: $('.policy-toggle[data-policy="rate_limiting"]').is(':checked') ? '1' : '0'
                },
                allowedModels: $('#policy_allowedModels').val(),
                homeworkSettings: {
                    subjectsAllowed: $('#homework_subjects').val(),
                    noDirectAnswers: $('#homework_noDirectAnswers').is(':checked') ? '1' : '0',
                    requireExplanation: $('#homework_requireExplanation').is(':checked') ? '1' : '0'
                },
                piiSettings: {
                    redactNames: $('#pii_names').is(':checked') ? '1' : '0',
                    redactAddresses: $('#pii_addresses').is(':checked') ? '1' : '0',
                    redactPhones: $('#pii_phones').is(':checked') ? '1' : '0',
                    redactEmails: $('#pii_emails').is(':checked') ? '1' : '0',
                    redactSSN: $('#pii_ssn').is(':checked') ? '1' : '0',
                    redactCreditCards: $('#pii_creditCards').is(':checked') ? '1' : '0'
                }
            }
        };

        $.ajax({
            url: '/api/sark/policy/set',
            type: 'POST',
            data: data,
            success: function(response) {
                if (response.result !== 'failed') {
                    alert('{{ lang._("Policies saved successfully") }}');
                } else {
                    alert('{{ lang._("Error saving policies") }}: ' + JSON.stringify(response.validations));
                }
            }
        });
    });

    // Save & Apply
    $('#applyPolicies').click(function() {
        $('#savePolicies').click();
        setTimeout(function() {
            $.post('/api/sark/service/reconfigure', function() {
                alert('{{ lang._("Policies applied") }}');
            });
        }, 500);
    });

    // Rule management
    $('#addRule').click(function() {
        $('#ruleModalTitle').text('{{ lang._("Add Rule") }}');
        $('#ruleForm')[0].reset();
        $('#rule_uuid').val('');
        $('#ruleModal').modal('show');
    });

    $(document).on('click', '.editRule', function() {
        var uuid = $(this).closest('tr').data('uuid');
        $.ajax({
            url: '/api/sark/policy/getRule/' + uuid,
            success: function(data) {
                if (data.rule) {
                    var r = data.rule;
                    $('#ruleModalTitle').text('{{ lang._("Edit Rule") }}');
                    $('#rule_uuid').val(uuid);
                    $('#rule_name').val(r.name);
                    $('#rule_type').val(r.type);
                    $('#rule_pattern').val(r.pattern);
                    $('#rule_action').val(r.action);
                    $('#rule_priority').val(r.priority);
                    $('#rule_appliesToUsers').val(r.appliesToUsers);
                    $('#rule_enabled').prop('checked', r.enabled === '1');
                    $('#ruleModal').modal('show');
                }
            }
        });
    });

    $(document).on('click', '.deleteRule', function() {
        if (confirm('{{ lang._("Delete this rule?") }}')) {
            var uuid = $(this).closest('tr').data('uuid');
            $.post('/api/sark/policy/delRule/' + uuid, function() {
                loadRules();
            });
        }
    });

    $('#saveRule').click(function() {
        var uuid = $('#rule_uuid').val();
        var data = {
            rule: {
                name: $('#rule_name').val(),
                type: $('#rule_type').val(),
                pattern: $('#rule_pattern').val(),
                action: $('#rule_action').val(),
                priority: $('#rule_priority').val(),
                appliesToUsers: $('#rule_appliesToUsers').val(),
                enabled: $('#rule_enabled').is(':checked') ? '1' : '0'
            }
        };

        var url = uuid ? '/api/sark/policy/setRule/' + uuid : '/api/sark/policy/addRule';
        $.post(url, data, function(response) {
            if (response.result !== 'failed') {
                $('#ruleModal').modal('hide');
                loadRules();
            } else {
                alert('Error: ' + JSON.stringify(response.validations));
            }
        });
    });

    // Initialize
    loadAvailablePolicies();
    setTimeout(loadPolicies, 500); // Give time for available policies to load
    loadRules();
});
</script>
