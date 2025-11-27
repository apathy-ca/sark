import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { oneDark } from '@codemirror/theme-one-dark';
import { useUIStore } from '@/stores/uiStore';

interface RegoEditorProps {
  value: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  height?: string;
  placeholder?: string;
}

/**
 * Rego code editor with syntax highlighting
 * Uses JavaScript mode as Rego has similar syntax patterns
 */
export function RegoEditor({
  value,
  onChange,
  readOnly = false,
  height = '600px',
  placeholder = 'Enter Rego policy code...',
}: RegoEditorProps) {
  const { theme } = useUIStore();
  const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  return (
    <div className="border rounded-lg overflow-hidden">
      <CodeMirror
        value={value}
        height={height}
        extensions={[javascript()]}
        onChange={onChange}
        readOnly={readOnly}
        placeholder={placeholder}
        theme={isDark ? oneDark : 'light'}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLineGutter: true,
          highlightSpecialChars: true,
          foldGutter: true,
          drawSelection: true,
          dropCursor: true,
          allowMultipleSelections: true,
          indentOnInput: true,
          syntaxHighlighting: true,
          bracketMatching: true,
          closeBrackets: true,
          autocompletion: true,
          rectangularSelection: true,
          crosshairCursor: true,
          highlightActiveLine: true,
          highlightSelectionMatches: true,
          closeBracketsKeymap: true,
          searchKeymap: true,
          foldKeymap: true,
          completionKeymap: true,
          lintKeymap: true,
        }}
        className="text-sm"
      />
    </div>
  );
}

interface RegoViewerProps {
  value: string;
  height?: string;
}

/**
 * Read-only Rego code viewer with syntax highlighting
 */
export function RegoViewer({ value, height = '400px' }: RegoViewerProps) {
  return <RegoEditor value={value} readOnly height={height} />;
}
