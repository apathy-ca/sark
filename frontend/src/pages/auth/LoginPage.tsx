export default function LoginPage() {
  return (
    <div className="bg-card p-8 rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6">Login</h2>
      <form className="space-y-4">
        <div>
          <label htmlFor="username" className="block text-sm font-medium mb-2">
            Username
          </label>
          <input
            type="text"
            id="username"
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
            placeholder="john.doe"
          />
        </div>
        <div>
          <label htmlFor="password" className="block text-sm font-medium mb-2">
            Password
          </label>
          <input
            type="password"
            id="password"
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
            placeholder="••••••••"
          />
        </div>
        <button
          type="submit"
          className="w-full bg-primary text-primary-foreground py-2 rounded-md hover:opacity-90 transition-opacity"
        >
          Sign In
        </button>
      </form>
      <div className="mt-6 text-center text-sm text-muted-foreground">
        <p>Development credentials:</p>
        <p className="mt-1">john.doe / password</p>
      </div>
    </div>
  );
}
