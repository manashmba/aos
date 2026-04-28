import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Boxes } from "lucide-react";
import { InventoryAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export function InventoryPage() {
  const { t } = useTranslation();
  const reorder = useQuery({
    queryKey: ["reorder", "full"],
    queryFn: () => InventoryAPI.reorderSuggestions().then((r) => r.data),
  });

  const rows = (reorder.data as any[] | undefined) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Boxes className="h-5 w-5 text-muted-foreground" />
        <h2 className="text-2xl font-semibold tracking-tight">{t("nav.inventory")}</h2>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">{t("dashboard.reorderTitle")}</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {reorder.isLoading ? (
            <p className="p-6 text-sm text-muted-foreground">{t("common.loading")}</p>
          ) : rows.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">{t("dashboard.colProduct")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("dashboard.colOnHand")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("dashboard.colReorder")}</th>
                    <th className="px-4 py-2 text-right font-medium">{t("dashboard.colSuggested")}</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-t hover:bg-muted/30">
                      <td className="px-4 py-2">{r.product_name ?? r.product_id}</td>
                      <td className="px-4 py-2 text-right tabular-nums">{r.on_hand}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{r.reorder_level}</td>
                      <td className="px-4 py-2 text-right font-medium tabular-nums">{r.suggested_qty}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="p-6 text-sm text-muted-foreground">{t("dashboard.healthy")}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
