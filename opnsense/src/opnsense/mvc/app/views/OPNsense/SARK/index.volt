{#
    Copyright (C) 2024 SARK Project
    All rights reserved.

    SARK Home Gateway - Dashboard View
#}

<script src="{{ cache_safe('/ui/js/chart.min.js') }}"></script>

<div class="content-box">
    <div class="content-box-header">
        <h3>{{ lang._('SARK Home Gateway') }}</h3>
    </div>
    <div class="content-box-main">
        {# Service Status Row #}
        <div class="row">
            <div class="col-md-6">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-server"></i> {{ lang._('Service Status') }}
                    </div>
                    <div class="panel-body">
                        <div class="row">
                            <div class="col-md-6">
                                <span id="sark-status" class="label label-default">
                                    <i class="fa fa-spinner fa-spin"></i> {{ lang._('Loading...') }}
                                </span>
                            </div>
                            <div class="col-md-6 text-right">
                                <div class="btn-group">
                                    <button class="btn btn-success btn-xs" id="startService" disabled>
                                        <i class="fa fa-play"></i> {{ lang._('Start') }}
                                    </button>
                                    <button class="btn btn-warning btn-xs" id="restartService" disabled>
                                        <i class="fa fa-refresh"></i> {{ lang._('Restart') }}
                                    </button>
                                    <button class="btn btn-danger btn-xs" id="stopService" disabled>
                                        <i class="fa fa-stop"></i> {{ lang._('Stop') }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-shield"></i> {{ lang._('Governance Mode') }}
                    </div>
                    <div class="panel-body">
                        <span id="governance-mode" class="label label-info">-</span>
                        <a href="/ui/sark/settings" class="btn btn-default btn-xs pull-right">
                            <i class="fa fa-cog"></i> {{ lang._('Configure') }}
                        </a>
                    </div>
                </div>
            </div>
        </div>

        {# Statistics Cards #}
        <div class="row">
            <div class="col-md-3">
                <div class="panel panel-primary">
                    <div class="panel-heading">
                        <i class="fa fa-comments"></i> {{ lang._('Requests Today') }}
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="stat-requests">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-info">
                    <div class="panel-heading">
                        <i class="fa fa-database"></i> {{ lang._('Tokens Used') }}
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="stat-tokens">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-success">
                    <div class="panel-heading">
                        <i class="fa fa-dollar"></i> {{ lang._('Est. Cost Today') }}
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="stat-cost">-</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="panel panel-warning">
                    <div class="panel-heading">
                        <i class="fa fa-exclamation-triangle"></i> {{ lang._('Policy Violations') }}
                    </div>
                    <div class="panel-body text-center">
                        <h2 id="stat-violations">-</h2>
                    </div>
                </div>
            </div>
        </div>

        {# Usage Charts #}
        <div class="row">
            <div class="col-md-8">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-line-chart"></i> {{ lang._('Usage Today (Hourly)') }}
                    </div>
                    <div class="panel-body">
                        <canvas id="usageChart" height="200"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-pie-chart"></i> {{ lang._('Usage by User') }}
                    </div>
                    <div class="panel-body">
                        <canvas id="userChart" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>

        {# Quick Links #}
        <div class="row">
            <div class="col-md-12">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <i class="fa fa-link"></i> {{ lang._('Quick Actions') }}
                    </div>
                    <div class="panel-body">
                        <a href="/ui/sark/settings" class="btn btn-default">
                            <i class="fa fa-cog"></i> {{ lang._('Settings') }}
                        </a>
                        <a href="/ui/sark/policies" class="btn btn-default">
                            <i class="fa fa-shield"></i> {{ lang._('Policies') }}
                        </a>
                        <a href="/ui/sark/logs" class="btn btn-default">
                            <i class="fa fa-list"></i> {{ lang._('View Logs') }}
                        </a>
                        <button id="exportStats" class="btn btn-default">
                            <i class="fa fa-download"></i> {{ lang._('Export Stats') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    var usageChart = null;
    var userChart = null;

    // Initialize Charts
    function initCharts() {
        var usageCtx = document.getElementById('usageChart').getContext('2d');
        usageChart = new Chart(usageCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '{{ lang._("Requests") }}',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    yAxisID: 'y'
                }, {
                    label: '{{ lang._("Tokens (K)") }}',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: '{{ lang._("Requests") }}' }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: '{{ lang._("Tokens (K)") }}' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });

        var userCtx = document.getElementById('userChart').getContext('2d');
        userChart = new Chart(userCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgb(255, 99, 132)',
                        'rgb(54, 162, 235)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)',
                        'rgb(153, 102, 255)'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    // Update service status
    function updateStatus() {
        $.ajax({
            url: '/api/sark/service/status',
            success: function(data) {
                var label = $('#sark-status');
                var startBtn = $('#startService');
                var stopBtn = $('#stopService');
                var restartBtn = $('#restartService');

                if (data.status === 'running') {
                    label.removeClass('label-default label-danger')
                         .addClass('label-success')
                         .html('<i class="fa fa-check"></i> {{ lang._("Running") }}');
                    startBtn.prop('disabled', true);
                    stopBtn.prop('disabled', false);
                    restartBtn.prop('disabled', false);
                } else {
                    label.removeClass('label-default label-success')
                         .addClass('label-danger')
                         .html('<i class="fa fa-times"></i> {{ lang._("Stopped") }}');
                    startBtn.prop('disabled', false);
                    stopBtn.prop('disabled', true);
                    restartBtn.prop('disabled', true);
                }
            },
            error: function() {
                $('#sark-status').removeClass('label-success label-danger')
                    .addClass('label-default')
                    .html('<i class="fa fa-question"></i> {{ lang._("Unknown") }}');
            }
        });
    }

    // Load summary statistics
    function loadSummary() {
        $.ajax({
            url: '/api/sark/analytics/summary',
            success: function(data) {
                if (data.status === 'ok' && data.summary) {
                    $('#stat-requests').text(data.summary.requests_today.toLocaleString());
                    $('#stat-tokens').text(data.summary.tokens_today.toLocaleString());
                    $('#stat-cost').text('$' + parseFloat(data.summary.cost_today).toFixed(2));
                    $('#stat-violations').text(data.summary.policy_violations);
                }
            }
        });
    }

    // Load hourly chart data
    function loadHourlyData() {
        $.ajax({
            url: '/api/sark/analytics/hourly',
            success: function(data) {
                if (data.status === 'ok' && data.data && data.data.hours) {
                    var labels = [];
                    var requests = [];
                    var tokens = [];

                    data.data.hours.forEach(function(hour) {
                        labels.push(hour.hour + ':00');
                        requests.push(hour.requests);
                        tokens.push(hour.tokens / 1000); // Convert to K
                    });

                    usageChart.data.labels = labels;
                    usageChart.data.datasets[0].data = requests;
                    usageChart.data.datasets[1].data = tokens;
                    usageChart.update();
                }
            }
        });
    }

    // Load user breakdown
    function loadUserData() {
        $.ajax({
            url: '/api/sark/analytics/users',
            success: function(data) {
                if (data.status === 'ok' && data.data && data.data.users) {
                    var labels = [];
                    var values = [];

                    Object.keys(data.data.users).forEach(function(user) {
                        labels.push(user);
                        values.push(data.data.users[user].tokens || 0);
                    });

                    if (labels.length > 0) {
                        userChart.data.labels = labels;
                        userChart.data.datasets[0].data = values;
                        userChart.update();
                    }
                }
            }
        });
    }

    // Load settings for governance mode display
    function loadSettings() {
        $.ajax({
            url: '/api/sark/settings/get',
            success: function(data) {
                if (data.general && data.general.mode) {
                    var mode = data.general.mode;
                    var modeLabel = $('#governance-mode');
                    var modeText = {
                        'observe': '{{ lang._("Observe Only") }}',
                        'advisory': '{{ lang._("Advisory") }}',
                        'enforce': '{{ lang._("Enforce") }}'
                    };
                    modeLabel.text(modeText[mode] || mode);

                    if (mode === 'enforce') {
                        modeLabel.removeClass('label-info label-warning').addClass('label-danger');
                    } else if (mode === 'advisory') {
                        modeLabel.removeClass('label-info label-danger').addClass('label-warning');
                    }
                }
            }
        });
    }

    // Service controls
    $('#startService').click(function() {
        $(this).prop('disabled', true);
        $.post('/api/sark/service/start', function() {
            setTimeout(updateStatus, 1000);
        });
    });

    $('#stopService').click(function() {
        $(this).prop('disabled', true);
        $.post('/api/sark/service/stop', function() {
            setTimeout(updateStatus, 1000);
        });
    });

    $('#restartService').click(function() {
        $(this).prop('disabled', true);
        $.post('/api/sark/service/restart', function() {
            setTimeout(updateStatus, 2000);
        });
    });

    // Export stats
    $('#exportStats').click(function() {
        window.location.href = '/api/sark/analytics/export?format=csv&period=day';
    });

    // Initialize
    initCharts();
    updateStatus();
    loadSummary();
    loadHourlyData();
    loadUserData();
    loadSettings();

    // Auto-refresh every 30 seconds
    setInterval(function() {
        updateStatus();
        loadSummary();
    }, 30000);
});
</script>
