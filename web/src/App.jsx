import { useEffect, useRef, useState } from "react";
import {
  Calendar,
  ChartColumn,
  CircleStop,
  ClipboardList,
  Coins,
  Braces,
  Database,
  FileSpreadsheet,
  FileText,
  Hourglass,
  Link,
  Megaphone,
  NotebookText,
  Sparkles,
  Table2,
  Timer,
  Users,
  UsersRound,
} from "lucide-react";
import { ClosingBlock } from "@/components/ClosingBlock";
import { IdleRaccoon, useIdleRaccoon } from "@/components/Critter";
import { Field } from "@/components/Field";
import { QuestionnaireField } from "@/components/QuestionnaireField";
import { SourceBadges } from "@/components/SourceBadges";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { getJson, postForm, postJson } from "@/lib/api";
import { DONE_PHRASES, MODEL_PHRASES, pickPhrase, shufflePhrases } from "@/lib/modelPhrases";
import {
  collectPreview,
  dealLinks,
  formatElapsed,
  formatRespondents,
  formatTokens,
  optionLabel,
  respondentsFromPayload,
} from "@/lib/format";
import { cn } from "@/lib/utils";

const NONE = "__none__";

const SLOGANS = [
  "We create attention",
  "We create lift",
  "We create хаос",
  "We still create attention",
];

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [row, setRow] = useState(NONE);
  const [current, setCurrent] = useState(null);
  const [collected, setCollected] = useState(false);
  const [status, setStatus] = useState({ text: "", kind: "" });
  const [collecting, setCollecting] = useState(false);
  const [modeling, setModeling] = useState(false);
  const [workOpen, setWorkOpen] = useState(false);
  const [workOpenItems, setWorkOpenItems] = useState([]);
  const [badges, setBadges] = useState([]);
  const [collectView, setCollectView] = useState("");
  const [promptView, setPromptView] = useState("");
  const [modelView, setModelView] = useState("");
  const [elapsed, setElapsed] = useState("");
  const [tokens, setTokens] = useState("");
  const [qOk, setQOk] = useState(false);
  const [qName, setQName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [waitPhrases, setWaitPhrases] = useState(false);
  const [sloganIndex, setSloganIndex] = useState(0);
  const abortRef = useRef(null);
  const raccoonVisible = useIdleRaccoon(collecting || modeling || uploading);

  const { notionUrl, crmUrl } = dealLinks(current);
  const linkCount = [crmUrl, notionUrl, current?.bt_url].filter(Boolean).length;
  const closingFilled = (current?.closing || []).filter((row) => row && row.value).length;

  useEffect(() => {
    if (!waitPhrases) return undefined;
    let deck = shufflePhrases(MODEL_PHRASES);
    let index = 0;
    setStatus({ text: deck[0].text, kind: "", icon: deck[0].icon });
    const timer = setInterval(() => {
      index += 1;
      if (index >= deck.length) {
        deck = shufflePhrases(MODEL_PHRASES, deck[deck.length - 1].text);
        index = 0;
      }
      const next = deck[index];
      setStatus({ text: next.text, kind: "", icon: next.icon });
    }, 3500);
    return () => clearInterval(timer);
  }, [waitPhrases]);

  useEffect(() => {
    getJson("/api/campaigns")
      .then((data) => {
        const items = data.items || [];
        setCampaigns(items);
        setStatus({ text: `В списке ${items.length} кампаний`, kind: "" });
      })
      .catch((err) => {
        setStatus({ text: err.message, kind: "bad" });
      });
  }, []);

  function resetWork() {
    setCollected(false);
    setWorkOpen(false);
    setWorkOpenItems([]);
    setBadges([]);
    setCollectView("");
    setPromptView("");
    setModelView("");
    setElapsed("");
    setTokens("");
    setQOk(false);
    setQName("");
    setUploading(false);
    setWaitPhrases(false);
  }

  function applyPack(pack, nextCurrent) {
    const q = pack.questionnaire || {};
    const crm = pack.crm || {};
    const src = pack.sources || {};
    const questionnaireOk = Boolean(q.ok && q.text);
    if (nextCurrent) setCurrent(nextCurrent);
    setCollected(true);
    setQOk(questionnaireOk);
    setQName(q.name || (questionnaireOk ? "Анкета найдена" : ""));
    setWorkOpen(true);
    setWorkOpenItems(["collect"]);
    setPromptView(pack.prompt || "Промпт ещё не собран");
    setModelView("Сначала смоделируй исследование");
    setBadges([
      { label: "Карточка", source: crm.source || src.brand || "crm", ok: Boolean(crm.ok) },
      { label: "Бренд", source: src.brand, ok: Boolean(pack.advertised_brand) },
      { label: "Гео", source: src.geo, ok: Boolean(pack.geo) },
      { label: "ЦА", source: src.targeting, ok: Boolean(pack.targeting) },
      { label: "Анкета", source: src.questionnaire || q.source, ok: questionnaireOk },
      { label: "БТ", source: src.bt, ok: Boolean(pack.bt_url) },
      { label: "Закрытие", source: src.closing, ok: Boolean(src.closing) },
    ]);
    setCollectView(JSON.stringify(collectPreview(pack), null, 2));
    setStatus({
      text: questionnaireOk
        ? "Данные собраны. Можно моделировать."
        : q.error || "Не удалось собрать анкету",
      kind: questionnaireOk ? "" : "bad",
    });
  }

  function onSelectCampaign(value) {
    if (abortRef.current) abortRef.current.abort();
    setRow(value);
    if (value === NONE) {
      setCurrent(null);
      resetWork();
      setStatus({ text: "", kind: "" });
      return;
    }
    const next = campaigns.find((item) => String(item.row) === value) || null;
    setCurrent(next);
    resetWork();
    setStatus({ text: next ? "Можно собирать данные" : "", kind: "" });
  }

  async function onCollect() {
    if (!current) return;
    setCollecting(true);
    setStatus({ text: "Собираю анкету и CRM…", kind: "" });
    try {
      const pack = await postJson("/api/collect", { row: current.row });
      applyPack(pack, {
        ...current,
        targeting: pack.targeting || "",
        respondents_contact: pack.respondents_contact,
        respondents_noncontact: pack.respondents_noncontact,
        crm_deal_url: pack.crm_deal_url || "",
        notion_url: pack.notion_url || current.crm_url || "",
        bt_url: pack.bt_url || "",
        closing: pack.closing || [],
      });
    } catch (err) {
      setCollected(false);
      setStatus({ text: err.message, kind: "bad" });
    } finally {
      setCollecting(false);
    }
  }

  async function onStop() {
    if (abortRef.current) abortRef.current.abort();
    setWaitPhrases(false);
    setStatus({ text: "Останавливаю моделирование…", kind: "warn" });
    try {
      await postJson("/api/model/stop", {});
    } catch {
      /* кнопка всё равно глушит UI */
    }
  }

  async function onUploadQuestionnaire(file) {
    if (!current) return;
    setUploading(true);
    setStatus({ text: "Загружаю анкету…", kind: "" });
    try {
      const body = new FormData();
      body.append("row", String(current.row));
      body.append("file", file);
      const pack = await postForm("/api/questionnaire", body);
      applyPack(pack, current);
    } catch (err) {
      setStatus({ text: err.message, kind: "bad" });
    } finally {
      setUploading(false);
    }
  }

  async function onModel() {
    if (!current || !qOk) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setModeling(true);
    setWaitPhrases(true);
    try {
      const result = await postJson(
        "/api/model",
        { row: current.row, prompt: promptView },
        controller.signal
      );
      setWorkOpen(true);
      if (result.prompt) setPromptView(result.prompt);
      setModelView(JSON.stringify(result.payload, null, 2));
      setWorkOpenItems((items) => (items.includes("model") ? items : [...items, "model"]));
      setElapsed(formatElapsed(result.elapsed_sec));
      setTokens(formatTokens(result.usage));
      const modeled = respondentsFromPayload(result.payload);
      setCurrent((prev) =>
        prev
          ? {
              ...prev,
              result_url: result.spreadsheet_url || prev.result_url,
              respondents_contact: modeled ? prev.respondents_contact : prev.respondents_contact,
              respondents_noncontact: modeled ? prev.respondents_noncontact : prev.respondents_noncontact,
              _modeledRespondents: modeled || "",
            }
          : prev
      );
      if (result.gas_error) {
        setStatus({
          text: `Модель готова за ${formatElapsed(result.elapsed_sec)}, таблица: ${result.gas_error}`,
          kind: "bad",
        });
      } else {
        const done = pickPhrase(DONE_PHRASES);
        setStatus({
          text: done.text,
          kind: "ok",
          icon: done.icon,
        });
      }
    } catch (err) {
      if (err.name === "AbortError" || /остановлен/i.test(err.message || "")) {
        setStatus({ text: "Моделирование остановлено", kind: "warn" });
      } else {
        setStatus({ text: err.message, kind: "bad" });
      }
    } finally {
      abortRef.current = null;
      setWaitPhrases(false);
      setModeling(false);
    }
  }

  const respondents =
    (current && current._modeledRespondents) ||
    (current
      ? formatRespondents(current.respondents_contact, current.respondents_noncontact)
      : "");

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-header text-[#fafafa] border-b border-[rgba(240,74,94,0.35)]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-6 py-4">
          <div className="flex items-center gap-3.5">
            <img src="/logo.svg" alt="AstraLab" width="108" height="24" className="block h-6 w-auto" />
            <h1 className="group grid text-lg font-bold text-[#fafafa]">
              <span className="col-start-1 row-start-1 group-hover:invisible">BLS Creator</span>
              <span className="col-start-1 row-start-1 invisible group-hover:visible">БЛС генератор</span>
            </h1>
          </div>
          <button
            type="button"
            onClick={() => setSloganIndex((i) => (i + 1) % SLOGANS.length)}
            className="cursor-pointer rounded-full border border-primary px-3 py-1 text-[13px] leading-none text-[#fafafa]/80"
          >
            {SLOGANS[sloganIndex]}
          </button>
        </div>
      </header>
      {raccoonVisible ? <IdleRaccoon /> : null}

      <main className="mx-auto max-w-7xl px-6 pb-8">
        <Card>
          <CardTitle>Кампания</CardTitle>
          <Label htmlFor="campaign" className="flex items-center gap-1.5">
            <Megaphone className="size-3.5 shrink-0" />
            Название РК
          </Label>
          <Select value={row} onValueChange={onSelectCampaign}>
            <SelectTrigger id="campaign" className="w-full">
              <SelectValue placeholder={campaigns.length ? "Выбери РК" : "Загрузка списка…"} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>Выбери РК</SelectItem>
              {campaigns.map((item) => (
                <SelectItem key={item.row} value={String(item.row)}>
                  {optionLabel(item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="mt-3.5 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Дата заявки" icon={Calendar} value={current?.submitted_at} />
            <Field label="Тип исследования" icon={ClipboardList} value={current?.research_type} />
            <Field label="DL" icon={Timer} value={current?.dl} />
            <Field
              label="Количество респондентов"
              icon={UsersRound}
              value={current ? respondents : ""}
            />
            <QuestionnaireField
              name={qName}
              ok={qOk}
              collected={collected}
              uploading={uploading}
              onUpload={onUploadQuestionnaire}
              className="sm:col-span-2 lg:col-span-4"
            />
          </div>

          <Accordion type="multiple" className="mt-3 rounded-lg border border-border px-3">
            <AccordionItem value="links">
              <AccordionTrigger>
                <span className="flex items-center gap-1.5">
                  <Link className="size-3.5 shrink-0" />
                  Ссылки
                  <span className="font-normal text-muted-foreground">
                    {linkCount ? `${linkCount} из 3` : "нет"}
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <div className="grid grid-cols-1 gap-x-4 gap-y-3 lg:grid-cols-3">
                  <Field label="Ссылка в CRM" icon={Link} value={crmUrl} isLink />
                  <Field label="Ссылка на сделку в Notion" icon={NotebookText} value={notionUrl} isLink />
                  <Field label="Ссылка на Buying Table" icon={Table2} value={current?.bt_url} isLink />
                </div>
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="closing">
              <AccordionTrigger>
                <span className="flex items-center gap-1.5">
                  <ChartColumn className="size-3.5 shrink-0" />
                  Закрытие
                  <span className="font-normal text-muted-foreground">
                    {closingFilled ? `${closingFilled} полей` : "нет"}
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <ClosingBlock rows={current?.closing} />
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="targeting">
              <AccordionTrigger>
                <span className="flex items-center gap-1.5">
                  <Users className="size-3.5 shrink-0" />
                  ЦА + таргетинг
                  <span className="font-normal text-muted-foreground">
                    {current?.targeting ? "есть" : "нет"}
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <Field value={current?.targeting} wrap />
              </AccordionContent>
            </AccordionItem>
          </Accordion>

          <div className="mt-4 flex flex-wrap gap-2.5">
            <Button type="button" variant="collect" disabled={!current || collecting || modeling} onClick={onCollect}>
              <Database />
              Собрать данные исследования
            </Button>
            <Button
              type="button"
              variant={qOk ? "success" : "secondary"}
              disabled={!current || !qOk || collecting || modeling || uploading}
              onClick={onModel}
            >
              <Sparkles />
              Смоделировать исследование
            </Button>
            <Button type="button" variant="stop" disabled={!modeling} onClick={onStop}>
              <CircleStop />
              Стоп
            </Button>
          </div>
          {status.text ? (
            <div
              className={cn(
                "mt-3 rounded-lg border px-3.5 py-3 text-base font-semibold leading-snug",
                status.kind === "ok" && "border-ok bg-ok-bg text-ok",
                status.kind === "bad" && "border-bad bg-bad-bg text-bad",
                status.kind === "warn" && "border-warn bg-[#fff6e8] text-warn",
                !status.kind && "border-border bg-muted text-foreground"
              )}
            >
              <span
                key={status.text}
                className="inline-flex items-center gap-2 animate-in fade-in duration-300"
              >
                {status.icon ? <status.icon className="size-5 shrink-0" /> : null}
                {status.text}
              </span>
            </div>
          ) : null}

          <div className="mt-3.5 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Время генерации" icon={Hourglass} value={elapsed} />
            <Field label="Токены" icon={Coins} value={tokens} />
            <Field
              label="Результаты исследования"
              icon={FileSpreadsheet}
              value={current?.result_url}
              isLink
              className="sm:col-span-2"
            />
          </div>
        </Card>

        {workOpen ? (
          <Card>
            <Accordion
              type="multiple"
              value={workOpenItems}
              onValueChange={setWorkOpenItems}
              className="rounded-lg border border-border px-3"
            >
              <AccordionItem value="collect">
                <AccordionTrigger>
                  <span className="flex items-center gap-1.5">
                    <Database className="size-3.5 shrink-0" />
                    Собранные данные
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  <SourceBadges items={badges} />
                  <pre className="m-0 min-h-[16rem] max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-ink bg-ink p-3 font-mono text-xs leading-snug text-[#fafafa]">
                    {collectView}
                  </pre>
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="prompt">
                <AccordionTrigger>
                  <span className="flex items-center gap-1.5">
                    <FileText className="size-3.5 shrink-0" />
                    Промпт
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  <textarea
                    value={promptView}
                    onChange={(event) => setPromptView(event.target.value)}
                    disabled={modeling}
                    spellCheck={false}
                    className="m-0 min-h-[16rem] w-full resize-y overflow-auto whitespace-pre-wrap break-words rounded-lg border border-ink bg-ink p-3 font-mono text-xs leading-snug text-[#fafafa] outline-none focus:ring-2 focus:ring-ring disabled:opacity-70"
                  />
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="model">
                <AccordionTrigger>
                  <span className="flex items-center gap-1.5">
                    <Braces className="size-3.5 shrink-0" />
                    Данные модели
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  <pre className="m-0 min-h-[16rem] max-h-[32rem] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-ink bg-ink p-3 font-mono text-xs leading-snug text-[#fafafa]">
                    {modelView}
                  </pre>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </Card>
        ) : null}
      </main>
    </div>
  );
}
