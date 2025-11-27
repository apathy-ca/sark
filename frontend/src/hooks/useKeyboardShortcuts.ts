import { useHotkeys } from 'react-hotkeys-hook';
import { useNavigate } from 'react-router-dom';

export interface KeyboardShortcut {
  key: string;
  description: string;
  category: string;
}

/**
 * All available keyboard shortcuts in the application
 */
export const KEYBOARD_SHORTCUTS: KeyboardShortcut[] = [
  // Navigation
  { key: 'g d', description: 'Go to Dashboard', category: 'Navigation' },
  { key: 'g s', description: 'Go to Servers', category: 'Navigation' },
  { key: 'g p', description: 'Go to Policies', category: 'Navigation' },
  { key: 'g a', description: 'Go to Audit Logs', category: 'Navigation' },
  { key: 'g k', description: 'Go to API Keys', category: 'Navigation' },

  // Actions
  { key: 'ctrl+n', description: 'Create new (context-aware)', category: 'Actions' },
  { key: 'ctrl+k', description: 'Open command palette', category: 'Actions' },
  { key: 'ctrl+/', description: 'Show keyboard shortcuts', category: 'Actions' },
  { key: 'escape', description: 'Close modal/cancel', category: 'Actions' },

  // Theme
  { key: 't', description: 'Toggle theme', category: 'UI' },
];

/**
 * Hook for global keyboard shortcuts
 * Provides navigation and common actions
 */
export function useKeyboardShortcuts() {
  const navigate = useNavigate();

  // Navigation shortcuts (g + key)
  useHotkeys('g', () => {}, { preventDefault: false }); // Enable g as prefix

  useHotkeys('g,d', (e) => {
    e.preventDefault();
    navigate('/');
  });

  useHotkeys('g,s', (e) => {
    e.preventDefault();
    navigate('/servers');
  });

  useHotkeys('g,p', (e) => {
    e.preventDefault();
    navigate('/policies');
  });

  useHotkeys('g,a', (e) => {
    e.preventDefault();
    navigate('/audit');
  });

  useHotkeys('g,k', (e) => {
    e.preventDefault();
    navigate('/api-keys');
  });
}

/**
 * Hook for page-specific keyboard shortcuts
 * @param shortcuts - Object mapping keys to callback functions
 * @param options - Configuration options
 */
export function usePageShortcuts(
  shortcuts: Record<string, () => void>,
  options?: {
    enabled?: boolean;
    preventDefault?: boolean;
  }
) {
  const { enabled = true, preventDefault = true } = options || {};

  Object.entries(shortcuts).forEach(([key, callback]) => {
    useHotkeys(
      key,
      (e) => {
        if (preventDefault) e.preventDefault();
        callback();
      },
      { enabled }
    );
  });
}
