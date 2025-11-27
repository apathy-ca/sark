import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-2">SARK</h1>
          <p className="text-muted-foreground">
            Security Audit and Resource Kontroler
          </p>
        </div>
        <Outlet />
      </div>
    </div>
  );
}
