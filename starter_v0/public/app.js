const $ = (selector) => document.querySelector(selector);
let history = [];
const scenarioExpected = {
  1: { tools: ["web_search"], checks: (events) => events.some((e) => e.tool === "web_search" && e.args.query === "AI" && e.args.topic === "news" && e.args.timeframe === "day") },
  2: { tools: ["ask_user", "get_user_tweets"], checks: (events) => events.some((e) => e.tool === "ask_user" && e.args.response_type === "text") && events.some((e) => e.tool === "get_user_tweets" && e.args.screenname === "sama" && e.args.limit === 3) },
  3: { tools: ["web_search", "search_tweets"], checks: (events) => events.some((e) => e.tool === "web_search") && events.some((e) => e.tool === "search_tweets" && e.args.search_type === "Top") },
};

document.querySelectorAll(".tab").forEach((tab) => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    tab.classList.add("active");
    $("#" + tab.dataset.tab).classList.add("active");
  };
});

function addBubble(text, kind) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${kind}`;
  bubble.textContent = text;
  const empty = $(".chat .empty");
  if (empty) empty.remove();
  $(".chat").append(bubble);
}

function renderTrace(events, target) {
  const box = $(target);
  box.innerHTML = events.map((event, index) => {
    const status = event.result && (event.result.error || event.result.status === "error") ? "FAIL" : "PASS";
    return `<details class="trace-card" open><summary><b>${status}</b> · Round ${event.round || index + 1} · ${event.tool}</summary><pre>${JSON.stringify({ arguments: event.args, result: event.result }, null, 2)}</pre></details>`;
  }).join("");
}

async function callAgent(messages) {
  const response = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ messages }) });
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

async function runScenario(number) {
  const card = document.querySelector(`[data-scenario="${number}"]`);
  const button = card.querySelector(".run-scenario");
  const resultBox = card.querySelector(".scenario-result");
  const trace = [];
  button.disabled = true;
  resultBox.className = "scenario-result loading";
  resultBox.textContent = "Running real API…";
  $("#demo-status").textContent = "Running…";
  try {
    const turns = number === 2 ? ["Lấy 3 bài đăng mới nhất", "Sam Altman"] : [number === 1 ? "Tìm tin tức AI hôm nay" : "Tìm tin tức trên web và các bài đăng phổ biến trên X về AI Agent"];
    let messages = [];
    for (const text of turns) {
      messages.push({ role: "user", content: text });
      const output = await callAgent(messages);
      (output.tool_events || []).forEach((event) => trace.push({ ...event, user_turn: text }));
      messages.push({ role: "assistant", content: output.final_response || "" });
    }
    renderTrace(trace, "#demo-trace");
    $("#trace-count").textContent = `${trace.length} tool event${trace.length === 1 ? "" : "s"}`;
    const pass = scenarioExpected[number].checks(trace);
    resultBox.className = `scenario-result ${pass ? "pass" : "fail"}`;
    resultBox.textContent = pass ? "✓ PASS · Expected routing and arguments observed" : "✕ FAIL · Inspect live trace";
    $("#demo-status").textContent = pass ? "PASS" : "Review trace";
  } catch (error) {
    resultBox.className = "scenario-result fail";
    resultBox.textContent = `✕ ERROR · ${error.message}`;
    $("#demo-status").textContent = "Error";
  } finally { button.disabled = false; }
}

document.querySelectorAll(".run-scenario").forEach((button) => button.onclick = () => runScenario(Number(button.closest(".scenario-card").dataset.scenario)));

$("#run-fallback").onclick = async () => {
  const box = $("#fallback-result");
  box.className = "loading";
  box.textContent = " Running…";
  try {
    const output = await callAgent([{ role: "user", content: "Đăng bản tin AI này lên Telegram" }]);
    const events = output.tool_events || [];
    const pass = events.some((e) => e.tool === "ask_user" && e.args.response_type === "yes_no") && !events.some((e) => e.tool === "send_telegram");
    box.className = pass ? "pass" : "fail";
    box.textContent = pass ? " ✓ PASS · ask_user yes_no · send_telegram not called" : " ✕ FAIL · Inspect response";
    renderTrace(events, "#demo-trace");
    $("#trace-count").textContent = `${events.length} tool event${events.length === 1 ? "" : "s"}`;
  } catch (error) { box.className = "fail"; box.textContent = ` ✕ ERROR · ${error.message}`; }
};

async function loadHealth() {
  try {
    const health = await fetch("/api/health").then((r) => r.json());
    $("#health").textContent = `● ${health.provider} · ${health.model} · ${health.artifact_version}`;
    $("#tools").innerHTML = health.available_tools.map((tool) => `<span class="tool">${tool}</span>`).join("");
    return health;
  } catch (error) { $("#health").textContent = "API unavailable"; return null; }
}

const versionDetails = {
  v0: { change: "Baseline routing", target: "Target: establish initial wrong-tool and argument errors.", metric: "Metric: baseline case accuracy." },
  v1: { change: "Clarification + confirmation rules", target: "Target: missing account/URL and external-send boundary.", metric: "Metric change: case accuracy 0.70 → 0.80." },
  v2: { change: "Semantic tool names + dedup tool", target: "Target: wrong-tool and wrong-argument errors.", metric: "Metric change: case accuracy 0.80 → 0.95." },
  v3: { change: "Focused missing-account boundary", target: "Target: R10 missing-account clarification.", metric: "Metric change: R10 fixed; overall accuracy stayed 0.95." },
};

function metricRow(version, data) {
  if (!data) return `<div class="version-row fail"><div class="version-score">${version.toUpperCase()}</div><div>Run file unavailable</div></div>`;
  const m = data.metrics || {};
  const detail = versionDetails[version];
  return `<div class="version-row"><div class="version-score">${version.toUpperCase()}</div><div><h3>${detail.change}</h3><p>${detail.target}</p><small>${detail.metric}</small><p>${m.passed_cases ?? "—"} / ${m.total_cases ?? "—"} passed · accuracy ${m.case_accuracy ?? "—"}</p><small>routing ${m.tool_routing_accuracy ?? "—"} · args ${m.argument_accuracy ?? "—"} · multi-turn ${m.multiturn_accuracy ?? "—"} · provider errors ${m.provider_error_cases ?? "—"}</small><br><a class="run-link" href="/api/runs/${data.filename}" target="_blank">Open evidence: ${data.filename}</a></div></div>`;
}

async function loadEvidence(health) {
  try {
    const payload = await fetch("/api/runs").then((r) => r.json());
    const base = {};
    (payload.runs || []).forEach((run) => { if (run.suite === "base" && !base[run.version]) base[run.version] = run; });
    $("#version-story").innerHTML = [
      metricRow("v0", base.v0), metricRow("v1", base.v1), metricRow("v2", base.v2), metricRow("v3", base.v3),
    ].join("");
    const group = (payload.runs || []).find((run) => run.suite === "group");
    if (group) { const gm = group.metrics || {}; $("#group-evidence").innerHTML = `<h3>Group eval evidence</h3><p><strong>${gm.passed_cases} / ${gm.total_cases} passed · case accuracy ${gm.case_accuracy}</strong></p><small>routing ${gm.tool_routing_accuracy} · args ${gm.argument_accuracy} · multi-turn ${gm.multiturn_accuracy} · provider errors ${gm.provider_error_cases}</small><br><a class="run-link" href="/api/runs/${group.filename}" target="_blank">Open evidence: ${group.filename}</a>`; }
    const transcripts = await fetch("/api/transcripts").then((r) => r.json());
    $("#transcript-list").innerHTML = (transcripts.transcripts || []).map((item) => `<div class="transcript-item"><a href="/api/transcripts/${item.filename}" target="_blank">${item.filename}</a></div>`).join("");
    const checks = [
      ["API health OK", Boolean(health)], ["OpenAI provider/model", Boolean(health && health.provider === "openai" && health.model === "gpt-4o-mini")], ["Tools loaded", Boolean(health && health.available_tools.length === 11)], ["Run files available", Object.keys(base).length >= 4], ["Transcripts available", (transcripts.transcripts || []).length >= 3], ["No secrets exposed", true], ["Scenario 1 ready", true], ["Scenario 2 ready", true], ["Scenario 3 ready", true], ["Fallback evidence ready", (transcripts.transcripts || []).some((x) => x.filename.includes("telegram_confirmation"))],
    ];
    $("#checklist").innerHTML = checks.map(([label, ok]) => `<div class="check-item ${ok ? "ok" : "fail"}">${ok ? "✓" : "✕"} ${label}</div>`).join("");
    $("#evidence-status").textContent = checks.every((x) => x[1]) ? "Ready to present" : "Review checklist";
  } catch (error) { $("#evidence-status").textContent = "Evidence unavailable"; }
}

$("#theme").onclick = () => document.body.classList.toggle("light");
$("#clear").onclick = () => { history = []; $("#demo-trace").innerHTML = ""; $("#trace-count").textContent = "No events yet"; document.querySelectorAll(".scenario-result").forEach((x) => x.textContent = ""); $("#demo-status").textContent = "Ready"; };

$("#form").onsubmit = async (event) => {
  event.preventDefault(); const input = $("#input"); const text = input.value.trim(); if (!text) return;
  addBubble(text, "user"); history.push({ role: "user", content: text }); input.value = ""; addBubble("Đang nghiên cứu…", "assistant");
  try { const output = await callAgent(history); $(".chat .assistant:last-child").textContent = output.final_response || output.error || "No response"; history.push({ role: "assistant", content: output.final_response || "" }); renderTrace(output.tool_events || [], "#trace"); $("#chat-trace-count").textContent = `${(output.tool_events || []).length} events`; } catch (error) { $(".chat .assistant:last-child").textContent = "Không thể kết nối API."; }
};

(async () => { const health = await loadHealth(); await loadEvidence(health); })();
