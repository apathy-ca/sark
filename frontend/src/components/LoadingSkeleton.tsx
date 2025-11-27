/**
 * Loading skeleton components for various UI elements
 * Provides visual feedback while content is loading
 */

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="bg-card rounded-lg border overflow-hidden">
      <div className="animate-pulse">
        {/* Header */}
        <div className="bg-muted/50 p-4 border-b flex gap-4">
          <div className="h-4 bg-muted rounded flex-1" />
          <div className="h-4 bg-muted rounded flex-1" />
          <div className="h-4 bg-muted rounded flex-1" />
          <div className="h-4 bg-muted rounded w-20" />
        </div>

        {/* Rows */}
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="p-4 border-b flex gap-4">
            <div className="h-4 bg-muted rounded flex-1" />
            <div className="h-4 bg-muted rounded flex-1" />
            <div className="h-4 bg-muted rounded flex-1" />
            <div className="h-4 bg-muted rounded w-20" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-card p-6 rounded-lg border">
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-muted rounded w-1/3" />
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded" />
          <div className="h-4 bg-muted rounded w-5/6" />
        </div>
      </div>
    </div>
  );
}

export function ListSkeleton({ items = 5 }: { items?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="bg-card p-4 rounded-lg border">
          <div className="animate-pulse flex items-center gap-4">
            <div className="h-10 w-10 bg-muted rounded-full" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-muted rounded w-1/4" />
              <div className="h-3 bg-muted rounded w-2/3" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function FormSkeleton() {
  return (
    <div className="bg-card p-6 rounded-lg border space-y-6">
      <div className="animate-pulse space-y-4">
        <div>
          <div className="h-4 bg-muted rounded w-24 mb-2" />
          <div className="h-10 bg-muted rounded" />
        </div>
        <div>
          <div className="h-4 bg-muted rounded w-32 mb-2" />
          <div className="h-10 bg-muted rounded" />
        </div>
        <div>
          <div className="h-4 bg-muted rounded w-28 mb-2" />
          <div className="h-24 bg-muted rounded" />
        </div>
        <div className="flex gap-3 justify-end">
          <div className="h-10 bg-muted rounded w-24" />
          <div className="h-10 bg-muted rounded w-32" />
        </div>
      </div>
    </div>
  );
}

export function Spinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <div
      className={`inline-block animate-spin rounded-full border-2 border-border border-t-primary ${sizeClasses[size]}`}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center space-y-4">
        <Spinner size="lg" />
        <p className="text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}
