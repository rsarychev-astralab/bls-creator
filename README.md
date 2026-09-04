# BLS Creator

Внутренний тул AstraLab: одна кампания за запуск. Собирает карточку и анкету, гоняет DeepSeek, пишет таблицу результата в Google Drive.

Репозиторий: https://github.com/rsarychev-astralab/bls-creator

## Как устроено

1. Список РК из Google Sheet заявок.
2. Сбор: CRM (`crm.al-ad.tech`), пустые поля и анкета добираются из Notion, потом Drive, потом ручная загрузка в UI.
3. Промпт можно поправить в аккордеоне.
4. Модель возвращает JSON. Таблица: xlsx на диск и загрузка в папку Drive (`RESULT_FOLDER_ID`). GAS в горячем пути не участвует.

Пак сбора живёт **в памяти процесса**. Рестарт или второй воркер uvicorn: model скажет «Сначала собери данные». На сервере всегда `--workers 1`.

## Локально

Нужны Python 3.12, Node 20+, файл сервисного аккаунта Google.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# заполни .env и положи JSON ключа рядом с репо
```

Фронт в проде отдаёт FastAPI из `web/dist`:

```bash
cd web && npm install && npm run build && cd ..
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Разработка UI (прокси `/api` на :8000):

```bash
# терминал 1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# терминал 2
cd web && npm run dev
```

Открыть: http://127.0.0.1:8000/ или http://localhost:5173/

Проверка: `curl -s http://127.0.0.1:8000/health` → `{"ok":true}`

Тесты: `python3 -m pytest -q`

## Переменные

Файл `.env` в корне. Не коммитить. Пример: `.env.example`.

| Ключ | Зачем |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_FILE` | JSON ключа. Локально имя файла в корне репо |
| `SPREADSHEET_ID` | Таблица заявок BLS |
| `SHEET_NAME` | Лист, по умолчанию `2026 год` |
| `RESULT_FOLDER_ID` | Папка на **Shared drive**, куда класть результат |
| `CRM_API_URL` | `https://crm.al-ad.tech/api` |
| `CRM_LOGIN` / `CRM_PASSWORD` | Сервисный вход в CRM, не Mattermost-only |
| `NOTION_TOKEN` | Запасной канал анкеты и полей |
| `DEEPSEEK_API_KEY` | Модель |
| `DEEPSEEK_MODEL` | По умолчанию `deepseek-v4-pro` |

Сервисный аккаунт Google: Sheets + Drive. Папка результата только Shared drive, иначе `storageQuotaExceeded`. Почта ключа (вид `...@....iam.gserviceaccount.com`) должна быть менеджером контента этой папки и иметь доступ к таблице заявок.

Не класть в git: `.env`, `crm-sable.md`, `*service-account*.json`, `bls-auto-*.json`.

## Деплой Docker

На сервере:

```bash
git clone https://github.com/rsarychev-astralab/bls-creator.git
cd bls-creator
cp .env.example .env
# заполни .env
# положи ключ: service-account.json в корень (или путь из GOOGLE_SERVICE_ACCOUNT_FILE)
mkdir -p data
docker compose up -d --build
curl -s http://127.0.0.1:8000/health
```

Compose читает `.env`, монтирует ключ read-only и `./data` под результаты. Порт снаружи: `PORT=8000` в `.env` или дефолт 8000.

Обновление:

```bash
git pull
docker compose up -d --build
```

Перед прокси (nginx/caddy) таймаут чтения не меньше 300с. Пример: [`deploy/nginx.conf.example`](deploy/nginx.conf.example).

## Деплой без Docker

```bash
sudo useradd -r -m -d /opt/bls-creator bls
sudo -u bls git clone https://github.com/rsarychev-astralab/bls-creator.git /opt/bls-creator
cd /opt/bls-creator
sudo -u bls python3 -m venv .venv
sudo -u bls .venv/bin/pip install -r requirements.txt
cd web && npm ci && npm run build && cd ..
# .env и service-account.json от пользователя bls, chmod 600
sudo cp deploy/bls-creator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bls-creator
curl -s http://127.0.0.1:8000/health
```

Юнит слушает `127.0.0.1:8000`. Наружу только через nginx.

## Ограничения

- Одна РК за раз, ручной запуск.
- Анкета в CRM часто пустая. Тогда Notion / Drive / загрузка в UI.
- Рекламодатель и рекламируемый бренд разные (пример: DNS платит, в анкете TCL).
- Если модель вернула пустой `[]` (тип не BLS или нет анкеты), это не успех исследования.
- `table_creator.gas` в репо для справки, сервер его не вызывает.
