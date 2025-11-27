interface PaginationProps {
  hasMore: boolean;
  onLoadMore: () => void;
  isLoading: boolean;
  currentCount?: number;
  totalCount?: number;
  className?: string;
}

/**
 * Pagination component for cursor-based pagination
 * Shows "Load More" button when more items are available
 */
export function Pagination({
  hasMore,
  onLoadMore,
  isLoading,
  currentCount,
  totalCount,
  className = '',
}: PaginationProps) {
  return (
    <div className={`flex flex-col items-center gap-3 ${className}`}>
      {currentCount !== undefined && totalCount !== undefined && (
        <p className="text-sm text-muted-foreground">
          Showing {currentCount} of {totalCount} items
        </p>
      )}

      {hasMore && (
        <button
          onClick={onLoadMore}
          disabled={isLoading}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <svg
                className="animate-spin h-4 w-4"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Loading...
            </span>
          ) : (
            'Load More'
          )}
        </button>
      )}

      {!hasMore && currentCount !== undefined && currentCount > 0 && (
        <p className="text-sm text-muted-foreground">No more items to load</p>
      )}
    </div>
  );
}

interface OffsetPaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  isLoading?: boolean;
  className?: string;
}

/**
 * Offset-based pagination component
 * Shows page numbers and navigation buttons
 */
export function OffsetPagination({
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  className = '',
}: OffsetPaginationProps) {
  const maxVisiblePages = 7;
  const halfVisible = Math.floor(maxVisiblePages / 2);

  let startPage = Math.max(1, currentPage - halfVisible);
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

  if (endPage - startPage < maxVisiblePages - 1) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }

  const pages = Array.from({ length: endPage - startPage + 1 }, (_, i) => startPage + i);

  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1 || isLoading}
        className="px-3 py-1 border rounded-md hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Previous page"
      >
        ←
      </button>

      {startPage > 1 && (
        <>
          <button
            onClick={() => onPageChange(1)}
            disabled={isLoading}
            className="px-3 py-1 border rounded-md hover:bg-muted transition-colors"
          >
            1
          </button>
          {startPage > 2 && <span className="px-2 text-muted-foreground">...</span>}
        </>
      )}

      {pages.map((page) => (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          disabled={isLoading}
          className={`px-3 py-1 border rounded-md transition-colors ${
            page === currentPage
              ? 'bg-primary text-primary-foreground'
              : 'hover:bg-muted'
          }`}
        >
          {page}
        </button>
      ))}

      {endPage < totalPages && (
        <>
          {endPage < totalPages - 1 && <span className="px-2 text-muted-foreground">...</span>}
          <button
            onClick={() => onPageChange(totalPages)}
            disabled={isLoading}
            className="px-3 py-1 border rounded-md hover:bg-muted transition-colors"
          >
            {totalPages}
          </button>
        </>
      )}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages || isLoading}
        className="px-3 py-1 border rounded-md hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Next page"
      >
        →
      </button>
    </div>
  );
}
