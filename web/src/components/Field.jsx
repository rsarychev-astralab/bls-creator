import { ExternalLink } from "lucide-react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

function Field({ label, value, isLink = false, wrap = false, className, icon: Icon }) {
  const empty = !value;
  return (
    <div className={className}>
      {label ? (
        <Label className="flex items-center gap-1.5">
          {Icon ? <Icon className="size-3.5 shrink-0" /> : null}
          {label}
        </Label>
      ) : null}
      <div
        title={!empty && !wrap ? String(value) : undefined}
        className={cn(
          "rounded-lg border border-input bg-card px-2.5 text-sm",
          wrap
            ? "min-h-9 py-1.5 whitespace-pre-wrap break-words leading-snug"
            : "flex h-9 items-center overflow-hidden",
          empty && "text-[#b3b3b3]"
        )}
      >
        {empty ? (
          "—"
        ) : isLink ? (
          <a
            href={value}
            target="_blank"
            rel="noreferrer"
            className={cn(
              "inline-flex min-w-0 items-center gap-1 text-link hover:underline",
              wrap ? "break-all items-start" : "truncate"
            )}
          >
            <span className={wrap ? undefined : "truncate"}>{value}</span>
            <ExternalLink className="size-3.5 shrink-0" />
          </a>
        ) : wrap ? (
          value
        ) : (
          <span className="truncate">{value}</span>
        )}
      </div>
    </div>
  );
}

export { Field };
