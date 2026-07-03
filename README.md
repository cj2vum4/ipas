# iPAS NotebookLM + RAG

這個專案有兩個部分：

- 依 2026-10-30 考試日產生手機可讀的每日讀書進度表。
- 用 Playwright 從 Google NotebookLM 匯出筆記本 metadata、來源與筆記。
- 把本機 `iPAS教材/` 與 `data/*.json` 建成可部署到 GitHub Pages 的 RAG 檢索索引，並透過 Vercel API 安全呼叫 OpenRouter 免費模型產生答案。

## 安裝

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

PDF 解析會優先使用 `pypdf`。如果沒有安裝 PDF parser，`rag-build` 仍會處理 DOCX、XLSX、TXT、Markdown 與 NotebookLM JSON，並列出略過的 PDF。

## 讀書進度表

考試日：`2026-10-30`

讀書計畫從 `2026-07-03` 排到 `2026-10-29`，共 119 個讀書日。前端會先顯示今日任務、近期 7 天、各階段進度，並用瀏覽器 `localStorage` 保存手機上的完成狀態。

```bash
python scripts/build_study_plan.py
python scripts/build_study_materials.py
python scripts/build_curriculum.py
```

輸出：

- `docs/study_plan.json`
- `docs/study_materials.json`
- `docs/curriculum.json`，每日整理後教學資訊、難度分析與練習/測驗題
- `docs/material_assets/`，放無法抽文字的圖片與掃描 PDF 附件

階段安排：

| 日期 | 階段 |
| --- | --- |
| 2026-07-03 ~ 2026-07-16 | 基礎盤點與初級核心 |
| 2026-07-17 ~ 2026-08-06 | 初級科目一與科目二 |
| 2026-08-07 ~ 2026-08-30 | 中級 L21 人工智慧技術應用與規劃 |
| 2026-08-31 ~ 2026-09-22 | 中級 L22 大數據處理分析與應用 |
| 2026-09-23 ~ 2026-10-13 | 中級 L23 機器學習技術與應用 |
| 2026-10-14 ~ 2026-10-29 | 考前總複習與模擬考 |

## NotebookLM 匯出

NotebookLM 沒有公開匯出 API，所以這裡用已登入的瀏覽器 session 讀取頁面。

```bash
python main.py login
python main.py list
python main.py extract <notebook_id>
python main.py extract-all
python main.py debug-dump <notebook_id>
```

輸出會寫到 `data/`。`data/*.json` 已在 `.gitignore`，避免把個人筆記與來源內容誤 commit。

常用環境變數：

| 變數 | 預設 | 說明 |
| --- | --- | --- |
| `NBLM_BROWSER_CHANNEL` | `msedge` | 使用 Edge；也可設為 `chrome` 或空字串 |
| `NBLM_USER_DATA_DIR` | `.nblm_profile` | 保存 Google login session |
| `NBLM_DATA_DIR` | `data` | NotebookLM JSON 輸出資料夾 |
| `NBLM_HEADLESS` | `1` | 設為 `0` 可顯示瀏覽器 |

## 建立 RAG 索引

```bash
python main.py rag-build
```

預設會掃描：

- `iPAS教材/`
- `data/`

並輸出：

- `docs/rag_index.json`

可調整 chunk：

```bash
python main.py rag-build --chunk-size 1400 --chunk-overlap 180
python main.py rag-build iPAS教材/中級 -o docs/rag_index.json
python main.py rag-build --max-chunks 200
```

索引格式是 `ipas-rag-index-v1`，使用 dependency-free 的 sparse hash embedding，前端可直接在瀏覽器做 cosine similarity 檢索。這不是 transformer 等級語意模型，但好處是可離線、可重現、部署簡單。

注意：`docs/rag_index.json` 會包含教材文字片段。若 GitHub repo 或 Pages 是公開的，請先確認內容可以公開。

## GitHub Pages 前端

前端在 `docs/`：

- `docs/index.html`
- `docs/styles.css`
- `docs/app.js`
- `docs/study_plan.json`，由 `scripts/build_study_plan.py` 產生
- `docs/rag_index.json`，由 `rag-build` 產生

GitHub Pages 設定可選：

- Source: `Deploy from a branch`
- Branch: `main`
- Folder: `/docs`

頁面預設顯示 `curriculum.json` 的每日整合課程：難度、教學資訊、重點觀念、考點提醒，以及當日練習或測驗題。`教材庫` 分頁會載入 `study_materials.json`，可在手機上搜尋、分類、閱讀抽出的教材文字；圖片與純掃描 PDF 會標記為需要 OCR/手動整理，並提供原始附件連結。切到 `RAG 問答` 分頁後才會載入 RAG index；在 `Search` 模式只顯示來源片段，在 `Answer` 模式會把 top-k context 送到 API endpoint。

## Vercel OpenRouter API

Serverless function 在：

- `api/ask.js`

Vercel 環境變數：

Vercel Application Preset 可選 `Other` 或 `Node.js`，Root Directory 保持 `./`。不要新增 `DEFAULT_MODEL`；模型請填在 `OPENROUTER_MODEL`。

本專案已在 `vercel.json` 指定 `framework: null`、`buildCommand: null`、`outputDirectory: docs`，所以不需要 `package.json`、`index.js` 或 `server.js`。如果 Vercel 顯示 `No entrypoint found`，請確認重新部署的是最新 commit，並且專案的 Root Directory 是 `./`。

| 變數 | 必填 | 說明 |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | yes | OpenRouter API key，只放在 Vercel |
| `OPENROUTER_MODEL` | no | 預設 `openrouter/free`；也可改成 OpenRouter 模型頁列出的 `:free` 模型 |
| `OPENROUTER_MAX_TOKENS` | no | 預設 `1000` |
| `OPENROUTER_SITE_URL` | no | 建議填 `https://cj2vum4.github.io/ipas/docs/` |
| `OPENROUTER_APP_TITLE` | no | 建議填 `iPAS Study Planner` |
| `ALLOWED_ORIGINS` | no | 建議填 `https://cj2vum4.github.io` |

部署後，在前端的 `API endpoint` 填入：

```text
https://<your-vercel-app>.vercel.app/api/ask
```

如果前端也由 Vercel 提供，endpoint 可留空，預設會呼叫 `/api/ask`。

## 測試

```bash
python tests/test_extraction.py
python tests/test_rag.py
python scripts/build_study_plan.py
python scripts/build_study_materials.py
python scripts/build_curriculum.py
```

`tests/test_extraction.py` 需要 Playwright browser；`tests/test_rag.py` 不需要外部服務。

## 專案結構

```text
main.py
src/
  notebooklm/       # NotebookLM browser extraction
  rag/              # local document loading, chunking, sparse index build
docs/               # GitHub Pages RAG app
api/                # Vercel serverless function
iPAS教材/           # local study material
data/               # NotebookLM exports
tests/
```
