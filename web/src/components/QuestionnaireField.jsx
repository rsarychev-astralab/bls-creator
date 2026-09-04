import { FileText, Upload } from "lucide-react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

function QuestionnaireField({ name, ok, collected, uploading, onUpload }) {
  return (
    <div className="sm:col-span-2">
      <Label className="flex items-center gap-1.5">
        <FileText className="size-3.5 shrink-0" />
        Анкета
      </Label>
      {ok && name ? (
        <div className="min-h-9 rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm">
          {name}
        </div>
      ) : collected ? (
        <label
          className={cn(
            "flex min-h-9 cursor-pointer items-center justify-between gap-2 rounded-lg border border-dashed border-input bg-card px-2.5 py-1.5 text-sm text-muted-foreground",
            uploading && "pointer-events-none opacity-45"
          )}
        >
          <span>{uploading ? "Загружаю анкету…" : "Файл не найден. Загрузи .xlsx, .docx, .txt, .md или .csv"}</span>
          <Upload className="size-4 shrink-0" />
          <input
            type="file"
            accept=".xlsx,.docx,.txt,.md,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            className="sr-only"
            disabled={uploading}
            onChange={(event) => {
              const file = event.target.files && event.target.files[0];
              event.target.value = "";
              if (file) onUpload(file);
            }}
          />
        </label>
      ) : (
        <div className="min-h-9 rounded-lg border border-input bg-card px-2.5 py-1.5 text-sm text-[#b3b3b3]">
          —
        </div>
      )}
    </div>
  );
}

export { QuestionnaireField };
