import { useState } from 'react';
import { exportData, generateTimestampedFilename } from '@/utils/export';
import { toast } from 'sonner';

interface ExportButtonProps {
  data: any[];
  baseFilename: string;
  headers?: string[];
  disabled?: boolean;
  className?: string;
  label?: string;
}

/**
 * Reusable export button component with format selection
 * Supports CSV and JSON export formats
 */
export function ExportButton({
  data,
  baseFilename,
  headers,
  disabled = false,
  className = '',
  label = 'Export',
}: ExportButtonProps) {
  const [showMenu, setShowMenu] = useState(false);

  const handleExport = (format: 'csv' | 'json') => {
    try {
      if (data.length === 0) {
        toast.error('No data to export');
        return;
      }

      const filename = generateTimestampedFilename(baseFilename, format);
      exportData(data, filename.replace(`.${format}`, ''), format, headers);
      toast.success(`Exported ${data.length} items as ${format.toUpperCase()}`);
      setShowMenu(false);
    } catch (error) {
      toast.error(`Failed to export data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        disabled={disabled || data.length === 0}
        className={`px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      >
        📥 {label}
      </button>

      {showMenu && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowMenu(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 mt-2 w-48 bg-card border rounded-md shadow-lg z-20">
            <div className="py-1">
              <button
                onClick={() => handleExport('csv')}
                className="w-full px-4 py-2 text-left hover:bg-muted transition-colors flex items-center gap-2"
              >
                <span>📄</span>
                <div>
                  <div className="font-medium">Export as CSV</div>
                  <div className="text-xs text-muted-foreground">Comma-separated values</div>
                </div>
              </button>
              <button
                onClick={() => handleExport('json')}
                className="w-full px-4 py-2 text-left hover:bg-muted transition-colors flex items-center gap-2"
              >
                <span>📋</span>
                <div>
                  <div className="font-medium">Export as JSON</div>
                  <div className="text-xs text-muted-foreground">JavaScript Object Notation</div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface SimpleExportButtonProps {
  data: any[];
  filename: string;
  format: 'csv' | 'json';
  headers?: string[];
  disabled?: boolean;
  className?: string;
  label?: string;
}

/**
 * Simple export button for a specific format
 * No menu, exports directly on click
 */
export function SimpleExportButton({
  data,
  filename,
  format,
  headers,
  disabled = false,
  className = '',
  label,
}: SimpleExportButtonProps) {
  const handleExport = () => {
    try {
      if (data.length === 0) {
        toast.error('No data to export');
        return;
      }

      const timestampedFilename = generateTimestampedFilename(filename, format);
      exportData(data, timestampedFilename.replace(`.${format}`, ''), format, headers);
      toast.success(`Exported ${data.length} items as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(`Failed to export data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={disabled || data.length === 0}
      className={`px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      📥 {label || `Export ${format.toUpperCase()}`}
    </button>
  );
}
