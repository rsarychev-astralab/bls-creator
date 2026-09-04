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
        className={cn(
          "min-h-9 rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm",
          wrap && "whitespace-pre-wrap break-words leading-snug",
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
            className="inline-flex items-start gap-1 break-all text-link hover:underline"
          >
            <span>{value}</span>
            <ExternalLink className="mt-0.5 size-3.5 shrink-0" />
          </a>
        ) : (
          value
        )}
      </div>
    </div>
  );
}

export { Field };
