{#
    Copyright (C) 2024 SARK Project
    All rights reserved.

    SARK Home Gateway - Settings View
#}

<div class="content-box">
    <div class="content-box-header">
        <h3>{{ lang._('SARK Settings') }}</h3>
    </div>
    <div class="content-box-main">
        <ul class="nav nav-tabs" role="tablist">
            <li class="active">
                <a data-toggle="tab" href="#general">
                    <i class="fa fa-cog"></i> {{ lang._('General') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#budget">
                    <i class="fa fa-dollar"></i> {{ lang._('Budget') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#users">
                    <i class="fa fa-users"></i> {{ lang._('Users') }}
                </a>
            </li>
            <li>
                <a data-toggle="tab" href="#providers">
                    <i class="fa fa-cloud"></i> {{ lang._('Providers') }}
                </a>
            </li>
        </ul>

        <div class="tab-content">
            {# General Settings Tab #}
            <div id="general" class="tab-pane fade in active">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-cog"></i> {{ lang._('Service Configuration') }}
                    </div>
                    <div class="panel-body">
                        <form id="generalForm">
                            <div class="form-group">
                                <label>{{ lang._('Enable SARK') }}</label>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="general_enabled" name="enabled">
                                        {{ lang._('Enable SARK Home Gateway') }}
                                    </label>
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="general_mode">{{ lang._('Governance Mode') }}</label>
                                <select class="form-control" id="general_mode" name="mode">
                                    <option value="observe">{{ lang._('Observe Only - Monitor without blocking') }}</option>
                                    <option value="advisory">{{ lang._('Advisory - Warn but allow') }}</option>
                                    <option value="enforce">{{ lang._('Enforce - Block policy violations') }}</option>
                                </select>
                                <span class="help-block">{{ lang._('How strictly to enforce governance policies') }}</span>
                            </div>
                            <div class="form-group">
                                <label for="general_listenAddress">{{ lang._('Listen Address') }}</label>
                                <input type="text" class="form-control" id="general_listenAddress" name="listenAddress" value="0.0.0.0">
                                <span class="help-block">{{ lang._('IP address to listen on (0.0.0.0 for all)') }}</span>
                            </div>
                            <div class="form-group">
                                <label for="general_listenPort">{{ lang._('Listen Port') }}</label>
                                <input type="number" class="form-control" id="general_listenPort" name="listenPort" value="8443" min="1" max="65535">
                                <span class="help-block">{{ lang._('Port for the SARK proxy') }}</span>
                            </div>
                            <div class="form-group">
                                <label>{{ lang._('TLS/HTTPS') }}</label>
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="general_tlsEnabled" name="tlsEnabled" checked>
                                        {{ lang._('Enable TLS encryption') }}
                                    </label>
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="general_logLevel">{{ lang._('Log Level') }}</label>
                                <select class="form-control" id="general_logLevel" name="logLevel">
                                    <option value="debug">{{ lang._('Debug') }}</option>
                                    <option value="info" selected>{{ lang._('Info') }}</option>
                                    <option value="warning">{{ lang._('Warning') }}</option>
                                    <option value="error">{{ lang._('Error') }}</option>
                                </select>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            {# Budget Tab #}
            <div id="budget" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-dollar"></i> {{ lang._('Budget Controls') }}
                    </div>
                    <div class="panel-body">
                        <form id="budgetForm">
                            <div class="form-group">
                                <label for="general_dailyTokenLimit">{{ lang._('Daily Token Limit') }}</label>
                                <input type="number" class="form-control" id="general_dailyTokenLimit" name="dailyTokenLimit" value="100000" min="0">
                                <span class="help-block">{{ lang._('Maximum tokens per day (0 for unlimited)') }}</span>
                            </div>
                            <div class="form-group">
                                <label for="general_dailyCostLimit">{{ lang._('Daily Cost Limit ($)') }}</label>
                                <input type="text" class="form-control" id="general_dailyCostLimit" name="dailyCostLimit" value="5.00">
                                <span class="help-block">{{ lang._('Maximum spending per day') }}</span>
                            </div>
                            <div class="form-group">
                                <label for="general_monthlyBudget">{{ lang._('Monthly Budget ($)') }}</label>
                                <input type="text" class="form-control" id="general_monthlyBudget" name="monthlyBudget" value="50.00">
                                <span class="help-block">{{ lang._('Total monthly spending limit') }}</span>
                            </div>
                            <hr>
                            <h4>{{ lang._('Bedtime Controls') }}</h4>
                            <div class="form-group">
                                <div class="checkbox">
                                    <label>
                                        <input type="checkbox" id="general_bedtimeEnabled" name="bedtimeEnabled">
                                        {{ lang._('Enable bedtime restrictions') }}
                                    </label>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label for="general_bedtimeStart">{{ lang._('Bedtime Start') }}</label>
                                        <input type="text" class="form-control" id="general_bedtimeStart" name="bedtimeStart" value="21:00" placeholder="HH:MM">
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label for="general_bedtimeEnd">{{ lang._('Bedtime End') }}</label>
                                        <input type="text" class="form-control" id="general_bedtimeEnd" name="bedtimeEnd" value="07:00" placeholder="HH:MM">
                                    </div>
                                </div>
                            </div>
                            <div class="form-group">
                                <label for="general_bedtimeUsers">{{ lang._('Bedtime Users') }}</label>
                                <input type="text" class="form-control" id="general_bedtimeUsers" name="bedtimeUsers" placeholder="user1,user2">
                                <span class="help-block">{{ lang._('Comma-separated list of users (empty = all children)') }}</span>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            {# Users Tab #}
            <div id="users" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-users"></i> {{ lang._('Household Users') }}
                        <button class="btn btn-primary btn-xs pull-right" id="addUser">
                            <i class="fa fa-plus"></i> {{ lang._('Add User') }}
                        </button>
                    </div>
                    <div class="panel-body">
                        <table class="table table-striped table-condensed" id="usersTable">
                            <thead>
                                <tr>
                                    <th>{{ lang._('Name') }}</th>
                                    <th>{{ lang._('Role') }}</th>
                                    <th>{{ lang._('Daily Limit') }}</th>
                                    <th>{{ lang._('Enabled') }}</th>
                                    <th>{{ lang._('Actions') }}</th>
                                </tr>
                            </thead>
                            <tbody id="usersTableBody">
                                <tr><td colspan="5" class="text-center">{{ lang._('Loading...') }}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            {# Providers Tab #}
            <div id="providers" class="tab-pane fade">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-cloud"></i> {{ lang._('API Providers') }}
                        <button class="btn btn-primary btn-xs pull-right" id="addProvider">
                            <i class="fa fa-plus"></i> {{ lang._('Add Provider') }}
                        </button>
                    </div>
                    <div class="panel-body">
                        <table class="table table-striped table-condensed" id="providersTable">
                            <thead>
                                <tr>
                                    <th>{{ lang._('Name') }}</th>
                                    <th>{{ lang._('Type') }}</th>
                                    <th>{{ lang._('Rate Limit') }}</th>
                                    <th>{{ lang._('Enabled') }}</th>
                                    <th>{{ lang._('Actions') }}</th>
                                </tr>
                            </thead>
                            <tbody id="providersTableBody">
                                <tr><td colspan="5" class="text-center">{{ lang._('Loading...') }}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        {# Save Button #}
        <div class="row">
            <div class="col-md-12">
                <hr>
                <button class="btn btn-primary" id="saveSettings">
                    <i class="fa fa-save"></i> {{ lang._('Save') }}
                </button>
                <button class="btn btn-default" id="applySettings">
                    <i class="fa fa-check"></i> {{ lang._('Save & Apply') }}
                </button>
            </div>
        </div>
    </div>
</div>

{# User Modal #}
<div class="modal fade" id="userModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title" id="userModalTitle">{{ lang._('Add User') }}</h4>
            </div>
            <div class="modal-body">
                <form id="userForm">
                    <input type="hidden" id="user_uuid">
                    <div class="form-group">
                        <label for="user_name">{{ lang._('Username') }}</label>
                        <input type="text" class="form-control" id="user_name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="user_role">{{ lang._('Role') }}</label>
                        <select class="form-control" id="user_role" name="role">
                            <option value="admin">{{ lang._('Administrator') }}</option>
                            <option value="parent">{{ lang._('Parent') }}</option>
                            <option value="child" selected>{{ lang._('Child') }}</option>
                            <option value="guest">{{ lang._('Guest') }}</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="user_dailyLimit">{{ lang._('Daily Token Limit') }}</label>
                        <input type="number" class="form-control" id="user_dailyLimit" name="dailyLimit" value="10000" min="0">
                    </div>
                    <div class="form-group">
                        <div class="checkbox">
                            <label>
                                <input type="checkbox" id="user_enabled" name="enabled" checked>
                                {{ lang._('Enabled') }}
                            </label>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">{{ lang._('Cancel') }}</button>
                <button type="button" class="btn btn-primary" id="saveUser">{{ lang._('Save') }}</button>
            </div>
        </div>
    </div>
</div>

{# Provider Modal #}
<div class="modal fade" id="providerModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title" id="providerModalTitle">{{ lang._('Add Provider') }}</h4>
            </div>
            <div class="modal-body">
                <form id="providerForm">
                    <input type="hidden" id="provider_uuid">
                    <div class="form-group">
                        <label for="provider_name">{{ lang._('Name') }}</label>
                        <input type="text" class="form-control" id="provider_name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="provider_type">{{ lang._('Type') }}</label>
                        <select class="form-control" id="provider_type" name="type">
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="google">Google AI</option>
                            <option value="azure">Azure OpenAI</option>
                            <option value="local">Local/Ollama</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="provider_apiKey">{{ lang._('API Key') }}</label>
                        <input type="password" class="form-control" id="provider_apiKey" name="apiKey">
                        <span class="help-block">{{ lang._('Leave empty to use environment variable') }}</span>
                    </div>
                    <div class="form-group">
                        <label for="provider_endpoint">{{ lang._('Custom Endpoint') }}</label>
                        <input type="url" class="form-control" id="provider_endpoint" name="endpoint" placeholder="https://api.example.com/v1">
                        <span class="help-block">{{ lang._('Optional: override default API endpoint') }}</span>
                    </div>
                    <div class="form-group">
                        <label for="provider_rateLimit">{{ lang._('Rate Limit (req/min)') }}</label>
                        <input type="number" class="form-control" id="provider_rateLimit" name="rateLimit" value="60" min="0">
                    </div>
                    <div class="form-group">
                        <div class="checkbox">
                            <label>
                                <input type="checkbox" id="provider_enabled" name="enabled" checked>
                                {{ lang._('Enabled') }}
                            </label>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">{{ lang._('Cancel') }}</button>
                <button type="button" class="btn btn-primary" id="saveProvider">{{ lang._('Save') }}</button>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    // Load settings on page load
    function loadSettings() {
        $.ajax({
            url: '/api/sark/settings/get',
            success: function(data) {
                if (data.general) {
                    var g = data.general;
                    $('#general_enabled').prop('checked', g.enabled === '1');
                    $('#general_mode').val(g.mode);
                    $('#general_listenAddress').val(g.listenAddress);
                    $('#general_listenPort').val(g.listenPort);
                    $('#general_tlsEnabled').prop('checked', g.tlsEnabled === '1');
                    $('#general_logLevel').val(g.logLevel);
                    $('#general_dailyTokenLimit').val(g.dailyTokenLimit);
                    $('#general_dailyCostLimit').val(g.dailyCostLimit);
                    $('#general_monthlyBudget').val(g.monthlyBudget);
                    $('#general_bedtimeEnabled').prop('checked', g.bedtimeEnabled === '1');
                    $('#general_bedtimeStart').val(g.bedtimeStart);
                    $('#general_bedtimeEnd').val(g.bedtimeEnd);
                    $('#general_bedtimeUsers').val(g.bedtimeUsers);
                }
            }
        });
    }

    // Load users
    function loadUsers() {
        $.ajax({
            url: '/api/sark/settings/getUsers',
            success: function(data) {
                var tbody = $('#usersTableBody');
                tbody.empty();
                if (data.users && Object.keys(data.users).length > 0) {
                    $.each(data.users, function(uuid, user) {
                        var row = '<tr data-uuid="' + uuid + '">' +
                            '<td>' + user.name + '</td>' +
                            '<td>' + user.role + '</td>' +
                            '<td>' + user.dailyLimit + '</td>' +
                            '<td>' + (user.enabled === '1' ? '<i class="fa fa-check text-success"></i>' : '<i class="fa fa-times text-danger"></i>') + '</td>' +
                            '<td>' +
                                '<button class="btn btn-xs btn-default editUser"><i class="fa fa-pencil"></i></button> ' +
                                '<button class="btn btn-xs btn-danger deleteUser"><i class="fa fa-trash"></i></button>' +
                            '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                } else {
                    tbody.html('<tr><td colspan="5" class="text-center">{{ lang._("No users configured") }}</td></tr>');
                }
            }
        });
    }

    // Load providers
    function loadProviders() {
        $.ajax({
            url: '/api/sark/settings/getProviders',
            success: function(data) {
                var tbody = $('#providersTableBody');
                tbody.empty();
                if (data.providers && Object.keys(data.providers).length > 0) {
                    $.each(data.providers, function(uuid, provider) {
                        var row = '<tr data-uuid="' + uuid + '">' +
                            '<td>' + provider.name + '</td>' +
                            '<td>' + provider.type + '</td>' +
                            '<td>' + provider.rateLimit + '/min</td>' +
                            '<td>' + (provider.enabled === '1' ? '<i class="fa fa-check text-success"></i>' : '<i class="fa fa-times text-danger"></i>') + '</td>' +
                            '<td>' +
                                '<button class="btn btn-xs btn-default editProvider"><i class="fa fa-pencil"></i></button> ' +
                                '<button class="btn btn-xs btn-danger deleteProvider"><i class="fa fa-trash"></i></button>' +
                            '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                } else {
                    tbody.html('<tr><td colspan="5" class="text-center">{{ lang._("No providers configured") }}</td></tr>');
                }
            }
        });
    }

    // Save settings
    $('#saveSettings').click(function() {
        var data = {
            general: {
                enabled: $('#general_enabled').is(':checked') ? '1' : '0',
                mode: $('#general_mode').val(),
                listenAddress: $('#general_listenAddress').val(),
                listenPort: $('#general_listenPort').val(),
                tlsEnabled: $('#general_tlsEnabled').is(':checked') ? '1' : '0',
                logLevel: $('#general_logLevel').val(),
                dailyTokenLimit: $('#general_dailyTokenLimit').val(),
                dailyCostLimit: $('#general_dailyCostLimit').val(),
                monthlyBudget: $('#general_monthlyBudget').val(),
                bedtimeEnabled: $('#general_bedtimeEnabled').is(':checked') ? '1' : '0',
                bedtimeStart: $('#general_bedtimeStart').val(),
                bedtimeEnd: $('#general_bedtimeEnd').val(),
                bedtimeUsers: $('#general_bedtimeUsers').val()
            }
        };

        $.ajax({
            url: '/api/sark/settings/set',
            type: 'POST',
            data: data,
            success: function(response) {
                if (response.result !== 'failed') {
                    alert('{{ lang._("Settings saved successfully") }}');
                } else {
                    alert('{{ lang._("Error saving settings") }}: ' + JSON.stringify(response.validations));
                }
            }
        });
    });

    // Save & Apply
    $('#applySettings').click(function() {
        $('#saveSettings').click();
        setTimeout(function() {
            $.post('/api/sark/service/reconfigure', function() {
                alert('{{ lang._("Settings applied") }}');
            });
        }, 500);
    });

    // User management
    $('#addUser').click(function() {
        $('#userModalTitle').text('{{ lang._("Add User") }}');
        $('#userForm')[0].reset();
        $('#user_uuid').val('');
        $('#userModal').modal('show');
    });

    $(document).on('click', '.editUser', function() {
        var uuid = $(this).closest('tr').data('uuid');
        // Load user and populate form
        $('#userModalTitle').text('{{ lang._("Edit User") }}');
        $('#user_uuid').val(uuid);
        // TODO: Fetch user details
        $('#userModal').modal('show');
    });

    $(document).on('click', '.deleteUser', function() {
        if (confirm('{{ lang._("Delete this user?") }}')) {
            var uuid = $(this).closest('tr').data('uuid');
            $.post('/api/sark/settings/delUser/' + uuid, function() {
                loadUsers();
            });
        }
    });

    $('#saveUser').click(function() {
        var uuid = $('#user_uuid').val();
        var data = {
            user: {
                name: $('#user_name').val(),
                role: $('#user_role').val(),
                dailyLimit: $('#user_dailyLimit').val(),
                enabled: $('#user_enabled').is(':checked') ? '1' : '0'
            }
        };

        var url = uuid ? '/api/sark/settings/setUser/' + uuid : '/api/sark/settings/addUser';
        $.post(url, data, function(response) {
            if (response.result !== 'failed') {
                $('#userModal').modal('hide');
                loadUsers();
            } else {
                alert('Error: ' + JSON.stringify(response.validations));
            }
        });
    });

    // Provider management
    $('#addProvider').click(function() {
        $('#providerModalTitle').text('{{ lang._("Add Provider") }}');
        $('#providerForm')[0].reset();
        $('#provider_uuid').val('');
        $('#providerModal').modal('show');
    });

    $(document).on('click', '.editProvider', function() {
        var uuid = $(this).closest('tr').data('uuid');
        $('#providerModalTitle').text('{{ lang._("Edit Provider") }}');
        $('#provider_uuid').val(uuid);
        $('#providerModal').modal('show');
    });

    $(document).on('click', '.deleteProvider', function() {
        if (confirm('{{ lang._("Delete this provider?") }}')) {
            var uuid = $(this).closest('tr').data('uuid');
            $.post('/api/sark/settings/delProvider/' + uuid, function() {
                loadProviders();
            });
        }
    });

    $('#saveProvider').click(function() {
        var uuid = $('#provider_uuid').val();
        var data = {
            provider: {
                name: $('#provider_name').val(),
                type: $('#provider_type').val(),
                apiKey: $('#provider_apiKey').val(),
                endpoint: $('#provider_endpoint').val(),
                rateLimit: $('#provider_rateLimit').val(),
                enabled: $('#provider_enabled').is(':checked') ? '1' : '0'
            }
        };

        var url = uuid ? '/api/sark/settings/setProvider/' + uuid : '/api/sark/settings/addProvider';
        $.post(url, data, function(response) {
            if (response.result !== 'failed') {
                $('#providerModal').modal('hide');
                loadProviders();
            } else {
                alert('Error: ' + JSON.stringify(response.validations));
            }
        });
    });

    // Initialize
    loadSettings();
    loadUsers();
    loadProviders();
});
</script>
