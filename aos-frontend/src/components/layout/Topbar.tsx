import { useTranslation } from "react-i18next";
import { LogOut, Menu } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useAuthStore } from "@/store/auth";
import { DEMO_MODE } from "@/lib/api";

interface Props {
  onMenu?: () => void;
}

export function Topbar({ onMenu }: Props = {}) {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const initials = (user?.name ?? "")
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="flex h-14 items-center justify-between border-b bg-card/80 px-4 backdrop-blur lg:px-6">
      <div className="flex items-center gap-3 text-sm">
        {onMenu && (
          <button
            onClick={onMenu}
            aria-label="Open menu"
            className="rounded-md p-2 text-muted-foreground hover:bg-muted hover:text-foreground lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
          {initials || "U"}
        </div>
        <div className="leading-tight">
          <div className="font-medium">{user?.name ?? "—"}</div>
          <div className="text-xs capitalize text-muted-foreground">{user?.role}</div>
        </div>
        {DEMO_MODE && (
          <span className="rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-900">
            {t("topbar.demoBadge")}
          </span>
        )}
      </div>

      <div className="flex items-center gap-1">
        <LanguageSwitcher />
        <Button variant="ghost" size="sm" onClick={logout}>
          <LogOut className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">{t("topbar.signOut")}</span>
        </Button>
      </div>
    </header>
  );
}
