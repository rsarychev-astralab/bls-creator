import {
  ChartColumn,
  Clock3,
  Gauge,
  Layers,
  MessageSquare,
  MousePointerClick,
  Package,
  Percent,
  Play,
  Target,
} from "lucide-react";
import { Field } from "@/components/Field";
import { CLOSING_FIELDS } from "@/lib/format";

const CLOSING_ICONS = {
  volumeActual: Package,
  ctrActual: MousePointerClick,
  vtrActual: Play,
  passingIndexActual: Gauge,
  brandRateActual: Percent,
  timeActual: Clock3,
  depthActual: Layers,
  conversionsActual: Target,
  feedback: MessageSquare,
};

function ClosingBlock({ rows }) {
  const byKey = {};
  for (const row of rows || []) {
    if (row && row.key) byKey[row.key] = row.value || "";
  }
  return (
    <div className="col-span-full mt-1.5 border-t border-border pt-3">
      <h3 className="mb-2.5 flex items-center gap-1.5 text-[0.95rem] font-semibold">
        <ChartColumn className="size-4 shrink-0" />
        Закрытие
      </h3>
      <div className="grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2">
        {CLOSING_FIELDS.map((spec) => (
          <Field
            key={spec.key}
            label={spec.label}
            icon={CLOSING_ICONS[spec.key]}
            value={byKey[spec.key] || ""}
            wrap={spec.wide}
            className={spec.wide ? "sm:col-span-2" : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export { ClosingBlock };
