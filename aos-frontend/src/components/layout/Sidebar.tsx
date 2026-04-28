import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  BarChart3,
  Boxes,
  ClipboardCheck,
  IndianRupee,
  MessageSquare,
  PackageSearch,
  ScrollText,
  ShoppingCart,
  Sparkles,
  UserRound,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Item {
  to: string;
  key: string;       // i18n key under `nav.*`
  icon: React.ElementType;
}

const SECTIONS: Array<{ label: string; items: Item[] }> = [
  {
    label: "nav.sectionWorkspace",
    items: [
      { to: "/chat",      key: "nav.chat",      icon: MessageSquare },
      { to: "/dashboard", key: "nav.dashboard", icon: BarChart3 },
    ],
  },
  {
    label: "nav.sectionModules",
    items: [
      { to: "/finance",     key: "nav.finance",     icon: IndianRupee },
      { to: "/procurement", key: "nav.procurement", icon: ShoppingCart },
      { to: "/sales",       key: "nav.sales",       icon: PackageSearch },
      { to: "/inventory",   key: "nav.inventory",   icon: Boxes },
      { to: "/hr",          key: "nav.hr",          icon: UserRound },
    ],
  },
  {
    label: "nav.sectionGovern",
    items: [
      { to: "/approvals", key: "nav.approvals", icon: ClipboardCheck },
      { to: "/audit",     key: "nav.audit",     icon: ScrollText },
    ],
  },
];

interface Props {
  /** When provided, sidebar renders as a mobile drawer with a backdrop. */
  open?: boolean;
  onClose?: () => void;
}

export function Sidebar({ open, onClose }: Props) {
  const { t } = useTranslation();
  const isDrawer = typeof open === "boolean";

  const body = (
    <>
      <div className="flex h-14 items-center gap-2 border-b px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
        <h1 className="text-sm font-semibold tracking-tight">{t("brand.name", "AOS")}</h1>
        <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          v0.1
        </span>
        {isDrawer && (
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="ml-auto rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 overflow-auto p-3">
        {SECTIONS.map((section) => (
          <div key={section.label} className="mb-5 last:mb-0">
            <div className="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/80">
              {t(section.label)}
            </div>
            <div className="flex flex-col gap-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={isDrawer ? onClose : undefined}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-primary/10 font-medium text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" />
                  <span className="truncate">{t(item.key)}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>
    </>
  );

  // ── Desktop: persistent rail ─────────────────────────────────────
  if (!isDrawer) {
    return (
      <aside className="hidden w-64 shrink-0 flex-col border-r bg-card/60 backdrop-blur lg:flex">
        {body}
      </aside>
    );
  }

  // ── Mobile: slide-in drawer with backdrop ────────────────────────
  return (
    <>
      <div
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-foreground/40 backdrop-blur-sm transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r bg-card shadow-xl transition-transform duration-200 lg:hidden",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-hidden={!open}
      >
        {body}
      </aside>
    </>
  );
}
