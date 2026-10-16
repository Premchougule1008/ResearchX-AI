"use strict";

/* ═══════════════════════════════════════════════════════════════
   ResearchX — Frontend Logic
═══════════════════════════════════════════════════════════════ */

// ── DOM refs ─────────────────────────────────────────────────
const form          = document.querySelector("#research-form");
const topicInput    = document.querySelector("#topic-input");
const submitBtn     = document.querySelector("#submit-button");
const charCount     = document.querySelector("#char-count");
const homePanel     = document.querySelector("#home-panel");
const loadingPanel  = document.querySelector("#loading-panel");
const resultsPanel  = document.querySelector("#results-panel");
const errorPanel    = document.querySelector("#error-panel");
const errorMsg      = document.querySelector("#error-message");
const recentList    = document.querySelector("#recent-list");
const clearBtn      = document.querySelector("#clear-recent");
const toast         = document.querySelector("#toast");
const liveBadge     = document.querySelector("#live-badge");
const liveLabel     = document.querySelector("#live-label");
const topbarSection = document.querySelector("#topbar-section");
const navHome       = document.querySelector("#nav-home");
const navRecent     = document.querySelector("#nav-recent");

const HISTORY_KEY   = "researchx.recent-searches";
let latestResult    = null;
let toastTimer      = null;

// ── Progress simulation timers ────────────────────────────────
const STEP_TIMINGS  = [0, 8000, 22000, 40000]; // when each step activates (ms)
let progressTimers  = [];

/* ═══════════════════════════════════════════════════════════════
   MARKDOWN RENDERER  (simple but effective)
═══════════════════════════════════════════════════════════════ */
function formatInline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/(https?:\/\/[^\s<&"']+)/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
}

function renderMarkdown(raw) {
  if (!raw || !raw.trim()) return '<p class="empty-note">No content available.</p>';

  // Escape HTML entities first
  const escaped = raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  const lines = escaped.split("\n");
  let html = "";
  let inList = false;
  let inPara = false;

  const closePara = () => { if (inPara) { html += "</p>"; inPara = false; } };
  const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (!line.trim()) {
      closePara(); closeList();
      continue;
    }

    if (/^###\s/.test(line)) {
      closePara(); closeList();
      html += `<h4>${formatInline(line.replace(/^###\s/, ""))}</h4>`;
    } else if (/^##\s/.test(line)) {
      closePara(); closeList();
      html += `<h3>${formatInline(line.replace(/^##\s/, ""))}</h3>`;
    } else if (/^#\s/.test(line)) {
      closePara(); closeList();
      html += `<h2>${formatInline(line.replace(/^#\s/, ""))}</h2>`;
    } else if (/^[-•*]\s/.test(line.trimStart())) {
      closePara();
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${formatInline(line.trimStart().replace(/^[-•*]\s/, ""))}</li>`;
    } else {
      closeList();
      if (!inPara) { html += "<p>"; inPara = true; }
      else html += " ";
      html += formatInline(line.trim());
    }
  }

  closePara(); closeList();
  return html;
}

/* ═══════════════════════════════════════════════════════════════
   SCORE PARSING & RENDERING
═══════════════════════════════════════════════════════════════ */
function parseScore(feedback) {
  if (!feedback) return null;
  const m = feedback.match(/Score:\s*(\d+)\s*\/\s*10/i);
  return m ? Math.min(10, Math.max(0, parseInt(m[1], 10))) : null;
}

function renderScore(score) {
  const banner = document.querySelector("#score-banner");
  if (score === null) { banner.hidden = true; return; }

  const isHigh = score >= 7;
  const isMid  = score >= 5 && score < 7;

  banner.hidden = false;
  banner.className = `score-banner ${isHigh ? "score-high" : isMid ? "score-mid" : "score-low"}`;
  document.querySelector("#score-num").textContent = score;
  document.querySelector("#score-label").textContent =
    isHigh ? "High quality report" : isMid ? "Average quality report" : "Needs improvement";
  document.querySelector("#score-info-desc") && (
    document.querySelector("#score-info-desc").textContent = ""
  );

  const scoreDesc = document.querySelector("#score-desc");
  scoreDesc.textContent = isHigh
    ? "The critic agent approved this report. It is factual, structured and source-backed."
    : isMid
    ? "The report is reasonable but may have gaps. Cross-check sources for best results."
    : "The report did not fully pass the critic's review. Treat it as a starting point.";

  // Animate bar after a tick
  const bar = document.querySelector("#score-bar");
  bar.style.width = "0%";
  requestAnimationFrame(() => {
    setTimeout(() => { bar.style.width = `${(score / 10) * 100}%`; }, 60);
  });
}

/* ═══════════════════════════════════════════════════════════════
   AGENT PROGRESS STEPS
═══════════════════════════════════════════════════════════════ */
const AGENTS = [
  { id: "sb-agent-1", stepId: "step-1", label: "Searching…" },
  { id: "sb-agent-2", stepId: "step-2", label: "Extracting…" },
  { id: "sb-agent-3", stepId: "step-3", label: "Writing…" },
  { id: "sb-agent-4", stepId: "step-4", label: "Reviewing…" },
];

function setStepState(index, state) {
  // Main step item
  const step = document.querySelector(`#step-${index + 1}`);
  if (step) {
    step.dataset.state = state;
    const badge = step.querySelector(".step-badge");
    if (badge) badge.textContent = state === "active" ? "Running" : state === "done" ? "Done" : "Pending";
  }

  // Sidebar agent row
  const agentRow = document.querySelector(`#sb-agent-${index + 1}`);
  if (agentRow) {
    agentRow.className = `agent-row ${state === "active" ? "active" : state === "done" ? "done" : ""}`;
  }
}

function startProgress() {
  // Reset all
  AGENTS.forEach((_, i) => setStepState(i, "pending"));

  STEP_TIMINGS.forEach((delay, i) => {
    const t = setTimeout(() => {
      // Mark previous done
      if (i > 0) setStepState(i - 1, "done");
      setStepState(i, "active");
      liveLabel.textContent = AGENTS[i].label;
    }, delay);
    progressTimers.push(t);
  });
}

function completeProgress() {
  progressTimers.forEach(clearTimeout);
  progressTimers = [];
  AGENTS.forEach((_, i) => setStepState(i, "done"));
}

function resetProgress() {
  progressTimers.forEach(clearTimeout);
  progressTimers = [];
  AGENTS.forEach((_, i) => setStepState(i, "pending"));
}

/* ═══════════════════════════════════════════════════════════════
   PANEL VISIBILITY
═══════════════════════════════════════════════════════════════ */
function showPanel(name) {
  homePanel.hidden    = name !== "home";
  loadingPanel.hidden = name !== "loading";
  resultsPanel.hidden = name !== "results";
  topbarSection.textContent =
    name === "loading" ? "Research in progress…" :
    name === "results" ? "Research complete"      : "New research";

  navHome.classList.toggle("active",    name === "home");
  navRecent.classList.toggle("active",  false);

  liveBadge.hidden = name !== "loading";
}

/* ═══════════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════════ */
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    const target = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach(t => {
      t.classList.toggle("active", t.dataset.tab === target);
      t.setAttribute("aria-selected", t.dataset.tab === target ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach(p => {
      p.hidden = p.id !== `tab-${target}`;
      p.classList.toggle("active", p.id === `tab-${target}`);
    });
  });
});

/* ═══════════════════════════════════════════════════════════════
   RENDER RESULT
═══════════════════════════════════════════════════════════════ */
function renderResult(result) {
  document.querySelector("#result-topic").textContent = result.topic || "";

  // Tags
  const tagsEl = document.querySelector("#result-tags");
  tagsEl.innerHTML = "";
  const aiTag = document.createElement("span");
  aiTag.className = `result-tag ${result.fallback ? "tag-fallback" : "tag-ai"}`;
  aiTag.textContent = result.fallback ? "⚠ Quick digest" : "✓ AI generated";
  tagsEl.appendChild(aiTag);

  // Score
  const score = parseScore(result.feedback || "");
  renderScore(result.fallback ? null : score);

  // Report (markdown rendered)
  document.querySelector("#report-body").innerHTML = renderMarkdown(result.report);

  // Plain sections
  document.querySelector("#search-body").textContent  = result.search_results  || "No search results returned.";
  document.querySelector("#scraped-body").textContent = result.scraped_content  || "No in-depth content returned.";
  document.querySelector("#feedback-body").textContent = result.feedback         || "No critic review available.";

  // Reset to report tab
  document.querySelectorAll(".tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === "report");
    t.setAttribute("aria-selected", t.dataset.tab === "report" ? "true" : "false");
  });
  document.querySelectorAll(".tab-panel").forEach(p => {
    p.hidden = p.id !== "tab-report";
    p.classList.toggle("active", p.id === "tab-report");
  });
}

/* ═══════════════════════════════════════════════════════════════
   CORE RESEARCH FUNCTION
═══════════════════════════════════════════════════════════════ */
async function runResearch(topic) {
  errorPanel.hidden = true;
  showPanel("loading");
  startProgress();
  submitBtn.disabled = true;
  document.querySelector(".btn-label").textContent = "Researching…";

  try {
    const res = await fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    const payload = await res.json();

    if (!res.ok) {
      const detail = payload.detail || payload.error;
      const msg = Array.isArray(detail)
        ? detail.map(d => d.msg).join(" ")
        : detail || `Request failed (${res.status}).`;
      throw new Error(msg);
    }

    completeProgress();
    latestResult = payload;
    renderResult(payload);
    saveRecent(topic);
    showPanel("results");

    if (payload.fallback) {
      showToast("⚠ Model timed out — showing quick digest.");
    } else {
      showToast("✓ Research complete!");
    }

  } catch (err) {
    resetProgress();
    showPanel("home");
    showError(err instanceof Error ? err.message : "An unexpected error occurred.");
  } finally {
    submitBtn.disabled = false;
    document.querySelector(".btn-label").textContent = "Start researching";
  }
}

/* ═══════════════════════════════════════════════════════════════
   RECENT SEARCHES
═══════════════════════════════════════════════════════════════ */
function getRecent() {
  try {
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(saved) ? saved.filter(s => typeof s === "string") : [];
  } catch {
    return [];
  }
}

function saveRecent(topic) {
  const list = getRecent().filter(t => t.toLowerCase() !== topic.toLowerCase());
  list.unshift(topic);
  try { localStorage.setItem(HISTORY_KEY, JSON.stringify(list.slice(0, 8))); } catch { /* noop */ }
  renderRecent();
}

function renderRecent() {
  const searches = getRecent();
  clearBtn.hidden = searches.length === 0;
  recentList.replaceChildren();

  if (!searches.length) {
    const empty = document.createElement("div");
    empty.className = "recent-empty";
    empty.innerHTML = `<p>Your research history will appear here.</p>`;
    recentList.appendChild(empty);
    return;
  }

  for (const topic of searches) {
    const btn = document.createElement("button");
    btn.className = "recent-item";
    btn.type = "button";
    btn.title = `Research again: ${topic}`;
    btn.innerHTML = `<span aria-hidden="true">▤</span><span>${topic}</span>`;
    btn.addEventListener("click", () => {
      topicInput.value = topic;
      form.requestSubmit();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    recentList.appendChild(btn);
  }
}

/* ═══════════════════════════════════════════════════════════════
   TOAST & ERROR
═══════════════════════════════════════════════════════════════ */
function showToast(message, duration = 2600) {
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), duration);
}

function showError(message) {
  errorMsg.textContent = message;
  errorPanel.hidden = false;
  errorPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/* ═══════════════════════════════════════════════════════════════
   EVENT LISTENERS
═══════════════════════════════════════════════════════════════ */

// Form submit
form.addEventListener("submit", e => {
  e.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) { topicInput.focus(); return; }
  runResearch(topic);
});

// Ctrl+Enter shortcut
topicInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    form.requestSubmit();
  }
});

// Character counter
topicInput.addEventListener("input", () => {
  const len = topicInput.value.length;
  charCount.textContent = len > 0 ? `${len} / 500` : "";
  charCount.style.color = len > 450 ? "var(--red)" : len > 380 ? "var(--amber)" : "";
});

// Suggestion chips
document.querySelectorAll(".chip").forEach(chip => {
  chip.addEventListener("click", () => {
    topicInput.value = chip.dataset.topic;
    topicInput.dispatchEvent(new Event("input"));
    topicInput.focus();
  });
});

// Nav items
navHome.addEventListener("click", e => {
  e.preventDefault();
  showPanel("home");
  window.scrollTo({ top: 0, behavior: "smooth" });
});
navRecent.addEventListener("click", e => {
  e.preventDefault();
  showPanel("home");
  setTimeout(() => {
    document.querySelector("#recent-section")?.scrollIntoView({ behavior: "smooth" });
  }, 60);
});

// New research button (inside results)
document.querySelector("#new-research-btn").addEventListener("click", () => {
  showPanel("home");
  topicInput.value = "";
  charCount.textContent = "";
  topicInput.focus();
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// Copy report
document.querySelector("#copy-report").addEventListener("click", async () => {
  if (!latestResult) return;
  try {
    await navigator.clipboard.writeText(
      `${latestResult.topic}\n${"=".repeat(Math.min(latestResult.topic.length, 72))}\n\n${latestResult.report || ""}`
    );
    showToast("✓ Report copied to clipboard.");
  } catch {
    showError("Clipboard access was blocked by your browser. Select and copy the text manually.");
  }
});

// Download report
document.querySelector("#download-report").addEventListener("click", () => {
  if (!latestResult) return;
  const lines = [
    latestResult.topic,
    "=".repeat(Math.min(latestResult.topic.length, 72)),
    "",
    "RESEARCH REPORT",
    "─".repeat(40),
    latestResult.report || "",
    "",
    "CRITIC'S REVIEW",
    "─".repeat(40),
    latestResult.feedback || "",
    "",
    "SEARCH FINDINGS",
    "─".repeat(40),
    latestResult.search_results || "",
    "",
    "IN-DEPTH READING",
    "─".repeat(40),
    latestResult.scraped_content || "",
  ];
  const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url; a.download = "researchx-report.txt"; a.click();
  URL.revokeObjectURL(url);
  showToast("✓ Report downloaded.");
});

// Clear recent
clearBtn.addEventListener("click", () => {
  try { localStorage.removeItem(HISTORY_KEY); } catch { /* noop */ }
  renderRecent();
  showToast("Search history cleared.");
});

// Dismiss error
document.querySelector("#dismiss-error").addEventListener("click", () => {
  errorPanel.hidden = true;
});

/* ═══════════════════════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════════════════════ */
renderRecent();
showPanel("home");