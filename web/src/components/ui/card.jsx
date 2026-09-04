import { cn } from "@/lib/utils";

function Card({ className, ...props }) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-card text-card-foreground px-4 py-4 mt-4",
        className
      )}
      {...props}
    />
  );
}

function CardTitle({ className, ...props }) {
  return (
    <h2 className={cn("mb-3.5 text-base font-semibold", className)} {...props} />
  );
}

function CardDescription({ className, ...props }) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)} {...props} />
  );
}

export { Card, CardTitle, CardDescription };
