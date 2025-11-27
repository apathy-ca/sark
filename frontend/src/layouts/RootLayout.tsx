import { Outlet, Link, useNavigate } from "react-router-dom";
import { useEffect } from "react";
import { getAccessToken } from "../services/api";
import { ThemeToggleIcon } from "@/components/ThemeToggle";
import { KeyboardShortcutsHelp } from "@/components/KeyboardShortcutsHelp";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

export default function RootLayout() {
  const navigate = useNavigate();

  // Enable global keyboard shortcuts
  useKeyboardShortcuts();

  useEffect(() => {
    // Check if user is authenticated
    const token = getAccessToken();
    if (!token) {
      navigate("/auth/login");
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-8">
              <Link to="/" className="text-2xl font-bold">
                SARK
              </Link>
              <nav className="hidden md:flex space-x-6">
                <Link
                  to="/"
                  className="text-foreground/80 hover:text-foreground transition-colors"
                >
                  Dashboard
                </Link>
                <Link
                  to="/servers"
                  className="text-foreground/80 hover:text-foreground transition-colors"
                >
                  Servers
                </Link>
                <Link
                  to="/policies"
                  className="text-foreground/80 hover:text-foreground transition-colors"
                >
                  Policies
                </Link>
                <Link
                  to="/audit"
                  className="text-foreground/80 hover:text-foreground transition-colors"
                >
                  Audit
                </Link>
                <Link
                  to="/api-keys"
                  className="text-foreground/80 hover:text-foreground transition-colors"
                >
                  API Keys
                </Link>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <ThemeToggleIcon />
              <Link
                to="/profile"
                className="text-foreground/80 hover:text-foreground transition-colors"
              >
                Profile
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <Outlet />
      </main>

      {/* Keyboard Shortcuts Help Modal */}
      <KeyboardShortcutsHelp />
    </div>
  );
}
