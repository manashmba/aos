import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  ClipboardCheck,
  IndianRupee,
  MessageSquare,
  PackageSearch,
  ScrollText,
  ShoppingCart,
  UserRound,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/chat", label: "Chat", icon: MessageSquare },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
  { to: "/finance", label: "Finance", icon: IndianRupee },
  { to: "/procurement", label: "Procurement", icon: ShoppingCart },
  { to: "/sales", label: "Sales", icon: PackageSearch },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/hr", label: "HR", icon: UserRound },
  { to: "/approvals", label: "Approvals", icon: ClipboardCheck },
  { to: "/audit", label: "Audit", icon: ScrollText },
];

export function Sidebar() {
  return (
    <aside className="w-60 border-r bg-card">
      <div className="flex h-14 items-center px-6 border-b">
        <h1 className="text-base font-semibold tracking-tight">AOS</h1>
        <span className="ml-2 text-xs text-muted-foreground">v0.1</span>
      </div>
      <nav className="flex flex-col gap-1 p-3">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent/50",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
