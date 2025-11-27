import { useQuery } from '@tanstack/react-query';
import { auditApi } from '@/services/api';
import { useState } from 'react';
import type { AuditEvent } from '@/types/api';

type TimePeriod = '1h' | '24h' | '7d' | '30d';

export default function AuditLogsPage() {
  const [period, setPeriod] = useState<TimePeriod>('24h');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');
  const [userFilter, setUserFilter] = useState<string>('');
  const [serverFilter, setServerFilter] = useState<string>('');

  const getStartTime = (period: TimePeriod): string => {
    const now = new Date();
    const hours: Record<TimePeriod, number> = {
      '1h': 1,
      '24h': 24,
      '7d': 24 * 7,
      '30d': 24 * 30,
    };
    now.setHours(now.getHours() - hours[period]);
    return now.toISOString();
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-events', period, eventTypeFilter, userFilter, serverFilter],
    queryFn: () =>
      auditApi.getEvents({
        start_time: getStartTime(period),
        event_type: eventTypeFilter || undefined,
        user_email: userFilter || undefined,
        server_name: serverFilter || undefined,
      }),
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'allow':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'deny':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'tool_invocation':
        return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20';
      case 'server_registration':
        return 'text-purple-600 bg-purple-50 dark:bg-purple-900/20';
      case 'policy_evaluation':
        return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20';
      case 'authentication':
        return 'text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20';
      default:
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  };

  const exportToCSV = () => {
    if (!data?.events || data.events.length === 0) return;

    const headers = ['Timestamp', 'Event Type', 'User', 'Server', 'Tool', 'Decision', 'Reason'];
    const rows = data.events.map((event: AuditEvent) => [
      event.timestamp,
      event.event_type,
      event.user_email || '',
      event.server_name || '',
      event.tool_name || '',
      event.decision || '',
      event.reason || '',
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${period}-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Audit Logs</h1>
        <div className="flex gap-3">
          <button
            onClick={() => refetch()}
            className="px-4 py-2 border rounded-md hover:bg-muted transition-colors text-sm"
          >
            🔄 Refresh
          </button>
          <button
            onClick={exportToCSV}
            disabled={!data?.events || data.events.length === 0}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            📥 Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card p-4 rounded-lg border mb-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Time Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value as TimePeriod)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="1h">Last Hour</option>
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Event Type</label>
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Types</option>
              <option value="tool_invocation">Tool Invocation</option>
              <option value="server_registration">Server Registration</option>
              <option value="policy_evaluation">Policy Evaluation</option>
              <option value="authentication">Authentication</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">User Filter</label>
            <input
              type="search"
              placeholder="Filter by user email..."
              value={userFilter}
              onChange={(e) => setUserFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Server Filter</label>
            <input
              type="search"
              placeholder="Filter by server name..."
              value={serverFilter}
              onChange={(e) => setServerFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-card p-8 rounded-lg border text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading audit logs...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Failed to load audit logs: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Data Table */}
      {!isLoading && !error && data && (
        <div className="bg-card rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50 border-b">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Timestamp</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Event Type</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">User</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Server</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Tool</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Decision</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.events.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                      No audit logs found for the selected filters.
                    </td>
                  </tr>
                ) : (
                  data.events.map((event: AuditEvent) => (
                    <tr key={event.event_id} className="hover:bg-muted/50 transition-colors">
                      <td className="px-4 py-3 text-sm font-mono">
                        {formatTimestamp(event.timestamp)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getEventTypeColor(
                            event.event_type
                          )}`}
                        >
                          {event.event_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {event.user_email || (
                          <span className="text-muted-foreground italic">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {event.server_name || (
                          <span className="text-muted-foreground italic">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {event.tool_name || (
                          <span className="text-muted-foreground italic">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {event.decision ? (
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getDecisionColor(
                              event.decision
                            )}`}
                          >
                            {event.decision}
                          </span>
                        ) : (
                          <span className="text-muted-foreground italic text-xs">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground max-w-xs truncate">
                        {event.reason || '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Stats Footer */}
          <div className="border-t px-4 py-3 bg-muted/30 flex justify-between items-center">
            <p className="text-sm text-muted-foreground">
              Showing {data.events.length} event{data.events.length !== 1 ? 's' : ''}
              {data.total > data.events.length && ` of ${data.total} total`}
            </p>
            <p className="text-xs text-muted-foreground">Auto-refreshes every 30 seconds</p>
          </div>
        </div>
      )}
    </div>
  );
}
