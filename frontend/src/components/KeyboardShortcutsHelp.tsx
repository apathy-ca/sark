import { useState } from 'react';
import { useHotkeys } from 'react-hotkeys-hook';
import { KEYBOARD_SHORTCUTS, type KeyboardShortcut } from '@/hooks/useKeyboardShortcuts';

/**
 * Keyboard shortcuts help modal
 * Shows all available shortcuts grouped by category
 */
export function KeyboardShortcutsHelp() {
  const [isOpen, setIsOpen] = useState(false);

  // Toggle with Ctrl+/ or Cmd+/
  useHotkeys('ctrl+/, meta+/', (e) => {
    e.preventDefault();
    setIsOpen((prev) => !prev);
  });

  // Close with Escape
  useHotkeys('escape', () => {
    if (isOpen) setIsOpen(false);
  }, { enabled: isOpen });

  if (!isOpen) return null;

  // Group shortcuts by category
  const groupedShortcuts = KEYBOARD_SHORTCUTS.reduce((acc, shortcut) => {
    if (!acc[shortcut.category]) {
      acc[shortcut.category] = [];
    }
    acc[shortcut.category].push(shortcut);
    return acc;
  }, {} as Record<string, KeyboardShortcut[]>);

  const formatKey = (key: string) => {
    return key
      .split('+')
      .map((k) => k.trim())
      .map((k) => {
        // Replace common key names with symbols
        const keyMap: Record<string, string> = {
          ctrl: '⌃',
          cmd: '⌘',
          meta: '⌘',
          alt: '⌥',
          shift: '⇧',
          escape: 'Esc',
        };
        return keyMap[k.toLowerCase()] || k.toUpperCase();
      });
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-card rounded-lg border max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="sticky top-0 bg-card px-6 py-4 border-b flex justify-between items-center">
          <h2 className="text-2xl font-semibold">Keyboard Shortcuts</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-foreground p-1"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="p-6 space-y-6">
          {Object.entries(groupedShortcuts).map(([category, shortcuts]) => (
            <div key={category}>
              <h3 className="text-lg font-semibold mb-3 text-primary">{category}</h3>
              <div className="space-y-2">
                {shortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-2 rounded hover:bg-muted/50"
                  >
                    <span className="text-foreground">{shortcut.description}</span>
                    <div className="flex gap-1">
                      {formatKey(shortcut.key).map((key, i) => (
                        <kbd
                          key={i}
                          className="px-2 py-1 text-xs font-semibold text-foreground bg-muted border border-border rounded shadow-sm"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="pt-4 border-t">
            <p className="text-sm text-muted-foreground text-center">
              Press <kbd className="px-2 py-1 text-xs font-semibold bg-muted border border-border rounded">Ctrl</kbd> +{' '}
              <kbd className="px-2 py-1 text-xs font-semibold bg-muted border border-border rounded">/</kbd> to toggle this help
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
