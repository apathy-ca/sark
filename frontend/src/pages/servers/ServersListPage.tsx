import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { serversApi } from '@/services/api';
import { useState } from 'react';
import type { ServerListItem } from '@/types/api';

export default function ServersListPage() {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sensitivityFilter, setSensitivityFilter] = useState<string>('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['servers', search, statusFilter, sensitivityFilter],
    queryFn: () => serversApi.list({
      search: search || undefined,
      status: statusFilter || undefined,
      sensitivity_level: sensitivityFilter || undefined,
    }),
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      case 'inactive':
        return 'text-gray-600 bg-gray-50 dark:bg-gray-900/20';
      case 'error':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getSensitivityColor = (level: string) => {
    switch (level) {
      case 'critical':
        return 'text-red-600 bg-red-50 dark:bg-red-900/20';
      case 'high':
        return 'text-orange-600 bg-orange-50 dark:bg-orange-900/20';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20';
      case 'low':
        return 'text-green-600 bg-green-50 dark:bg-green-900/20';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">MCP Servers</h1>
        <Link
          to="/servers/register"
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
        >
          Register Server
        </Link>
      </div>

      {/* Search and Filters */}
      <div className="bg-card p-4 rounded-lg border mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Search</label>
            <input
              type="search"
              placeholder="Search by name or description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Sensitivity</label>
            <select
              value={sensitivityFilter}
              onChange={(e) => setSensitivityFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">All Levels</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-card p-8 rounded-lg border text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading servers...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Failed to load servers: {error instanceof Error ? error.message : 'Unknown error'}
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
                  <th className="px-4 py-3 text-left text-sm font-semibold">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Transport</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Sensitivity</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold">Tools</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      No servers found. {search || statusFilter || sensitivityFilter ? 'Try adjusting your filters.' : 'Register your first server to get started.'}
                    </td>
                  </tr>
                ) : (
                  data.items.map((server: ServerListItem) => (
                    <tr key={server.id} className="hover:bg-muted/50 transition-colors">
                      <td className="px-4 py-3">
                        <Link
                          to={`/servers/${server.id}`}
                          className="font-medium text-primary hover:underline"
                        >
                          {server.name}
                        </Link>
                        {server.description && (
                          <p className="text-sm text-muted-foreground mt-1">
                            {server.description}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted">
                          {server.transport}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getStatusColor(server.status)}`}>
                          {server.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getSensitivityColor(server.sensitivity_level)}`}>
                          {server.sensitivity_level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {server.tool_count} {server.tool_count === 1 ? 'tool' : 'tools'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/servers/${server.id}`}
                          className="text-sm text-primary hover:underline"
                        >
                          View Details →
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.items.length > 0 && data.has_more && (
            <div className="border-t p-4 flex justify-center">
              <button className="px-4 py-2 text-sm text-primary hover:bg-muted rounded-md transition-colors">
                Load More Servers
              </button>
            </div>
          )}

          {/* Stats Footer */}
          <div className="border-t px-4 py-3 bg-muted/30">
            <p className="text-sm text-muted-foreground">
              Showing {data.items.length} server{data.items.length !== 1 ? 's' : ''}
              {data.has_more && ' • More available'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
