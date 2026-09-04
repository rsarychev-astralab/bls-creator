export function formatElapsed(sec) {
  if (sec == null || sec === "") return "";
  const n = Number(sec);
  if (!Number.isFinite(n)) return String(sec);
  const m = Math.floor(n / 60);
  const s = Math.round(n % 60);
  if (m <= 0) return `${s} сек`;
  return `${m} мин ${s} сек`;
}

export function formatCount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("ru-RU");
}

export function formatTokens(usage) {
  if (!usage || usage.total_tokens == null) return "";
  const total = formatCount(usage.total_tokens);
  const parts = [];
  if (usage.prompt_tokens != null) parts.push(`вход ${formatCount(usage.prompt_tokens)}`);
  if (usage.completion_tokens != null) parts.push(`выход ${formatCount(usage.completion_tokens)}`);
  if (usage.reasoning_tokens != null) parts.push(`мысли ${formatCount(usage.reasoning_tokens)}`);
  return parts.length ? `${total} (${parts.join(", ")})` : total;
}

export function formatRespondents(contact, noncontact) {
  const c = Number(contact);
  const n = Number(noncontact);
  const left = Number.isFinite(c) ? c : 400;
  const right = Number.isFinite(n) ? n : 400;
  return `${left} контакт / ${right} неконтакт`;
}

export function respondentsFromPayload(payload) {
  const first = Array.isArray(payload) ? payload[0] : payload;
  if (!first || typeof first !== "object") return "";
  const block = Object.values(first)[0] || {};
  const meta = block.metadata || {};
  if (meta.total_contact_group == null && meta.total_noncontact_group == null) {
    return "";
  }
  return formatRespondents(meta.total_contact_group, meta.total_noncontact_group);
}

export function isNotionUrl(url) {
  return /notion\.(so|com|site)/i.test(url || "");
}

export function isCrmUrl(url) {
  return /crm\.al-ad\.tech/i.test(url || "");
}

export function optionLabel(item) {
  const typ = item.research_type ? ` [${item.research_type}]` : "";
  return `${item.name}${typ}`;
}

export function sourceLabel(value) {
  if (value === "crm") return "CRM";
  if (value === "notion") return "Notion";
  if (value === "drive") return "Drive";
  if (value === "name") return "название РК";
  if (value === "crm+notion") return "CRM + Notion";
  if (value === "upload") return "загрузка";
  return value || "нет";
}

export function collectPreview(pack) {
  const q = pack.questionnaire || {};
  const crm = pack.crm || {};
  return {
    campaign: pack.campaign.name,
    advertised_brand: pack.advertised_brand,
    geo: pack.geo,
    targeting: pack.targeting,
    sources: pack.sources || {},
    questionnaire_ok: q.ok,
    questionnaire_source: q.source || "",
    questionnaire_error: q.error || "",
    questionnaire_name: q.name || "",
    questionnaire_text: q.text || "",
    crm_ok: crm.ok,
    crm_source: crm.source || "",
    crm_deal_id: crm.deal_id || "",
    crm_deal_url: pack.crm_deal_url || crm.url || "",
    notion_url: pack.notion_url || "",
    bt_url: pack.bt_url || "",
    closing: pack.closing || [],
    crm_error: crm.error || crm.crm_error || "",
    crm_properties: crm.properties || {},
    comment: pack.campaign.comment,
  };
}

export function dealLinks(item) {
  if (!item) return { notionUrl: "", crmUrl: "" };
  const notionUrl = item.notion_url || (isNotionUrl(item.crm_url) ? item.crm_url : "") || "";
  const crmUrl = item.crm_deal_url || (isCrmUrl(item.crm_url) ? item.crm_url : "") || "";
  return { notionUrl, crmUrl };
}

export const CLOSING_FIELDS = [
  { key: "volumeActual", label: "Объем факт" },
  { key: "ctrActual", label: "CTR факт" },
  { key: "vtrActual", label: "VTR факт" },
  { key: "passingIndexActual", label: "Passing Index факт" },
  { key: "brandRateActual", label: "BR факт" },
  { key: "timeActual", label: "Время факт" },
  { key: "depthActual", label: "Глубина факт" },
  { key: "conversionsActual", label: "Количество конверсий факт" },
  { key: "feedback", label: "FeedBack", wide: true },
];
