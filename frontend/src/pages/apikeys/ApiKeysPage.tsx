import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiKeysApi } from '@/services/api';
import { useState } from 'react';
import { toast } from 'sonner';
import { copyToClipboard } from '@/utils/export';
import type { ApiKey } from '@/types/api';

export default function ApiKeysPage() {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpires, setNewKeyExpires] = useState('30');
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const { data: apiKeys, isLoading, error } = useQuery({
    queryKey: ['api-keys'],
    queryFn: apiKeysApi.list,
  });

  const createMutation = useMutation({
    mutationFn: ({ name, expires_in_days }: { name: string; expires_in_days?: number }) =>
      apiKeysApi.create(name, expires_in_days),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      setCreatedKey(data.key);
      toast.success('API key created successfully');
      setNewKeyName('');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create API key');
    },
  });

  const revokeMutation = useMutation({
    mutationFn: apiKeysApi.revoke,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] });
      toast.success('API key revoked successfully');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to revoke API key');
    },
  });

  const handleCreate = () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }

    const expiresInDays = newKeyExpires === 'never' ? undefined : parseInt(newKeyExpires);
    createMutation.mutate({ name: newKeyName, expires_in_days: expiresInDays });
  };

  const handleRevoke = (keyId: string, keyName: string) => {
    if (confirm(`Are you sure you want to revoke the API key "${keyName}"? This action cannot be undone.`)) {
      revokeMutation.mutate(keyId);
    }
  };

  const handleCopyKey = async (key: string) => {
    try {
      await copyToClipboard(key, false);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleCloseCreatedKey = () => {
    setCreatedKey(null);
    setShowCreateModal(false);
  };

  const formatDate = (dateString: string) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(dateString));
  };

  const isExpired = (expiresAt: string | null) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">API Keys</h1>
          <p className="text-muted-foreground mt-1">
            Manage API keys for programmatic access to SARK
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
        >
          + Create API Key
        </button>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg mb-6">
        <p className="text-sm text-blue-800 dark:text-blue-200">
          <strong>Important:</strong> API keys provide full access to your account. Keep them secure and never share them publicly.
        </p>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-card p-8 rounded-lg border text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading API keys...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Failed to load API keys: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* API Keys List */}
      {!isLoading && !error && apiKeys && (
        <div className="bg-card rounded-lg border overflow-hidden">
          {apiKeys.keys.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-muted-foreground">
                <p className="text-lg mb-2">No API keys yet</p>
                <p className="text-sm">Create your first API key to get started with programmatic access</p>
              </div>
            </div>
          ) : (
            <div className="divide-y">
              {apiKeys.keys.map((key: ApiKey) => (
                <div key={key.id} className="p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold">{key.name}</h3>
                        {isExpired(key.expires_at) && (
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-red-50 dark:bg-red-900/20 text-red-600">
                            Expired
                          </span>
                        )}
                        {!key.is_active && !isExpired(key.expires_at) && (
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-gray-50 dark:bg-gray-900/20 text-gray-600">
                            Revoked
                          </span>
                        )}
                      </div>

                      <div className="space-y-1 text-sm text-muted-foreground">
                        <p>
                          <span className="font-medium">Key ID:</span>{' '}
                          <code className="bg-muted px-2 py-0.5 rounded text-xs">
                            {key.id}
                          </code>
                        </p>
                        <p>
                          <span className="font-medium">Created:</span> {formatDate(key.created_at)}
                        </p>
                        {key.last_used_at && (
                          <p>
                            <span className="font-medium">Last used:</span> {formatDate(key.last_used_at)}
                          </p>
                        )}
                        {key.expires_at ? (
                          <p>
                            <span className="font-medium">Expires:</span> {formatDate(key.expires_at)}
                          </p>
                        ) : (
                          <p>
                            <span className="font-medium">Expires:</span> Never
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      {key.is_active && !isExpired(key.expires_at) && (
                        <button
                          onClick={() => handleRevoke(key.id, key.name)}
                          disabled={revokeMutation.isPending}
                          className="text-sm px-3 py-1 text-red-600 hover:text-red-700 dark:text-red-400 disabled:opacity-50"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-card rounded-lg border max-w-md w-full">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold">Create API Key</h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setCreatedKey(null);
                }}
                className="text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>

            {!createdKey ? (
              <>
                <div className="p-6 space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Key Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      placeholder="Production API Key"
                      className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      A descriptive name to help you identify this key
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Expires In</label>
                    <select
                      value={newKeyExpires}
                      onChange={(e) => setNewKeyExpires(e.target.value)}
                      className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="7">7 days</option>
                      <option value="30">30 days</option>
                      <option value="90">90 days</option>
                      <option value="365">1 year</option>
                      <option value="never">Never</option>
                    </select>
                  </div>
                </div>

                <div className="px-6 py-4 border-t flex justify-end space-x-3">
                  <button
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={createMutation.isPending}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                  >
                    {createMutation.isPending ? 'Creating...' : 'Create Key'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="p-6 space-y-4">
                  <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-4 rounded-lg">
                    <p className="text-sm text-green-800 dark:text-green-200 font-medium mb-2">
                      ✓ API Key Created Successfully
                    </p>
                    <p className="text-xs text-green-700 dark:text-green-300">
                      Make sure to copy your API key now. You won't be able to see it again!
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Your API Key</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={createdKey}
                        readOnly
                        className="flex-1 px-3 py-2 border rounded-md bg-muted font-mono text-sm"
                      />
                      <button
                        onClick={() => handleCopyKey(createdKey)}
                        className="px-3 py-2 border rounded-md hover:bg-muted transition-colors"
                        title="Copy to clipboard"
                      >
                        📋
                      </button>
                    </div>
                  </div>
                </div>

                <div className="px-6 py-4 border-t flex justify-end">
                  <button
                    onClick={handleCloseCreatedKey}
                    className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
