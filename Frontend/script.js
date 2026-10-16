"use strict";

const form = document.querySelector("#research-form");
const topicInput = document.querySelector("#topic-input");
const submitButton = document.querySelector("#submit-button");
const statusPanel = document.querySelector("#research-status");
const errorPanel = document.querySelector("#error-panel");
const results = document.querySelector("#results");
const recentList = document.querySelector("#recent-list");
const clearRecentButton = document.querySelector("#clear-recent");
const toast = document.querySelector("#toast");
const historyKey = "researchx.recent-searches";
let latestResult = null;
let toastTimer;

function getRecentSearches() {
  try {
    const saved = JSON.parse(localStorage.getItem(historyKey) || "[]");
    return Array.isArray(saved) ? saved.filter((item) => typeof item === "string") : [];
  } catch (error) {
    console.warn("Could not load recent searches from local storage.", error);
    return [];
  }
}

function renderRecentSearches() {
  const searches = getRecentSearches();
  clearRecentButton.hidden = searches.length === 0;
  recentList.replaceChildren();
  if (!searches.length) {
    const empty = document.createElement("div");
    empty.className = "recent-empty";
    const mark = document.createElement("span");
    mark.className = "empty-mark";
    mark.setAttribute("aria-hidden", "true");
    mark.textContent = "↗";
    const message = document.createElement("p");
    message.textContent = "Your research history will show up here.";
    empty.append(mark, message);
    recentList.append(empty);
    return;
  }
  for (const topic of searches) {
    const button = document.createElement("button");
    button.className = "recent-item";
    button.type = "button";
    button.title = `Research again: ${topic}`;
    const icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "▤";
    const label = document.createElement("span");
    label.textContent = topic;
    button.append(icon, label);
    button.addEventListener("click", () => {
      topicInput.value = topic;
      form.requestSubmit();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    recentList.append(button);
  }
}

function saveRecentSearch(topic) {
  const searches = getRecentSearches().filter((item) => item.toLowerCase() !== topic.toLowerCase());
  searches.unshift(topic);
  try {
    localStorage.setItem(historyKey, JSON.stringify(searches.slice(0, 6)));
  } catch (error) {
    console.warn("Could not save this search to local storage.", error);
  }
  renderRecentSearches();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2400);
}

function showError(message) {
  document.querySelector("#error-message").textContent = message;
  errorPanel.hidden = false;
}

function renderResult(result) {
  document.querySelector("#result-topic").textContent = result.topic;
  document.querySelector("#report-body").textContent = result.report || "No report was returned.";
  document.querySelector("#search-body").textContent = result.search_results || "No search findings were returned.";
  document.querySelector("#scraped-body").textContent = result.scraped_content || "No in-depth reading was returned.";
  document.querySelector("#feedback-body").textContent = result.feedback || "No critic review was returned.";
  results.hidden = false;
}

async function runResearch(topic) {
  errorPanel.hidden = true;
  results.hidden = true;
  statusPanel.hidden = false;
  document.querySelector("#status-title").textContent = "Your research is underway";
  document.querySelector("#status-message").textContent = "Searching trusted sources and shaping your report. This can take a little while.";
  document.querySelector(".loading-spinner").hidden = false;
  submitButton.disabled = true;
  submitButton.querySelector(".button-label").textContent = "Researching…";
  try {
    const response = await fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });
    const payload = await response.json();
    if (!response.ok) {
      const detail = payload.error || payload.detail;
      const message = Array.isArray(detail) ? detail.map((item) => item.msg).join(" ") : detail;
      throw new Error(message || `Research request failed (${response.status}).`);
    }
    latestResult = payload;
    renderResult(payload);
    saveRecentSearch(topic);
    document.querySelector("#status-title").textContent = payload.fallback
      ? "Quick source digest ready"
      : "Research complete";
    document.querySelector("#status-message").textContent = payload.fallback
      ? "The AI model timed out. This digest contains retrieved source material, not an AI-generated report."
      : "Your report and research findings are ready below.";
    document.querySelector(".loading-spinner").hidden = true;
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error instanceof Error ? error.message : "An unexpected error occurred.");
    statusPanel.hidden = true;
  } finally {
    submitButton.disabled = false;
    submitButton.querySelector(".button-label").textContent = "Start researching";
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) {
    topicInput.focus();
    return;
  }
  runResearch(topic);
});

document.querySelectorAll(".suggestion-chip").forEach((button) => {
  button.addEventListener("click", () => {
    topicInput.value = button.dataset.topic;
    topicInput.focus();
  });
});

document.querySelector("#copy-report").addEventListener("click", async () => {
  if (!latestResult) return;
  try {
    await navigator.clipboard.writeText(`${latestResult.topic}\n\n${latestResult.report || ""}`);
    showToast("Report copied to clipboard.");
  } catch {
    showError("Clipboard access was blocked by your browser. You can select and copy the report text instead.");
  }
});

document.querySelector("#download-report").addEventListener("click", () => {
  if (!latestResult) return;
  const content = [
    latestResult.topic, "=".repeat(Math.min(latestResult.topic.length, 72)), "",
    "RESEARCH REPORT", latestResult.report || "", "",
    "CRITIC'S REVIEW", latestResult.feedback || "", "",
    "SEARCH FINDINGS", latestResult.search_results || "", "",
    "IN-DEPTH READING", latestResult.scraped_content || "",
  ].join("\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "researchx-report.txt";
  link.click();
  URL.revokeObjectURL(url);
  showToast("Your report has been downloaded.");
});

clearRecentButton.addEventListener("click", () => {
  try {
    localStorage.removeItem(historyKey);
  } catch {
    showError("Could not clear search history from this browser.");
    return;
  }
  renderRecentSearches();
  showToast("Search history cleared.");
});

document.querySelector("#dismiss-error").addEventListener("click", () => {
  errorPanel.hidden = true;
});

renderRecentSearches();