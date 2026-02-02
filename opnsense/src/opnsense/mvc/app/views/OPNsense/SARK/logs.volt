{#
    Copyright (C) 2024 SARK Project
    All rights reserved.

    SARK Home Gateway - Logs View
#}

<div class="content-box">
    <div class="content-box-header">
        <h3>{{ lang._('SARK Logs') }}</h3>
    </div>
    <div class="content-box-main">
        {# Filter Controls #}
        <div class="panel panel-default">
            <div class="panel-heading">
                <i class="fa fa-filter"></i> {{ lang._('Filters') }}
            </div>
            <div class="panel-body">
                <form class="form-inline" id="logFilters">
                    <div class="form-group">
                        <label for="filter_level">{{ lang._('Level') }}</label>
                        <select class="form-control" id="filter_level">
                            <option value="">{{ lang._('All') }}</option>
                            <option value="debug">Debug</option>
                            <option value="info">Info</option>
                            <option value="warning">Warning</option>
                            <option value="error">Error</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="filter_user">{{ lang._('User') }}</label>
                        <input type="text" class="form-control" id="filter_user" placeholder="{{ lang._('Username') }}">
                    </div>
                    <div class="form-group">
                        <label for="filter_limit">{{ lang._('Show') }}</label>
                        <select class="form-control" id="filter_limit">
                            <option value="50">50</option>
                            <option value="100" selected>100</option>
                            <option value="250">250</option>
                            <option value="500">500</option>
                        </select>
                    </div>
                    <button type="button" class="btn btn-primary" id="applyFilters">
                        <i class="fa fa-search"></i> {{ lang._('Apply') }}
                    </button>
                    <button type="button" class="btn btn-default" id="refreshLogs">
                        <i class="fa fa-refresh"></i> {{ lang._('Refresh') }}
                    </button>
                    <div class="checkbox pull-right">
                        <label>
                            <input type="checkbox" id="autoRefresh">
                            {{ lang._('Auto-refresh (30s)') }}
                        </label>
                    </div>
                </form>
            </div>
        </div>

        {# Logs Table #}
        <div class="panel panel-default">
            <div class="panel-heading">
                <i class="fa fa-list"></i> {{ lang._('Audit Log') }}
                <span class="badge" id="logCount">0</span>
                <div class="pull-right">
                    <button class="btn btn-xs btn-default" id="exportLogs">
                        <i class="fa fa-download"></i> {{ lang._('Export') }}
                    </button>
                    <button class="btn btn-xs btn-danger" id="clearLogs">
                        <i class="fa fa-trash"></i> {{ lang._('Clear') }}
                    </button>
                </div>
            </div>
            <div class="panel-body" style="max-height: 600px; overflow-y: auto;">
                <table class="table table-striped table-condensed table-hover" id="logsTable">
                    <thead>
                        <tr>
                            <th style="width: 150px;">{{ lang._('Timestamp') }}</th>
                            <th style="width: 80px;">{{ lang._('Level') }}</th>
                            <th style="width: 100px;">{{ lang._('User') }}</th>
                            <th style="width: 120px;">{{ lang._('Action') }}</th>
                            <th>{{ lang._('Message') }}</th>
                            <th style="width: 80px;">{{ lang._('Details') }}</th>
                        </tr>
                    </thead>
                    <tbody id="logsTableBody">
                        <tr><td colspan="6" class="text-center">{{ lang._('Loading...') }}</td></tr>
                    </tbody>
                </table>
            </div>
            <div class="panel-footer">
                <nav>
                    <ul class="pagination pagination-sm" id="logPagination" style="margin: 0;">
                    </ul>
                </nav>
            </div>
        </div>

        {# Recent Violations #}
        <div class="panel panel-warning">
            <div class="panel-heading">
                <i class="fa fa-exclamation-triangle"></i> {{ lang._('Recent Policy Violations') }}
            </div>
            <div class="panel-body">
                <table class="table table-condensed" id="violationsTable">
                    <thead>
                        <tr>
                            <th>{{ lang._('Time') }}</th>
                            <th>{{ lang._('User') }}</th>
                            <th>{{ lang._('Policy') }}</th>
                            <th>{{ lang._('Action Taken') }}</th>
                        </tr>
                    </thead>
                    <tbody id="violationsTableBody">
                        <tr><td colspan="4" class="text-center">{{ lang._('No recent violations') }}</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

{# Log Detail Modal #}
<div class="modal fade" id="logDetailModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal">&times;</button>
                <h4 class="modal-title">{{ lang._('Log Details') }}</h4>
            </div>
            <div class="modal-body">
                <dl class="dl-horizontal">
                    <dt>{{ lang._('Timestamp') }}</dt>
                    <dd id="detail_timestamp">-</dd>

                    <dt>{{ lang._('Level') }}</dt>
                    <dd id="detail_level">-</dd>

                    <dt>{{ lang._('User') }}</dt>
                    <dd id="detail_user">-</dd>

                    <dt>{{ lang._('Action') }}</dt>
                    <dd id="detail_action">-</dd>

                    <dt>{{ lang._('Message') }}</dt>
                    <dd id="detail_message">-</dd>

                    <dt>{{ lang._('Model') }}</dt>
                    <dd id="detail_model">-</dd>

                    <dt>{{ lang._('Tokens') }}</dt>
                    <dd id="detail_tokens">-</dd>

                    <dt>{{ lang._('Duration') }}</dt>
                    <dd id="detail_duration">-</dd>
                </dl>

                <h5>{{ lang._('Request (truncated)') }}</h5>
                <pre id="detail_request" style="max-height: 200px; overflow-y: auto;">-</pre>

                <h5>{{ lang._('Metadata') }}</h5>
                <pre id="detail_metadata" style="max-height: 200px; overflow-y: auto;">-</pre>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-default" data-dismiss="modal">{{ lang._('Close') }}</button>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    var currentOffset = 0;
    var autoRefreshInterval = null;

    // Load logs
    function loadLogs() {
        var limit = parseInt($('#filter_limit').val());
        var level = $('#filter_level').val();
        var user = $('#filter_user').val();

        $.ajax({
            url: '/api/sark/analytics/logs',
            data: {
                limit: limit,
                offset: currentOffset,
                level: level,
                user: user
            },
            success: function(data) {
                var tbody = $('#logsTableBody');
                tbody.empty();

                if (data.status === 'ok' && data.data && data.data.logs && data.data.logs.length > 0) {
                    $('#logCount').text(data.data.total || data.data.logs.length);

                    $.each(data.data.logs, function(i, log) {
                        var levelClass = {
                            'debug': 'label-default',
                            'info': 'label-info',
                            'warning': 'label-warning',
                            'error': 'label-danger'
                        }[log.level] || 'label-default';

                        var row = '<tr data-log=\'' + JSON.stringify(log) + '\'>' +
                            '<td><small>' + formatTimestamp(log.timestamp) + '</small></td>' +
                            '<td><span class="label ' + levelClass + '">' + log.level + '</span></td>' +
                            '<td>' + (log.user || '-') + '</td>' +
                            '<td>' + (log.action || '-') + '</td>' +
                            '<td>' + truncate(log.message, 80) + '</td>' +
                            '<td><button class="btn btn-xs btn-default viewLog"><i class="fa fa-eye"></i></button></td>' +
                            '</tr>';
                        tbody.append(row);
                    });

                    // Update pagination
                    updatePagination(data.data.total || data.data.logs.length, limit);
                } else {
                    tbody.html('<tr><td colspan="6" class="text-center">{{ lang._("No logs found") }}</td></tr>');
                    $('#logCount').text('0');
                }
            },
            error: function() {
                $('#logsTableBody').html('<tr><td colspan="6" class="text-center text-danger">{{ lang._("Error loading logs") }}</td></tr>');
            }
        });
    }

    // Load violations
    function loadViolations() {
        $.ajax({
            url: '/api/sark/analytics/violations',
            success: function(data) {
                var tbody = $('#violationsTableBody');
                tbody.empty();

                if (data.status === 'ok' && data.data && data.data.recent && data.data.recent.length > 0) {
                    $.each(data.data.recent.slice(0, 10), function(i, v) {
                        var row = '<tr>' +
                            '<td><small>' + formatTimestamp(v.timestamp) + '</small></td>' +
                            '<td>' + (v.user || '-') + '</td>' +
                            '<td>' + (v.policy || '-') + '</td>' +
                            '<td>' + (v.action || '-') + '</td>' +
                            '</tr>';
                        tbody.append(row);
                    });
                } else {
                    tbody.html('<tr><td colspan="4" class="text-center">{{ lang._("No recent violations") }}</td></tr>');
                }
            }
        });
    }

    // Format timestamp
    function formatTimestamp(ts) {
        if (!ts) return '-';
        var d = new Date(ts);
        return d.toLocaleString();
    }

    // Truncate string
    function truncate(str, len) {
        if (!str) return '-';
        return str.length > len ? str.substring(0, len) + '...' : str;
    }

    // Update pagination
    function updatePagination(total, limit) {
        var pages = Math.ceil(total / limit);
        var currentPage = Math.floor(currentOffset / limit) + 1;
        var pagination = $('#logPagination');
        pagination.empty();

        if (pages <= 1) return;

        // Previous
        pagination.append('<li class="' + (currentPage === 1 ? 'disabled' : '') + '">' +
            '<a href="#" data-offset="' + Math.max(0, currentOffset - limit) + '">&laquo;</a></li>');

        // Page numbers
        for (var i = Math.max(1, currentPage - 2); i <= Math.min(pages, currentPage + 2); i++) {
            pagination.append('<li class="' + (i === currentPage ? 'active' : '') + '">' +
                '<a href="#" data-offset="' + ((i - 1) * limit) + '">' + i + '</a></li>');
        }

        // Next
        pagination.append('<li class="' + (currentPage === pages ? 'disabled' : '') + '">' +
            '<a href="#" data-offset="' + Math.min((pages - 1) * limit, currentOffset + limit) + '">&raquo;</a></li>');
    }

    // Pagination click
    $(document).on('click', '#logPagination a', function(e) {
        e.preventDefault();
        var offset = $(this).data('offset');
        if (offset !== undefined && !$(this).parent().hasClass('disabled')) {
            currentOffset = offset;
            loadLogs();
        }
    });

    // Apply filters
    $('#applyFilters').click(function() {
        currentOffset = 0;
        loadLogs();
    });

    // Refresh
    $('#refreshLogs').click(function() {
        loadLogs();
        loadViolations();
    });

    // Auto-refresh toggle
    $('#autoRefresh').change(function() {
        if ($(this).is(':checked')) {
            autoRefreshInterval = setInterval(function() {
                loadLogs();
                loadViolations();
            }, 30000);
        } else {
            clearInterval(autoRefreshInterval);
        }
    });

    // View log details
    $(document).on('click', '.viewLog', function() {
        var log = $(this).closest('tr').data('log');
        if (log) {
            $('#detail_timestamp').text(formatTimestamp(log.timestamp));
            $('#detail_level').html('<span class="label label-' + ({
                'debug': 'default',
                'info': 'info',
                'warning': 'warning',
                'error': 'danger'
            }[log.level] || 'default') + '">' + log.level + '</span>');
            $('#detail_user').text(log.user || '-');
            $('#detail_action').text(log.action || '-');
            $('#detail_message').text(log.message || '-');
            $('#detail_model').text(log.model || '-');
            $('#detail_tokens').text(log.tokens ? log.tokens.toLocaleString() : '-');
            $('#detail_duration').text(log.duration ? log.duration + 'ms' : '-');
            $('#detail_request').text(log.request ? truncate(log.request, 500) : '-');
            $('#detail_metadata').text(log.metadata ? JSON.stringify(log.metadata, null, 2) : '-');
            $('#logDetailModal').modal('show');
        }
    });

    // Export logs
    $('#exportLogs').click(function() {
        var level = $('#filter_level').val();
        var user = $('#filter_user').val();
        window.location.href = '/api/sark/analytics/export?format=csv&period=day' +
            (level ? '&level=' + level : '') +
            (user ? '&user=' + user : '');
    });

    // Clear logs (confirm first)
    $('#clearLogs').click(function() {
        if (confirm('{{ lang._("Are you sure you want to clear all logs? This cannot be undone.") }}')) {
            // This would need a backend endpoint
            alert('{{ lang._("Log clearing not yet implemented") }}');
        }
    });

    // Initialize
    loadLogs();
    loadViolations();
});
</script>
