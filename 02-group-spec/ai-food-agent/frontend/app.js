/**
 * AI Food Agent — Yumi | Frontend Logic
 * Chat engine + mood selector + context bar + result cards
 */

// ── State ──────────────────────────────────────────
const state = {
  conversationHistory: [],
  sessionPreferences: {},
  weatherContext: null,
  currentMood: null,
  lastSuggestions: null,
  location: { lat: null, lon: null, source: "default" },
  isLoading: false,
};

const STORAGE_KEY = "yumi-session-v1";

// ── DOM refs ───────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const els = {
  messageList: $("#message-list"),
  chatForm: $("#chat-form"),
  chatInput: $("#chat-input"),
  btnSend: $("#btn-send"),
  btnReset: $("#btn-reset"),
  ctxWeather: $("#ctx-weather"),
  ctxTime: $("#ctx-time"),
  ctxLocation: $("#ctx-location"),
  resultsList: $("#results-list"),
  resultsBadge: $("#results-badge"),
  llmProvider: $("#llm-provider"),
  llmModel: $("#llm-model"),
  toast: $("#toast"),
};

// ── Helpers ────────────────────────────────────────
function formatMoney(val) {
  return new Intl.NumberFormat("vi-VN").format(val) + "đ";
}

function showToast(msg, duration = 2500) {
  els.toast.textContent = msg;
  els.toast.classList.add("show");
  setTimeout(() => els.toast.classList.remove("show"), duration);
}

function persistState() {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      conversationHistory: state.conversationHistory,
      sessionPreferences: state.sessionPreferences,
      currentMood: state.currentMood,
      lastSuggestions: state.lastSuggestions,
      location: state.location,
    }));
  } catch (err) {
    console.warn("Could not persist Yumi session:", err);
  }
}

function restoreState() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
    if (!saved) return false;
    state.conversationHistory = saved.conversationHistory || [];
    state.sessionPreferences = saved.sessionPreferences || {};
    state.currentMood = saved.currentMood || null;
    state.lastSuggestions = saved.lastSuggestions || null;
    state.location = saved.location || state.location;
    return state.conversationHistory.length > 0 || Boolean(state.lastSuggestions);
  } catch (err) {
    console.warn("Could not restore Yumi session:", err);
    return false;
  }
}

function cleanAIReply(reply) {
  if (!reply) return "";
  let clean = reply.trim();

  // 1. Remove markdown code blocks
  if (clean.includes("```json")) {
    clean = clean.split("```json")[1].split("```")[0].trim();
  } else if (clean.includes("```")) {
    clean = clean.split("```")[1].split("```")[0].trim();
  }

  clean = clean.trim();

  // 2. If it is a valid JSON string, parse and extract message
  if (clean.startsWith("{")) {
    try {
      const parsed = JSON.parse(clean);
      if (parsed.message) {
        return parsed.message;
      }
    } catch (err) {
      // 3. Fallback: try to extract "message" field using regex if JSON is invalid/truncated
      const msgMatch = clean.match(/"message"\s*:\s*"((?:[^"\\]|\\.)*)"/);
      if (msgMatch && msgMatch[1]) {
        return msgMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      }

      const openMatch = clean.match(/"message"\s*:\s*"([^"]*)/);
      if (openMatch && openMatch[1]) {
        return openMatch[1].replace(/\\n/g, '\n').replace(/\\"/g, '"');
      }
    }
  }

  return reply;
}

function updateTime() {
  const now = new Date();
  const h = now.getHours();
  const m = String(now.getMinutes()).padStart(2, "0");
  let period = "sáng";
  if (h >= 10 && h < 14) period = "trưa";
  else if (h >= 14 && h < 17) period = "chiều";
  else if (h >= 17 && h < 21) period = "tối";
  else if (h >= 21 || h < 5) period = "đêm khuya";

  els.ctxTime.querySelector(".ctx-text").textContent = `${h}:${m} — Bữa ${period}`;
}

// ── API calls ──────────────────────────────────────
const API_BASE = window.location.origin;

function updateLocationLabel(label) {
  els.ctxLocation.querySelector(".ctx-text").textContent = label;
}

async function requestCurrentLocation(showFeedback = false) {
  if (!navigator.geolocation) {
    if (showFeedback) showToast("Trình duyệt không hỗ trợ định vị.");
    return false;
  }

  updateLocationLabel("Đang xác định vị trí...");
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        state.location = {
          lat: position.coords.latitude,
          lon: position.coords.longitude,
          source: "gps",
        };
        updateLocationLabel(
          `Vị trí hiện tại (${state.location.lat.toFixed(4)}, ${state.location.lon.toFixed(4)})`
        );
        persistState();
        if (showFeedback) showToast("Đã cập nhật vị trí hiện tại.");
        resolve(true);
      },
      () => {
        state.location = { lat: null, lon: null, source: "default" };
        if (showFeedback) showToast("Không lấy được GPS, Yumi dùng vị trí mặc định.");
        resolve(false);
      },
      { enableHighAccuracy: false, timeout: 6000, maximumAge: 10 * 60 * 1000 }
    );
  });
}

async function fetchContext() {
  try {
    const params = new URLSearchParams();
    if (state.location.lat !== null && state.location.lon !== null) {
      params.set("lat", state.location.lat);
      params.set("lon", state.location.lon);
    }
    const query = params.toString() ? `?${params.toString()}` : "";
    const resp = await fetch(`${API_BASE}/api/context${query}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    state.weatherContext = data.weather;

    if (state.location.source !== "gps") {
      state.location = {
        lat: data.location.lat,
        lon: data.location.lon,
        source: "default",
      };
      updateLocationLabel(`${data.location.city} (mặc định)`);
    }

    // Update context bar
    const w = data.weather;
    els.ctxWeather.querySelector(".ctx-icon").textContent = w.emoji || "🌤️";
    els.ctxWeather.querySelector(".ctx-text").textContent =
      `${w.description}, ${w.temperature}°C`;

    if (w.is_mock) {
      els.ctxWeather.querySelector(".ctx-text").textContent += " (demo)";
    }
    persistState();
  } catch (err) {
    console.error("Failed to fetch context:", err);
    els.ctxWeather.querySelector(".ctx-text").textContent = "Không tải được thời tiết";
  }
}

async function sendChat(message) {
  if (state.isLoading) return;
  state.isLoading = true;
  els.btnSend.disabled = true;

  // Add user message
  const historyForRequest = state.conversationHistory.slice(-8);
  addMessage("user", message);
  state.conversationHistory.push({ role: "user", content: message });

  // Show typing indicator
  const typingEl = showTypingIndicator();

  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        lat: state.location.lat,
        lon: state.location.lon,
        provider: els.llmProvider.value,
        model: els.llmModel.value,
        conversation_history: historyForRequest,
        session_preferences: state.sessionPreferences,
        weather_context: state.weatherContext,
      }),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();

    // Remove typing
    typingEl.remove();

    // Update session preferences
    if (data.session_preferences) {
      state.sessionPreferences = data.session_preferences;
    }

    // Update weather if returned
    if (data.weather) {
      state.weatherContext = data.weather;
    }

    const cleanReply = cleanAIReply(data.reply);

    // Handle clarification
    if (data.clarification && data.clarification.needed) {
      addMessage("ai", cleanReply, data.clarification.options);
    } else {
      addMessage("ai", cleanReply);
    }

    // Handle suggestions
    if (data.suggestions && (data.suggestions.primary || data.suggestions.length > 0)) {
      renderSuggestions(data.suggestions);
    } else if (data.suggestions && !data.clarification?.needed) {
      renderSuggestions(data.suggestions);
    }

    // Save conversation
    state.conversationHistory.push({ role: "assistant", content: cleanReply });

    // Update mood display
    if (data.mood_detected && data.mood_detected !== "không rõ") {
      setMoodActive(data.mood_detected);
    }
    persistState();
  } catch (err) {
    typingEl.remove();
    addMessage("ai", `Xin lỗi, Yumi gặp lỗi: ${err.message}. Bạn thử lại nhé!`);
    console.error("Chat error:", err);
    persistState();
  } finally {
    state.isLoading = false;
    els.btnSend.disabled = false;
    els.chatInput.focus();
  }
}

// ── Messages ───────────────────────────────────────
function addMessage(role, text, clarifyOptions = []) {
  const row = document.createElement("div");
  row.className = `msg-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = `msg-bubble ${role}`;
  bubble.textContent = text;

  // Add clarification options
  if (role === "ai" && clarifyOptions.length > 0) {
    const optionsDiv = document.createElement("div");
    optionsDiv.className = "clarify-options";
    clarifyOptions.forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "clarify-btn";
      btn.textContent = opt;
      btn.addEventListener("click", () => {
        sendChat(opt);
      });
      optionsDiv.appendChild(btn);
    });
    bubble.appendChild(optionsDiv);
  }

  row.appendChild(bubble);
  els.messageList.appendChild(row);
  els.messageList.scrollTop = els.messageList.scrollHeight;
}

function showTypingIndicator() {
  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>
  `;
  els.messageList.appendChild(row);
  els.messageList.scrollTop = els.messageList.scrollHeight;
  return row;
}

// ── Suggestions / Cards ────────────────────────────
function renderSuggestions(data) {
  const primary = data.primary;
  const backups = data.backups || [];

  if (!primary) {
    els.resultsBadge.textContent = "0 kết quả";
    els.resultsList.innerHTML = `
      <div class="results-empty">
        <div class="empty-icon">🔎</div>
        <p>Chưa tìm thấy món đang mở phù hợp. Hãy thử đổi món hoặc nới ngân sách.</p>
      </div>
    `;
    state.lastSuggestions = null;
    persistState();
    return;
  }

  const total = 1 + backups.length;
  els.resultsBadge.textContent = `${total} gợi ý`;

  let html = "";

  // Primary card
  html += renderCard(primary, "primary");

  // Backup cards
  backups.forEach((b) => {
    const type = (b.backup_role || "").includes("An toàn")
      ? "safe"
      : (b.backup_role || "").includes("Nhanh")
        ? "fast"
        : "cheap";
    html += renderCard(b, type);
  });

  // Override buttons
  html += `
    <div class="override-bar">
      <button class="override-btn" data-message="Đổi món khác đi">🔄 Đổi món</button>
      <button class="override-btn" data-message="Đổi quán khác nhưng giữ loại món này">📍 Đổi quán</button>
      <button class="override-btn" data-message="Muốn ăn comfort food ngọt ngào">🍰 Ngọt ngào</button>
      <button class="override-btn" data-message="Muốn ăn cay nồng">🌶️ Cay nồng</button>
      <button class="override-btn" data-message="Muốn ăn healthy thanh đạm">🥗 Thanh đạm</button>
      <button class="override-btn" data-message="Muốn ăn nhanh gọn">⚡ Nhanh gọn</button>
    </div>
  `;

  els.resultsList.innerHTML = html;
  state.lastSuggestions = data;
  persistState();
}

function renderCard(item, type) {
  const badgeClass =
    type === "primary" ? "badge-primary"
      : type === "safe" ? "badge-safe"
        : type === "fast" ? "badge-fast"
          : "badge-cheap";

  const roleLabel = item.backup_role || "🏆 Quán chính";
  const cal = item.nutrition?.calories || item.item_calories || "N/A";
  const nutritionIsUsda = item.nutrition?.source === "usda_fdc";
  const calLabel = nutritionIsUsda ? `${cal} kcal/100g` : `${cal} kcal`;
  const qualityTags = [];
  if (item.price_is_estimated) qualityTags.push("Giá/menu ước tính");
  if (nutritionIsUsda) {
    qualityTags.push("Dinh dưỡng USDA / 100g");
  } else {
    qualityTags.push("Dinh dưỡng ước tính");
  }
  qualityTags.push("Phí ship ước tính");
  if (item.restaurant_source === "mock") qualityTags.push("Dữ liệu quán demo");
  if (item.open_status_source === "unknown_assumed_open") {
    qualityTags.push("Chưa xác minh mở cửa");
  }
  const qualityHtml = qualityTags
    .map((label) => `<span class="meta-tag meta-estimate">ℹ️ ${escapeHtml(label)}</span>`)
    .join("");

  return `
    <div class="restaurant-card" data-restaurant="${escapeHtml(item.restaurant_name)}">
      <div class="card-role-badge ${badgeClass}">${roleLabel}</div>
      <div class="card-body">
        <div class="card-title">${escapeHtml(item.item_name)}</div>
        <div class="card-restaurant">📍 ${escapeHtml(item.restaurant_name)} — ${escapeHtml(item.restaurant_address || "")}</div>
        <div class="card-meta">
          <span class="meta-tag meta-price">💵 ${formatMoney(item.item_price)}</span>
          <span class="meta-tag meta-ship">🚚 Ship ${formatMoney(item.shipping_fee)}</span>
          <span class="meta-tag meta-total">💰 Tổng ${formatMoney(item.total_cost)}</span>
          <span class="meta-tag meta-cal">🔥 ${calLabel}</span>
          <span class="meta-tag meta-rating">⭐ ${item.restaurant_rating}</span>
          <span class="meta-tag meta-time">⏱️ ${item.delivery_time_min} phút</span>
          <span class="meta-tag meta-dist">📏 ${item.distance_km} km</span>
          ${qualityHtml}
        </div>
        <div class="card-reason">${escapeHtml(item.backup_reason || "Phù hợp với yêu cầu của bạn")}</div>
        <div class="card-actions">
          <button class="btn-copy" data-copy="${escapeHtml(item.restaurant_name)}">
            📋 Copy tên quán
          </button>
        </div>
        <div class="card-score">Điểm phù hợp: ${item.score}/100</div>
      </div>
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Mood ───────────────────────────────────────────
function setMoodActive(mood) {
  $$(".mood-chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.mood === mood);
  });
  state.currentMood = mood;
  state.sessionPreferences.mood = mood;
  persistState();
}

// ── Copy to clipboard ──────────────────────────────
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showToast(`✅ Đã copy "${text}" — Dán vào ShopeeFood để tìm quán!`);
    return true;
  } catch {
    // Fallback
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
    showToast(`✅ Đã copy "${text}"`);
    return true;
  }
}

// ── Reset ──────────────────────────────────────────
function resetConversation() {
  state.conversationHistory = [];
  state.sessionPreferences = {};
  state.currentMood = null;
  state.lastSuggestions = null;

  els.messageList.innerHTML = "";
  els.resultsList.innerHTML = `
    <div class="results-empty">
      <div class="empty-icon">🍽️</div>
      <p>Nhắn tin cho Yumi để nhận gợi ý món ăn phù hợp nhé!</p>
      <div class="quick-starts">
        <button class="quick-btn" data-message="Ăn gì giờ?">🍜 Ăn gì giờ?</button>
        <button class="quick-btn" data-message="Có gì dưới 50k?">💰 Dưới 50k</button>
        <button class="quick-btn" data-message="Trời mưa ăn gì ngon?">🌧️ Trời mưa</button>
        <button class="quick-btn" data-message="Muốn ăn healthy">🥗 Healthy</button>
        <button class="quick-btn" data-message="Buồn quá muốn ăn gì ngọt">😢 Comfort food</button>
        <button class="quick-btn" data-message="Đang stress muốn ăn cay">😤 Ăn cay</button>
      </div>
    </div>
  `;
  els.resultsBadge.textContent = "0 kết quả";

  $$(".mood-chip").forEach((c) => c.classList.remove("active"));

  addMessage(
    "ai",
    "Chào bạn! Mình là Yumi 🍜 — trợ lý AI gợi ý món ăn theo ngữ cảnh.\n\nBạn có thể nhắn kiểu:\n• \"Ăn gì giờ?\" — Mình sẽ xem thời tiết, giờ giấc rồi gợi ý\n• \"Trời mưa muốn ăn phở dưới 60k\" — Cụ thể hơn\n• Hoặc chọn tâm trạng bên dưới để mình hiểu bạn hơn!\n\nBắt đầu thôi nào! 😊"
  );
  persistState();
}

function renderRestoredConversation() {
  els.messageList.innerHTML = "";
  state.conversationHistory.forEach((message) => {
    const role = message.role === "assistant" ? "ai" : "user";
    addMessage(role, message.content);
  });
  if (state.lastSuggestions) {
    renderSuggestions(state.lastSuggestions);
  }
  if (state.currentMood) {
    setMoodActive(state.currentMood);
  }
}

// ── Event Listeners ────────────────────────────────

// Model options mapping
const modelsByProvider = {
  openai: [
    { value: "gpt-4o-mini", label: "GPT-4o Mini" }
  ],
  gemini: [
    { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
    { value: "gemini-flash-latest", label: "Gemini Flash" },
    { value: "gemini-2.0-flash-lite", label: "Gemini 2.0 Flash Lite" }
  ]
};

function updateModelDropdown() {
  const provider = els.llmProvider.value;
  const models = modelsByProvider[provider] || [];
  els.llmModel.innerHTML = models
    .map(m => `<option value="${m.value}">${m.label}</option>`)
    .join("");
}

// LLM Provider change event
els.llmProvider.addEventListener("change", updateModelDropdown);

// Chat form submit
els.chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = els.chatInput.value.trim();
  if (!msg) return;
  els.chatInput.value = "";
  sendChat(msg);
});

// Reset button
els.btnReset.addEventListener("click", resetConversation);

// Location chip: allow the user to retry GPS explicitly.
els.ctxLocation.addEventListener("click", async () => {
  await requestCurrentLocation(true);
  await fetchContext();
});

// Mood chips
$$(".mood-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const mood = chip.dataset.mood;
    setMoodActive(mood);
    showToast(`Tâm trạng: ${chip.textContent}`);
  });
});

// Delegated clicks (quick buttons, copy, override, clarify)
document.addEventListener("click", (e) => {
  // Quick start buttons
  const quick = e.target.closest("[data-message]");
  if (quick && !quick.classList.contains("clarify-btn")) {
    sendChat(quick.dataset.message);
    return;
  }

  // Copy button
  const copyBtn = e.target.closest("[data-copy]");
  if (copyBtn) {
    const name = copyBtn.dataset.copy;
    copyToClipboard(name);
    copyBtn.classList.add("copied");
    copyBtn.innerHTML = "✅ Đã copy!";
    setTimeout(() => {
      copyBtn.classList.remove("copied");
      copyBtn.innerHTML = `📋 Copy tên quán`;
    }, 2000);
  }
});

// ── Init ───────────────────────────────────────────
(async function init() {
  const restored = restoreState();
  updateTime();
  setInterval(updateTime, 30000);

  updateModelDropdown();
  if (state.location.source === "gps") {
    updateLocationLabel(
      `Vị trí hiện tại (${state.location.lat.toFixed(4)}, ${state.location.lon.toFixed(4)})`
    );
  } else {
    await requestCurrentLocation(false);
  }
  await fetchContext();
  if (restored) {
    renderRestoredConversation();
  } else {
    resetConversation();
  }
})();
