import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoginPage } from "@/pages/Login";
import { ChatPage } from "@/pages/Chat";
import { DashboardPage } from "@/pages/Dashboard";
import { FinancePage } from "@/pages/Finance";
import { ProcurementPage } from "@/pages/Procurement";
import { SalesPage } from "@/pages/Sales";
import { InventoryPage } from "@/pages/Inventory";
import { HRPage } from "@/pages/HR";
import { ApprovalsPage } from "@/pages/Approvals";
import { AuditPage } from "@/pages/Audit";
import { useAuthStore } from "@/store/auth";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <AppLayout />
          </RequireAuth>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="finance" element={<FinancePage />} />
        <Route path="procurement" element={<ProcurementPage />} />
        <Route path="sales" element={<SalesPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="hr" element={<HRPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="audit" element={<AuditPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
