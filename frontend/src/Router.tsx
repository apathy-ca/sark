import { createBrowserRouter, RouterProvider } from "react-router-dom";
import RootLayout from "./layouts/RootLayout";
import AuthLayout from "./layouts/AuthLayout";
import LoginPage from "./pages/auth/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ServersListPage from "./pages/servers/ServersListPage";
import ServerDetailPage from "./pages/servers/ServerDetailPage";
import ServerRegisterPage from "./pages/servers/ServerRegisterPage";
import PoliciesPage from "./pages/policies/PoliciesPage";
import AuditLogsPage from "./pages/audit/AuditLogsPage";
import ApiKeysPage from "./pages/apikeys/ApiKeysPage";
import SessionsPage from "./pages/sessions/SessionsPage";
import ProfilePage from "./pages/ProfilePage";

const router = createBrowserRouter([
  {
    path: "/auth",
    element: <AuthLayout />,
    children: [
      {
        path: "login",
        element: <LoginPage />,
      },
    ],
  },
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <DashboardPage />,
      },
      {
        path: "servers",
        children: [
          {
            index: true,
            element: <ServersListPage />,
          },
          {
            path: "register",
            element: <ServerRegisterPage />,
          },
          {
            path: ":serverId",
            element: <ServerDetailPage />,
          },
        ],
      },
      {
        path: "policies",
        element: <PoliciesPage />,
      },
      {
        path: "audit",
        element: <AuditLogsPage />,
      },
      {
        path: "api-keys",
        element: <ApiKeysPage />,
      },
      {
        path: "sessions",
        element: <SessionsPage />,
      },
      {
        path: "profile",
        element: <ProfilePage />,
      },
    ],
  },
]);

export default function Router() {
  return <RouterProvider router={router} />;
}
