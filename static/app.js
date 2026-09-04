const $ = (id) => document.getElementById(id);

const select = $("campaign");
const btnCollect = $("btn-collect");
const btnModel = $("btn-model");
const btnStop = $("btn-stop");
const statusEl = $("status");

let campaigns = [];
let current = null;
let collected = false;
let modelAbort = null;

function setStatus(text, kind) {
  statusEl.textContent = text || "";
  statusEl.className = "status" + (kind ? " " + kind : "");
}

function fillReadonly(el, value, isLink) {
  el.classList.toggle("empty", !value);
  if (!value) {
    el.textContent = "—";
    return;
  }
  if (isLink) {
    el.innerHTML = "";
    const a = document.createElement("a");
    a.href = value;
    a.target = "_blank";
    a.rel = "noreferrer";
    a.textContent = value;
    el.appendChild(a);
    return;
  }
  el.textContent = value;
}

function formatElapsed(sec) {
  if (sec == null || sec === "") return "";
  const n = Number(sec);
  if (!Number.isFinite(n)) return String(sec);
  const m = Math.floor(n / 60);
  const s = Math.round(n % 60);
  if (m <= 0) return `${s} сек`;
  return `${m} мин ${s} сек`;
}

function formatCount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("ru-RU");
}

function formatTokens(usage) {
  if (!usage || usage.total_tokens == null) return "";
  const total = formatCount(usage.total_tokens);
  const parts = [];
  if (usage.prompt_tokens != null) parts.push(`вход ${formatCount(usage.prompt_tokens)}`);
  if (usage.completion_tokens != null) parts.push(`выход ${formatCount(usage.completion_tokens)}`);
  if (usage.reasoning_tokens != null) parts.push(`мысли ${formatCount(usage.reasoning_tokens)}`);
  return parts.length ? `${total} (${parts.join(", ")})` : total;
}

function formatRespondents(contact, noncontact) {
  const c = Number(contact);
  const n = Number(noncontact);
  const left = Number.isFinite(c) ? c : 400;
  const right = Number.isFinite(n) ? n : 400;
  return `${left} контакт / ${right} неконтакт`;
}

function respondentsFromPayload(payload) {
  const first = Array.isArray(payload) ? payload[0] : payload;
  if (!first || typeof first !== "object") return "";
  const block = Object.values(first)[0] || {};
  const meta = block.metadata || {};
  if (meta.total_contact_group == null && meta.total_noncontact_group == null) {
    return "";
  }
  return formatRespondents(meta.total_contact_group, meta.total_noncontact_group);
}

function isNotionUrl(url) {
  return /notion\.(so|com|site)/i.test(url || "");
}

function isCrmUrl(url) {
  return /crm\.al-ad\.tech/i.test(url || "");
}

const CLOSING_FIELDS = [
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

function renderClosing(rows) {
  const grid = $("closing-grid");
  if (!grid) return;
  const byKey = {};
  for (const row of rows || []) {
    if (row && row.key) byKey[row.key] = row.value || "";
  }
  grid.innerHTML = "";
  for (const spec of CLOSING_FIELDS) {
    const wrap = document.createElement("div");
    if (spec.wide) wrap.className = "span-2";
    const label = document.createElement("label");
    label.textContent = spec.label;
    const box = document.createElement("div");
    box.id = "f-closing-" + spec.key;
    box.className = spec.wide ? "readonly readonly-wrap" : "readonly";
    fillReadonly(box, byKey[spec.key] || "", false);
    wrap.appendChild(label);
    wrap.appendChild(box);
    grid.appendChild(wrap);
  }
}

function renderFields(item) {
  const notionUrl = (item && (item.notion_url || (isNotionUrl(item.crm_url) ? item.crm_url : ""))) || "";
  const crmUrl = (item && (item.crm_deal_url || (isCrmUrl(item.crm_url) ? item.crm_url : ""))) || "";
  fillReadonly($("f-date"), item && item.submitted_at);
  fillReadonly($("f-type"), item && item.research_type);
  fillReadonly($("f-dl"), item && item.dl);
  fillReadonly($("f-crm"), crmUrl, true);
  fillReadonly($("f-notion"), notionUrl, true);
  fillReadonly($("f-bt"), item && item.bt_url, true);
  renderClosing(item && item.closing);
  fillReadonly($("f-targeting"), item && item.targeting);
  fillReadonly($("f-respondents"), item ? formatRespondents(item.respondents_contact, item.respondents_noncontact) : "");
  fillReadonly($("f-elapsed"), "");
  fillReadonly($("f-tokens"), "");
  fillReadonly($("f-result"), item && item.result_url, true);
}

function optionLabel(item) {
  const typ = item.research_type ? ` [${item.research_type}]` : "";
  return `${item.name}${typ}`;
}

async function loadCampaigns() {
  const resp = await fetch("/api/campaigns");
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || "Не удалось загрузить список РК");
  campaigns = data.items || [];
  select.innerHTML = '<option value="">Выбери РК</option>';
  for (const item of campaigns) {
    const opt = document.createElement("option");
    opt.value = String(item.row);
    opt.textContent = optionLabel(item);
    select.appendChild(opt);
  }
  setStatus(`В списке ${campaigns.length} кампаний`);
}

select.addEventListener("change", () => {
  const row = Number(select.value);
  current = campaigns.find((x) => x.row === row) || null;
  collected = false;
  if (modelAbort) modelAbort.abort();
  btnCollect.disabled = !current;
  btnModel.disabled = true;
  btnStop.disabled = true;
  $("work-card").hidden = true;
  $("collect-view").textContent = "";
  $("prompt-view").textContent = "";
  $("model-view").textContent = "";
  activateTab("collect");
  renderFields(current);
  setStatus(current ? "Можно собирать данные" : "");
});

function activateTab(name) {
  for (const btn of document.querySelectorAll(".tab")) {
    btn.classList.toggle("is-active", btn.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll(".tab-panel")) {
    panel.hidden = panel.dataset.panel !== name;
  }
}

document.querySelector(".tabs")?.addEventListener("click", (event) => {
  const btn = event.target.closest(".tab");
  if (!btn) return;
  activateTab(btn.dataset.tab);
});

async function postJson(url, body, signal) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || resp.statusText);
  return data;
}

function sourceLabel(value) {
  if (value === "crm") return "CRM";
  if (value === "notion") return "Notion";
  if (value === "drive") return "Drive";
  if (value === "name") return "название РК";
  if (value === "crm+notion") return "CRM + Notion";
  return value || "нет";
}

function sourceTag(label, source, ok) {
  const state = ok ? "ок" : "ошибка";
  const cls = ok ? "ok" : "bad";
  return `<span class="tag ${cls}">${label} - ${sourceLabel(source)} - ${state}</span>`;
}

function collectPreview(pack) {
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

btnCollect.addEventListener("click", async () => {
  if (!current) return;
  btnCollect.disabled = true;
  btnModel.disabled = true;
  setStatus("Собираю анкету и CRM…");
  try {
    const pack = await postJson("/api/collect", { row: current.row });
    collected = true;
    current.targeting = pack.targeting || "";
    current.respondents_contact = pack.respondents_contact;
    current.respondents_noncontact = pack.respondents_noncontact;
    current.crm_deal_url = pack.crm_deal_url || "";
    current.notion_url = pack.notion_url || current.crm_url || "";
    current.bt_url = pack.bt_url || "";
    current.closing = pack.closing || [];
    fillReadonly($("f-crm"), current.crm_deal_url, true);
    fillReadonly($("f-notion"), current.notion_url, true);
    fillReadonly($("f-bt"), current.bt_url, true);
    renderClosing(current.closing);
    fillReadonly($("f-targeting"), current.targeting);
    fillReadonly($("f-respondents"), formatRespondents(current.respondents_contact, current.respondents_noncontact));
    $("work-card").hidden = false;
    activateTab("collect");
    $("prompt-view").textContent = pack.prompt || "Промпт ещё не собран";
    $("model-view").textContent = "Сначала смоделируй исследование";
    const q = pack.questionnaire || {};
    const crm = pack.crm || {};
    const src = pack.sources || {};
    const qOk = Boolean(q.ok && q.text);
    const crmOk = Boolean(crm.ok);
    $("collect-meta").innerHTML =
      sourceTag("Карточка", crm.source || src.brand || "crm", crmOk) +
      sourceTag("Бренд", src.brand, Boolean(pack.advertised_brand)) +
      sourceTag("Гео", src.geo, Boolean(pack.geo)) +
      sourceTag("ЦА", src.targeting, Boolean(pack.targeting)) +
      sourceTag("Анкета", src.questionnaire || q.source, qOk) +
      sourceTag("БТ", src.bt, Boolean(pack.bt_url)) +
      sourceTag("Закрытие", src.closing, Boolean(src.closing));
    $("collect-view").textContent = JSON.stringify(collectPreview(pack), null, 2);
    btnModel.disabled = !qOk;
    setStatus(
      qOk ? "Данные собраны. Можно моделировать." : pack.questionnaire.error,
      qOk ? "" : "bad"
    );
  } catch (err) {
    collected = false;
    setStatus(err.message, "bad");
  } finally {
    btnCollect.disabled = !current;
  }
});

btnStop.addEventListener("click", async () => {
  if (modelAbort) modelAbort.abort();
  btnStop.disabled = true;
  setStatus("Останавливаю моделирование…", "warn");
  try {
    await postJson("/api/model/stop", {});
  } catch (_) {
    /* кнопка всё равно глушит UI */
  }
});

btnModel.addEventListener("click", async () => {
  if (!current || !collected) return;
  modelAbort = new AbortController();
  btnModel.disabled = true;
  btnCollect.disabled = true;
  btnStop.disabled = false;
  setStatus("Моделирую в DeepSeek. Это может занять минуту…");
  try {
    const result = await postJson("/api/model", { row: current.row }, modelAbort.signal);
    $("work-card").hidden = false;
    if (result.prompt) $("prompt-view").textContent = result.prompt;
    $("model-view").textContent = JSON.stringify(result.payload, null, 2);
    activateTab("model");
    fillReadonly($("f-elapsed"), formatElapsed(result.elapsed_sec));
    fillReadonly($("f-tokens"), formatTokens(result.usage));
    fillReadonly($("f-result"), result.spreadsheet_url, true);
    const modeled = respondentsFromPayload(result.payload);
    if (modeled) fillReadonly($("f-respondents"), modeled);
    if (current && result.spreadsheet_url) current.result_url = result.spreadsheet_url;
    if (result.gas_error) {
      setStatus(`Модель готова за ${formatElapsed(result.elapsed_sec)}, таблица: ${result.gas_error}`, "bad");
    } else {
      const gasName = result.spreadsheet_name ? ` ${result.spreadsheet_name}` : "";
      setStatus(`Готово за ${formatElapsed(result.elapsed_sec)}. Таблица:${gasName}`);
    }
  } catch (err) {
    if (err.name === "AbortError" || /остановлен/i.test(err.message || "")) {
      setStatus("Моделирование остановлено", "warn");
    } else {
      setStatus(err.message, "bad");
    }
  } finally {
    modelAbort = null;
    btnStop.disabled = true;
    btnCollect.disabled = !current;
    btnModel.disabled = !collected;
  }
});

renderClosing([]);
loadCampaigns().catch((err) => {
  select.innerHTML = '<option value="">Список недоступен</option>';
  setStatus(err.message, "bad");
});
