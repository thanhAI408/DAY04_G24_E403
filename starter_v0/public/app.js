const $ = (selector) => document.querySelector(selector);
let history = [];

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

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error(`health ${response.status}`);
    const health = await response.json();
    $("#health").textContent = `● ${health.provider} · ${health.model} · ${health.artifact_version}`;
    $("#tools").innerHTML = health.available_tools
      .map((tool) => `<span class="tool">${tool}</span>`)
      .join("");
  } catch (error) {
    $("#health").textContent = "API unavailable";
    console.error(error);
  }
}

loadHealth();

document.querySelectorAll(".samples button").forEach((button) => {
  button.onclick = () => {
    $("#input").value = button.textContent;
    $("#input").focus();
  };
});

$("#theme").onclick = () => document.body.classList.toggle("light");

$("#clear").onclick = () => {
  history = [];
  $(".chat").innerHTML = '<div class="empty"><div class="orb">✦</div><h2>Bắt đầu một phiên nghiên cứu</h2><p>Hỏi về tin tức, tweet, URL, paper hoặc nguồn trùng lặp.</p></div>';
  $("#trace").innerHTML = "";
  $("#trace-count").textContent = "No events yet";
};

$("#form").onsubmit = async (event) => {
  event.preventDefault();
  const input = $("#input");
  const text = input.value.trim();
  if (!text) return;

  addBubble(text, "user");
  history.push({ role: "user", content: text });
  input.value = "";
  addBubble("Đang nghiên cứu…", "assistant");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: history }),
    });
    const result = await response.json();
    $(".chat .assistant:last-child").textContent = result.final_response || result.error || "No response";
    history.push({ role: "assistant", content: result.final_response || "" });
    const events = result.tool_events || [];
    $("#trace-count").textContent = events.length + " event" + (events.length === 1 ? "" : "s");
    $("#trace").innerHTML = events.map(function (item) {
      const payload = JSON.stringify({ args: item.args, result: item.result }, null, 2);
      return "<details class=\"event\"><summary>" + item.tool + " - completed</summary><pre>" + payload + "</pre></details>";
    }).join("");
  } catch (error) {
    $(".chat .assistant:last-child").textContent = "Không thể kết nối API.";
    console.error(error);
  }
};
