import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/format";

function SourceBadges({ items }) {
  if (!items.length) return null;
  return (
    <div className="mb-2.5 flex flex-wrap gap-3 text-xs text-muted-foreground">
      {items.map((item) => (
        <Badge key={item.label} variant={item.ok ? "ok" : "bad"}>
          {item.label} - {sourceLabel(item.source)} - {item.ok ? "ок" : "ошибка"}
        </Badge>
      ))}
    </div>
  );
}

export { SourceBadges };
