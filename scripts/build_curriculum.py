"""Build an integrated daily curriculum, not just a file schedule."""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "study_plan.json"
MATERIALS_PATH = ROOT / "docs" / "study_materials.json"
OUTPUT = ROOT / "docs" / "curriculum.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_+#.-]+|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "說明",
    "請說明",
    "應用",
    "技術",
    "資料",
    "模型",
    "人工智慧",
    "生成式",
    "考題",
    "情境",
    "整理",
    "重點",
    "章節",
    "概念",
    "the",
    "and",
    "for",
    "with",
}

PHASE_BASE_DIFFICULTY = {
    "foundation": 1,
    "junior": 2,
    "l21": 3,
    "l22": 4,
    "l23": 5,
    "final": 4,
}

FOCUS_GUIDES: dict[str, dict[str, Any]] = {
    "考試範圍盤點與診斷": {
        "overview": "先把考試範圍拆成初級基礎、L21 技術規劃、L22 大數據、L23 機器學習與考古題五個資料夾。今天的目的不是背誦，而是建立個人弱點表，知道哪些章節需要反覆練題。",
        "concepts": [
            ["範圍盤點", "把教材、樣題、情境題與筆記分門別類，避免讀到後期才發現缺一科。"],
            ["弱點表", "每次測驗後記錄錯因：觀念不熟、題幹誤讀、公式不會、情境判斷錯。"],
            ["讀書節奏", "平日讀新觀念，週六做測驗，週日回收錯題。"],
        ],
        "exam_focus": "先確認你能說出各科考什麼、題型怎麼問、哪些資料是官方指引或考古題。",
        "common_mistakes": ["只照檔名亂讀，沒有弱點追蹤。", "一開始就刷題，卻不知道錯在哪個章節。"],
    },
    "AI 基礎名詞與生成式 AI 字彙": {
        "overview": "把 AI、ML、DL、生成式 AI、LLM、Prompt、RAG、Embedding 等詞彙建立成可互相比較的表格。考題常用相近名詞混淆，重點是能用一句話分辨差異。",
        "concepts": [
            ["AI / ML / DL", "AI 是大範圍目標，ML 是讓模型從資料學習，DL 是以深層神經網路處理複雜特徵。"],
            ["生成式 AI", "依照訓練出的機率分布生成文字、圖片或程式碼，不只是分類或預測。"],
            ["RAG", "先檢索外部資料，再把資料交給語言模型回答，用來降低幻覺並提高可追溯性。"],
        ],
        "exam_focus": "遇到名詞題時先判斷它屬於資料、模型、生成、檢索、治理哪一層。",
        "common_mistakes": ["把生成式 AI 當成一般搜尋引擎。", "把 Prompt Engineering 誤認為模型訓練。"],
    },
    "AI 基礎理論": {
        "overview": "AI 系統由資料、演算法/模型、訓練、推論與評估組成。讀這章要能把一個 AI 應用拆成輸入資料、模型任務、輸出結果與評估指標。",
        "concepts": [
            ["資料", "模型品質受資料量、品質、標註與偏誤影響。"],
            ["訓練與推論", "訓練是調整模型參數；推論是用訓練好的模型產生預測或回應。"],
            ["評估", "依任務選指標，例如分類看準確率/召回率，回歸看誤差，生成式看事實性與可用性。"],
        ],
        "exam_focus": "題目給場景時，要先辨識任務類型與適合指標。",
        "common_mistakes": ["只背模型名稱，忽略資料與評估。", "把訓練資料和測試資料混用。"],
    },
    "產業常見 AI 應用": {
        "overview": "產業應用可分成辨識、預測、推薦、最佳化、自動化與生成。答題時要從商業目標反推 AI 功能，而不是看到 AI 就直接選最複雜模型。",
        "concepts": [
            ["辨識", "影像、語音、文字分類等，把輸入映射到類別或標籤。"],
            ["預測", "用歷史資料估計未來需求、風險、銷售或異常。"],
            ["推薦與生成", "推薦強調排序與個人化，生成強調產出新內容。"],
        ],
        "exam_focus": "情境題常問：這個需求最適合哪種 AI 功能、需要什麼資料、如何衡量成效。",
        "common_mistakes": ["把推薦、搜尋、生成混成同一件事。", "忽略導入後的維運與使用者流程。"],
    },
    "負責任 AI": {
        "overview": "負責任 AI 不是考道德口號，而是考風險控制：公平性、透明性、隱私、資安、可解釋性、問責與持續監控。每個 AI 專案都要把風險放進流程。",
        "concepts": [
            ["公平性", "檢查資料與模型是否對特定群體產生不合理差異。"],
            ["透明與可解釋", "讓使用者知道 AI 如何被使用，並能追蹤決策依據。"],
            ["隱私與資安", "資料最小化、權限控管、去識別化與存取紀錄。"],
        ],
        "exam_focus": "看到個資、金融、醫療、招募或自動決策題，要優先想到治理與風險緩解。",
        "common_mistakes": ["只追求準確率，忽略偏誤與法規。", "把資料匿名化當成萬靈丹。"],
    },
    "機器學習技術概覽": {
        "overview": "先掌握監督式、非監督式、半監督、強化學習的差異，再看資料前處理、訓練、驗證、測試與部署流程。這是後面 L23 的地基。",
        "concepts": [
            ["監督式學習", "有標籤資料，用於分類或回歸。"],
            ["非監督式學習", "沒有標籤，用於分群、降維、異常偵測。"],
            ["泛化能力", "模型在新資料上的表現，需透過驗證與測試確認。"],
        ],
        "exam_focus": "題目常要求從資料型態與目標判斷學習類型。",
        "common_mistakes": ["把分群當成分類。", "只看訓練準確率，不看測試或驗證。"],
    },
    "企業導入 AI 策略": {
        "overview": "AI 導入要從問題定義、資料可用性、PoC、成效指標、治理、部署維運一路串起。考題常問哪個步驟先做、哪種風險要先處理。",
        "concepts": [
            ["需求定義", "先明確業務問題、使用者、輸出與成功指標。"],
            ["PoC", "小規模驗證資料、模型與流程是否可行，不等於正式上線。"],
            ["維運治理", "上線後要監控成效、漂移、資安、成本與使用者回饋。"],
        ],
        "exam_focus": "企業導入題要同時回答技術可行、商業價值與治理風險。",
        "common_mistakes": ["先選模型再找問題。", "PoC 成功就直接大規模上線。"],
    },
}

FOCUS_GUIDES.update(
    {
        "人工智慧基礎概論": {
            "overview": "本章把 AI 發展、資料、演算法、模型與應用情境串成一張地圖。讀的時候不要只背定義，要能把題目場景拆成輸入資料、任務類型、模型輸出與評估方式。",
            "concepts": [["AI 任務類型", "分類、回歸、分群、推薦、生成各有不同輸出與評估方式。"], ["資料品質", "資料完整性、代表性、標註一致性會直接影響模型表現。"], ["應用情境", "把技術連到商業流程，確認使用者、輸出與成功指標。"]],
            "exam_focus": "初級題常問定義與應用配對；先判斷題目問的是資料、模型、流程或風險。",
            "common_mistakes": ["把 AI、ML、DL 視為同義詞。", "看到應用情境時只選熱門技術，沒有檢查資料條件。"],
        },
        "搜尋、推論與知識表示": {
            "overview": "搜尋與推論是早期 AI 的核心：搜尋負責在狀態空間找解，推論負責依規則或知識得到結論。現代 AI 雖以資料驅動為主，但知識表示仍常出現在專家系統、規則引擎與可解釋流程。",
            "concepts": [["狀態空間搜尋", "把問題拆成狀態、動作、目標與成本。"], ["推論規則", "由既有事實與規則推出新結論。"], ["知識表示", "用規則、語意網、知識圖譜等形式保存領域知識。"]],
            "exam_focus": "看到規則、專家經驗、知識庫、路徑最佳化，先判斷是否在問搜尋或推論。",
            "common_mistakes": ["把所有 AI 都想成深度學習。", "忽略規則式系統在高可解釋需求中的價值。"],
        },
        "機器學習基本流程": {
            "overview": "機器學習流程包含問題定義、資料蒐集、前處理、特徵工程、模型訓練、驗證測試、部署與監控。考題常把流程順序打亂，要能判斷每一步的目的。",
            "concepts": [["資料切分", "訓練集用來學習，驗證集用來調參，測試集用來估計泛化表現。"], ["過擬合", "訓練表現很好但新資料表現差，常用正則化、更多資料或簡化模型處理。"], ["評估指標", "分類、回歸、分群各自有不同指標，不能混用。"]],
            "exam_focus": "流程題先看它問資料、模型、驗證還是部署；指標題先判斷任務類型。",
            "common_mistakes": ["用測試集反覆調參。", "只看 accuracy，忽略資料不平衡。"],
        },
        "生成式 AI 應用與規劃": {
            "overview": "生成式 AI 導入重點是任務邊界、資料來源、Prompt/RAG 設計、輸出驗證與風險控管。它能產生內容，但仍需要人類審核與流程設計。",
            "concepts": [["LLM", "大型語言模型依上下文產生文字，擅長摘要、問答、改寫與推理輔助。"], ["Prompt", "用角色、目標、限制、格式與範例引導模型輸出。"], ["RAG", "用檢索資料補足模型知識，讓答案能追溯到來源。"]],
            "exam_focus": "看到企業知識問答、文件摘要、客服助理，優先想到資料來源、RAG 與驗證機制。",
            "common_mistakes": ["把 RAG 當成重新訓練模型。", "忽略幻覺、個資與機密資料外洩。"],
        },
        "提示設計與導入流程": {
            "overview": "提示設計不是只寫一句問題，而是把任務、角色、資料、限制、輸出格式與驗收標準寫清楚。企業導入時要能測試提示是否穩定、可重複、可控。",
            "concepts": [["角色與任務", "指定模型扮演的角色與要完成的工作。"], ["約束條件", "限制資料來源、格式、語氣、禁止事項與輸出長度。"], ["驗收標準", "用測試題、人工審查或指標確認輸出是否可用。"]],
            "exam_focus": "Prompt 題常問如何降低錯誤輸出；答案通常包含明確指令、範例、格式與資料依據。",
            "common_mistakes": ["只要求模型『詳細回答』，沒有給格式與限制。", "沒有保存測試案例，導致提示改版難以驗證。"],
        },
        "風險、隱私與治理": {
            "overview": "AI 風險包含個資、資安、偏誤、可解釋性、責任歸屬與模型漂移。治理不是最後補文件，而是從資料蒐集到上線監控都要納入。",
            "concepts": [["個資保護", "資料最小化、去識別化、同意與目的限制。"], ["模型風險", "偏誤、幻覺、漂移、錯誤決策都需要監控與補救。"], ["治理機制", "權限、紀錄、審核、責任分工與例外處理。"]],
            "exam_focus": "看到敏感資料、自動決策、金融醫療等場景，先找治理與法規風險。",
            "common_mistakes": ["只靠技術準確率判斷專案成功。", "把去識別化等同於完全沒有隱私風險。"],
        },
        "初級模擬題與錯題整理": {
            "overview": "模擬題的目的不是追求一次高分，而是找出穩定錯因。每題都要標記對應章節、錯因與下次判斷規則。",
            "concepts": [["錯題分類", "分成觀念不熟、題幹誤讀、選項比較錯、時間壓力。"], ["訂正方式", "寫出正解理由與錯選項為何錯。"], ["回測", "隔 2 到 3 天重做同類題，確認錯因消失。"]],
            "exam_focus": "模擬後要建立錯題本，而不是只看分數。",
            "common_mistakes": ["只把正確答案抄下來。", "沒有把錯題回扣到章節。"],
        },
        "L21 總覽與考點地圖": {
            "overview": "L21 是 AI 技術應用與規劃，核心是從場景判斷技術、資料條件、導入流程與風險。讀這科要建立『需求-資料-技術-部署-治理』的答題鏈。",
            "concepts": [["技術選型", "依任務選擇 NLP、CV、推薦、預測或生成式 AI。"], ["導入規劃", "先做需求與資料評估，再 PoC、上線與維運。"], ["風險治理", "技術可行不代表可上線，還要看合規、資安與組織流程。"]],
            "exam_focus": "L21 情境題常問下一步、優先風險、適合技術與成效指標。",
            "common_mistakes": ["把技術名詞背熟但不會套場景。", "忽略導入前的資料盤點。"],
        },
        "AI 相關技術應用": {
            "overview": "AI 技術應用要能對應到辨識、預測、推薦、生成、最佳化等功能。答題時從業務目標反推模型任務，而不是從模型名稱倒推需求。",
            "concepts": [["辨識技術", "用於影像、語音、文字分類與偵測。"], ["預測技術", "用歷史資料預測數值、風險或趨勢。"], ["生成與推薦", "生成產生內容，推薦排序候選項目。"]],
            "exam_focus": "題目若給客戶需求，要寫出適用 AI 功能與資料需求。",
            "common_mistakes": ["把聊天機器人等同於所有 NLP。", "忽略推薦系統需要回饋資料。"],
        },
        "自然語言處理技術": {
            "overview": "NLP 處理文字資料，從斷詞、向量化、分類、摘要、問答到語意搜尋。現代 NLP 常結合 Embedding、LLM 與 RAG。",
            "concepts": [["斷詞與前處理", "中文需處理斷詞、停用詞、同義詞與語料清理。"], ["Embedding", "把文字轉成向量，使語意相近的文字距離較近。"], ["語意搜尋/RAG", "先用向量或關鍵字找資料，再生成回答。"]],
            "exam_focus": "看到文件問答、客服、摘要、分類，要判斷是否需要 NLP 與資料檢索。",
            "common_mistakes": ["把關鍵字搜尋與語意搜尋混淆。", "忽略語料品質對 NLP 的影響。"],
        },
        "AI 導入評估規劃": {
            "overview": "導入評估要先問：問題是否值得解、資料是否可用、技術是否成熟、效益能否衡量、風險是否可控。PoC 是驗證，不是正式營運。",
            "concepts": [["可行性", "資料、技術、人力、成本與時程是否可支撐。"], ["效益指標", "定義節省時間、提升準確率、降低成本或改善體驗。"], ["風險評估", "合規、資安、偏誤、流程衝擊都要納入。"]],
            "exam_focus": "導入題常問優先順序；通常先定義問題與資料，再選模型。",
            "common_mistakes": ["沒有 KPI 就開始 PoC。", "只看技術 demo，不看流程整合。"],
        },
        "AI 技術應用與系統部署": {
            "overview": "部署關注模型如何穩定提供服務，包括 API、資料管線、監控、版本管理、權限與回滾。上線後仍要追蹤漂移與使用者回饋。",
            "concepts": [["API 服務", "讓前端或業務系統呼叫模型能力。"], ["MLOps", "管理資料、模型、部署、監控與版本。"], ["監控與回滾", "偵測效能下降、資料漂移或錯誤輸出並快速處理。"]],
            "exam_focus": "看到上線、維運、監控、成本，答案要包含部署架構與治理。",
            "common_mistakes": ["把模型訓練完成當成專案結束。", "沒有版本控管與回滾機制。"],
        },
        "企業 AI 素養與金融 AI 指引": {
            "overview": "企業 AI 素養包含高階治理、員工使用規範、資料保護、模型風險與第三方管理。金融場景更重視可解釋、可稽核與客戶權益。",
            "concepts": [["AI 素養", "組織成員要理解能力邊界、風險與正確使用方式。"], ["金融 AI 指引", "強調公平、透明、責任、資安與監督。"], ["第三方風險", "外部模型或服務仍需契約、資安與資料使用審查。"]],
            "exam_focus": "金融或高風險題目優先回答治理、稽核與責任分工。",
            "common_mistakes": ["把供應商模型當成免責。", "忽略員工使用生成式 AI 的資料外洩風險。"],
        },
        "L21 情境題演練": {
            "overview": "L21 情境題要把需求、資料、技術、導入步驟與風險一起判斷。作答時用固定框架避免漏項。",
            "concepts": [["需求判斷", "先確定問題、使用者與輸出。"], ["方案選型", "依資料型態與任務選 AI 技術。"], ["風險補強", "加入個資、偏誤、資安、監控與人審。"]],
            "exam_focus": "看到案例題先畫出需求-資料-技術-治理鏈。",
            "common_mistakes": ["只回答模型名稱。", "沒有處理資料不足或風險。"],
        },
        "機率統計基礎": {
            "overview": "機率統計是大數據與機器學習的語言。今天要理解隨機變數、分佈、抽樣與估計，知道資料不確定性如何影響分析結論。",
            "concepts": [["隨機變數", "把不確定事件轉成可分析的數值或類別。"], ["機率分佈", "描述結果出現的可能性，例如常態、二項、卜瓦松。"], ["抽樣", "用部分資料推估母體，需注意偏誤與代表性。"]],
            "exam_focus": "統計題要先判斷資料型態、分佈假設與樣本是否代表母體。",
            "common_mistakes": ["把相關當因果。", "忽略樣本偏誤與分佈假設。"],
        },
        "敘述性統計與資料摘要": {
            "overview": "敘述性統計用平均數、中位數、變異數、標準差、分位數與圖表描述資料樣貌。它是建模前理解資料的第一步。",
            "concepts": [["集中趨勢", "平均數容易受極端值影響，中位數較穩健。"], ["離散程度", "變異數與標準差描述資料分散程度。"], ["視覺化", "直方圖、盒鬚圖、散佈圖協助找分佈與異常。"]],
            "exam_focus": "看到資料摘要題，先判斷要描述中心、分散、關係還是異常。",
            "common_mistakes": ["只看平均數忽略極端值。", "用錯圖表表達資料型態。"],
        },
        "資料清理與整合": {
            "overview": "資料清理處理缺失值、異常值、重複值、格式不一致與資料整合。建模成敗常取決於這一步，而不是模型多複雜。",
            "concepts": [["缺失值", "可刪除、補值或用模型推估，需看缺失機制與比例。"], ["異常值", "用 Z-score、IQR 或模型方法檢測，但不一定要刪除。"], ["資料整合", "JOIN、格式轉換與主鍵一致性會影響資料正確性。"]],
            "exam_focus": "題目問資料品質時，先列缺失、異常、重複、格式、整合與偏誤。",
            "common_mistakes": ["看到異常值就刪。", "JOIN 後沒有檢查筆數與重複。"],
        },
        "大數據處理技術": {
            "overview": "大數據處理關注資料量、速度與多樣性。批次處理適合大量離線分析，串流處理適合即時事件，分散式架構用來提高擴展性。",
            "concepts": [["批次處理", "定期處理大量資料，例如每日報表或訓練資料生成。"], ["串流處理", "即時處理事件，例如交易異常或 IoT 監控。"], ["分散式運算", "Spark、Flink 等工具分散處理資料與容錯。"]],
            "exam_focus": "看到即時、低延遲、事件流就想到串流；看到大量離線報表就想到批次。",
            "common_mistakes": ["所有情境都選即時串流。", "忽略成本、延遲與一致性取捨。"],
        },
        "大數據分析方法與工具": {
            "overview": "分析方法包含描述、診斷、預測、規範性分析，也包含回歸、分群、檢定與重抽樣。工具選擇要看資料量、技能、部署與維運。",
            "concepts": [["回歸分析", "估計變數關係並做預測，可檢查影響方向與強度。"], ["分群分析", "在無標籤資料中找相似群組。"], ["Bootstrap", "用重抽樣估計統計量不確定性。"]],
            "exam_focus": "方法題先判斷目標是描述、預測、分類、分群還是決策最佳化。",
            "common_mistakes": ["把分群結果當成已知分類。", "忽略方法假設與資料型態。"],
        },
        "時間序列與預測": {
            "overview": "時間序列資料有趨勢、季節性、自相關與異常。ARIMA、Prophet、LSTM/GRU 各有適用場景，不能只用模型新舊判斷好壞。",
            "concepts": [["趨勢與季節性", "長期方向與週期變化要分開看。"], ["ARIMA/Prophet", "適合有時間結構且可解釋需求的預測。"], ["LSTM/GRU", "適合複雜序列模式，但需要較多資料與調參。"]],
            "exam_focus": "看到時間欄位與預測未來，先檢查趨勢、季節性與資料頻率。",
            "common_mistakes": ["隨機切分時間序列資料。", "忽略資料洩漏與未來資訊。"],
        },
        "資料儲存、合規與成本": {
            "overview": "資料工程不只存得下，還要查得快、管得住、成本可控且符合法規。格式、分區、索引、權限與保留政策都可能成為考點。",
            "concepts": [["儲存格式", "CSV 易用，Parquet 欄式儲存適合分析查詢。"], ["分區與索引", "透過 Partition、Index、Sharding 提升查詢與擴展能力。"], ["合規", "GDPR、ISO 27001、SOC 2 等關注資料保護與管理流程。"]],
            "exam_focus": "看到成本或效能題，先看儲存格式、分區策略與查詢模式。",
            "common_mistakes": ["只考慮容量，不考慮查詢與治理。", "把加密當成完整合規。"],
        },
        "大數據在 AI 之應用": {
            "overview": "大數據支撐 AI 的資料量、特徵多樣性與即時回饋。重點在特徵工程、高維資料、非結構資料與隱私保護。",
            "concepts": [["特徵工程", "把原始資料轉成模型可學習的變數。"], ["高維資料", "可用特徵選擇、PCA、t-SNE 等方法處理維度問題。"], ["非結構資料", "文字、圖片、語音常需 embedding 或深度學習處理。"]],
            "exam_focus": "AI 應用題要回答資料來源、特徵處理、模型與隱私保護。",
            "common_mistakes": ["資料越多就一定越好。", "忽略非結構資料的前處理成本。"],
        },
        "L22 情境題演練": {
            "overview": "L22 情境題通常描述資料來源、處理需求、分析目標與限制。作答要能設計資料流程並選擇合適工具。",
            "concepts": [["資料流程", "蒐集、清理、整合、儲存、分析、視覺化。"], ["工具選擇", "依資料量、延遲、成本與團隊技能選工具。"], ["資料治理", "品質、權限、血緣、合規與監控。"]],
            "exam_focus": "看到大數據案例先分辨批次/串流、結構/非結構、分析/預測。",
            "common_mistakes": ["只選工具不說原因。", "忽略資料品質與治理。"],
        },
        "線性代數與 ML 基礎": {
            "overview": "線性代數提供向量、矩陣、距離、投影與降維概念，是理解模型、相似度與深度學習的基礎。",
            "concepts": [["向量", "可表示特徵、文字 embedding 或樣本位置。"], ["矩陣", "用於資料表、線性轉換與模型參數。"], ["距離與相似度", "KNN、分群、檢索都依賴距離或相似度度量。"]],
            "exam_focus": "看到相似度、降維、embedding、KNN，要回到向量與距離。",
            "common_mistakes": ["把維度越多當成一定越好。", "忽略尺度差異會影響距離。"],
        },
        "機率統計之 ML 應用": {
            "overview": "ML 會用機率統計處理不確定性、估計參數、檢定假設與評估模型可信度。重點是知道統計假設如何影響模型結論。",
            "concepts": [["參數估計", "用資料估計模型參數，例如最大似然估計。"], ["假設檢定", "判斷觀察結果是否可能由隨機變異造成。"], ["不確定性", "用信賴區間、交叉驗證或重抽樣評估穩定性。"]],
            "exam_focus": "看到模型驗證與統計假設，先問資料分佈、樣本數與評估方式。",
            "common_mistakes": ["把 p-value 當成效果大小。", "忽略資料獨立性假設。"],
        },
        "線性迴歸與邏輯迴歸": {
            "overview": "線性迴歸預測連續值，邏輯迴歸處理二元或多類分類。兩者都重視特徵、損失函數、正則化與解釋性。",
            "concepts": [["線性迴歸", "估計輸入特徵與連續目標的線性關係。"], ["邏輯迴歸", "輸出類別機率，常用於分類與風險評分。"], ["正則化", "L1/L2 用於降低過擬合並控制模型複雜度。"]],
            "exam_focus": "先判斷目標是連續數值還是類別機率，再選回歸模型。",
            "common_mistakes": ["把邏輯迴歸當成回歸預測連續值。", "忽略特徵尺度與共線性。"],
        },
        "樹模型與集成方法": {
            "overview": "決策樹容易解釋但可能過擬合；隨機森林透過多棵樹降低變異；XGBoost 逐步修正錯誤，常有高準確率但需調參。",
            "concepts": [["決策樹", "以規則切分資料，適合解釋但容易過擬合。"], ["隨機森林", "Bagging 多棵樹，提升穩定性。"], ["XGBoost", "Boosting 逐步修正殘差，表現強但需注意調參與過擬合。"]],
            "exam_focus": "看到可解釋與規則可視化想到決策樹；追求穩定表現可考慮集成。",
            "common_mistakes": ["以為樹模型不需資料前處理。", "忽略模型複雜度與過擬合。"],
        },
        "KNN、SVM、DBSCAN": {
            "overview": "KNN 用距離找鄰居，SVM 找最大間隔分類邊界，DBSCAN 用密度找群與離群點。三者都很依賴資料尺度與參數。",
            "concepts": [["KNN", "根據最近鄰樣本投票或平均，簡單但受尺度與 k 值影響。"], ["SVM", "用最大間隔與核函數處理分類，適合中小型高維資料。"], ["DBSCAN", "依密度分群，可找離群點且不需指定群數。"]],
            "exam_focus": "看到距離、核函數、密度、離群點時要分辨三種模型。",
            "common_mistakes": ["KNN 前沒有標準化。", "把 DBSCAN 當成需要指定 K 的分群。"],
        },
        "CNN、RNN 與深度學習": {
            "overview": "CNN 擅長影像與局部特徵，RNN/LSTM/GRU 擅長序列資料，深度學習需大量資料、算力與調參，也需注意可解釋性。",
            "concepts": [["CNN", "用卷積擷取局部空間特徵，常用於影像辨識。"], ["RNN/LSTM/GRU", "處理序列與時間依賴，例如文字或時間序列。"], ["深度學習限制", "需要資料與算力，且可解釋性與部署成本較高。"]],
            "exam_focus": "影像先想到 CNN；序列先想到 RNN/LSTM/GRU；小資料不一定適合深度學習。",
            "common_mistakes": ["看到 AI 就選深度學習。", "忽略資料量與標註成本。"],
        },
        "建模、驗證與參數調整": {
            "overview": "建模不只是訓練模型，還要透過驗證集、交叉驗證與調參確認泛化能力。評估指標必須符合任務與商業目標。",
            "concepts": [["交叉驗證", "用多次切分估計模型穩定性。"], ["Grid/Random Search", "搜尋超參數組合，避免只憑直覺調參。"], ["評估指標", "分類看 Precision/Recall/F1/AUC，回歸看 MAE/RMSE/R2。"]],
            "exam_focus": "看到調參、驗證、資料切分，先避免資料洩漏。",
            "common_mistakes": ["用測試集調參。", "資料不平衡仍只看 accuracy。"],
        },
        "機器學習治理": {
            "overview": "機器學習治理涵蓋模型監控、漂移偵測、偏誤管理、可解釋性、版本控管與審計。模型上線後才是治理開始。",
            "concepts": [["資料漂移", "輸入資料分佈改變，可能讓模型表現下降。"], ["模型監控", "追蹤指標、錯誤、延遲、成本與使用情境。"], ["可解釋性", "讓利害關係人理解模型依據與限制。"]],
            "exam_focus": "高風險或上線題要補監控、回滾、人審與責任分工。",
            "common_mistakes": ["模型準確率高就不監控。", "沒有版本與資料血緣紀錄。"],
        },
        "L23 情境模擬題": {
            "overview": "L23 情境題重點是模型選擇與理由：任務是分類/回歸/分群？資料量與標籤如何？指標是什麼？風險如何治理？",
            "concepts": [["模型選擇", "由任務、資料、解釋性、成本與風險決定。"], ["驗證流程", "切分資料、選指標、調參、測試與監控。"], ["弱點補強", "把錯題整理成模型選擇規則。"]],
            "exam_focus": "作答要寫模型名稱、選擇理由、評估方式與風險控管。",
            "common_mistakes": ["只回答模型名稱沒有理由。", "忽略資料標籤與指標。"],
        },
        "初級與中級總複習": {
            "overview": "總複習要把初級名詞、L21 導入規劃、L22 大數據、L23 模型選擇串起來。目標是看到題目能快速定位到科目與章節。",
            "concepts": [["科目定位", "先判斷題目屬於基礎、導入、大數據或機器學習。"], ["易混淆比較", "把相似名詞整理成表格。"], ["錯題回收", "優先補重複錯誤，而不是平均重讀。"]],
            "exam_focus": "用題目定位章節，縮短思考時間。",
            "common_mistakes": ["最後階段重新精讀全部教材。", "忽略高頻錯題。"],
        },
        "L21 全科模擬": {
            "overview": "L21 模擬要練情境判斷：需求、資料、技術、導入流程、部署與治理。每題都要說出為什麼其他選項不適合。",
            "concepts": [["需求分析", "找出使用者、輸出與成功指標。"], ["技術規劃", "依資料型態與任務選技術。"], ["導入治理", "處理風險、資安、監控與人審。"]],
            "exam_focus": "練速度與選項排除法。",
            "common_mistakes": ["只背單點知識。", "沒有比較選項差異。"],
        },
        "L22 全科模擬": {
            "overview": "L22 模擬要整合統計、資料處理、分析工具、儲存與治理。遇到案例先畫資料流。",
            "concepts": [["統計判斷", "資料型態、分佈、抽樣與檢定。"], ["資料工程", "清理、整合、批次/串流、儲存。"], ["分析治理", "方法選擇、成本、權限與合規。"]],
            "exam_focus": "把題目限制轉成工具與流程選擇。",
            "common_mistakes": ["只記工具名。", "忽略資料品質。"],
        },
        "L23 全科模擬": {
            "overview": "L23 模擬要把模型原理、選型、驗證、調參與治理整合。題目若給資料與目標，先判斷任務類型，再選模型與指標。",
            "concepts": [["任務判斷", "分類、回歸、分群、序列、影像等。"], ["模型比較", "比較可解釋性、資料量、成本與準確率。"], ["驗證治理", "交叉驗證、指標、漂移監控與偏誤管理。"]],
            "exam_focus": "答案要包含模型、理由、指標與風險。",
            "common_mistakes": ["看關鍵字就選模型。", "沒有說明評估指標。"],
        },
        "歷屆題與樣題": {
            "overview": "歷屆題用來校準出題語氣與陷阱。每做完一回，要把題目歸類到章節並更新錯題本。",
            "concepts": [["題型辨識", "定義題、流程題、情境題、比較題。"], ["錯題歸因", "找出錯在知識、閱讀或判斷。"], ["回測", "隔天重做錯題確認是否修正。"]],
            "exam_focus": "用歷屆題訓練速度與選項排除。",
            "common_mistakes": ["只做題不訂正。", "不分析出題模式。"],
        },
        "弱點補強與口訣速記": {
            "overview": "最後階段不再大量新增內容，而是把弱點變成口訣、比較表與錯題規則。目標是考場快速取用。",
            "concepts": [["比較表", "整理相似概念的定義、用途、限制與指標。"], ["速記卡", "每張卡只放一個概念或一個判斷規則。"], ["考前策略", "優先穩住高頻錯題與容易混淆題。"]],
            "exam_focus": "把錯題轉成考場可用的判斷規則。",
            "common_mistakes": ["考前還開新坑。", "只看筆記不回測。"],
        },
    }
)

FALLBACK_GUIDES = {
    "junior": "本日以初級考點為主，先建立名詞與流程，再用題目檢查是否能辨識正確選項。",
    "l21": "本日以 AI 技術應用與規劃為主，重點是從情境判斷技術選型、導入條件與風險控管。",
    "l22": "本日以大數據處理分析為主，重點是資料品質、統計概念、處理架構、分析工具與治理。",
    "l23": "本日以機器學習技術為主，重點是模型原理、適用場景、驗證調參與治理。",
    "final": "本日以考前整合為主，重點是限時作答、錯題歸因、易混淆觀念比較與最後弱點補強。",
}


def main() -> int:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    materials_payload = json.loads(MATERIALS_PATH.read_text(encoding="utf-8"))
    materials = materials_payload["materials"]
    section_index = _build_section_index(materials)

    days = []
    for day in plan["days"]:
        matches = _rank_sections(day, section_index)
        keywords = _keywords_from_matches(matches)
        guide = _guide_for(day, keywords)
        difficulty = _difficulty_for(day, keywords)
        assessment = _assessment_for(day, guide, difficulty)
        days.append(
            {
                **day,
                "difficulty": difficulty,
                "integratedSources": _integrated_sources(matches, materials),
                "teaching": guide,
                "assessment": assessment,
            }
        )

    payload = {
        "schema": "ipas-integrated-curriculum-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "startDate": plan["startDate"],
        "examDate": plan["examDate"],
        "examLabel": plan["examLabel"],
        "timezone": plan["timezone"],
        "totalStudyDays": plan["totalStudyDays"],
        "phases": plan["phases"],
        "days": days,
        "examDay": plan["examDay"],
        "coverage": {
            "materialCount": materials_payload["sourceCount"],
            "readableMaterials": materials_payload["readyCount"],
            "needsOcr": materials_payload["needsOcrCount"],
            "indexedSections": len(section_index),
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(days)} integrated days")
    return 0


def _build_section_index(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = []
    for material in materials:
        if material.get("status") != "ready":
            continue
        for section in material.get("sections", []):
            text = section.get("text", "")
            if not text:
                continue
            index.append(
                {
                    "materialId": material["id"],
                    "title": material["title"],
                    "category": material["category"],
                    "path": material["path"],
                    "section": section["index"],
                    "text": text,
                    "tokens": Counter(_tokens(f"{material['title']} {material['category']} {text[:1800]}")),
                }
            )
    return index


def _rank_sections(day: dict[str, Any], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query = " ".join([day["focus"], day["phase"], *day.get("chapters", [])])
    query_tokens = _tokens(query)
    material_ids = {item.get("id") for item in day.get("materials", [])}
    scored = []
    for section in sections:
        score = sum(section["tokens"].get(token, 0) for token in query_tokens)
        if section["materialId"] in material_ids:
            score += 8
        if day["phaseId"].upper() in section["title"].upper() or day["phaseId"].upper() in section["path"].upper():
            score += 4
        if score > 0:
            scored.append((score, len(section["text"]), section))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [section for _, _, section in scored[:8]]


def _tokens(text: str) -> list[str]:
    tokens = []
    for raw in TOKEN_RE.findall(text):
        token = raw.lower().strip()
        if len(token) < 2 or token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens


def _keywords_from_matches(matches: list[dict[str, Any]]) -> list[str]:
    counts: Counter[str] = Counter()
    for match in matches:
        counts.update(_tokens(match["text"][:2200]))
    return [token for token, _ in counts.most_common(10)]


def _guide_for(day: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    focus = day["focus"]
    base = FOCUS_GUIDES.get(focus)
    if not base:
        base = _generic_guide(day)

    concepts = [
        {"term": term, "explanation": explanation}
        for term, explanation in base["concepts"]
    ]
    return {
        "title": focus,
        "objectives": _objectives_for(day),
        "overview": base["overview"],
        "studyFlow": [
            "先讀整理講義，確認今天的核心問題。",
            "把重點觀念整理成自己的 3 句話。",
            "做當日練習或測驗，將錯題歸因到觀念、題幹、公式或情境判斷。",
        ],
        "keyConcepts": concepts,
        "examFocus": base["exam_focus"],
        "commonMistakes": base["common_mistakes"],
        "integratedKeywords": keywords[:8],
        "memoryHook": _memory_hook(day),
    }


def _generic_guide(day: dict[str, Any]) -> dict[str, Any]:
    chapters = "、".join(day.get("chapters", []))
    phase_note = FALLBACK_GUIDES.get(day["phaseId"], "本日以章節整合與題型判斷為主。")
    concepts = [[chapter, f"掌握「{chapter}」的定義、用途、限制與常見題型。"] for chapter in day.get("chapters", [])[:4]]
    if not concepts:
        concepts = [[day["focus"], "整理定義、適用情境、限制條件與考題判斷線索。"]]
    return {
        "overview": f"{phase_note} 今天聚焦「{day['focus']}」，章節範圍是 {chapters}。讀完後要能把概念套到情境題，而不是只背名詞。",
        "concepts": concepts,
        "exam_focus": f"看到題目時，先判斷它在問定義、流程、工具選擇、風險治理還是成效評估，再回到「{day['focus']}」的判斷框架。",
        "common_mistakes": ["只記名詞，沒有連到情境。", "看到熟悉關鍵字就急著作答，忽略題目限制條件。"],
    }


def _objectives_for(day: dict[str, Any]) -> list[str]:
    chapters = day.get("chapters", [])
    first = chapters[0] if chapters else day["focus"]
    second = chapters[1] if len(chapters) > 1 else day["phase"]
    return [
        f"能用自己的話說明「{first}」的定義與用途。",
        f"能比較「{day['focus']}」相關概念的差異與限制。",
        f"能在情境題中判斷何時使用「{second}」相關方法。",
    ]


def _difficulty_for(day: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    score = PHASE_BASE_DIFFICULTY.get(day["phaseId"], 3)
    text = " ".join([day["focus"], *day.get("chapters", []), *keywords])
    hard_terms = ["線性代數", "機率", "統計", "檢定", "svm", "dbscan", "cnn", "rnn", "參數", "治理", "部署", "串流"]
    score += min(1, sum(1 for term in hard_terms if term.lower() in text.lower()) // 2)
    score = max(1, min(5, score))
    labels = {1: "入門", 2: "基礎", 3: "中等", 4: "偏難", 5: "高難"}
    reasons = []
    if day["phaseId"] in {"l22", "l23"}:
        reasons.append("包含統計、資料處理或模型判斷，需要理解流程與適用條件。")
    if day["studyType"] in {"mock", "review"}:
        reasons.append("重點在錯題整合與限時判斷，難度來自綜合應用。")
    if not reasons:
        reasons.append("以建立概念骨架為主，先求理解再求速度。")
    return {
        "score": score,
        "label": labels[score],
        "reasons": reasons,
        "prerequisite": _prerequisite_for(day),
    }


def _prerequisite_for(day: dict[str, Any]) -> str:
    if day["phaseId"] == "foundation":
        return "不需先備數學，重點是名詞與流程。"
    if day["phaseId"] == "l22":
        return "需熟悉平均、變異、分佈、抽樣與基本資料清理概念。"
    if day["phaseId"] == "l23":
        return "需先理解監督式/非監督式學習、訓練/驗證/測試與基本統計。"
    return "需先能辨識 AI 任務類型與企業導入流程。"


def _assessment_for(day: dict[str, Any], guide: dict[str, Any], difficulty: dict[str, Any]) -> dict[str, Any]:
    weekday = day["weekday"]
    final = day["phaseId"] == "final"
    if weekday == "日":
        mode = "review"
        title = "錯題回顧，不安排新測驗"
        questions = _review_questions(day)
    elif weekday == "六" or final:
        mode = "mock"
        title = "整合測驗"
        questions = _quiz_questions(day, guide, count=6)
    elif weekday in {"二", "四"}:
        mode = "quiz"
        title = "小測驗"
        questions = _quiz_questions(day, guide, count=5)
    else:
        mode = "self_check"
        title = "自我檢核"
        questions = _quiz_questions(day, guide, count=3)

    return {
        "mode": mode,
        "title": title,
        "isFormalTest": mode in {"quiz", "mock"},
        "suggestedMinutes": 15 if mode == "self_check" else 30 if mode == "quiz" else 50,
        "questionCount": len(questions),
        "difficulty": difficulty["label"],
        "instructions": _assessment_instruction(mode),
        "questions": questions,
    }


def _quiz_questions(day: dict[str, Any], guide: dict[str, Any], count: int) -> list[dict[str, Any]]:
    concepts = _expanded_concepts(guide["keyConcepts"])
    questions = []
    for index in range(count):
        concept = concepts[index % len(concepts)]
        term = concept["term"]
        qid = f"{day['date']}-q{index + 1}"
        questions.append(
            _build_choice_question(
                qid=qid,
                question_type="short_answer" if index % 3 == 0 else "scenario",
                prompt=_question_prompt(day, term, index),
                correct_text=concept["explanation"],
                distractor_texts=_distractor_texts(concepts, concept, index),
                seed=qid,
            )
        )
    return questions


def _question_prompt(day: dict[str, Any], term: str, index: int) -> str:
    if day["focus"] == "考試範圍盤點與診斷":
        prompts = [
            f"關於「{term}」如何幫助你安排讀書順序，下列敘述何者正確？",
            "若診斷後發現 L22 與 L23 都偏弱，下列何者是較合理的下週時間分配？",
            "下列何者最容易讓你誤判讀書進度，需要特別修正？",
        ]
        return prompts[index % len(prompts)]
    if index % 3 == 0:
        return f"關於「{term}」在「{day['focus']}」中的用途，下列敘述何者正確？"
    if index % 3 == 1:
        return f"情境題：企業想導入與「{day['focus']}」相關的 AI 專案，下列敘述何者正確？"
    return f"比較題：下列關於「{term}」的敘述，何者正確？"


def _distractor_texts(concepts: list[dict[str, str]], concept: dict[str, str], index: int) -> list[str]:
    others = [item["explanation"] for item in concepts if item["term"] != concept["term"]]
    picks: list[str] = []
    for step in range(1, len(others) + 1):
        candidate = others[(index + step) % len(others)]
        if candidate not in picks:
            picks.append(candidate)
        if len(picks) == 3:
            break
    while len(picks) < 3:
        picks.append("此為干擾選項，內容與本題重點不符。")
    return picks


def _build_choice_question(
    qid: str,
    question_type: str,
    prompt: str,
    correct_text: str,
    distractor_texts: list[str],
    seed: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    options = [(correct_text, True)] + [(text, False) for text in distractor_texts]
    rng.shuffle(options)
    keys = ["A", "B", "C", "D"]
    labeled = []
    correct_key = ""
    for key, (text, is_correct) in zip(keys, options):
        labeled.append({"key": key, "text": text})
        if is_correct:
            correct_key = key
    return {
        "id": qid,
        "type": "multiple_choice",
        "questionType": question_type,
        "prompt": prompt,
        "options": labeled,
        "correctKey": correct_key,
        "answer": f"正確答案 {correct_key}：{correct_text}",
    }


def _expanded_concepts(concepts: list[dict[str, str]]) -> list[dict[str, str]]:
    extras = [
        {"term": "資料條件", "explanation": "先確認資料來源、品質、代表性、標籤與限制，才能判斷方法是否可行。"},
        {"term": "評估指標", "explanation": "指標必須對應任務與商業目標，例如分類、回歸、分群與生成式任務各不相同。"},
        {"term": "風險治理", "explanation": "高風險應用需考慮隱私、偏誤、可解釋性、監控、回滾與人類審核。"},
        {"term": "適用限制", "explanation": "每種方法都有資料量、可解釋性、成本、延遲與維運限制。"},
    ]
    seen = {item["term"] for item in concepts}
    expanded = list(concepts)
    for item in extras:
        if item["term"] not in seen:
            expanded.append(item)
    return expanded


def _review_questions(day: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _build_choice_question(
            qid=f"{day['date']}-r1",
            question_type="reflection",
            prompt="整理本週錯題時，下列做法何者最有效？",
            correct_text="把錯題分群，優先補同一錯因（觀念、題幹、公式、情境判斷）重複出現的部分。",
            distractor_texts=[
                "只重做同樣的題目，不分析錯因。",
                "直接跳過錯題，先做新題目累積題量。",
                "只記錄最終答案代號，不寫下錯誤原因。",
            ],
            seed=f"{day['date']}-r1",
        ),
        _build_choice_question(
            qid=f"{day['date']}-r2",
            question_type="reflection",
            prompt="訂正錯題時，下列敘述何者正確？",
            correct_text="重寫題幹關鍵字與正確判斷流程，並寫出排除其他選項的理由。",
            distractor_texts=[
                "只需要記住正確選項代號即可。",
                "不需要重看題幹，直接背答案。",
                "選項對了就好，不必說明排除其他選項的理由。",
            ],
            seed=f"{day['date']}-r2",
        ),
    ]


def _assessment_instruction(mode: str) -> str:
    if mode == "mock":
        return "請限時作答，逐題選出正確選項，作答完立刻核對並把錯題加入錯題本。"
    if mode == "quiz":
        return "先選出你認為正確的選項，再核對正確答案與解析，確認是否漏掉條件、限制或風險。"
    if mode == "review":
        return "今天不追求新題量，重點是把錯題變成可反覆核對的選擇題規則。"
    return "選出正確選項；若答錯，回到教學資訊的重點觀念再複習一次。"


def _integrated_sources(matches: list[dict[str, Any]], materials: list[dict[str, Any]]) -> dict[str, Any]:
    material_map = {material["id"]: material for material in materials}
    seen = []
    for match in matches:
        if match["materialId"] not in seen:
            seen.append(match["materialId"])
    titles = [material_map[mid]["title"] for mid in seen[:5] if mid in material_map]
    return {
        "materialCount": len(seen),
        "sectionCount": len(matches),
        "titles": titles,
    }


def _memory_hook(day: dict[str, Any]) -> str:
    if day["phaseId"] == "l22":
        return "大數據題先問：資料從哪來、怎麼清、怎麼存、怎麼算、怎麼治理。"
    if day["phaseId"] == "l23":
        return "模型題先問：任務、資料、指標、驗證、風險。"
    if day["phaseId"] == "l21":
        return "導入題先問：需求、資料、技術、效益、風險、維運。"
    return "基礎題先問：定義、用途、限制、例子。"


if __name__ == "__main__":
    raise SystemExit(main())
