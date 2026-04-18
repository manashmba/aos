import { useQuery } from "@tanstack/react-query";
import { InventoryAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

export function InventoryPage() {
  const reorder = useQuery({
    queryKey: ["reorder", "full"],
    queryFn: () => InventoryAPI.reorderSuggestions().then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-semibold">Inventory</h2>
      <Card>
        <CardHeader>
          <CardTitle>Reorder suggestions</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-muted p-3 rounded overflow-auto">
            {JSON.stringify(reorder.data ?? [], null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
