export async function getJson(url) {
  const resp = await fetch(url);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || "Не удалось загрузить данные");
  return data;
}

function errorDetail(data, fallback) {
  const detail = data && data.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail) && detail[0] && detail[0].msg) return detail[0].msg;
  return fallback;
}

export async function postJson(url, body, signal) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(errorDetail(data, resp.statusText));
  return data;
}

export async function postForm(url, formData) {
  const resp = await fetch(url, { method: "POST", body: formData });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(errorDetail(data, resp.statusText));
  return data;
}
