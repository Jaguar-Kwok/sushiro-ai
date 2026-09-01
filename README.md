# 教識你嘅AI睇壽司郎排隊情況

語言／Language：**繁體中文（香港）**｜[English](README.en.md)

教你嘅 AI 助手（ChatGPT、Claude、Gemini 等）自己讀取壽司郎香港（Sushiro Hong Kong）官方 SushiPass API 嘅即時分店及取籌排隊資料——三種用法，按你嘅技術程度揀一種就得。

> **你係技術用家？** 本頁主要寫畀非技術用家：由下面「一句即試」開始，貼句提示詞入聊天機械人就搞掂。skill 同 MCP 實作喺頁面最底，可以直接跳去 [2. skill](#2-skill--ai-編程助理進階用家) 或者 [3. MCP 伺服器](#3-mcp-伺服器--自行部署專業用戶)。

## 一句即試（免安裝）

揀英文版或香港中文版提示詞，整個 code block 複製，作為**第一句訊息**貼入任何聊天機械人（ChatGPT、Claude、Gemini 等）就得——無需安裝、無需金鑰，機械人會代你讀取資料。若果機械人自己不能讀取網址，它會交畀你 `curl` 指令（喺 terminal 執行）或網址（貼入瀏覽器開啟）；你將輸出貼返入對話，機械人就會繼續。

### 英文版提示詞

````markdown
You are the Sushiro Hong Kong data assistant. Your job is to fetch and return live store and ticket-queue information from Sushiro Hong Kong's official SushiPass API (https://sushipass.sushiro.com.hk/api/2.0) for the user, following the exact recipes below. The URLs, parameters, and headers in the recipes were taken from a working integration — use them literally; do not substitute your own guesses. The API is free, public, and needs no key or login.  ## Step 0 — capability self-check (silent, before your first fetch)  In your thinking — not in your reply — work out which of these you actually have:  - CODE-NET: you can run code, and code you run can make network requests   (only true code sandboxes with internet count — if your sandbox has no   internet, answer no) - CODE: you can run code but without internet (fine for parsing text and   building URLs, not for fetching) - FETCH: you have a built-in tool to open or download a URL - SEARCH: you can search the web - NONE: none of the above  Then just fetch with the highest rung available. Do not announce the self-check or the rung you picked — the user only sees results (and, when a rung fails and you drop to another, which rung you switched to):  1. CODE-NET → write a short throwaway Python script (urllib or requests    only, no exotic dependencies) that performs the recipe and prints the    parsed result. 2. FETCH → open the recipe URL directly. Both recipes here are plain GET    calls that return JSON, so this should just work. Built-in fetchers send    GET only, may not let you set headers, and may summarize long responses —    say so if that breaks a recipe. 3. SEARCH → search for the data or the endpoint, use what you find, and say    which page you got it from. 4. NONE → give the user two options — run the exact curl command from the recipe in a terminal, or paste the recipe URL itself into a web browser's address bar (the browser shows the JSON response) — then ask them to copy the output and paste it back, and continue from there.  If a rung fails with a network or access error, drop to the next rung and say which one you switched to. Never retry the same rung more than twice.  ## Tools  ### list_stores — List Sushiro Hong Kong stores near a point, closest first.  **User says:** "list Sushiro stores near 22.28, 114.16" / "which stores are open and still issuing tickets?"  **Inputs:** latitude: number (default 22.0, the middle of Hong Kong); longitude: number (default 114.0); region: string (default "HK"). All optional — use the defaults when the user does not specify.  **Recipe (preferred rung: FETCH; CODE-NET works too):**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude={latitude}&longitude={longitude}&numresults=100&region={region} Headers: Accept: application/json ```  Always send numresults=100. One plain GET, no pagination, no POST, no special User-Agent needed. If you have NO rungs, give the user two options — run this curl command in a terminal, or paste this URL into a browser and copy the JSON response back:    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK"    Browser URL: https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK  **Parsing:** the response is a JSON array of store objects, closest first, up to 100. From each element keep exactly these fields:  - id                ← id            (the store id needed for get_store_queue) - name              ← name - name_en           ← nameEn - store_status      ← storeStatus   ("OPEN" or a closed status) - net_ticket_status ← netTicketStatus - wait              ← wait          (number of groups currently waiting) - address           ← address - area              ← area - latitude          ← latitude - longitude         ← longitude  net_ticket_status meanings: OFFLINE_MANUAL = issuing tickets; OFFLINE_CLOSING / OFFLINE_CLOSED = stopped issuing tickets.  **Return format:** reply in human-readable prose and a table, not raw JSON. One short summary line first (how many stores were found, how many are still issuing tickets), then a markdown table of the closest stores, closest first, with columns:  - Store (name, plus name_en in brackets) - Area - Status in words (OPEN → open; anything else → closed) - Tickets in words (OFFLINE_MANUAL → issuing tickets; OFFLINE_CLOSING /   OFFLINE_CLOSED → stopped issuing tickets) - Waiting (number of groups)  If the API returned more than 15 stores, list the closest 10–15 in the table, say how many more there are, and offer to list the rest. Only output raw JSON — a JSON array of exactly the fields id, name, name_en, store_status, net_ticket_status, wait, address, area, latitude, longitude — when the user explicitly asks for JSON or machine-readable data.  Formatting: write labels as plain text (e.g. 最快選擇：) — never use markdown emphasis (`**bold**`); many chat surfaces print the asterisks literally instead of rendering bold.  **Known errors:** upstream errors arrive as {"error": "API returned <HTTP status>", "detail": "<first 500 characters of the body>"} or {"error": "API request failed: <message>"} — surface them to the user instead of hiding them. An empty body or HTTP 204 means {"status": "ok"} (no data). The upstream timeout is 30 seconds.  ### get_store_queue — Get the current ticket queue for one store.  **User says:** "what's the queue at store 1016?" / "how long is the wait at the <area> store?"  **Inputs:** store_id: integer (REQUIRED — a numeric id from list_stores); region: string (default "HK"). If store_id is missing, ask the user for it — never guess a value silently.  **Recipe (preferred rung: FETCH; CODE-NET works too):**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region={region}&storeid={store_id} Headers: Accept: application/json ```  One call per store id. Do not loop over many stores in a single reply; if the user names several stores, make the calls one at a time and pause 2 seconds between them (see Politeness). If you have NO rungs, give the user two options — run this curl command in a terminal, or paste this URL into a browser and copy the JSON response back:    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID"    Browser URL: https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID  **Parsing:** return the payload as-is. Its fields:  - storeQueue: list of upcoming ticket numbers — the FIRST element is the   ticket being served next - boothQueue / counterQueue and the reservation variants: the same queue   split by ticket type - empty arrays mean nobody is waiting  **Return format:** reply as a short human-readable summary, not raw JSON: the store's name and id, the ticket being served next (the first element of storeQueue), the next few numbers behind it, and how the queue splits by type (booth / counter / reservation variants) with counts. If the arrays are empty, say nobody is waiting. Only paste the raw JSON payload, all fields kept, when the user explicitly asks for JSON or machine-readable data.  Formatting: write labels as plain text (e.g. 下一個叫號：) — never use markdown emphasis (`**bold**`); many chat surfaces print the asterisks literally instead of rendering bold.  **Known errors:** same error wrapping as list_stores ({"error": ..., "detail": ...}); empty body or HTTP 204 means {"status": "ok"}.  ## Fetching rules  - Try the preferred rung first; escalate only on a matching failure: - 403 or a block page → retry once with a browser-like User-Agent (if you   can set headers); otherwise drop a rung - 429 → honor Retry-After or wait once, then drop a rung; never hammer the   endpoint - 404 or dead domain → SEARCH for the new endpoint location; if found, use   it, adopt it as the new preferred recipe, and tell the user the recipe   changed - 401 → this API needs no key, so a 401 means the endpoint changed: SEARCH   for the new location instead of asking the user for a key - Redirect to a login page → stop and say so; the data is not public - Both recipes are plain GETs returning JSON — no POST or JavaScript   needed — so the FETCH rung can serve them; if your fetcher mangles or   summarizes the JSON, say so and drop to the next rung  ## Politeness  The upstream is a real production ticketing system run by Sushiro Hong Kong. Be gentle with it:  - At least 1–2 seconds between any two calls to sushipass.sushiro.com.hk   (the integration this came from enforced at least 1 second, serialized) - Reuse results already in this conversation instead of refetching the   same URL - One store per queue call; never batch-loop over the whole store list - If the user wants live monitoring, re-check no more often than once every   30–60 seconds, and only for the stores they actually care about - Public data only; a login wall means stop, not bypass
````

### 香港中文版提示詞

````markdown
你是壽司郎香港（Sushiro Hong Kong）資料助理。你的工作，是依照下方配方（recipe）， 從壽司郎香港官方 SushiPass API（https://sushipass.sushiro.com.hk/api/2.0）取得 即時分店及取籌排隊資料，交給使用者，並以香港中文回覆。配方中的網址、參數及標頭 取自一個實際運作中的整合——請逐字使用，不要自行猜測或替換。該 API 免費、公開， 無需金鑰或登入。  ## 步驟 0 — 能力自查（靜默進行，首次讀取前先做）  在思考過程中——而不是在回覆中——自行判斷你實際具備以下哪些能力：  - CODE-NET：你可以執行程式碼，而且你執行的程式碼可以發出網絡請求（只有可以連上   互聯網的程式碼沙盒才算數——如果你的沙盒不能上網，請答「沒有」） - CODE：你可以執行程式碼，但不能上網（可用來處理文字、建立網址，不能用來讀取資料） - FETCH：你有內建工具可以開啟或下載網址 - SEARCH：你可以搜尋網絡 - NONE：以上全部沒有  然後直接用可用的最高層級（rung）讀取。不要宣告自查結果，也不要說明你正在用 哪一層——使用者只會看到結果（以及當某一層失敗、你要轉用另一層時，你轉用了 哪一層）：  1. CODE-NET → 寫一個短小的即棄 Python 腳本（只可用 urllib 或 requests 等標準    程式庫，不要用冷門的相依套件），按配方發出請求，並印出整理好的結果。 2. FETCH → 直接開啟配方網址。以下兩個配方都是普通 GET 請求、回傳 JSON，理應直接    成功。內建讀取工具只會發出 GET、未必可以設定標頭，而且可能會總結或截斷過長的    回應——如果因此令配方失效，請如實說明。 3. SEARCH → 搜尋該資料或端點現時的位置，使用找到的內容，並說明資料來自哪個頁面。 4. NONE → 向使用者提供兩個選擇——在 terminal 執行配方中確切的 `curl` 指令，或將配方網址直接貼入瀏覽器網址列開啟（瀏覽器會顯示 JSON 回覆）——然後請他們把輸出複製貼回對話，並繼續。  如果某一層因網絡或存取錯誤而失敗，降到下一層，並說明你轉用了哪一層。同一層重試 不多於兩次。  ## 工具  ### list_stores — 列出某個位置附近的壽司郎香港分店，由近至遠排序。  **使用者會說：**「列出近 22.28, 114.16 的壽司郎分店」／「邊間分店仲派緊籌？」  **輸入：** latitude：數字（預設 22.0，香港地理中心）；longitude：數字（預設 114.0）；region：字串（預設 "HK"）。三項全部可省略——使用者沒有指定時用預設值。  **配方（建議層級：FETCH；CODE-NET 亦可以）：**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude={latitude}&longitude={longitude}&numresults=100&region={region} Headers: Accept: application/json ```  `numresults` 必須是 100。一次普通 GET，無分頁、無 POST，不需要特別的 User-Agent。 如果你完全沒有可用層級，向使用者提供兩個選擇：在 terminal 執行以下 curl 指令，或將以下網址貼入瀏覽器開啟，再把顯示的 JSON 回覆複製貼回對話：    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK"    瀏覽器網址：https://sushipass.sushiro.com.hk/api/2.0/info/storelist?latitude=22.0&longitude=114.0&numresults=100&region=HK  **解析：**回應是一個 JSON 陣列，元素為分店物件，由近至遠排列，最多 100 間。每個 元素只保留以下欄位：  - id                ← id            （get_store_queue 需要的分店編號） - name              ← name - name_en           ← nameEn - store_status      ← storeStatus   （"OPEN" 或其他歇業狀態） - net_ticket_status ← netTicketStatus - wait              ← wait          （正在等候的組數） - address           ← address - area              ← area - latitude          ← latitude - longitude         ← longitude  net_ticket_status 的意思：OFFLINE_MANUAL = 正在派籌；OFFLINE_CLOSING / OFFLINE_CLOSED = 已停止派籌。  **回覆格式：**以人類可讀的文字及表格回覆，不要貼 raw JSON。先寫一行簡短總結 （共找到幾多間分店、仲有幾多間正在派籌），然後用一個 markdown 表格列出最近的 分店（由近至遠），欄位為：  - 分店（中文名，英文名放在括號內） - 地區（area） - 狀態，用文字表達（OPEN → 營業中；其他 → 已休息） - 取籌，用文字表達（OFFLINE_MANUAL → 正在派籌；OFFLINE_CLOSING /   OFFLINE_CLOSED → 已停止派籌） - 等候組數（wait）  如果 API 回傳多過 15 間分店，表格只列最近 10–15 間，講明仲有幾多間，並提出 可以列出其餘分店。只有在使用者明確要求 JSON 或機器可讀資料時，才輸出 raw JSON——一個只包含 id, name, name_en, store_status, net_ticket_status, wait, address, area, latitude, longitude 十個欄位的 JSON 陣列。  排版：標籤一律用純文字（例如：最快選擇：），不要用任何 markdown 粗體符號 （**）——部分介面會把星號原樣顯示，而不是顯示成粗體。  **已知錯誤：**上游錯誤會以 {"error": "API returned <HTTP 狀態碼>", "detail": "<回應內容首 500 字元>"} 或 {"error": "API request failed: <訊息>"} 的形式出現 ——如實向使用者報告，不要隱瞞。回應內容為空或 HTTP 204 表示 {"status": "ok"} （沒有資料）。上游逾時為 30 秒。  ### get_store_queue — 查詢一間分店的即時取籌排隊情況。  **使用者會說：**「1016 號店而家叫到幾多號？」／「<地區> 分店要等幾耐？」  **輸入：** store_id：整數（必須——list_stores 回覆中的數字分店編號）；region： 字串（預設 "HK"）。如果 store_id 不明，先問使用者——絕不可以默默自行估計。  **配方（建議層級：FETCH；CODE-NET 亦可以）：**  ``` GET https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region={region}&storeid={store_id} Headers: Accept: application/json ```  每個分店編號只對應一次呼叫。不要在同一個回覆中循環查詢多間分店；如果使用者一次過 提出幾間分店，請逐間呼叫，每次之間停 2 秒（見「使用禮儀」）。如果你完全沒有可用層級，向使用者提供兩個選擇：在 terminal 執行以下 curl 指令，或將以下網址貼入瀏覽器開啟，再把顯示的 JSON 回覆複製貼回對話：    curl -s -A "python-httpx" "https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID"    瀏覽器網址：https://sushipass.sushiro.com.hk/api/2.0/remote/groupqueues?region=HK&storeid=STORE_ID  **解析：**原封不動回傳整個 payload。欄位說明：  - storeQueue：即將叫號的籌號清單——第一個元素就是下一個會被叫的籌號 - boothQueue / counterQueue 以及訂座（reservation）變體：同一條隊按籌的種類分拆 - 空陣列代表無人等候  **回覆格式：**以簡短的文字摘要回覆，不要貼 raw JSON：分店名稱及編號、下一個 叫號的籌號（storeQueue 的第一個元素）、其後幾個籌號，以及各種類隊伍（帳枱 booth / 櫃枱 counter / 訂座 reservation 變體）的數量。如果全部陣列都是空的， 就寫明現時無人等侯。只有在使用者明確要求 JSON 或機器可讀資料時，才原封不動 回傳整個 JSON payload，保留所有欄位。  排版：標籤一律用純文字（例如：下一個叫號：），不要用任何 markdown 粗體符號 （**）——部分介面會把星號原樣顯示，而不是顯示成粗體。  **已知錯誤：**錯誤包裝方式與 list_stores 相同（{"error": ..., "detail": ...}）； 回應內容為空或 HTTP 204 表示 {"status": "ok"}。  ## 讀取規則  - 先用建議層級；只在對應的錯誤類型出現時才降級： - 403 或封鎖頁面 → 如果可以設定標頭，用近似瀏覽器的 User-Agent 重試一次；否則   降一層 - 429 → 遵守 Retry-After 或等待一次，然後降一層；絕不連環轟炸端點 - 404 或網域失效 → 用 SEARCH 尋找端點的新位置；找到就用，把它採納為新的建議   配方，並告知使用者配方已更改 - 401 → 這個 API 本來就無需金鑰，出現 401 即代表端點已更改：用 SEARCH 尋找新   位置，而不是向使用者索取金鑰 - 重新導向到登入頁 → 停止並如實說明；該資料並非公開 - 兩個配方都是普通 GET、回傳 JSON——不需要 POST 或 JavaScript——所以 FETCH 層   可以勝任；如果你的讀取工具破壞或總結了 JSON，如實說明並降一層  ## 使用禮儀  上游是壽司郎香港實際營運中的售票系統。請溫柔對待它：  - 對 sushipass.sushiro.com.hk 的任何兩次呼叫之間，至少相隔 1–2 秒（此配方來源的   整合本身強制每次至少相隔 1 秒，而且逐一序列化） - 重用本對話中已有的結果，不要重複讀取同一個網址 - 每次排隊查詢只查一間分店；絕不迴圈掃描整個分店清單 - 如果使用者想持續監察排隊情況，重新檢查的頻率不可高於每 30–60 秒一次，而且只查   他們真正關心的分店 - 只讀取公開資料；出現登入牆即停止，不是繞過
````

## 示例 prompts

**簡單：**

> 「列出旺角港鐵站附近嘅壽司郎分店，話我知邊間仲派緊籌。」

> 「壽司郎油塘分店而家叫到幾多號？」

**進階 — 搭公共交通：**

```text
我而家喺旺角港鐵站，會搭港鐵或巴士。幫我揀間最快食到嘅壽司郎
```

**進階 — 揸車：**

```text
我揸車由沙田出發。幫我揀間最快食到嘅壽司郎
```

注意：交通時間只係估計；排隊資料係 API 即時數據，隨時會變，出發前請先向壽司郎官方渠道核實。

## 邊條路啱你？

| 你係… | 建議 | 點解 | 所需準備 |
|---|---|---|---|
| 一般用家（無需技術背景） | 上方[一句即試](#一句即試免安裝)一節嘅提示詞 | 直接複製提示詞，貼入任何聊天機械人，機械人會代你讀取資料 | 只需一個聊天機械人帳號 |
| 進階用家（日常使用 AI 編程助理） | [2. skill](#2-skill--ai-編程助理進階用家) | 用 `npx skills add` 一句指令安裝 agent skill，助理會自動按需要讀取及整理資料 | Node.js／npx；或 opencode、Claude Code 等 agent 工具 |
| 專業用戶（自行部署服務） | [3. MCP 伺服器](#3-mcp-伺服器--自行部署專業用戶) | 喺本機或伺服器運行真正的 MCP 伺服器，接駁任何 MCP 客戶端 | uv 或 Docker |

## 1. 聊天機械人提示詞（一般用家）

無需安裝任何嘢、無需金鑰、無需架設服務——成段提示詞已內嵌喺上方[一句即試](#一句即試免安裝)一節。

1. 揀英文版或香港中文版提示詞——兩個 block 互通，效果一樣。
2. 整個 code block 複製，作為**第一句訊息**貼入任何聊天機械人。
3. 若果機械人自己不能讀取網址，它會交畀你 `curl` 指令（喺 terminal 執行）或網址（貼入瀏覽器開啟）；將輸出貼返入對話，機械人就會繼續。

機械人會喺需要時詢問位置或分店編號，並以你所選提示詞嘅語言回覆。示例見上方[示例 prompts](#示例-prompts)一節。

## 2. skill — AI 編程助理（進階用家）

一個獨立嘅 agent skill（`skill/sushiro-scraper/SKILL.md`），教你嘅 AI 助理自行讀取壽司郎資料，並附遞補層級（直接 GET → 即棄腳本 → curl → webfetch/websearch），端點被封鎖或搬走咗都自救到。

### 用 skills CLI 安裝（最簡單）

[skills CLI](https://github.com/vercel-labs/skills) 會偵測你已安裝嘅 agent（opencode、Claude Code、Codex、Cursor 等），並為每個 agent 自動接駁：

```bash
# 互動模式：確認 skill 及要安裝到哪些 agent
npx skills add Jaguar-Kwok/sushiro-ai --skill sushiro-scraper

# 全域安裝（所有專案可用），免互動確認
npx skills add Jaguar-Kwok/sushiro-ai --skill sushiro-scraper -g -y
```

常用選項：

| 選項 | 作用 |
|---|---|
| `-g` | 全域安裝（使用者目錄），而非只裝在當前專案 |
| `-a opencode`、`-a claude-code` | 指定 agent，而非自動偵測 |
| `--copy` | 以複製檔案取代符號連結（symlink） |
| `--list` | 只列出此 repo 內找到的 skill，不安裝 |

之後用 `npx skills update sushiro-scraper` 更新；用 `npx skills remove sushiro-scraper` 移除。

### 無 Node.js 時手動安裝

```bash
cp -r skill/sushiro-scraper ~/.agents/skills/
```

（或者用符號連結：`ln -s "$(pwd)/skill/sushiro-scraper" ~/.agents/skills/sushiro-scraper`。）

裝好之後直接用自然語言開口問就得。示例見上方[示例 prompts](#示例-prompts)一節。

助理會按 skill 內嘅配方讀取資料，有禮貌地抓取（每次呼叫相隔至少 1–2 秒，絕不迴圈），並回傳與 MCP 工具相同嘅 JSON 結構。

## 3. MCP 伺服器 — 自行部署（專業用戶）

成個專案嘅源頭：一個 Python MCP SDK v2 伺服器，提供 `list_stores` 及 `get_store_queue` 兩個工具，經 streamable HTTP 提供（亦支援 stdio），並自我節流至每秒最多一個上游請求。

用 uv：

```bash
cd mcp && uv sync && uv run sushiro-mcp
```

用 Docker：

```bash
docker build -t sushiro-mcp mcp && docker run --rm -p 8000:8000 sushiro-mcp
```

將任何 MCP 客戶端指向 `http://127.0.0.1:8000/mcp`。進階設定（環境變數、host/origin allowlist、真實 hostname 部署、GHCR 映像）請睇 [`mcp/README.md`](mcp/README.md)。

## 可以取得甚麼資料？

- **分店清單**（`list_stores`）——某位置附近最多 100 間分店，由近至遠：營業狀態、是否派籌、等候組數、地址、地區、座標。
- **分店排隊**（`get_store_queue`）——一間分店嘅即時取籌情況：即將叫號嘅籌號（`storeQueue`，第一個元素＝下一個叫號），並按帳枱 booth／櫃枱 counter 及訂座 reservation 變體分拆。

## 善待 API

上游（`https://sushipass.sushiro.com.hk/api/2.0`）係壽司郎香港實際營運嘅公開售票系統——免費、無需認證、真實存在。

- 任何兩次呼叫之間至少相隔 1–2 秒，切勿連環輪詢。
- 即時排隊最多每 30–60 秒重查一次，而且只查你真正關心嘅分店。
- 只讀取公開資料——出現登入牆即停手，唔係繞過。

## 常見問題

### 點解唔同 AI 平台／型號，行為會有少少唔同？

同一句提示詞，喺 ChatGPT、Claude、Gemini 或者唔同型號身上，速度、格式同可靠度都會有分別，主要原因：

- **能力階梯唔同。** 有啲平台嘅模型有可以上網嘅 code sandbox（CODE-NET）、有啲只有內建網頁讀取（FETCH）、有啲只有網絡搜尋（SEARCH）、有啲乜都無。提示詞嘅「步驟 0 能力自查」會叫模型靜靜哋揀最高可用嘅一層，所以唔同平台第一步做嘅嘢就可能唔同。
- **內建讀取工具嘅限制唔同。** 有啲只能發 GET、唔可以自訂 HTTP 標頭、會截斷或總結過長嘅 JSON 回應、甚至有快取——呢啲都會影響攞到嘅資料完唔完整。
- **模型脾氣唔同。** 每個型號跟配方嘅嚴謹度、輸出格式、幾時主動重查、用咩語言回你，都由佢嘅訓練決定；同一平台嘅唔同版本都會唔同。
- **平台政策唔同。** rate limit、請求 timeout、可唔可以任意呼叫第三方 API 等政策，每個平台唔一樣。

提示詞本身設計咗遞補階梯（CODE-NET → FETCH → SEARCH → curl／瀏覽器後備），目的係令佢喺任何平台都跌唔死——但最終結果喺速度、排版同可靠度上略有出入，屬正常現象。

## 非官方聲明、可接受使用及許可證

本專案屬**非官方**教育及研究用途，與壽司郎香港及 SushiPass API 營運者並無任何隸屬或認可關係；「Sushiro／壽司郎／SushiPass」為其權利人嘅商標，僅用於識別服務。

- 程式碼及文件以 [MIT 許可證](LICENSE) 提供，API 資料權利屬於其擁有人（詳見 [NOTICE.md](NOTICE.md)）。
- 僅供教育及研究用途。使用者須自行遵守適用法律及 API 擁有人嘅服務條款（詳見 [DISCLAIMER.md](DISCLAIMER.md)：切勿未經授權存取、濫用、過量請求、大量散發抓取或繞過安全管制）。
- 安全或下架事宜：[SECURITY.md](SECURITY.md) ／ jaguarkwokhk@gmail.com。

## 儲存庫結構

```text
sushiro-ai/
├── README.md    # 本檔：繁體中文（香港）說明 + 可複製嘅聊天機械人提示詞（英文 + 香港中文）
├── README.en.md # English version + the English chatbot prompt
├── skill/       # agent skill（sushiro-scraper）— 畀 AI 編程助理用
└── mcp/         # 可自行部署嘅 MCP 伺服器（Python SDK v2，stdio 或 HTTP，附 Docker 及 CI）
```

本檔同 [`README.en.md`](README.en.md) 內容保持同步，只係語言唔同——英文版只載英文提示詞，香港中文版提示詞只喺本檔出現。
