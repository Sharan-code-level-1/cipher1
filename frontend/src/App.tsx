import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { useThemeStore } from "@/stores/theme";
import { api } from "@/api/client";
import AppShell from "@/components/layout/AppShell";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import CustomerDashboard from "@/pages/customer/Dashboard";
import ClaimsPage from "@/pages/customer/ClaimsPage";
import ClaimDetailPage from "@/pages/customer/ClaimDetailPage";
import NewClaimPage from "@/pages/customer/NewClaimPage";
import VehiclesPage from "@/pages/customer/VehiclesPage";
import SurveyorQueue from "@/pages/surveyor/SurveyorQueue";
import AdminDashboard from "@/pages/admin/AdminDashboard";
import AdminUsers from "@/pages/admin/AdminUsers";
import AdminAudit from "@/pages/admin/AdminAudit";
import type { User } from "@/types";

function Protected({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.accessToken);
  if (!token || !user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role) && user.role !== "super_admin") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function HomeRedirect() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  if (["admin", "super_admin", "insurance_officer"].includes(user.role)) {
    return <Navigate to="/admin" replace />;
  }
  if (["surveyor", "fraud_analyst"].includes(user.role)) {
    return <Navigate to="/surveyor" replace />;
  }
  return <Navigate to="/app" replace />;
}

export default function App() {
  const setUser = useAuthStore((s) => s.setUser);
  const token = useAuthStore((s) => s.accessToken);
  const logout = useAuthStore((s) => s.logout);
  const dark = useThemeStore((s) => s.dark);
  const setDark = useThemeStore((s) => s.setDark);

  useEffect(() => {
    setDark(dark);
  }, [dark, setDark]);

  useEffect(() => {
    if (!token) return;
    api
      .get<User>("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => logout());
  }, [token, setUser, logout]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route
        path="/app"
        element={
          <Protected roles={["customer"]}>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<CustomerDashboard />} />
        <Route path="claims" element={<ClaimsPage />} />
        <Route path="claims/new" element={<NewClaimPage />} />
        <Route path="claims/:id" element={<ClaimDetailPage />} />
        <Route path="vehicles" element={<VehiclesPage />} />
      </Route>

      <Route
        path="/surveyor"
        element={
          <Protected roles={["surveyor", "fraud_analyst", "admin", "super_admin"]}>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<SurveyorQueue />} />
        <Route path="claims/:id" element={<ClaimDetailPage />} />
      </Route>

      <Route
        path="/admin"
        element={
          <Protected roles={["admin", "super_admin", "insurance_officer"]}>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="audit" element={<AdminAudit />} />
        <Route path="claims/:id" element={<ClaimDetailPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
