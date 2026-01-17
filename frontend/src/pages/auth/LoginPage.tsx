import { useState, FormEvent } from 'react';
import { useAuth } from '../../hooks/useAuth';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoggingIn } = useAuth();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    login({ username, password });
  };

  return (
    <div className="bg-card p-8 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6">Login</h2>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label htmlFor="username" className="block text-sm font-medium mb-2">
            Username
          </label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
            placeholder="john.doe"
            required
            disabled={isLoggingIn}
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium mb-2">
            Password
          </label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
            placeholder="••••••••"
            required
            disabled={isLoggingIn}
          />
        </div>
        <button
          type="submit"
          disabled={isLoggingIn}
          className="w-full bg-primary text-primary-foreground py-2 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoggingIn ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
      <div className="mt-6 text-center text-sm text-muted-foreground">
        <p>Development credentials:</p>
        <p className="mt-1">john.doe / password</p>
      </div>
    </div>
  );
}
