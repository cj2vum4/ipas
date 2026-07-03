const PLAN_URL = "curriculum.json";
const MATERIALS_URL = "study_materials.json";
const INDEX_URL = "rag_index.json";
const DEFAULT_DIMENSIONS = 2048;
const LOCAL_MISTAKES_KEY = "ipas-mistakes-v1";
const PROGRESS_KINDS = ["read", "quiz", "review"];
const encoder = new TextEncoder();

const els = {
  tabButtons: document.querySelectorAll(".tab-button"),
  plannerView: document.querySelector("#plannerView"),
  materialsView: document.querySelector("#materialsView"),
  recordsView: document.querySelector("#recordsView"),
  ragView: document.querySelector("#ragView"),
  authForm: document.querySelector("#authForm"),
  authEmail: document.querySelector("#authEmail"),
  loginButton: document.querySelector("#loginButton"),
  logoutButton: document.querySelector("#logoutButton"),
  authLabel: document.querySelector("#authLabel"),
  syncStatus: document.querySelector("#syncStatus"),
  planStatus: document.querySelector("#planStatus"),
  daysLeft: document.querySelector("#daysLeft"),
  completedDays: document.querySelector("#completedDays"),
  todayMinutes: document.querySelector("#todayMinutes"),
  selectedTitle: document.querySelector("#selectedTitle"),
  selectedMeta: document.querySelector("#selectedMeta"),
  todayCard: document.querySelector("#todayCard"),
  weekMeta: document.querySelector("#weekMeta"),
  weekList: document.querySelector("#weekList"),
  phaseList: document.querySelector("#phaseList"),
  materialStatus: document.querySelector("#materialStatus"),
  materialSearch: document.querySelector("#materialSearch"),
  materialCategory: document.querySelector("#materialCategory"),
  materialListMeta: document.querySelector("#materialListMeta"),
  materialList: document.querySelector("#materialList"),
  readerTitle: document.querySelector("#readerTitle"),
  readerMeta: document.querySelector("#readerMeta"),
  materialReader: document.querySelector("#materialReader"),
  recordSyncMeta: document.querySelector("#recordSyncMeta"),
  recordCompletedDays: document.querySelector("#recordCompletedDays"),
  recordMistakeCount: document.querySelector("#recordMistakeCount"),
  recordOpenMistakes: document.querySelector("#recordOpenMistakes"),
  mistakeMeta: document.querySelector("#mistakeMeta"),
  mistakeList: document.querySelector("#mistakeList"),
  form: document.querySelector("#askForm"),
  question: document.querySelector("#question"),
  topK: document.querySelector("#topK"),
  endpoint: document.querySelector("#apiEndpoint"),
  askButton: document.querySelector("#askButton"),
  indexStatus: document.querySelector("#indexStatus"),
  sourceCount: document.querySelector("#sourceCount"),
  chunkCount: document.querySelector("#chunkCount"),
  runStatus: document.querySelector("#runStatus"),
  scoreStatus: document.querySelector("#scoreStatus"),
  answer: document.querySelector("#answer"),
  sources: document.querySelector("#sources"),
};

const state = {
  plan: null,
  materials: null,
  materialPromise: null,
  selectedMaterialId: null,
  selectedDate: null,
  index: null,
  indexPromise: null,
  dimensions: DEFAULT_DIMENSIONS,
  supabase: null,
  session: null,
  syncing: false,
  progress: new Map(),
  mistakes: new Map(),
  selectedOptions: new Map(),
};

init();

async function init() {
  els.endpoint.value = localStorage.getItem("ipas-rag-endpoint") || "";
  loadLocalMistakes();
  setupSupabase();
  bindTabs();
  bindAuthEvents();
  bindPlannerEvents();
  bindMaterialsEvents();
  bindRecordsEvents();
  bindRagEvents();
  await loadPlan();
  await hydrateSession();
  renderRecords();
}

function bindTabs() {
  els.tabButtons.forEach((button) => {
    button.addEventListener("click", async () => {
      const target = button.dataset.tab;
      els.tabButtons.forEach((item) => item.classList.toggle("active", item === button));
      els.plannerView.classList.toggle("active", target === "planner");
      els.materialsView.classList.toggle("active", target === "materials");
      els.recordsView.classList.toggle("active", target === "records");
      els.ragView.classList.toggle("active", target === "rag");
      if (target === "materials") {
        await loadMaterials();
      }
      if (target === "records") {
        renderRecords();
      }
      if (target === "rag") {
        await loadRagIndex();
      }
    });
  });
}

function switchTab(target) {
  els.tabButtons.forEach((button) => {
    const active = button.dataset.tab === target;
    button.classList.toggle("active", active);
  });
  els.plannerView.classList.toggle("active", target === "planner");
  els.materialsView.classList.toggle("active", target === "materials");
  els.recordsView.classList.toggle("active", target === "records");
  els.ragView.classList.toggle("active", target === "rag");
  if (target === "records") {
    renderRecords();
  }
}

function bindAuthEvents() {
  els.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.supabase) {
      setSyncStatus("Supabase 尚未設定");
      return;
    }
    const email = els.authEmail.value.trim();
    if (!email) {
      return;
    }
    els.loginButton.disabled = true;
    setSyncStatus("登入連結寄送中");
    const { error } = await state.supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.href.split("#")[0] },
    });
    els.loginButton.disabled = false;
    setSyncStatus(error ? error.message : "已寄出登入連結，請檢查信箱");
  });

  els.logoutButton.addEventListener("click", async () => {
    if (!state.supabase) {
      return;
    }
    await state.supabase.auth.signOut();
    state.session = null;
    updateAuthUi();
    renderRecords();
  });
}

function bindPlannerEvents() {
  document.addEventListener("change", async (event) => {
    const input = event.target;
    if (!input.matches("[data-progress-date][data-progress-kind]")) {
      return;
    }
    await updateProgress(input.dataset.progressDate, input.dataset.progressKind, input.checked);
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-select-date]");
    if (!button) {
      return;
    }
    state.selectedDate = button.dataset.selectDate;
    renderPlanner();
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-open-material]");
    if (!button) {
      return;
    }
    state.selectedMaterialId = button.dataset.openMaterial;
    switchTab("materials");
    await loadMaterials();
    renderMaterials();
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-option-select]");
    if (!button) {
      return;
    }
    const date = button.dataset.date;
    const questionIndex = Number.parseInt(button.dataset.questionIndex, 10);
    state.selectedOptions.set(mistakeKey(date, questionIndex), button.dataset.optionKey);
    renderPlanner();
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-mistake-toggle]");
    if (!button) {
      return;
    }
    const date = button.dataset.date;
    const questionIndex = Number.parseInt(button.dataset.questionIndex, 10);
    const question = getQuestion(date, questionIndex);
    if (!question) {
      return;
    }
    await setMistake(date, questionIndex, question, !hasMistake(date, questionIndex));
  });

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-mistake-resolved]");
    if (!button) {
      return;
    }
    const date = button.dataset.date;
    const questionIndex = Number.parseInt(button.dataset.questionIndex, 10);
    const mistake = state.mistakes.get(mistakeKey(date, questionIndex));
    if (!mistake) {
      return;
    }
    await updateMistake(date, questionIndex, { resolved: !mistake.resolved });
  });
}

function bindMaterialsEvents() {
  els.materialSearch.addEventListener("input", renderMaterials);
  els.materialCategory.addEventListener("change", renderMaterials);
  els.materialList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-material-id]");
    if (!button) {
      return;
    }
    state.selectedMaterialId = button.dataset.materialId;
    renderMaterials();
  });
}

function bindRecordsEvents() {
  els.mistakeList.addEventListener("click", async (event) => {
    const openButton = event.target.closest("[data-open-mistake-date]");
    if (openButton) {
      state.selectedDate = openButton.dataset.openMistakeDate;
      switchTab("planner");
      renderPlanner();
      return;
    }

    const resolvedButton = event.target.closest("[data-record-resolved]");
    if (resolvedButton) {
      await updateMistake(resolvedButton.dataset.date, Number.parseInt(resolvedButton.dataset.questionIndex, 10), {
        resolved: resolvedButton.dataset.nextResolved === "1",
      });
      return;
    }

    const removeButton = event.target.closest("[data-record-remove]");
    if (removeButton) {
      const date = removeButton.dataset.date;
      const questionIndex = Number.parseInt(removeButton.dataset.questionIndex, 10);
      const question = getQuestion(date, questionIndex);
      await setMistake(date, questionIndex, question, false);
    }
  });

  els.mistakeList.addEventListener("change", async (event) => {
    const input = event.target;
    if (!input.matches("[data-mistake-note]")) {
      return;
    }
    await updateMistake(input.dataset.date, Number.parseInt(input.dataset.questionIndex, 10), {
      note: input.value.trim(),
    });
  });
}

function bindRagEvents() {
  els.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const question = els.question.value.trim();
    if (!question) {
      return;
    }
    await loadRagIndex();
    if (!state.index) {
      return;
    }

    const mode = new FormData(els.form).get("mode");
    const topK = clamp(Number.parseInt(els.topK.value, 10) || 5, 1, 12);
    localStorage.setItem("ipas-rag-endpoint", els.endpoint.value.trim());

    setBusy(true, "Searching");
    const matches = search(question, topK);
    renderSources(matches);

    if (mode === "search") {
      els.answer.innerHTML = matches.length
        ? matches.map((match, index) => answerSnippet(match, index)).join("")
        : '<p class="empty-state">No matching chunks.</p>';
      setBusy(false, "Ready");
      return;
    }

    if (!matches.length) {
      els.answer.innerHTML = '<p class="empty-state">No matching chunks.</p>';
      setBusy(false, "Ready");
      return;
    }

    setBusy(true, "Generating");
    try {
      const answer = await askApi(question, matches);
      els.answer.innerHTML = paragraphs(answer.answer || "");
      els.runStatus.textContent = answer.model || "Ready";
    } catch (error) {
      els.answer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
      setBusy(false, "Ready");
    } finally {
      els.askButton.disabled = false;
    }
  });
}

async function loadPlan() {
  try {
    const response = await fetch(PLAN_URL, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    state.plan = await response.json();
    loadLocalProgress();
    state.selectedDate = pickInitialDate();
    renderPlanner();
    renderRecords();
  } catch (error) {
    els.planStatus.textContent = "Study plan not found";
    els.todayCard.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
}

function renderPlanner() {
  if (!state.plan) {
    return;
  }
  const selected = dayByDate(state.selectedDate) || state.plan.days[0];
  const examDate = parseDate(state.plan.examDate);
  const today = parseDate(todayIso());
  const left = Math.max(0, dateDiff(today, examDate));
  const completed = state.plan.days.filter((day) => isDayComplete(day.date)).length;

  els.planStatus.textContent = `Exam ${state.plan.examLabel}`;
  els.daysLeft.textContent = `${left} 天`;
  els.completedDays.textContent = `${completed} / ${state.plan.totalStudyDays}`;
  els.todayMinutes.textContent = `${selected.minutes} 分`;
  els.selectedTitle.textContent = selected.date === todayIso() ? "今日進度" : "選取日期";
  els.selectedMeta.textContent = `Day ${selected.dayIndex} / ${selected.weekday}`;
  els.todayCard.innerHTML = dayCard(selected);

  renderWeek(selected.date);
  renderPhases();
  renderRecords();
}

function renderWeek(anchorDate) {
  const days = state.plan.days;
  const startIndex = Math.min(
    Math.max(days.findIndex((day) => day.date === anchorDate), 0),
    Math.max(days.length - 7, 0),
  );
  const visible = days.slice(startIndex, startIndex + 7);
  els.weekMeta.textContent = `${visible[0]?.date || "--"} +7`;
  els.weekList.innerHTML = visible.map(weekItem).join("");
}

function renderPhases() {
  els.phaseList.innerHTML = state.plan.phases
    .map((phase) => {
      const days = state.plan.days.filter((day) => day.phaseId === phase.id);
      const done = days.filter((day) => isDayComplete(day.date)).length;
      const percent = days.length ? Math.round((done / days.length) * 100) : 0;
      return `
        <article class="phase-item">
          <div class="phase-topline">
            <strong>${escapeHtml(phase.title)}</strong>
            <span>${percent}%</span>
          </div>
          <div class="progress-track"><span style="width:${percent}%"></span></div>
          <p>${escapeHtml(phase.start)} - ${escapeHtml(phase.end)}</p>
          <p>${escapeHtml(phase.goal)}</p>
        </article>
      `;
    })
    .join("");
}

function dayCard(day) {
  const teaching = day.teaching || {};
  const difficulty = day.difficulty || {};
  const assessment = day.assessment || {};
  const sources = day.integratedSources || { materialCount: 0, sectionCount: 0, titles: [] };

  return `
    <div class="day-heading">
      <div>
        <span class="phase-pill">${escapeHtml(day.phase)}</span>
        <h3>${escapeHtml(day.focus)}</h3>
      </div>
      <strong>${escapeHtml(day.date)}</strong>
    </div>
    <div class="difficulty-strip">
      <span>難度 ${difficulty.score || "--"} / 5</span>
      <strong>${escapeHtml(difficulty.label || "未標示")}</strong>
      <em>${escapeHtml(difficulty.prerequisite || "")}</em>
    </div>
    <div class="chapter-list">
      ${day.chapters.map((chapter) => `<span>${escapeHtml(chapter)}</span>`).join("")}
    </div>
    <div class="task-block">
      <h4>1. 教學資訊</h4>
      <p>${escapeHtml(teaching.overview || "")}</p>
      <ul class="objective-list">
        ${(teaching.objectives || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    </div>
    <div class="task-block">
      <h4>重點觀念</h4>
      <div class="concept-grid">
        ${(teaching.keyConcepts || [])
          .map(
            (item) => `
              <article class="concept-item">
                <strong>${escapeHtml(item.term)}</strong>
                <p>${escapeHtml(item.explanation)}</p>
              </article>
            `,
          )
          .join("")}
      </div>
    </div>
    <div class="task-block">
      <h4>考點與易錯提醒</h4>
      <p>${escapeHtml(teaching.examFocus || "")}</p>
      <ul>${(teaching.commonMistakes || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    <div class="task-block">
      <h4>2. 測驗 / 練習</h4>
      <p>${escapeHtml(assessment.title || day.quiz?.type || "")}：${assessment.questionCount || day.quiz?.questions || 0} 題，${assessment.suggestedMinutes || 0} 分鐘</p>
      <p>${escapeHtml(assessment.instructions || day.quiz?.source || "")}</p>
      <div class="question-list">
        ${(assessment.questions || []).map((question, index) => questionItem(day, question, index)).join("")}
      </div>
    </div>
    <div class="check-grid">
      ${progressCheck(day.date, "read", "教學")}
      ${progressCheck(day.date, "quiz", "練習")}
      ${progressCheck(day.date, "review", "訂正")}
    </div>
    <div class="task-block">
      <h4>完成項目與整合來源</h4>
      <ul>${day.deliverables.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      <p>已整合 ${sources.materialCount} 份資料、${sources.sectionCount} 個教材段落；詳細來源可到「教材庫」查詢。</p>
    </div>
  `;
}

function questionItem(day, question, index) {
  const key = mistakeKey(day.date, index);
  const mistake = state.mistakes.get(key);
  const active = mistake ? " is-mistake" : "";
  const resolved = mistake?.resolved ? " is-resolved" : "";
  const selected = state.selectedOptions.get(key);
  const options = question.options || [];
  return `
    <details class="question-item${active}${resolved}"${mistake || selected ? " open" : ""}>
      <summary>${index + 1}. ${escapeHtml(question.prompt)}</summary>
      <div class="option-list">
        ${options.map((option) => optionButton(day.date, index, option, selected, question.correctKey)).join("")}
      </div>
      ${
        selected
          ? `<p class="option-explanation">${escapeHtml(question.answer)}</p>`
          : ""
      }
      <div class="question-actions">
        <button
          class="mistake-button${mistake ? " active" : ""}"
          type="button"
          data-mistake-toggle="1"
          data-date="${escapeHtml(day.date)}"
          data-question-index="${index}"
        >${mistake ? "已加入錯題" : "加入錯題"}</button>
        ${
          mistake
            ? `<button
                class="ghost-button"
                type="button"
                data-mistake-resolved="1"
                data-date="${escapeHtml(day.date)}"
                data-question-index="${index}"
              >${mistake.resolved ? "取消訂正" : "標記已訂正"}</button>`
            : ""
        }
      </div>
    </details>
  `;
}

function optionButton(date, index, option, selected, correctKey) {
  let state_ = "";
  if (selected) {
    if (option.key === correctKey) {
      state_ = " is-correct";
    } else if (option.key === selected) {
      state_ = " is-incorrect";
    }
  }
  return `
    <button
      class="option-button${state_}"
      type="button"
      data-option-select="1"
      data-date="${escapeHtml(date)}"
      data-question-index="${index}"
      data-option-key="${escapeHtml(option.key)}"
      ${selected ? "disabled" : ""}
    >
      <span class="option-key">${escapeHtml(option.key)}</span>
      <span class="option-text">${escapeHtml(option.text)}</span>
    </button>
  `;
}

function weekItem(day) {
  const active = day.date === state.selectedDate ? " active" : "";
  const complete = isDayComplete(day.date) ? " complete" : "";
  return `
    <button class="week-item${active}${complete}" type="button" data-select-date="${escapeHtml(day.date)}">
      <span>${escapeHtml(day.date.slice(5))} / ${escapeHtml(day.weekday)}</span>
      <strong>${escapeHtml(day.focus)}</strong>
      <em>${escapeHtml(day.difficulty?.label || "")} / ${escapeHtml(day.assessment?.title || day.quiz.type)} ${day.assessment?.questionCount || day.quiz.questions} 題</em>
    </button>
  `;
}

function progressCheck(date, key, label) {
  const checked = isProgressChecked(date, key) ? " checked" : "";
  return `
    <label class="check-item">
      <input
        type="checkbox"
        data-progress-date="${escapeHtml(date)}"
        data-progress-kind="${escapeHtml(key)}"
        ${checked}
      />
      <span>${escapeHtml(label)}</span>
    </label>
  `;
}

function setupSupabase() {
  const config = window.IPAS_CONFIG || {};
  if (!config.supabaseUrl || !config.supabaseAnonKey) {
    updateAuthUi("Supabase 未設定，本機模式");
    return;
  }
  if (!window.supabase?.createClient) {
    updateAuthUi("Supabase SDK 未載入，本機模式");
    return;
  }
  state.supabase = window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey);
  state.supabase.auth.onAuthStateChange((_event, session) => {
    void handleSession(session);
  });
  updateAuthUi();
}

async function hydrateSession() {
  if (!state.supabase) {
    updateAuthUi();
    return;
  }
  const { data, error } = await state.supabase.auth.getSession();
  if (error) {
    setSyncStatus(error.message);
    return;
  }
  await handleSession(data.session);
}

async function handleSession(session) {
  const previousUserId = state.session?.user?.id || "";
  const nextUserId = session?.user?.id || "";
  state.session = session;
  updateAuthUi();
  if (!session || !state.plan || state.syncing) {
    renderRecords();
    return;
  }
  if (previousUserId !== nextUserId || !state.syncing) {
    await syncCloudState();
  }
}

function updateAuthUi(message) {
  const email = state.session?.user?.email || "";
  els.authLabel.textContent = email || "本機模式";
  els.authForm.hidden = Boolean(state.session) || !state.supabase;
  els.logoutButton.hidden = !state.session;
  setSyncStatus(message || (state.session ? "已登入" : state.supabase ? "可登入同步" : "尚未設定同步"));
}

function setSyncStatus(message) {
  els.syncStatus.textContent = message;
  if (els.recordSyncMeta) {
    els.recordSyncMeta.textContent = message;
  }
}

function loadLocalProgress() {
  state.progress.clear();
  for (const day of state.plan?.days || []) {
    const record = {};
    for (const kind of PROGRESS_KINDS) {
      record[kind] = localStorage.getItem(progressKey(day.date, kind)) === "1";
    }
    if (PROGRESS_KINDS.some((kind) => record[kind])) {
      state.progress.set(day.date, record);
    }
  }
}

function saveLocalProgress(date, record) {
  for (const kind of PROGRESS_KINDS) {
    if (record[kind]) {
      localStorage.setItem(progressKey(date, kind), "1");
    } else {
      localStorage.removeItem(progressKey(date, kind));
    }
  }
}

function getProgressRecord(date) {
  return state.progress.get(date) || { read: false, quiz: false, review: false };
}

function isProgressChecked(date, key) {
  return Boolean(getProgressRecord(date)[key]);
}

async function updateProgress(date, kind, checked) {
  if (!PROGRESS_KINDS.includes(kind)) {
    return;
  }
  const record = { ...getProgressRecord(date), [kind]: checked, updatedAt: new Date().toISOString() };
  state.progress.set(date, record);
  saveLocalProgress(date, record);
  renderPlanner();
  try {
    await saveRemoteProgress(date, record);
  } catch (error) {
    setSyncStatus(error.message);
  }
}

async function saveRemoteProgress(date, record) {
  if (!state.supabase || !state.session) {
    return;
  }
  const { error } = await state.supabase.from("study_progress").upsert(
    {
      user_id: state.session.user.id,
      date,
      read: Boolean(record.read),
      quiz: Boolean(record.quiz),
      review: Boolean(record.review),
      updated_at: new Date().toISOString(),
    },
    { onConflict: "user_id,date" },
  );
  if (error) {
    throw error;
  }
  setSyncStatus("已同步進度");
}

function loadLocalMistakes() {
  state.mistakes.clear();
  const payload = localStorage.getItem(LOCAL_MISTAKES_KEY);
  if (!payload) {
    return;
  }
  try {
    const items = JSON.parse(payload);
    for (const item of Array.isArray(items) ? items : []) {
      const normalized = normalizeMistake(item);
      if (normalized) {
        state.mistakes.set(mistakeKey(normalized.date, normalized.questionIndex), normalized);
      }
    }
  } catch (_error) {
    localStorage.removeItem(LOCAL_MISTAKES_KEY);
  }
}

function saveLocalMistakes() {
  const items = [...state.mistakes.values()].sort(compareMistakes);
  localStorage.setItem(LOCAL_MISTAKES_KEY, JSON.stringify(items));
}

function normalizeMistake(item) {
  const date = String(item?.date || "");
  const questionIndex = Number.parseInt(item?.questionIndex ?? item?.question_index, 10);
  if (!date || Number.isNaN(questionIndex)) {
    return null;
  }
  return {
    date,
    questionIndex,
    prompt: String(item.prompt || ""),
    answer: String(item.answer || ""),
    note: String(item.note || ""),
    resolved: Boolean(item.resolved),
    updatedAt: item.updatedAt || item.updated_at || new Date().toISOString(),
  };
}

function hasMistake(date, questionIndex) {
  return state.mistakes.has(mistakeKey(date, questionIndex));
}

async function setMistake(date, questionIndex, question, shouldStore) {
  const key = mistakeKey(date, questionIndex);
  if (!shouldStore) {
    state.mistakes.delete(key);
    saveLocalMistakes();
    renderPlanner();
    renderRecords();
    try {
      await deleteRemoteMistake(date, questionIndex);
    } catch (error) {
      setSyncStatus(error.message);
    }
    return;
  }
  const mistake = {
    date,
    questionIndex,
    prompt: question?.prompt || "",
    answer: question?.answer || "",
    note: state.mistakes.get(key)?.note || "",
    resolved: false,
    updatedAt: new Date().toISOString(),
  };
  state.mistakes.set(key, mistake);
  saveLocalMistakes();
  renderPlanner();
  renderRecords();
  try {
    await saveRemoteMistake(mistake);
  } catch (error) {
    setSyncStatus(error.message);
  }
}

async function updateMistake(date, questionIndex, patch) {
  const key = mistakeKey(date, questionIndex);
  const current = state.mistakes.get(key);
  if (!current) {
    return;
  }
  const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
  state.mistakes.set(key, next);
  saveLocalMistakes();
  renderPlanner();
  renderRecords();
  try {
    await saveRemoteMistake(next);
  } catch (error) {
    setSyncStatus(error.message);
  }
}

async function saveRemoteMistake(mistake) {
  if (!state.supabase || !state.session) {
    return;
  }
  const { error } = await state.supabase.from("quiz_mistakes").upsert(
    {
      user_id: state.session.user.id,
      date: mistake.date,
      question_index: mistake.questionIndex,
      prompt: mistake.prompt,
      answer: mistake.answer,
      note: mistake.note,
      resolved: Boolean(mistake.resolved),
      updated_at: new Date().toISOString(),
    },
    { onConflict: "user_id,date,question_index" },
  );
  if (error) {
    throw error;
  }
  setSyncStatus("已同步錯題");
}

async function deleteRemoteMistake(date, questionIndex) {
  if (!state.supabase || !state.session) {
    return;
  }
  const { error } = await state.supabase
    .from("quiz_mistakes")
    .delete()
    .eq("user_id", state.session.user.id)
    .eq("date", date)
    .eq("question_index", questionIndex);
  if (error) {
    throw error;
  }
  setSyncStatus("已移除錯題");
}

async function syncCloudState() {
  if (!state.supabase || !state.session || state.syncing) {
    return;
  }
  state.syncing = true;
  setSyncStatus("同步中");
  try {
    const userId = state.session.user.id;
    const [progressResponse, mistakesResponse] = await Promise.all([
      state.supabase.from("study_progress").select("*").eq("user_id", userId),
      state.supabase.from("quiz_mistakes").select("*").eq("user_id", userId),
    ]);
    if (progressResponse.error) {
      throw progressResponse.error;
    }
    if (mistakesResponse.error) {
      throw mistakesResponse.error;
    }
    mergeRemoteProgress(progressResponse.data || []);
    mergeRemoteMistakes(mistakesResponse.data || []);
    await flushLocalStateToCloud();
    renderPlanner();
    renderRecords();
    setSyncStatus("已同步");
  } catch (error) {
    setSyncStatus(error.message);
  } finally {
    state.syncing = false;
  }
}

function mergeRemoteProgress(rows) {
  for (const row of rows) {
    const current = getProgressRecord(row.date);
    const merged = {
      read: Boolean(current.read || row.read),
      quiz: Boolean(current.quiz || row.quiz),
      review: Boolean(current.review || row.review),
      updatedAt: row.updated_at || current.updatedAt || new Date().toISOString(),
    };
    state.progress.set(row.date, merged);
    saveLocalProgress(row.date, merged);
  }
}

function mergeRemoteMistakes(rows) {
  for (const row of rows) {
    const incoming = normalizeMistake(row);
    if (!incoming) {
      continue;
    }
    const key = mistakeKey(incoming.date, incoming.questionIndex);
    const current = state.mistakes.get(key);
    if (!current || new Date(incoming.updatedAt) >= new Date(current.updatedAt)) {
      state.mistakes.set(key, incoming);
    }
  }
  saveLocalMistakes();
}

async function flushLocalStateToCloud() {
  const progressRows = [...state.progress.entries()]
    .filter(([_date, record]) => PROGRESS_KINDS.some((kind) => record[kind]))
    .map(([date, record]) => ({
      user_id: state.session.user.id,
      date,
      read: Boolean(record.read),
      quiz: Boolean(record.quiz),
      review: Boolean(record.review),
      updated_at: record.updatedAt || new Date().toISOString(),
    }));
  if (progressRows.length) {
    const { error } = await state.supabase.from("study_progress").upsert(progressRows, {
      onConflict: "user_id,date",
    });
    if (error) {
      throw error;
    }
  }

  const mistakeRows = [...state.mistakes.values()].map((mistake) => ({
    user_id: state.session.user.id,
    date: mistake.date,
    question_index: mistake.questionIndex,
    prompt: mistake.prompt,
    answer: mistake.answer,
    note: mistake.note,
    resolved: Boolean(mistake.resolved),
    updated_at: mistake.updatedAt || new Date().toISOString(),
  }));
  if (mistakeRows.length) {
    const { error } = await state.supabase.from("quiz_mistakes").upsert(mistakeRows, {
      onConflict: "user_id,date,question_index",
    });
    if (error) {
      throw error;
    }
  }
}

function renderRecords() {
  if (!state.plan) {
    return;
  }
  const completed = state.plan.days.filter((day) => isDayComplete(day.date)).length;
  const mistakes = [...state.mistakes.values()].sort(compareMistakes);
  const openMistakes = mistakes.filter((item) => !item.resolved);

  els.recordCompletedDays.textContent = `${completed} / ${state.plan.totalStudyDays}`;
  els.recordMistakeCount.textContent = String(mistakes.length);
  els.recordOpenMistakes.textContent = String(openMistakes.length);
  els.mistakeMeta.textContent = `${mistakes.length} items`;

  if (!mistakes.length) {
    els.mistakeList.innerHTML = '<p class="empty-state">目前沒有錯題。</p>';
    return;
  }
  els.mistakeList.innerHTML = mistakes.map(mistakeItem).join("");
}

function mistakeItem(mistake) {
  const day = dayByDate(mistake.date);
  const status = mistake.resolved ? "已訂正" : "待訂正";
  return `
    <article class="mistake-item${mistake.resolved ? " resolved" : ""}">
      <div class="mistake-topline">
        <button type="button" data-open-mistake-date="${escapeHtml(mistake.date)}">
          ${escapeHtml(mistake.date)} / ${escapeHtml(day?.focus || "未找到課程")}
        </button>
        <span>${status}</span>
      </div>
      <strong>Q${mistake.questionIndex + 1}. ${escapeHtml(mistake.prompt)}</strong>
      <details>
        <summary>參考答案</summary>
        <p>${escapeHtml(mistake.answer)}</p>
      </details>
      <label>
        <span>訂正筆記</span>
        <textarea
          data-mistake-note="1"
          data-date="${escapeHtml(mistake.date)}"
          data-question-index="${mistake.questionIndex}"
          rows="3"
        >${escapeHtml(mistake.note)}</textarea>
      </label>
      <div class="mistake-actions">
        <button
          type="button"
          class="ghost-button"
          data-record-resolved="1"
          data-date="${escapeHtml(mistake.date)}"
          data-question-index="${mistake.questionIndex}"
          data-next-resolved="${mistake.resolved ? "0" : "1"}"
        >${mistake.resolved ? "改為待訂正" : "標記已訂正"}</button>
        <button
          type="button"
          class="danger-button"
          data-record-remove="1"
          data-date="${escapeHtml(mistake.date)}"
          data-question-index="${mistake.questionIndex}"
        >移除</button>
      </div>
    </article>
  `;
}

function getQuestion(date, questionIndex) {
  const day = dayByDate(date);
  return day?.assessment?.questions?.[questionIndex] || null;
}

function mistakeKey(date, questionIndex) {
  return `${date}:${questionIndex}`;
}

function compareMistakes(a, b) {
  if (a.resolved !== b.resolved) {
    return a.resolved ? 1 : -1;
  }
  if (a.date !== b.date) {
    return a.date.localeCompare(b.date);
  }
  return a.questionIndex - b.questionIndex;
}

async function loadMaterials() {
  if (state.materials) {
    return state.materials;
  }
  if (state.materialPromise) {
    return state.materialPromise;
  }
  els.materialStatus.textContent = "Loading materials...";
  state.materialPromise = fetch(MATERIALS_URL, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then((payload) => {
      state.materials = payload;
      populateMaterialCategories(payload.materials || []);
      if (!state.selectedMaterialId) {
        const firstReady = (payload.materials || []).find((item) => item.status === "ready");
        state.selectedMaterialId = firstReady?.id || payload.materials?.[0]?.id || null;
      }
      renderMaterials();
      return payload;
    })
    .catch((error) => {
      els.materialStatus.textContent = "Materials not found";
      els.materialReader.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
      state.materialPromise = null;
      return null;
    });
  return state.materialPromise;
}

function populateMaterialCategories(materials) {
  const categories = [...new Set(materials.map((item) => item.category).filter(Boolean))].sort();
  els.materialCategory.innerHTML = '<option value="">全部分類</option>' +
    categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("");
}

function renderMaterials() {
  if (!state.materials) {
    return;
  }
  const materials = state.materials.materials || [];
  const query = els.materialSearch.value.trim().toLowerCase();
  const category = els.materialCategory.value;
  const filtered = materials.filter((item) => {
    const matchesCategory = !category || item.category === category;
    const haystack = `${item.title} ${item.path} ${item.category}`.toLowerCase();
    return matchesCategory && (!query || haystack.includes(query));
  });

  els.materialStatus.textContent =
    `${state.materials.readyCount} 可讀 / ${state.materials.sourceCount} 份資料，` +
    `${state.materials.needsOcrCount} 份需 OCR`;
  els.materialListMeta.textContent = `${filtered.length} items`;
  els.materialList.innerHTML = filtered.map(materialListItem).join("") ||
    '<p class="empty-state">沒有符合條件的教材。</p>';

  const selected = materials.find((item) => item.id === state.selectedMaterialId) || filtered[0];
  if (selected) {
    state.selectedMaterialId = selected.id;
    renderMaterialReader(selected);
  }
}

function materialListItem(item) {
  const active = item.id === state.selectedMaterialId ? " active" : "";
  const status = item.status === "ready" ? `${item.sections.length} 段` : "需處理";
  return `
    <button class="material-item${active}" type="button" data-material-id="${escapeHtml(item.id)}">
      <span>${escapeHtml(item.category)} / ${escapeHtml(item.kind)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <em>${escapeHtml(status)}</em>
    </button>
  `;
}

function renderMaterialReader(item) {
  els.readerTitle.textContent = item.title;
  els.readerMeta.textContent = item.status === "ready"
    ? `${item.sections.length} 段 / ${Math.round(item.chars / 1000)}k chars`
    : item.status;

  if (item.status !== "ready") {
    els.materialReader.innerHTML = `
      <div class="reader-intro">
        <span class="warning-pill">需 OCR/手動整理</span>
        <p>${escapeHtml(item.reason || "此資料目前沒有可抽取文字。")}</p>
        <p>${escapeHtml(item.path)}</p>
        ${assetPreview(item)}
      </div>
    `;
    return;
  }

  els.materialReader.innerHTML = `
    <div class="reader-intro">
      <span class="phase-pill">${escapeHtml(item.category)}</span>
      <p>${escapeHtml(item.path)}</p>
    </div>
    ${item.sections
      .map(
        (section) => `
          <section class="reader-section">
            <h3>${escapeHtml(section.title)}</h3>
            <p>${escapeHtml(section.text).replace(/\n/g, "<br>")}</p>
          </section>
        `,
      )
      .join("")}
  `;
}

function assetPreview(item) {
  if (!item.assetPath) {
    return "";
  }
  const url = encodeURI(item.assetPath);
  if (["jpg", "jpeg", "png"].includes(item.kind)) {
    return `
      <a class="asset-button" href="${url}" target="_blank" rel="noopener">開啟原始圖片</a>
      <img class="asset-image" src="${url}" alt="${escapeHtml(item.title)}" loading="lazy" />
    `;
  }
  if (item.kind === "pdf") {
    return `<a class="asset-button" href="${url}" target="_blank" rel="noopener">開啟原始 PDF</a>`;
  }
  return `<a class="asset-button" href="${url}" target="_blank" rel="noopener">開啟原始檔</a>`;
}

async function loadRagIndex() {
  if (state.index) {
    return state.index;
  }
  if (state.indexPromise) {
    return state.indexPromise;
  }
  els.indexStatus.textContent = "Loading RAG index...";
  state.indexPromise = fetch(INDEX_URL, { cache: "no-store" })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then((payload) => {
      state.index = payload;
      state.dimensions = payload?.embedding?.dimensions || DEFAULT_DIMENSIONS;
      els.indexStatus.textContent = `Index ready: ${formatDate(payload.generated_at)}`;
      els.sourceCount.textContent = `${payload?.sources?.length || 0} sources`;
      els.chunkCount.textContent = `${payload?.chunks?.length || 0} chunks`;
      return payload;
    })
    .catch((error) => {
      els.indexStatus.textContent = "Index not found";
      els.answer.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
      state.indexPromise = null;
      return null;
    });
  return state.indexPromise;
}

function search(question, topK) {
  const query = embedSparse(question, state.dimensions);
  const scored = [];
  for (const chunk of state.index.chunks || []) {
    const score = sparseDot(query, chunk.vector);
    if (score > 0) {
      scored.push({ ...chunk, score });
    }
  }
  scored.sort((a, b) => b.score - a.score);
  els.scoreStatus.textContent = scored.length
    ? `Best ${scored[0].score.toFixed(3)}`
    : "No match";
  return scored.slice(0, topK);
}

async function askApi(question, matches) {
  const endpoint = els.endpoint.value.trim() || "/api/ask";
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      question,
      contexts: matches.map((match, index) => ({
        rank: index + 1,
        score: match.score,
        sourceTitle: match.source_title,
        sourcePath: match.source_path,
        text: match.text,
      })),
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `${response.status} ${response.statusText}`);
  }
  return payload;
}

function renderSources(matches) {
  if (!matches.length) {
    els.sources.innerHTML = '<p class="empty-state">No sources.</p>';
    return;
  }
  els.sources.innerHTML = matches
    .map(
      (match, index) => `
        <article class="source-item">
          <div class="source-title">[${index + 1}] ${escapeHtml(match.source_title)}</div>
          <div class="source-score">Score ${match.score.toFixed(3)}</div>
          <div class="source-text">${escapeHtml(match.text)}</div>
          <div class="source-meta">${escapeHtml(match.source_path)}</div>
        </article>
      `,
    )
    .join("");
}

function answerSnippet(match, index) {
  return `
    <p><strong>[${index + 1}] ${escapeHtml(match.source_title)}</strong></p>
    <p>${escapeHtml(match.text)}</p>
  `;
}

function paragraphs(text) {
  const trimmed = text.trim();
  if (!trimmed) {
    return '<p class="empty-state">No answer returned.</p>';
  }
  return trimmed
    .split(/\n{2,}/)
    .map((part) => `<p>${escapeHtml(part).replace(/\n/g, "<br>")}</p>`)
    .join("");
}

function embedSparse(text, dimensions) {
  const accum = new Map();
  for (const feature of tokenize(text)) {
    const hashed = fnv1a32(feature);
    const index = hashed % dimensions;
    const sign = hashed & 0x80000000 ? -1 : 1;
    accum.set(index, (accum.get(index) || 0) + sign);
  }
  let norm = 0;
  for (const value of accum.values()) {
    norm += value * value;
  }
  norm = Math.sqrt(norm);
  if (!norm) {
    return new Map();
  }
  const normalised = new Map();
  for (const [index, value] of accum.entries()) {
    normalised.set(index, value / norm);
  }
  return normalised;
}

function tokenize(text) {
  const normalized = text.normalize("NFKC").toLowerCase();
  const matches = normalized.match(/[a-z0-9]+|[\u4e00-\u9fff]+/gi) || [];
  const tokens = [];
  for (const token of matches) {
    if (/^[\u4e00-\u9fff]+$/.test(token)) {
      const chars = Array.from(token);
      tokens.push(...chars);
      for (let index = 0; index < chars.length - 1; index += 1) {
        tokens.push(chars[index] + chars[index + 1]);
      }
    } else {
      tokens.push(token);
    }
  }
  const features = [...tokens];
  for (let index = 0; index < tokens.length - 1; index += 1) {
    features.push(`${tokens[index]}_${tokens[index + 1]}`);
  }
  return features;
}

function fnv1a32(text) {
  let value = 0x811c9dc5;
  for (const byte of encoder.encode(text)) {
    value ^= byte;
    value = Math.imul(value, 0x01000193) >>> 0;
  }
  return value >>> 0;
}

function sparseDot(query, vector) {
  if (!vector?.indices?.length) {
    return 0;
  }
  let score = 0;
  for (let offset = 0; offset < vector.indices.length; offset += 1) {
    score += (query.get(vector.indices[offset]) || 0) * vector.values[offset];
  }
  return score;
}

function pickInitialDate() {
  const today = todayIso();
  const first = state.plan.days[0].date;
  const last = state.plan.days[state.plan.days.length - 1].date;
  if (today < first) {
    return first;
  }
  if (today > last) {
    return last;
  }
  return today;
}

function dayByDate(dateValue) {
  return state.plan.days.find((day) => day.date === dateValue);
}

function isDayComplete(dateValue) {
  return PROGRESS_KINDS.every((key) => isProgressChecked(dateValue, key));
}

function progressKey(dateValue, key) {
  return `ipas-study:${dateValue}:${key}`;
}

function setBusy(isBusy, label) {
  els.askButton.disabled = isBusy;
  els.runStatus.textContent = label;
}

function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
}

function parseDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function dateDiff(start, end) {
  return Math.ceil((end.getTime() - start.getTime()) / 86400000);
}

function pad2(value) {
  return String(value).padStart(2, "0");
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) {
    return "unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
