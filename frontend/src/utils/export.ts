/**
 * Data export utilities for CSV and JSON formats
 */

/**
 * Convert an array of objects to CSV format
 * @param data - Array of objects to convert
 * @param headers - Optional custom headers. If not provided, uses object keys
 * @returns CSV string
 */
export function convertToCSV(data: any[], headers?: string[]): string {
  if (data.length === 0) return '';

  // Use provided headers or extract from first object
  const csvHeaders = headers || Object.keys(data[0]);

  // Create header row
  const headerRow = csvHeaders.join(',');

  // Create data rows
  const dataRows = data.map((item) => {
    return csvHeaders
      .map((header) => {
        const value = item[header];

        // Handle null/undefined
        if (value === null || value === undefined) return '';

        // Handle objects/arrays
        if (typeof value === 'object') {
          return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
        }

        // Handle strings with commas or quotes
        const stringValue = String(value);
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }

        return stringValue;
      })
      .join(',');
  });

  return [headerRow, ...dataRows].join('\n');
}

/**
 * Export data as CSV file
 * @param data - Array of objects to export
 * @param filename - Name of the file (without extension)
 * @param headers - Optional custom headers
 */
export function exportToCSV(data: any[], filename: string, headers?: string[]): void {
  const csv = convertToCSV(data, headers);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  downloadBlob(blob, `${filename}.csv`);
}

/**
 * Export data as JSON file
 * @param data - Data to export (can be object or array)
 * @param filename - Name of the file (without extension)
 * @param pretty - Whether to pretty-print the JSON (default: true)
 */
export function exportToJSON(data: any, filename: string, pretty: boolean = true): void {
  const json = pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data);
  const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
  downloadBlob(blob, `${filename}.json`);
}

/**
 * Export data as both CSV and JSON (user chooses format)
 * @param data - Array of objects to export
 * @param baseFilename - Base name of the file (without extension)
 * @param format - Export format ('csv' | 'json')
 * @param headers - Optional custom headers for CSV
 */
export function exportData(
  data: any[],
  baseFilename: string,
  format: 'csv' | 'json',
  headers?: string[]
): void {
  if (format === 'csv') {
    exportToCSV(data, baseFilename, headers);
  } else {
    exportToJSON(data, baseFilename);
  }
}

/**
 * Download a blob as a file
 * @param blob - Blob to download
 * @param filename - Name of the file
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Format data for export by flattening nested objects
 * @param data - Array of objects with potential nested properties
 * @param flattenNested - Whether to flatten nested objects (default: true)
 * @returns Flattened array suitable for CSV export
 */
export function prepareForExport(data: any[], flattenNested: boolean = true): any[] {
  if (!flattenNested) return data;

  return data.map((item) => {
    const flattened: any = {};

    function flatten(obj: any, prefix: string = ''): void {
      for (const key in obj) {
        const value = obj[key];
        const newKey = prefix ? `${prefix}.${key}` : key;

        if (value && typeof value === 'object' && !Array.isArray(value)) {
          flatten(value, newKey);
        } else if (Array.isArray(value)) {
          flattened[newKey] = value.join('; ');
        } else {
          flattened[newKey] = value;
        }
      }
    }

    flatten(item);
    return flattened;
  });
}

/**
 * Copy data to clipboard as JSON
 * @param data - Data to copy
 * @param pretty - Whether to pretty-print the JSON
 */
export async function copyToClipboard(data: any, pretty: boolean = true): Promise<void> {
  const json = pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data);

  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(json);
  } else {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = json;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
  }
}

/**
 * Generate a filename with timestamp
 * @param base - Base filename
 * @param extension - File extension (without dot)
 * @returns Filename with timestamp
 */
export function generateTimestampedFilename(base: string, extension: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  return `${base}-${timestamp}.${extension}`;
}
