const STATIC_BANK_URL = './question-bank.json';
const STORAGE_KEY = 'gtestQuizOfflineStateV1';
const letters = ['A', 'B', 'C', 'D'];
const policies = ['adaptive_mastery_v2', 'chapter_balanced_v1', 'random_baseline_v1'];

const DIFFICULTY_LEVEL = {
  basic: 0.25,
  standard: 0.55,
  advanced: 0.85,
};

const EXPECTED_TIME_MS = {
  basic: 22000,
  standard: 36000,
  advanced: 52000,
};

const reasonLabels = {
  new: '新規',
  weak_chapter: '弱点',
  review_due: '復習',
  balanced_practice: '調整',
  baseline_random: 'random',
  chapter_balance: '章バランス',
};

let state = loadState();
let bank = [];
let bankMeta = {};
let current = null;
let answered = false;
let startedAt = 0;

const el = (id) => document.getElementById(id);
const startBtn = el('startBtn');
const refreshBtn = el('refreshBtn');
const logoutBtn = el('logoutBtn');
const nextBtn = el('nextBtn');
const syncBtn = el('syncBtn');
const exportBtn = el('exportBtn');
const importBtn = el('importBtn');
const importFile = el('importFile');
const policySelect = el('policySelect');
const loadingBar = el('loadingBar');
const scoreEl = el('score');
const apiState = el('apiState');
const sessionState = el('sessionState');
const queueState = el('queueState');
const requestState = el('requestState');
const authState = el('authState');
const questionEl = el('question');
const resultEl = el('result');
const choicesEl = el('choices');
const chapterEl = el('chapter');
const difficultyEl = el('difficulty');
const reasonEl = el('reason');
const totalEl = el('total');
const accuracyEl = el('accuracy');
const streakEl = el('streak');
const correctTotalEl = el('correctTotal');
const answerTotalEl = el('answerTotal');
const dueNowEl = el('dueNow');
const trackedItemsEl = el('trackedItems');
const masteryList = el('masteryList');
const timeline = el('timeline');

function defaultState() {
  return {
    learnerId: '',
    createdAt: '',
    policyVariant: 'adaptive_mastery_v2',
    answers: [],
    learningItems: {},
    recent: [],
  };
}

function loadState() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (!parsed || typeof parsed !== 'object') return defaultState();
    return {
      ...defaultState(),
      ...parsed,
      policyVariant: policies.includes(parsed.policyVariant) ? parsed.policyVariant : 'adaptive_mastery_v2',
      answers: Array.isArray(parsed.answers) ? parsed.answers : [],
      learningItems: parsed.learningItems && typeof parsed.learningItems === 'object' ? parsed.learningItems : {},
      recent: Array.isArray(parsed.recent) ? parsed.recent : [],
    };
  } catch (_error) {
    return defaultState();
  }
}

function persistState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  requestState.textContent = `saved ${new Date().toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}`;
}

function newLearnerId() {
  if (crypto.randomUUID) return `L-${crypto.randomUUID().slice(0, 8)}`;
  return `L-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 6)}`;
}

function ensureLearner() {
  if (!state.learnerId) {
    state.learnerId = newLearnerId();
    state.createdAt = nowIso();
    persistState();
  }
  sessionState.textContent = state.learnerId;
  authState.textContent = 'ローカル学習プロファイル';
}

function nowIso() {
  return new Date().toISOString();
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(String(value).replace(' ', 'T'));
  return Number.isNaN(date.getTime()) ? null : date;
}

function pct(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function wilsonLowerBound(correct, total, z = 1.28) {
  if (total <= 0) return 0;
  const p = correct / total;
  const denom = 1 + ((z * z) / total);
  const centre = p + ((z * z) / (2 * total));
  const margin = z * Math.sqrt((p * (1 - p) + (z * z) / (4 * total)) / total);
  return clamp((centre - margin) / denom, 0, 1);
}

function difficultyValue(label) {
  return DIFFICULTY_LEVEL[label] ?? DIFFICULTY_LEVEL.standard;
}

function difficultyLabel(target) {
  return Object.keys(DIFFICULTY_LEVEL).reduce((best, label) => (
    Math.abs(DIFFICULTY_LEVEL[label] - target) < Math.abs(DIFFICULTY_LEVEL[best] - target) ? label : best
  ), 'standard');
}

function responseTimeScore(elapsedMs, difficulty) {
  if (!elapsedMs || elapsedMs <= 0) return 0.55;
  const expected = EXPECTED_TIME_MS[difficulty] ?? EXPECTED_TIME_MS.standard;
  const ratio = clamp(elapsedMs / expected, 0.15, 3.0);
  return clamp(1.2 - (ratio * 0.35), 0, 1);
}

function gradeAnswer(correct, elapsedMs, difficulty) {
  if (!correct) return responseTimeScore(elapsedMs, difficulty) >= 0.8 ? 2 : 1;
  const speed = responseTimeScore(elapsedMs, difficulty);
  if (speed >= 0.82) return 5;
  if (speed >= 0.55) return 4;
  return 3;
}

function retentionProbability(dueAt, intervalHours, now = new Date()) {
  const due = parseDate(dueAt);
  if (!due || intervalHours <= 0) return 0.35;
  const elapsedSinceLast = Math.max(0, intervalHours - ((due.getTime() - now.getTime()) / 3600000));
  const stability = Math.max(1, intervalHours);
  return clamp(Math.exp(-elapsedSinceLast / stability), 0, 1);
}

function updateSchedule(previous, correct, elapsedMs, difficulty, now = new Date()) {
  const grade = gradeAnswer(correct, elapsedMs, difficulty);
  let easiness = Number(previous?.easiness ?? 2.3);
  let intervalHours = Number(previous?.interval_hours ?? 0);
  let repetitions = Number(previous?.repetitions ?? 0);
  let lapses = Number(previous?.lapses ?? 0);
  const difficultyPenalty = 1.0 + (difficultyValue(difficulty) * 0.18);

  if (grade < 3) {
    lapses += 1;
    repetitions = 0;
    easiness = Math.max(1.3, easiness - 0.22);
    intervalHours = grade === 2 ? 2.0 : 0.5;
  } else {
    repetitions += 1;
    const speedBonus = (responseTimeScore(elapsedMs, difficulty) - 0.55) * 0.18;
    easiness = clamp(easiness + (0.08 * (grade - 3)) + speedBonus, 1.3, 2.85);
    if (repetitions === 1) intervalHours = 12.0;
    else if (repetitions === 2) intervalHours = 48.0;
    else intervalHours = Math.max(24.0, intervalHours * easiness / difficultyPenalty);
  }

  const due = new Date(now.getTime() + (intervalHours * 3600000));
  const dueAt = due.toISOString();
  return {
    easiness: Number(easiness.toFixed(4)),
    interval_hours: Number(intervalHours.toFixed(2)),
    due_at: dueAt,
    repetitions,
    lapses,
    last_grade: grade,
    retention: retentionProbability(dueAt, intervalHours, now),
    updated_at: now.toISOString(),
  };
}

function questionById() {
  return new Map(bank.map((question) => [question.id, question]));
}

function buildQuestionSummary() {
  const summary = {};
  for (const row of state.answers) {
    const qid = row.question_id;
    if (!qid) continue;
    const item = summary[qid] || {
      attempts: 0,
      wrongs: 0,
      last_answered_at: '',
      last_correct: false,
      elapsedValues: [],
    };
    item.attempts += 1;
    if (!row.correct) item.wrongs += 1;
    item.last_answered_at = row.answered_at || item.last_answered_at;
    item.last_correct = Boolean(row.correct);
    if (Number.isFinite(Number(row.elapsed_ms))) item.elapsedValues.push(Number(row.elapsed_ms));
    summary[qid] = item;
  }

  for (const [qid, item] of Object.entries(summary)) {
    const elapsed = item.elapsedValues || [];
    item.avg_elapsed_ms = elapsed.length ? elapsed.reduce((a, b) => a + b, 0) / elapsed.length : 0;
    delete item.elapsedValues;
    if (state.learningItems[qid]) Object.assign(item, state.learningItems[qid]);
  }

  for (const [qid, item] of Object.entries(state.learningItems)) {
    summary[qid] = { attempts: 0, wrongs: 0, last_answered_at: '', last_correct: false, avg_elapsed_ms: 0, ...summary[qid], ...item };
  }
  return summary;
}

function buildChapterMastery() {
  const byId = questionById();
  const grouped = {};
  for (const row of state.answers) {
    const chapterId = row.chapter_id;
    if (!chapterId) continue;
    const q = byId.get(row.question_id);
    const difficulty = q?.difficulty || 'standard';
    const bucket = grouped[chapterId] || { total: 0, correct: 0, elapsed: [], difficultySum: 0 };
    bucket.total += 1;
    if (row.correct) bucket.correct += 1;
    if (Number.isFinite(Number(row.elapsed_ms))) bucket.elapsed.push(Number(row.elapsed_ms));
    bucket.difficultySum += difficultyValue(difficulty);
    grouped[chapterId] = bucket;
  }

  return Object.fromEntries(Object.entries(grouped).map(([chapterId, values]) => {
    const total = values.total;
    const correct = values.correct;
    const avgElapsed = values.elapsed.length ? values.elapsed.reduce((a, b) => a + b, 0) / values.elapsed.length : 0;
    const difficultyAvg = total ? values.difficultySum / total : DIFFICULTY_LEVEL.standard;
    const accuracy = total ? correct / total : 0;
    const conservative = wilsonLowerBound(correct, total);
    const confidence = Math.min(1, total / 12);
    const speed = responseTimeScore(avgElapsed, difficultyLabel(difficultyAvg));
    const mastery = clamp((conservative * 0.55) + (accuracy * 0.25 * confidence) + (speed * 0.20), 0, 1);
    return [chapterId, {
      chapter_id: chapterId,
      total,
      correct,
      wrongs: total - correct,
      accuracy,
      avg_elapsed_ms: avgElapsed,
      mastery,
      priority: 1 - mastery,
    }];
  }));
}

function reviewUrgency(summary, now = new Date()) {
  const attempts = Number(summary?.attempts ?? 0);
  if (attempts <= 0) return 0.35;
  const dueAt = parseDate(summary?.due_at);
  if (dueAt) {
    const deltaHours = (now.getTime() - dueAt.getTime()) / 3600000;
    if (deltaHours >= 0) return Math.min(1, 0.65 + (deltaHours / 48));
    return Math.max(0, 0.45 + (deltaHours / 48));
  }
  const lastAt = parseDate(summary?.last_answered_at);
  if (!lastAt) return 0.2;
  const ageHours = Math.max(0, (now.getTime() - lastAt.getTime()) / 3600000);
  return clamp(ageHours / 24, 0, 1);
}

function questionMastery(summary, difficulty, now = new Date()) {
  const attempts = Number(summary?.attempts ?? 0);
  const wrongs = Number(summary?.wrongs ?? 0);
  const correct = Math.max(0, attempts - wrongs);
  const difficultyLevel = difficultyValue(difficulty);
  const priorStrength = 3.0;
  const prior = 0.68 - (difficultyLevel * 0.22);
  const posterior = attempts ? (correct + (prior * priorStrength)) / (attempts + priorStrength) : 0;
  const conservative = attempts ? wilsonLowerBound(correct, attempts) : 0;
  const speed = responseTimeScore(Number(summary?.avg_elapsed_ms ?? 0), difficulty);
  const scheduledPenalty = 0.22 * reviewUrgency(summary, now);
  return clamp((posterior * 0.52) + (conservative * 0.28) + (speed * 0.20) - scheduledPenalty, 0, 1);
}

function targetDifficulty(totalAnswers, accuracy) {
  if (totalAnswers < 8 || accuracy < 0.58) return DIFFICULTY_LEVEL.basic;
  if (accuracy < 0.78) return DIFFICULTY_LEVEL.standard;
  return DIFFICULTY_LEVEL.advanced;
}

function reasonForScore(unseen, weakness, review) {
  if (review >= 0.68 && !unseen) return 'review_due';
  if (weakness >= 0.58 && !unseen) return 'weak_chapter';
  if (unseen) return 'new';
  return 'balanced_practice';
}

function stats() {
  const total = state.answers.length;
  const correct = state.answers.filter((row) => row.correct).length;
  let streak = 0;
  for (let i = state.answers.length - 1; i >= 0; i -= 1) {
    if (!state.answers[i].correct) break;
    streak += 1;
  }
  return {
    total_answers: total,
    correct_answers: correct,
    accuracy: total ? correct / total : 0,
    current_streak: streak,
  };
}

function learningPlan() {
  const chapters = Object.values(buildChapterMastery()).sort((a, b) => (a.mastery - b.mastery) || (b.total - a.total));
  const now = new Date();
  const items = Object.values(state.learningItems);
  const dueNow = items.filter((item) => {
    const due = parseDate(item.due_at);
    return due && due <= now;
  });
  return {
    weakest: chapters.slice(0, 5),
    schedule: {
      tracked_items: items.length,
      due_now: dueNow.length,
    },
  };
}

function selectNextQuestion() {
  if (!bank.length) return null;
  const summary = buildQuestionSummary();
  const s = stats();
  const policyVariant = policies.includes(state.policyVariant) ? state.policyVariant : 'adaptive_mastery_v2';

  if (policyVariant === 'random_baseline_v1') {
    const question = bank[Math.floor(Math.random() * bank.length)];
    return { question, learning: { reason: 'baseline_random', policy_variant: policyVariant } };
  }

  if (policyVariant === 'chapter_balanced_v1') {
    const attemptsByChapter = {};
    for (const row of state.answers) attemptsByChapter[row.chapter_id] = (attemptsByChapter[row.chapter_id] || 0) + 1;
    const minAttempts = Math.min(...bank.map((question) => attemptsByChapter[question.chapter_id] || 0));
    const candidates = bank.filter((question) => (attemptsByChapter[question.chapter_id] || 0) === minAttempts);
    const unseen = candidates.filter((question) => Number(summary[question.id]?.attempts ?? 0) === 0);
    const pool = unseen.length ? unseen : candidates;
    const question = pool[Math.floor(Math.random() * pool.length)];
    return { question, learning: { reason: 'chapter_balance', policy_variant: policyVariant } };
  }

  const now = new Date();
  const chapterMastery = buildChapterMastery();
  const target = targetDifficulty(s.total_answers, s.accuracy);
  let best = null;

  for (const question of bank) {
    const item = summary[question.id] || {};
    const attempts = Number(item.attempts ?? 0);
    const unseen = attempts === 0;
    const chapter = chapterMastery[question.chapter_id] || {};
    const qMastery = attempts ? questionMastery(item, question.difficulty, now) : 0;
    const weakness = Number(chapter.priority ?? (unseen ? 0.72 : 0.35));
    const review = reviewUrgency(item, now);
    const difficultyFit = 1 - Math.min(1, Math.abs(difficultyValue(question.difficulty) - target));
    const score = (
      (!unseen ? 0.38 * review : 0)
      + (unseen ? 0.22 : 0)
      + (0.24 * weakness)
      + (0.12 * (1 - qMastery))
      + (0.08 * difficultyFit)
      + Math.random() * 0.015
    );
    if (!best || score > best.score) {
      best = {
        score,
        question,
        learning: {
          reason: reasonForScore(unseen, weakness, review),
          policy_variant: 'adaptive_mastery_v2',
          question_mastery: qMastery,
          review_urgency: review,
        },
      };
    }
  }
  return best;
}

function setBusy(isBusy) {
  loadingBar.hidden = !isBusy;
  startBtn.disabled = isBusy || !bank.length;
  nextBtn.disabled = isBusy || !current || !answered;
  [...choicesEl.querySelectorAll('button')].forEach((button) => { button.disabled = isBusy || answered; });
}

function setScore() {
  const s = stats();
  scoreEl.textContent = `${s.correct_answers} / ${s.total_answers}`;
}

function renderStats() {
  const s = stats();
  const learning = learningPlan();
  totalEl.textContent = `回答 ${s.total_answers}`;
  accuracyEl.textContent = pct(s.accuracy);
  streakEl.textContent = String(s.current_streak);
  correctTotalEl.textContent = String(s.correct_answers);
  answerTotalEl.textContent = String(s.total_answers);
  dueNowEl.textContent = String(learning.schedule.due_now);
  trackedItemsEl.textContent = String(learning.schedule.tracked_items);
  setScore();
  renderMastery(learning.weakest);
}

function renderMastery(items) {
  masteryList.innerHTML = '';
  if (!items.length) {
    masteryList.innerHTML = '<div class="empty">回答後に表示されます</div>';
    return;
  }
  for (const item of items.slice(0, 5)) {
    const mastery = clamp(Number(item.mastery) || 0, 0, 1);
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `
      <div class="row-label"><span title="${escapeHtml(item.chapter_id)}">${escapeHtml(item.chapter_id)}</span><strong>${pct(mastery)}</strong></div>
      <div class="bar"><span style="width:${Math.round(mastery * 100)}%"></span></div>
    `;
    masteryList.appendChild(row);
  }
}

function renderTimeline() {
  timeline.innerHTML = '';
  if (!state.recent.length) {
    timeline.innerHTML = '<div class="empty">履歴なし</div>';
    return;
  }
  for (const item of state.recent.slice(0, 7)) {
    const row = document.createElement('div');
    row.className = 'timeline';
    row.innerHTML = `
      <span class="dot ${item.correct ? 'correct' : 'wrong'}"></span>
      <span>${escapeHtml(item.label)}</span>
      <strong>${item.correct ? '正解' : '不正解'}</strong>
    `;
    timeline.appendChild(row);
  }
}

function renderQuestion(selection) {
  current = selection.question;
  answered = false;
  choicesEl.innerHTML = '';
  chapterEl.textContent = [current.chapter_group, current.chapter_id].filter(Boolean).join(' / ');
  questionEl.textContent = current.question;
  difficultyEl.textContent = current.difficulty || '-';
  const reason = selection.learning?.reason || 'balanced_practice';
  reasonEl.textContent = reasonLabels[reason] || reason;
  reasonEl.dataset.tone = reason === 'weak_chapter' ? 'red' : reason === 'new' ? 'green' : reason === 'review_due' ? 'amber' : 'blue';
  current.choices.forEach((choice, index) => {
    const button = document.createElement('button');
    button.className = 'choice';
    button.type = 'button';
    button.setAttribute('aria-pressed', 'false');
    button.innerHTML = `<span class="key">${letters[index]}</span><span class="choice-text"></span>`;
    button.querySelector('.choice-text').textContent = choice;
    button.addEventListener('click', () => answer(index));
    choicesEl.appendChild(button);
  });
  startedAt = performance.now();
  resultEl.textContent = '選択肢を選んでください。';
  nextBtn.disabled = true;
}

function answer(index) {
  if (answered || !current) return;
  answered = true;
  const elapsedMs = Math.round(performance.now() - startedAt);
  const correct = index === current.correct_index;
  const now = nowIso();
  const previous = state.learningItems[current.id] || null;
  const schedule = updateSchedule(previous, correct, elapsedMs, current.difficulty);
  state.learningItems[current.id] = {
    question_id: current.id,
    chapter_id: current.chapter_id,
    ...schedule,
  };
  state.answers.push({
    question_id: current.id,
    chapter_id: current.chapter_id,
    selected_index: index,
    correct,
    elapsed_ms: elapsedMs,
    answered_at: now,
  });
  state.recent.unshift({ correct, label: current.chapter_id, answered_at: now });
  state.recent = state.recent.slice(0, 20);
  persistState();

  const buttons = [...choicesEl.querySelectorAll('.choice')];
  buttons.forEach((button, choiceIndex) => {
    button.disabled = true;
    if (choiceIndex === current.correct_index) button.classList.add('is-correct');
    if (choiceIndex === index && !correct) button.classList.add('is-wrong');
  });
  buttons[index]?.setAttribute('aria-pressed', 'true');
  resultEl.textContent = `${correct ? '正解' : `不正解（正答 ${letters[current.correct_index]}）`}\n\n${current.explanation}`;
  nextBtn.disabled = false;
  renderStats();
  renderTimeline();
}

function startLearning() {
  ensureLearner();
  policySelect.value = state.policyVariant;
  const selection = selectNextQuestion();
  if (!selection) {
    questionEl.textContent = '問題データを読み込めませんでした。';
    resultEl.textContent = 'question-bank.json を確認してください。';
    return;
  }
  renderQuestion(selection);
  renderStats();
  renderTimeline();
  persistState();
}

async function loadQuestionBank() {
  setBusy(true);
  try {
    const response = await fetch(STATIC_BANK_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    bank = Array.isArray(payload) ? payload : payload.questions || [];
    bankMeta = Array.isArray(payload) ? {} : payload.meta || {};
    if (!bank.length) throw new Error('empty bank');
    apiState.textContent = '完全オフライン';
    apiState.dataset.tone = 'green';
    queueState.textContent = `問題 ${bank.length}`;
    authState.textContent = `問題バンク ${bankMeta.generated_at ? bankMeta.generated_at.slice(0, 10) : 'ready'}`;
    startLearning();
  } catch (error) {
    apiState.textContent = '読込失敗';
    apiState.dataset.tone = 'red';
    questionEl.textContent = '問題を読み込めませんでした。';
    resultEl.textContent = `${STATIC_BANK_URL} を同じ場所に配置してください。`;
  } finally {
    setBusy(false);
  }
}

function saveLocalState() {
  ensureLearner();
  persistState();
  renderStats();
  renderTimeline();
  resultEl.textContent = '保存しました。';
}

function resetState() {
  if (!confirm('この端末の学習履歴をリセットします。')) return;
  state = defaultState();
  localStorage.removeItem(STORAGE_KEY);
  current = null;
  answered = false;
  choicesEl.innerHTML = '';
  resultEl.textContent = 'リセットしました。';
  renderStats();
  renderTimeline();
  startLearning();
}

function exportAccount() {
  ensureLearner();
  const bundle = {
    schema_version: 'gtest_quiz_offline_export_v1',
    exported_at: nowIso(),
    state,
  };
  const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `gtest-quiz-offline-${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

async function importAccount(file) {
  if (!file) return;
  const payload = JSON.parse(await file.text());
  if (payload.schema_version === 'gtest_quiz_offline_export_v1' && payload.state) {
    state = { ...defaultState(), ...payload.state };
  } else {
    const importedAnswers = Array.isArray(payload.answers) ? payload.answers : [];
    const importedItems = Array.isArray(payload.learning_items) ? payload.learning_items : [];
    state.answers = importedAnswers.map(normalizeImportedAnswer).filter(Boolean);
    state.learningItems = Object.fromEntries(importedItems.filter((item) => item && item.question_id).map((item) => [item.question_id, item]));
    state.recent = state.answers.slice(-20).reverse().map((item) => ({ correct: item.correct, label: item.chapter_id, answered_at: item.answered_at }));
  }
  state.policyVariant = policies.includes(state.policyVariant) ? state.policyVariant : 'adaptive_mastery_v2';
  ensureLearner();
  persistState();
  policySelect.value = state.policyVariant;
  renderStats();
  renderTimeline();
  startLearning();
}

function normalizeImportedAnswer(row) {
  const q = bank.find((item) => item.id === row.question_id);
  if (!q) return null;
  const selectedIndex = clamp(Number(row.selected_index ?? 0), 0, 3);
  return {
    question_id: q.id,
    chapter_id: q.chapter_id,
    selected_index: selectedIndex,
    correct: selectedIndex === q.correct_index,
    elapsed_ms: clamp(Number(row.elapsed_ms ?? 0), 0, 3600000),
    answered_at: row.answered_at || nowIso(),
  };
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

startBtn.addEventListener('click', startLearning);
refreshBtn.addEventListener('click', saveLocalState);
logoutBtn.addEventListener('click', resetState);
nextBtn.addEventListener('click', startLearning);
syncBtn.addEventListener('click', saveLocalState);
exportBtn.addEventListener('click', exportAccount);
importBtn.addEventListener('click', () => importFile.click());
importFile.addEventListener('change', () => importAccount(importFile.files[0]).catch((error) => {
  resultEl.textContent = `インポートできませんでした。\n${error.message || error}`;
}));
policySelect.addEventListener('change', () => {
  state.policyVariant = policySelect.value;
  persistState();
  startLearning();
});
window.addEventListener('keydown', (event) => {
  if (!current || answered || event.altKey || event.ctrlKey || event.metaKey) return;
  const index = ['a', 'b', 'c', 'd', '1', '2', '3', '4'].indexOf(event.key.toLowerCase());
  if (index < 0) return;
  event.preventDefault();
  answer(index % 4);
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./service-worker.js').catch(() => {});
}

policySelect.value = state.policyVariant;
renderStats();
renderTimeline();
loadQuestionBank();
