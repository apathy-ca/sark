import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { policyApi } from '@/services/api';
import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { RegoEditor, RegoViewer } from '@/components/RegoEditor';

export default function PoliciesPage() {
  const queryClient = useQueryClient();
  const [selectedPolicyId, setSelectedPolicyId] = useState<string | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadContent, setUploadContent] = useState('');
  const [uploadName, setUploadName] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  const { data: policies, isLoading, error } = useQuery({
    queryKey: ['policies'],
    queryFn: policyApi.list,
  });

  const { data: selectedPolicy } = useQuery({
    queryKey: ['policy', selectedPolicyId],
    queryFn: () => policyApi.get(selectedPolicyId!),
    enabled: !!selectedPolicyId,
  });

  const uploadMutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      policyApi.create({ id: name, content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      toast.success('Policy uploaded successfully');
      setShowUploadModal(false);
      setUploadContent('');
      setUploadName('');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to upload policy');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: policyApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      toast.success('Policy deleted successfully');
      setSelectedPolicyId(null);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to delete policy');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, content }: { id: string; content: string }) =>
      policyApi.update(id, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['policies'] });
      queryClient.invalidateQueries({ queryKey: ['policy', selectedPolicyId] });
      toast.success('Policy updated successfully');
      setIsEditing(false);
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update policy');
    },
  });

  // Sync editContent with selectedPolicy
  useEffect(() => {
    if (selectedPolicy?.content) {
      setEditContent(selectedPolicy.content);
    }
  }, [selectedPolicy]);

  // Reset edit mode when changing policies
  useEffect(() => {
    setIsEditing(false);
  }, [selectedPolicyId]);

  const handleUpload = () => {
    if (!uploadName || !uploadContent) {
      toast.error('Please provide both name and policy content');
      return;
    }
    uploadMutation.mutate({ name: uploadName, content: uploadContent });
  };

  const handleDelete = (policyId: string) => {
    if (confirm('Are you sure you want to delete this policy?')) {
      deleteMutation.mutate(policyId);
    }
  };

  const handleSave = () => {
    if (!selectedPolicyId) return;
    updateMutation.mutate({ id: selectedPolicyId, content: editContent });
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditContent(selectedPolicy?.content || '');
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">OPA Policies</h1>
        <button
          onClick={() => setShowUploadModal(true)}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
        >
          Upload Policy
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="bg-card p-8 rounded-lg border text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <p className="mt-4 text-muted-foreground">Loading policies...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-4 rounded-lg">
          <p className="text-red-600 dark:text-red-400">
            Failed to load policies: {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {/* Main Content */}
      {!isLoading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Policy List - Left Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-card rounded-lg border overflow-hidden">
              <div className="bg-muted/50 px-4 py-3 border-b">
                <h2 className="font-semibold">Policies ({policies?.length || 0})</h2>
              </div>
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {(!policies || policies.length === 0) ? (
                  <div className="px-4 py-8 text-center text-muted-foreground text-sm">
                    No policies found. Upload your first policy to get started.
                  </div>
                ) : (
                  policies.map((policy: any) => (
                    <button
                      key={policy.id}
                      onClick={() => setSelectedPolicyId(policy.id)}
                      className={`w-full px-4 py-3 text-left hover:bg-muted/50 transition-colors ${
                        selectedPolicyId === policy.id ? 'bg-muted' : ''
                      }`}
                    >
                      <div className="font-medium text-sm">{policy.name}</div>
                      {policy.package_name && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {policy.package_name}
                        </div>
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Policy Content - Main Area */}
          <div className="lg:col-span-2">
            {!selectedPolicyId ? (
              <div className="bg-card rounded-lg border p-12 text-center">
                <div className="text-muted-foreground">
                  <p className="text-lg mb-2">No policy selected</p>
                  <p className="text-sm">Select a policy from the list to view its contents</p>
                </div>
              </div>
            ) : (
              <div className="bg-card rounded-lg border overflow-hidden">
                {/* Policy Header */}
                <div className="bg-muted/50 px-4 py-3 border-b flex justify-between items-center">
                  <div>
                    <h2 className="font-semibold">{selectedPolicy?.name}</h2>
                    {selectedPolicy?.package_name && (
                      <p className="text-xs text-muted-foreground">
                        Package: {selectedPolicy.package_name}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {isEditing ? (
                      <>
                        <button
                          onClick={handleCancelEdit}
                          disabled={updateMutation.isPending}
                          className="text-sm px-3 py-1 border rounded hover:bg-muted transition-colors disabled:opacity-50"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSave}
                          disabled={updateMutation.isPending}
                          className="text-sm px-3 py-1 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors disabled:opacity-50"
                        >
                          {updateMutation.isPending ? 'Saving...' : 'Save'}
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setIsEditing(true)}
                          className="text-sm px-3 py-1 border rounded hover:bg-muted transition-colors"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(selectedPolicyId)}
                          disabled={deleteMutation.isPending}
                          className="text-sm px-3 py-1 text-red-600 hover:text-red-700 dark:text-red-400 disabled:opacity-50"
                        >
                          {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Policy Metadata */}
                {selectedPolicy?.package_name && (
                  <div className="px-4 py-3 border-b bg-muted/20">
                    <p className="text-xs font-medium text-muted-foreground mb-2">Package:</p>
                    <div className="flex flex-wrap gap-2">
                      <span
                        className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-primary/10 text-primary"
                      >
                        {selectedPolicy.package_name}
                      </span>
                    </div>
                  </div>
                )}

                {/* Policy Content with Syntax Highlighting */}
                <div className="p-4">
                  {isEditing ? (
                    <RegoEditor
                      value={editContent}
                      onChange={(value) => setEditContent(value)}
                      height="600px"
                    />
                  ) : (
                    <RegoViewer
                      value={selectedPolicy?.content || ''}
                      height="600px"
                    />
                  )}
                </div>

                {/* Policy Stats */}
                {selectedPolicy && (
                  <div className="px-4 py-3 border-t bg-muted/20 text-xs text-muted-foreground">
                    <p>
                      Created: {new Date(selectedPolicy.created_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-card rounded-lg border max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-semibold">Upload OPA Policy</h2>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Policy Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="my_policy"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Used to identify and reference this policy
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Policy Content (Rego) <span className="text-red-500">*</span>
                </label>
                <RegoEditor
                  value={uploadContent}
                  onChange={(value) => setUploadContent(value)}
                  height="400px"
                  placeholder={`package sark.example

default allow = false

allow {
    input.user.role == "admin"
}`}
                />
              </div>

              <div className="bg-muted/50 p-3 rounded-md text-sm">
                <p className="font-medium mb-1">Tips:</p>
                <ul className="list-disc list-inside text-muted-foreground space-y-1">
                  <li>Policy must be valid Rego code</li>
                  <li>Use package name starting with "sark."</li>
                  <li>Define rules like "allow", "deny", or custom decisions</li>
                </ul>
              </div>
            </div>

            <div className="px-6 py-4 border-t flex justify-end space-x-3">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={uploadMutation.isPending}
                className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {uploadMutation.isPending ? 'Uploading...' : 'Upload Policy'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
