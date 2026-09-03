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

function renderFields(item) {
  fillReadonly($("f-date"), item && item.submitted_at);
  fillReadonly($("f-type"), item && item.research_type);
  fillReadonly($("f-dl"), item && item.dl);
  fillReadonly($("f-crm"), item && item.crm_url, true);
  fillReadonly($("f-elapsed"), "");
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
  $("collect-card").hidden = true;
  $("model-card").hidden = true;
  renderFields(current);
  setStatus(current ? "Можно собирать данные" : "");
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

function collectPreview(pack) {
  const q = pack.questionnaire || {};
  const crm = pack.crm || {};
  return {
    campaign: pack.campaign.name,
    advertised_brand: pack.advertised_brand,
    geo: pack.geo,
    targeting: pack.targeting,
    questionnaire_ok: q.ok,
    questionnaire_error: q.error || "",
    questionnaire_name: q.name || "",
    questionnaire_text: q.text || "",
    crm_ok: crm.ok,
    crm_error: crm.error || "",
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
    $("collect-card").hidden = false;
    const qOk = pack.questionnaire && pack.questionnaire.ok;
    const crmOk = pack.crm && pack.crm.ok;
    $("collect-meta").innerHTML =
      `<span class="tag">${qOk ? "анкета ок" : "анкета ошибка"}</span>` +
      `<span class="tag">${crmOk ? "CRM ок" : "CRM ошибка"}</span>` +
      `<span>бренд: ${pack.advertised_brand || "—"}</span>`;
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
    $("model-card").hidden = false;
    $("model-view").textContent = JSON.stringify(result.payload, null, 2);
    fillReadonly($("f-elapsed"), formatElapsed(result.elapsed_sec));
    fillReadonly($("f-result"), result.spreadsheet_url, true);
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

loadCampaigns().catch((err) => {
  select.innerHTML = '<option value="">Список недоступен</option>';
  setStatus(err.message, "bad");
});
