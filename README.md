# ipas — NotebookLM 資料擷取工具

從 Google **NotebookLM** 取出資料（筆記本、來源、筆記、摘要），存成本地 JSON。

## 為什麼用瀏覽器自動化？

NotebookLM **沒有官方公開 API** 可以程式化讀取筆記本內容。因此本工具用
[Playwright](https://playwright.dev/python/) 驅動一個「已登入」的 Chromium，
像使用者一樣瀏覽頁面並把內容抓下來。

> 若你是 **NotebookLM Enterprise**（透過 Google Agentspace / Vertex AI）使用者，
> 可改走官方 API，穩定度遠高於瀏覽器自動化。見文末〈企業版替代方案〉。

## 安裝

```bash
pip install -r requirements.txt
# 本 repo 執行環境已內建 Chromium；一般機器需額外執行：
python -m playwright install chromium
```

若使用系統既有的 Chromium，可用環境變數指定執行檔：

```bash
export NBLM_CHROMIUM_PATH=/opt/pw-browsers/chromium/chrome-linux/chrome
```

## 使用流程

```bash
# 1. 一次性登入。會用你電腦上「真正的 Edge」開啟一個視窗。
#    在那個視窗完成 Google 登入 + 2FA，看到筆記本後回終端機按 ENTER。
#    登入狀態存進持久化 profile（.nblm_profile/），之後不用再登入。
python main.py login

# 2. 列出你帳號裡的筆記本，取得 notebook id
python main.py list

# 3. 擷取單一筆記本 -> data/<title>__<id>.json
python main.py extract <notebook_id>

# 4. 或一次擷取全部
python main.py extract-all
```

### 為什麼用真正的 Edge/Chrome，而不是內建 Chromium？

Google 會偵測「被自動化控制的瀏覽器」，在內建 Chromium 上登入常被擋，顯示
**「這個瀏覽器或應用程式可能不安全」**。因此本工具預設改用你電腦上**真正安裝的
Microsoft Edge**（`channel=msedge`），並關閉 `navigator.webdriver` 自動化旗標，
Google 較不會攔阻。

- 想改用 Chrome：`set NBLM_BROWSER_CHANNEL=chrome`（PowerShell：`$env:NBLM_BROWSER_CHANNEL="chrome"`）
- 想用內建 Chromium：把 `NBLM_BROWSER_CHANNEL` 設為空字串。

### 登入務必「在跳出來的那個視窗」操作

`login` 會開一個由程式控制的視窗。**一定要在那個視窗裡登入**——如果你另外開自己的
Edge/Chrome 登入，程式這邊拿不到 session，會失敗。登入完看到筆記本後，回終端機按
**ENTER** 存檔即可。

登入是持久化的：狀態存在 `.nblm_profile/`，之後 `list` / `extract` 都能無頭
（headless）重複使用，不用再登入。

## 輸出格式

每個筆記本存成一個 JSON：

```json
{
  "id": "xxxxxxxx-xxxx-...",
  "title": "我的研究筆記本",
  "url": "https://notebooklm.google.com/notebook/...",
  "summary": "……NotebookLM 產生的總覽……",
  "sources": [{ "title": "報告.pdf", "kind": "unknown", "preview": "……" }],
  "notes": [{ "title": "重點整理", "content": "……" }],
  "extracted_at": "2026-07-01T00:00:00+00:00"
}
```

`data/notebooks_index.json` 則是所有筆記本的索引。

## 選擇器會失效——如何修

NotebookLM 是 Google 的 Angular SPA，**DOM 沒有穩定契約**，改版後
class/tag 名稱可能變動，導致擷取到空結果。修法：

```bash
# 印出實際渲染的頁面文字，用來重新對照選擇器
python main.py debug-dump <notebook_id>
```

然後更新 `src/notebooklm/extractor.py` 最上方的候選選擇器清單
（`_SOURCE_ITEM_SELECTORS`、`_NOTE_ITEM_SELECTORS` 等）。所有需要維護的
選擇器都集中在那裡。

## 設定（環境變數）

| 變數 | 預設 | 說明 |
|------|------|------|
| `NBLM_BROWSER_CHANNEL` | `msedge` | 要驅動的真實瀏覽器（`msedge`／`chrome`／空=內建 Chromium）|
| `NBLM_USER_DATA_DIR` | `./.nblm_profile` | 持久化登入 profile 資料夾 |
| `NBLM_DATA_DIR` | `./data` | 輸出資料夾 |
| `NBLM_HEADLESS` | `1` | 擷取是否無頭（`0` 顯示視窗）|
| `NBLM_CHROMIUM_PATH` | 無 | 指定 Chromium 執行檔（未用 channel 時）|
| `NBLM_BASE_URL` | `https://notebooklm.google.com` | NotebookLM 網址 |
| `NBLM_NAV_TIMEOUT_MS` | `60000` | 導覽逾時 |

## 專案結構

```
main.py                     # CLI 進入點
src/notebooklm/
  config.py                 # 設定與環境變數
  browser.py                # Playwright 瀏覽器生命週期
  auth.py                   # 互動登入、儲存 session
  extractor.py              # 核心擷取邏輯（選擇器集中處）
  models.py                 # Notebook / Source / Note 資料結構
  storage.py                # 輸出 JSON
data/                       # 擷取結果（已被 gitignore）
```

## 注意事項

- **`.nblm_profile/` 含你的 Google 登入 session，切勿 commit 或外流**（已列入 `.gitignore`）。
- 瀏覽器自動化屬灰色地帶，請遵守 Google 服務條款，僅擷取你有權存取的資料，
  並避免高頻率請求。
- 選擇器與流程會隨 NotebookLM 改版而需要維護。

## 企業版替代方案

若貴組織使用 **NotebookLM Enterprise**（Google Agentspace / Vertex AI），
可透過官方 API 以服務帳號存取，不需瀏覽器自動化、穩定度更高。屆時可另建一個
`enterprise_client.py`，改用 Google Cloud 憑證與 REST/gRPC 端點。若要走這條路，
告訴我你的 GCP 專案設定，我可以再補上對應實作。
```
