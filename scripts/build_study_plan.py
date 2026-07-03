"""Generate a daily iPAS study plan for the GitHub Pages app."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATERIAL_ROOT = ROOT / "iPAS教材"
OUTPUT = ROOT / "docs" / "study_plan.json"

START_DATE = date(2026, 7, 3)
EXAM_DATE = date(2026, 10, 30)


@dataclass(frozen=True)
class Topic:
    title: str
    chapters: list[str]
    keywords: list[str]


@dataclass(frozen=True)
class Phase:
    id: str
    title: str
    start: date
    end: date
    goal: str
    topics: list[Topic]


PHASES = [
    Phase(
        id="foundation",
        title="基礎盤點與初級核心",
        start=date(2026, 7, 3),
        end=date(2026, 7, 16),
        goal="建立 AI 基礎、生成式 AI、企業導入與負責任 AI 的共同語言。",
        topics=[
            Topic("考試範圍盤點與診斷", ["初級/中級範圍", "個人弱點表"], ["學習指引", "初級能力培訓", "官方測驗", "考試樣題"]),
            Topic("AI 基礎名詞與生成式 AI 字彙", ["名詞解釋", "Q&A"], ["名詞", "Q&A", "生成式"]),
            Topic("AI 基礎理論", ["AI 定義", "資料、模型、推論"], ["單元一", "AI基礎理論", "人工智慧基礎"]),
            Topic("產業常見 AI 應用", ["辨識、預測、推薦、生成"], ["單元二", "產業常見"]),
            Topic("負責任 AI", ["公平性", "透明性", "隱私", "治理"], ["單元三", "負責任"]),
            Topic("機器學習技術概覽", ["監督式/非監督式", "模型流程"], ["單元四", "機器學習"]),
            Topic("企業導入 AI 策略", ["需求盤點", "PoC", "導入流程"], ["單元七", "企業導入", "AI導入"]),
        ],
    ),
    Phase(
        id="junior",
        title="初級科目一與科目二",
        start=date(2026, 7, 17),
        end=date(2026, 8, 6),
        goal="把初級兩科讀完一輪，建立可快速答題的基礎題感。",
        topics=[
            Topic("人工智慧基礎概論", ["AI 發展", "資料與演算法", "應用情境"], ["人工智慧基礎概論", "科目1"]),
            Topic("搜尋、推論與知識表示", ["問題求解", "推論", "知識庫"], ["人工智慧基礎", "學習指引"]),
            Topic("機器學習基本流程", ["資料切分", "訓練/驗證/測試", "過擬合"], ["機器學習", "單元四"]),
            Topic("生成式 AI 應用與規劃", ["LLM", "RAG", "Prompt", "導入評估"], ["生成式", "科目二"]),
            Topic("提示設計與導入流程", ["需求定義", "資料準備", "驗收指標"], ["Prompt", "AI導入", "流程"]),
            Topic("風險、隱私與治理", ["個資", "資安", "責任歸屬"], ["負責任", "合規", "隱私"]),
            Topic("初級模擬題與錯題整理", ["科目一測驗", "科目二測驗", "錯題本"], ["模擬考題", "初級", "考題"]),
        ],
    ),
    Phase(
        id="l21",
        title="中級 L21 人工智慧技術應用與規劃",
        start=date(2026, 8, 7),
        end=date(2026, 8, 30),
        goal="熟悉 AI 技術選型、NLP、導入評估、部署與情境題判斷。",
        topics=[
            Topic("L21 總覽與考點地圖", ["技術應用", "規劃流程", "考點整理"], ["L21", "人工智慧技術應用與規劃", "核心考點"]),
            Topic("AI 相關技術應用", ["辨識", "預測", "推薦", "生成"], ["L211", "AI 相關技術"]),
            Topic("自然語言處理技術", ["斷詞", "向量化", "語意搜尋", "RAG"], ["L21101", "自然語言"]),
            Topic("AI 導入評估規劃", ["場景選擇", "效益評估", "風險"], ["L212", "導入評估"]),
            Topic("AI 技術應用與系統部署", ["API", "MLOps", "監控", "上線"], ["L213", "系統部署"]),
            Topic("企業 AI 素養與金融 AI 指引", ["治理", "模型風險", "監管"], ["企業應具備", "金融業", "AI指引"]),
            Topic("L21 情境題演練", ["案例判斷", "方案選型", "錯題回顧"], ["L21", "情境"]),
        ],
    ),
    Phase(
        id="l22",
        title="中級 L22 大數據處理分析與應用",
        start=date(2026, 8, 31),
        end=date(2026, 9, 22),
        goal="掌握統計、資料處理、分析工具、資料治理與大數據應用。",
        topics=[
            Topic("機率統計基礎", ["隨機變數", "分佈", "抽樣"], ["L221", "機率", "統計"]),
            Topic("敘述性統計與資料摘要", ["平均/變異", "相關", "視覺化"], ["L22101", "敘述性統計"]),
            Topic("資料清理與整合", ["缺失值", "異常值", "JOIN", "轉換"], ["缺失值", "異常值", "數據整合", "數據轉換"]),
            Topic("大數據處理技術", ["批次", "串流", "Kafka", "Spark"], ["L222", "處理技術", "Kafka", "Spark"]),
            Topic("大數據分析方法與工具", ["回歸", "分群", "Bootstrap", "檢定"], ["L223", "分析方法", "Bootstrap", "回歸"]),
            Topic("時間序列與預測", ["ARIMA", "Prophet", "LSTM/GRU"], ["ARIMA", "Prophet", "LSTM"]),
            Topic("資料儲存、合規與成本", ["Parquet", "Partition", "GDPR", "ISO"], ["儲存", "合規", "Partition", "GDPR"]),
            Topic("大數據在 AI 之應用", ["特徵工程", "高維資料", "隱私技術"], ["L224", "高維", "非結構"]),
            Topic("L22 情境題演練", ["資料流程設計", "工具選擇", "錯題回顧"], ["L22", "情境"]),
        ],
    ),
    Phase(
        id="l23",
        title="中級 L23 機器學習技術與應用",
        start=date(2026, 9, 23),
        end=date(2026, 10, 13),
        goal="把模型原理、建模參數、驗證調參與治理串成可答題的決策流程。",
        topics=[
            Topic("線性代數與 ML 基礎", ["向量", "矩陣", "距離", "降維"], ["L2302", "線性代數"]),
            Topic("機率統計之 ML 應用", ["估計", "檢定", "分佈假設"], ["L23101", "機率", "統計"]),
            Topic("線性迴歸與邏輯迴歸", ["損失函數", "正則化", "分類閾值"], ["線性迴歸", "邏輯回歸", "正則化"]),
            Topic("樹模型與集成方法", ["決策樹", "隨機森林", "XGBoost"], ["決策樹", "隨機森林", "Xgboost"]),
            Topic("KNN、SVM、DBSCAN", ["距離", "核函數", "密度分群"], ["KNN", "SVM", "DBSCAN"]),
            Topic("CNN、RNN 與深度學習", ["卷積", "序列", "特徵抽取"], ["CNN", "RNN"]),
            Topic("建模、驗證與參數調整", ["交叉驗證", "Grid/Random Search", "指標"], ["L2303", "模型驗證", "參數"]),
            Topic("機器學習治理", ["漂移", "監控", "可解釋性", "偏誤"], ["L2304", "治理", "偏誤"]),
            Topic("L23 情境模擬題", ["模型選擇", "錯題回顧", "弱點補強"], ["L23", "情境", "模擬"]),
        ],
    ),
    Phase(
        id="final",
        title="考前總複習與模擬考",
        start=date(2026, 10, 14),
        end=date(2026, 10, 29),
        goal="用模擬考、考古題與錯題本把弱點壓到最低。",
        topics=[
            Topic("初級與中級總複習", ["初級科目一/二", "L21/L22/L23 快速掃描"], ["總複習", "重點", "學習指引"]),
            Topic("L21 全科模擬", ["技術選型", "導入評估", "部署"], ["L21", "考題", "情境"]),
            Topic("L22 全科模擬", ["統計", "處理", "分析", "治理"], ["L22", "考題", "情境"]),
            Topic("L23 全科模擬", ["模型", "驗證", "治理", "情境"], ["L23", "考題", "模擬"]),
            Topic("歷屆題與樣題", ["考古題", "樣題", "錯題本"], ["考古題", "樣題", "測驗"]),
            Topic("弱點補強與口訣速記", ["錯題前 30 題", "公式/名詞卡", "易混淆比較"], ["比較表", "名詞", "錯題"]),
        ],
    ),
]


def main() -> int:
    materials = _material_catalog()
    days = []
    current = START_DATE
    day_index = 1
    while current < EXAM_DATE:
        phase = _phase_for(current)
        offset = (current - phase.start).days
        topic = phase.topics[offset % len(phase.topics)]
        weekday = current.weekday()
        is_saturday = weekday == 5
        is_sunday = weekday == 6
        days.append(_day_entry(current, day_index, phase, topic, materials, is_saturday, is_sunday))
        current += timedelta(days=1)
        day_index += 1

    payload = {
        "schema": "ipas-study-plan-v1",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "startDate": START_DATE.isoformat(),
        "examDate": EXAM_DATE.isoformat(),
        "examLabel": "2026-10-30",
        "timezone": "Asia/Taipei",
        "totalStudyDays": len(days),
        "phases": [
            {
                "id": phase.id,
                "title": phase.title,
                "start": phase.start.isoformat(),
                "end": phase.end.isoformat(),
                "goal": phase.goal,
            }
            for phase in PHASES
        ],
        "days": days,
        "examDay": {
            "date": EXAM_DATE.isoformat(),
            "title": "考試日",
            "tasks": ["只看錯題本與速記卡", "確認證件、文具、交通與到場時間", "睡眠優先"],
        },
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(days)} study days")
    return 0


def _material_catalog() -> list[dict[str, str]]:
    if not MATERIAL_ROOT.exists():
        return []
    records = []
    for path in sorted(MATERIAL_ROOT.rglob("*"), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        records.append(
            {
                "id": material_id(relative),
                "title": path.stem,
                "path": relative,
                "name": path.name,
            }
        )
    return records


def _phase_for(target: date) -> Phase:
    for phase in PHASES:
        if phase.start <= target <= phase.end:
            return phase
    raise ValueError(f"no phase for {target}")


def _day_entry(
    target: date,
    day_index: int,
    phase: Phase,
    topic: Topic,
    materials: list[dict[str, str]],
    is_saturday: bool,
    is_sunday: bool,
) -> dict:
    if is_sunday:
        study_type = "review"
        minutes = 90
        quiz = {"type": "錯題回顧", "questions": 30, "source": "本週錯題與標記題"}
        deliverables = ["整理本週錯題 10 題", "更新 10 張速記卡", "回看本週最低分章節"]
    elif is_saturday:
        study_type = "mock"
        minutes = 150
        quiz = {"type": "週測驗", "questions": 50, "source": "本週章節 + 模擬/考古題"}
        deliverables = ["完成週測驗", "訂正錯題並標註原因", "列出下週前三個弱點"]
    else:
        study_type = "learn"
        minutes = 120
        quiz = {"type": "章節測驗", "questions": 25, "source": "對應章節題庫/NotebookLM/RAG"}
        deliverables = ["完成章節筆記", "完成章節測驗", "錯題至少訂正 5 題"]

    if phase.id == "final" and not is_sunday:
        minutes = 150
        quiz = {"type": "模擬考/考古題", "questions": 80 if not is_saturday else 100, "source": "考古題、樣題、模擬試題"}
        deliverables = ["計時作答", "完成錯題訂正", "把易混淆觀念寫成比較表"]

    return {
        "date": target.isoformat(),
        "weekday": _weekday_zh(target.weekday()),
        "dayIndex": day_index,
        "phaseId": phase.id,
        "phase": phase.title,
        "studyType": study_type,
        "minutes": minutes,
        "focus": topic.title,
        "chapters": topic.chapters,
        "materials": _match_materials(materials, topic.keywords, limit=4),
        "quiz": quiz,
        "deliverables": deliverables,
    }


def _match_materials(
    materials: list[dict[str, str]],
    keywords: list[str],
    *,
    limit: int,
) -> list[dict[str, str]]:
    scored = []
    for material in materials:
        haystack = f"{material['title']} {material['path']}".lower()
        score = sum(1 for keyword in keywords if keyword.lower() in haystack)
        if score:
            scored.append((score, len(material["title"]), material))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]["path"]))
    return [
        {"id": material["id"], "title": material["title"], "path": material["path"]}
        for _, _, material in scored[:limit]
    ]


def material_id(relative_path: str) -> str:
    from hashlib import sha1

    return "src_" + sha1(relative_path.encode("utf-8")).hexdigest()[:14]


def _weekday_zh(index: int) -> str:
    return ["一", "二", "三", "四", "五", "六", "日"][index]


if __name__ == "__main__":
    raise SystemExit(main())
