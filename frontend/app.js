const FACETS = [
  { key: "issuers", label: "发布机关" },
  { key: "categories", label: "政策类型" },
  { key: "regions", label: "适用地区" },
  { key: "tags", label: "主题标签" },
];

const MODE_HINTS = {
  smart: "短语命中 + 分词相关度 + 编辑距离容错",
  keyword: "BM25 相关度，适合宽泛主题",
  exact: "正文短语匹配，适合条款原文",
  fuzzy: "编辑距离容错，适合错别字与简称",
};

const MODE_LABELS = {
  smart: "智能融合",
  keyword: "关键词",
  exact: "正文精确",
  fuzzy: "模糊容错",
};

const state = {
  query: "",
  mode: "smart",
  filters: {
    issuers: [],
    categories: [],
    regions: [],
    tags: [],
    date_from: null,
    date_to: null,
  },
  sort: "relevance",
  page: 1,
  size: 10,
  total: 0,
  facets: {},
  loading: false,
};

const expandedFacets = new Set();
let toastTimer = null;

/* ------------------------------------------------------------------ utils */

function $(selector) {
  return document.querySelector(selector);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

// OpenSearch returns the field text with <mark> tags; escape everything else.
function safeHighlight(value) {
  return escapeHtml(value)
    .replace(/&lt;mark&gt;/g, "<mark>")
    .replace(/&lt;\/mark&gt;/g, "</mark>");
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value) || 0);
}

function formatBytes(value) {
  const bytes = Number(value) || 0;
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let size = bytes / 1024;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[index]}`;
}

function formatDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

function totalPages() {
  return Math.max(1, Math.ceil(state.total / state.size));
}

function showToast(message, kind = "info") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", kind === "error");
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

async function api(path, options = {}) {
  const { auth = false, ...fetchOptions } = options;
  const headers = {
    "Content-Type": "application/json",
    ...(auth ? adminAuthHeaders() : {}),
    ...(fetchOptions.headers || {}),
  };
  const response = await fetch(path, { ...fetchOptions, headers });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      /* keep status text */
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

/* ------------------------------------------------------------------ stats */

async function refreshStats() {
  const container = $("#stats");
  try {
    const stats = await api("/api/stats");
    const online = stats.status === "ready";
    container.innerHTML = `
      <span class="stat dot ${online ? "" : "warn"}">${online ? "服务在线" : "索引降级"}</span>
      <span class="stat">文档 <b>${formatNumber(stats.documents)}</b></span>
      <span class="stat">索引 <b>${formatNumber(stats.index_docs)}</b></span>
      <span class="stat">体积 <b>${formatBytes(stats.index_size_bytes)}</b></span>
      <span class="stat accent">分词 <b>${escapeHtml(stats.analyzer)}</b></span>
    `;
  } catch (error) {
    container.innerHTML = `<span class="stat dot warn">服务离线</span>`;
    console.error(error);
  }
}

/* ----------------------------------------------------------------- search */

function cleanFilters() {
  return {
    issuers: state.filters.issuers,
    categories: state.filters.categories,
    regions: state.filters.regions,
    tags: state.filters.tags,
    date_from: state.filters.date_from || null,
    date_to: state.filters.date_to || null,
  };
}

function setLoading(loading) {
  state.loading = loading;
  const button = $(".search-btn");
  button.disabled = loading;
  button.firstChild.textContent = loading ? "检索中 " : "检索 ";
}

function renderSkeleton() {
  $("#results").innerHTML = Array.from({ length: 4 })
    .map(
      () => `
      <div class="skeleton">
        <div class="sk-line title"></div>
        <div class="sk-line short"></div>
        <div class="sk-line wide"></div>
        <div class="sk-line wide"></div>
      </div>`
    )
    .join("");
  $("#pagination").innerHTML = "";
  $("#resultSummary").innerHTML = "正在检索…";
}

async function runSearch(resetPage = true) {
  if (resetPage) state.page = 1;
  renderSkeleton();
  setLoading(true);

  const payload = {
    query: state.query,
    mode: state.mode,
    filters: cleanFilters(),
    page: state.page,
    size: state.size,
    sort: state.sort,
    slop: 2,
  };

  try {
    const result = await api("/api/search", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.total = result.total;
    state.facets = result.facets || {};
    renderSummary(result);
    renderResults(result);
    renderFacets();
    renderPagination();
  } catch (error) {
    $("#results").innerHTML = `
      <div class="empty">
        <div class="glyph">!</div>
        <h3>检索服务暂时不可用</h3>
        <p>${escapeHtml(error.message)}。请确认 PostgreSQL 与 OpenSearch 容器已启动。</p>
      </div>`;
    $("#pagination").innerHTML = "";
    $("#resultSummary").textContent = "检索失败";
    showToast(error.message, "error");
  } finally {
    setLoading(false);
  }
}

function renderSummary(result) {
  const took = `<span class="took">${result.took_ms} ms</span>`;
  if (!state.query) {
    $("#resultSummary").innerHTML = `共 <b>${formatNumber(result.total)}</b> 份文档 · ${took}`;
    return;
  }
  const modeLabel = MODE_LABELS[result.mode] || result.mode;
  $("#resultSummary").innerHTML =
    `<b>${formatNumber(result.total)}</b> 条结果 · ${took} · ${modeLabel}`;
}

function titleHtml(hit) {
  const highlight = (hit.highlights || []).find((item) => item.field === "title");
  return highlight ? safeHighlight(highlight.text) : escapeHtml(hit.title);
}

function snippetHtml(hit) {
  const highlights = hit.highlights || [];
  const content = highlights.find((item) => item.field === "content");
  const summary = highlights.find((item) => item.field === "summary");
  if (content) return safeHighlight(content.text);
  if (summary) return safeHighlight(summary.text);
  return escapeHtml(hit.summary || hit.content || "").slice(0, 240);
}

function renderResults(result) {
  const container = $("#results");

  if (!result.hits.length) {
    container.innerHTML = emptyState();
    return;
  }

  container.innerHTML = result.hits
    .map((hit) => {
      const tags = (hit.tags || [])
        .filter((tag) => tag !== hit.category)
        .slice(0, 4)
        .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
        .join("");
      const category = hit.category
        ? `<span class="tag cat">${escapeHtml(hit.category)}</span>`
        : "";
      const score = hit.score != null ? Number(hit.score).toFixed(2) : "";
      const scoreLine = score ? `<div class="score">${score}</div>` : "";

      return `
        <article class="hit" data-id="${escapeHtml(hit.doc_id)}" tabindex="0" role="button"
                 aria-label="查看文档：${escapeHtml(hit.title)}">
          <div class="hit-top">
            <div class="hit-main">
              <h2 class="hit-title">${titleHtml(hit)}</h2>
              <div class="hit-meta">
                <span class="issuer">${escapeHtml(hit.issuer || "未知机关")}</span>
                <span class="sep">/</span>
                <span class="docno">${escapeHtml(hit.doc_number || "无文号")}</span>
                <span class="sep">/</span>
                <span>${formatDate(hit.issue_date)}</span>
                ${hit.region ? `<span class="sep">/</span><span>${escapeHtml(hit.region)}</span>` : ""}
              </div>
              <p class="hit-snippet">${snippetHtml(hit)}</p>
              <div class="hit-tags">${category}${tags}</div>
            </div>
            <div class="hit-side">
              ${scoreLine}
              <div>${formatDate(hit.issue_date)}</div>
            </div>
          </div>
        </article>`;
    })
    .join("");
}

function emptyState() {
  if (!state.query) {
    return `
      <div class="empty">
        <div class="glyph">空</div>
        <h3>索引里还没有文档</h3>
        <p>先载入一批示例政策数据，用来验证分词、精确短语、模糊容错与字段筛选。</p>
        <button class="btn solid" id="emptySeed">载入 320 份示例数据</button>
      </div>`;
  }

  const hasFilters =
    state.filters.issuers.length ||
    state.filters.categories.length ||
    state.filters.regions.length ||
    state.filters.tags.length ||
    state.filters.date_from ||
    state.filters.date_to;

  return `
    <div class="empty">
      <div class="glyph">无</div>
      <h3>没有匹配的结果</h3>
      <p>${
        hasFilters
          ? "当前字段筛选可能过窄，清空筛选后再试一次。"
          : "换一个更短的关键词，或切换到「模糊容错」模式试试。"
      }</p>
      ${
        hasFilters
          ? '<button class="btn ghost" id="emptyClear">清空筛选</button>'
          : '<button class="btn ghost" id="emptyFuzzy">改用模糊容错</button>'
      }
    </div>`;
}

/* ----------------------------------------------------------------- facets */

function facetValues(facetKey) {
  return (state.facets[facetKey] || []).filter((bucket) => bucket.value);
}

function renderFacets() {
  const container = $("#facetGroups");
  const groups = FACETS.filter((facet) => facetValues(facet.key).length);

  if (!groups.length) {
    container.innerHTML = `<div class="filter-placeholder">当前结果没有可筛选字段</div>`;
    return;
  }

  container.innerHTML = groups
    .map((facet) => {
      const values = facetValues(facet.key);
      const expanded = expandedFacets.has(facet.key);
      const visible = expanded ? values : values.slice(0, 8);
      const collapsed = !values.length;

      const items = visible
        .map((bucket) => {
          const checked = state.filters[facet.key].includes(bucket.value);
          return `
            <label class="facet-item">
              <input type="checkbox" data-facet="${facet.key}"
                     value="${escapeHtml(bucket.value)}" ${checked ? "checked" : ""} />
              <span class="name" title="${escapeHtml(bucket.value)}">${escapeHtml(bucket.value)}</span>
              <span class="count">${formatNumber(bucket.count)}</span>
            </label>`;
        })
        .join("");

      const more =
        values.length > 8
          ? `<button class="facet-more" data-more="${facet.key}">
               ${expanded ? "收起" : `显示全部 ${values.length}`}
             </button>`
          : "";

      return `
        <div class="facet-group ${collapsed ? "collapsed" : ""}" data-group="${facet.key}">
          <button class="facet-title" data-toggle="${facet.key}">
            <span>${facet.label}</span>
            <span class="chev">▾</span>
          </button>
          <div class="facet-list">${items}${more}</div>
        </div>`;
    })
    .join("");
}

/* ------------------------------------------------------------- pagination */

function renderPagination() {
  const container = $("#pagination");
  const pages = totalPages();
  if (pages <= 1) {
    container.innerHTML = "";
    return;
  }

  const current = state.page;
  const numbers = [1];
  for (let page = Math.max(2, current - 1); page <= Math.min(pages - 1, current + 1); page += 1) {
    numbers.push(page);
  }
  if (pages > 1) numbers.push(pages);

  const unique = [...new Set(numbers)].sort((a, b) => a - b);
  const parts = [];

  unique.forEach((page, index) => {
    if (index > 0 && page - unique[index - 1] > 1) {
      parts.push('<span class="page-ellipsis">…</span>');
    }
    parts.push(
      `<button class="page-btn ${page === current ? "active" : ""}" data-page="${page}">${page}</button>`
    );
  });

  container.innerHTML = `
    <button class="page-btn" data-page="${current - 1}" ${current === 1 ? "disabled" : ""}>‹</button>
    ${parts.join("")}
    <button class="page-btn" data-page="${current + 1}" ${current === pages ? "disabled" : ""}>›</button>
  `;
}

/* ------------------------------------------------------------------ drawer */

async function openDocument(docId) {
  const drawer = $("#drawer");
  const overlay = $("#overlay");
  drawer.classList.add("open");
  overlay.classList.add("show");
  drawer.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
  $("#drawerBody").innerHTML = `<div class="doc-kicker">LOADING</div><div class="sk-line title"></div>`;

  try {
    const doc = await api(`/api/documents/${encodeURIComponent(docId)}`);
    const tags = (doc.tags || [])
      .filter((tag) => tag !== doc.category)
      .map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`)
      .join("");
    const paragraphs = String(doc.content || "")
      .split(/\n{2,}/)
      .filter(Boolean)
      .map((text) => `<p>${escapeHtml(text)}</p>`)
      .join("");
    const source = doc.source_url
      ? `<a href="${escapeHtml(doc.source_url)}" target="_blank" rel="noreferrer">打开原文 ↗</a>`
      : "";

    $("#drawerBody").innerHTML = `
      <div class="doc-kicker">POLICY DOCUMENT · ${escapeHtml(doc.doc_id)}</div>
      <h2 class="doc-title">${escapeHtml(doc.title)}</h2>
      <dl class="doc-grid">
        <dt>发布机关</dt><dd>${escapeHtml(doc.issuer || "—")}</dd>
        <dt>文号</dt><dd class="mono">${escapeHtml(doc.doc_number || "—")}</dd>
        <dt>发布日期</dt><dd>${formatDate(doc.issue_date)}</dd>
        <dt>施行日期</dt><dd>${formatDate(doc.effective_date)}</dd>
        <dt>政策类型</dt><dd>${escapeHtml(doc.category || "—")}</dd>
        <dt>适用地区</dt><dd>${escapeHtml(doc.region || "—")}</dd>
        <dt>状态</dt><dd>${escapeHtml(doc.status || "active")}</dd>
        <dt>内容指纹</dt><dd class="mono">${escapeHtml(doc.file_hash || "—")}</dd>
      </dl>
      <div class="doc-tags">${tags}</div>
      <div class="doc-body">${paragraphs || "<p>暂无正文。</p>"}</div>
      <div class="doc-foot">
        ${source}
        <span>入库时间 ${formatDate(doc.created_at)}</span>
      </div>
    `;
  } catch (error) {
    $("#drawerBody").innerHTML = `
      <div class="doc-kicker">ERROR</div>
      <h2 class="doc-title">文档读取失败</h2>
      <p>${escapeHtml(error.message)}</p>`;
  }
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#overlay").classList.remove("show");
  $("#drawer").setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

/* ----------------------------------------------------------------- actions */

async function seedData() {
  if (!window.confirm("将清空现有文档与索引，并重新导入 320 份示例政策。继续吗？")) return;
  const button = $("#seedBtn");
  button.disabled = true;
  button.textContent = "导入中…";
  try {
    const result = await api("/api/admin/seed", {
      method: "POST",
      auth: true,
      body: JSON.stringify({ count: 320, reset: true }),
    });
    showToast(result.message);
    await refreshStats();
    await runSearch(true);
  } catch (error) {
    showToast(`导入失败：${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "载入示例数据";
  }
}

async function reindex() {
  const button = $("#reindexBtn");
  button.disabled = true;
  button.textContent = "重建中…";
  try {
    const result = await api("/api/admin/reindex", { method: "POST", auth: true });
    showToast(result.message);
    await refreshStats();
    await runSearch(true);
  } catch (error) {
    showToast(`重建失败：${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = "重建索引";
  }
}

async function clearData() {
  if (!window.confirm("将清空全部文档与索引，此操作不可撤销。继续吗？")) return;
  const button = $("#adminClearBtn");
  if (button) {
    button.disabled = true;
    button.textContent = "清空中…";
  }
  try {
    const result = await api("/api/admin/clear", { method: "POST", auth: true });
    showToast(result.message);
    await refreshStats();
    await runSearch(true);
  } catch (error) {
    showToast(`清空失败：${error.message}`, "error");
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "清空数据";
    }
  }
}

function clearFilters() {
  state.filters = {
    issuers: [],
    categories: [],
    regions: [],
    tags: [],
    date_from: null,
    date_to: null,
  };
  $("#dateFrom").value = "";
  $("#dateTo").value = "";
  expandedFacets.clear();
  runSearch(true);
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === mode);
  });
  $("#modeHint").textContent = MODE_HINTS[mode] || "";
  if (state.query || state.total) runSearch(true);
}

/* -------------------------------------------------------------------- bind */

function bind() {
  $("#searchForm").addEventListener("submit", (event) => {
    event.preventDefault();
    state.query = $("#q").value.trim();
    runSearch(true);
  });

  document.querySelectorAll(".mode").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  $("#sort").addEventListener("change", (event) => {
    state.sort = event.target.value;
    runSearch(true);
  });

  $("#clearFilters").addEventListener("click", clearFilters);

  $("#facetGroups").addEventListener("change", (event) => {
    const input = event.target.closest("input[data-facet]");
    if (!input) return;
    const key = input.dataset.facet;
    const value = input.value;
    const list = state.filters[key];
    const index = list.indexOf(value);
    if (input.checked && index === -1) list.push(value);
    if (!input.checked && index !== -1) list.splice(index, 1);
    runSearch(true);
  });

  $("#facetGroups").addEventListener("click", (event) => {
    const more = event.target.closest("[data-more]");
    if (more) {
      const key = more.dataset.more;
      if (expandedFacets.has(key)) expandedFacets.delete(key);
      else expandedFacets.add(key);
      renderFacets();
      return;
    }

    const toggle = event.target.closest("[data-toggle]");
    if (toggle) {
      const group = toggle.closest(".facet-group");
      group.classList.toggle("collapsed");
    }
  });

  $("#facetGroups").addEventListener("click", (event) => {
    if (event.target.id === "emptySeed") seedData();
    if (event.target.id === "emptyClear") clearFilters();
    if (event.target.id === "emptyFuzzy") setMode("fuzzy");
  });

  $("#results").addEventListener("click", (event) => {
    const hit = event.target.closest(".hit");
    if (hit) openDocument(hit.dataset.id);
    if (event.target.id === "emptySeed") seedData();
    if (event.target.id === "emptyClear") clearFilters();
    if (event.target.id === "emptyFuzzy") setMode("fuzzy");
  });

  $("#results").addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const hit = event.target.closest(".hit");
    if (!hit) return;
    event.preventDefault();
    openDocument(hit.dataset.id);
  });

  $("#pagination").addEventListener("click", (event) => {
    const button = event.target.closest("[data-page]");
    if (!button || button.disabled) return;
    const page = Number(button.dataset.page);
    if (page < 1 || page > totalPages() || page === state.page) return;
    state.page = page;
    runSearch(false);
    window.scrollTo({ top: $(".results-bar").offsetTop - 90, behavior: "smooth" });
  });

  $("#dateFrom").addEventListener("change", (event) => {
    state.filters.date_from = event.target.value || null;
    runSearch(true);
  });

  $("#dateTo").addEventListener("change", (event) => {
    state.filters.date_to = event.target.value || null;
    runSearch(true);
  });

  $("#seedBtn").addEventListener("click", seedData);
  $("#reindexBtn").addEventListener("click", reindex);
  $("#drawerClose").addEventListener("click", closeDrawer);
  $("#overlay").addEventListener("click", closeDrawer);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeDrawer();
    if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)) {
      event.preventDefault();
      $("#q").focus();
    }
  });
}

/* --------------------------------------------------------------------- init */

document.addEventListener("DOMContentLoaded", async () => {
  bind();
  await refreshStats();
  await runSearch(true);
});

/* ------------------------------------------------------------------- admin */

const ADMIN_TOKEN_KEY = "policy_admin_token";
let adminToken = sessionStorage.getItem(ADMIN_TOKEN_KEY) || "";

function adminAuthHeaders() {
  return adminToken ? { Authorization: `Bearer ${adminToken}` } : {};
}

function setAdminToken(token) {
  adminToken = token || "";
  if (adminToken) sessionStorage.setItem(ADMIN_TOKEN_KEY, adminToken);
  else sessionStorage.removeItem(ADMIN_TOKEN_KEY);
  document.body.classList.toggle("admin-authed", Boolean(adminToken));
}

function showAdminView(authed) {
  const login = $("#adminLoginView");
  const panel = $("#adminPanelView");
  if (!login || !panel) return;
  login.hidden = authed;
  panel.hidden = !authed;
  document.body.classList.toggle("admin-authed", authed);
}

function formatAdminDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function openAdmin() {
  const backdrop = $("#adminBackdrop");
  if (!backdrop) return;
  backdrop.hidden = false;
  if (adminToken) loadAdminSession();
  else {
    showAdminView(false);
    $("#adminUsername")?.focus();
  }
}

function closeAdmin() {
  const backdrop = $("#adminBackdrop");
  if (backdrop) backdrop.hidden = true;
}

async function loadAdminSession() {
  if (!adminToken) {
    showAdminView(false);
    return;
  }
  try {
    const me = await api("/api/auth/me", { auth: true });
    const who = $("#adminWho");
    if (who) who.textContent = `${me.username} · ${me.role} · 会话有效期至 ${formatAdminDate(new Date(me.expires_at * 1000))}`;
    showAdminView(true);
    await loadTokens();
  } catch {
    setAdminToken("");
    showAdminView(false);
  }
}

async function adminLogin(event) {
  event.preventDefault();
  const errorNode = $("#adminLoginError");
  if (errorNode) errorNode.textContent = "";
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: $("#adminUsername").value.trim(),
        password: $("#adminPassword").value,
      }),
    });
    setAdminToken(result.access_token);
    $("#adminPassword").value = "";
    await loadAdminSession();
  } catch (error) {
    if (errorNode) errorNode.textContent = error.message;
  }
}

function adminLogout() {
  setAdminToken("");
  showAdminView(false);
  const created = $("#tokenCreated");
  if (created) created.hidden = true;
  const list = $("#tokenList");
  if (list) list.innerHTML = "";
}

function renderTokens(tokens) {
  const list = $("#tokenList");
  if (!list) return;
  if (!tokens.length) {
    list.innerHTML = `<div class="empty-token">还没有 Token。创建一个用于 MCP 客户端或 API 调用。</div>`;
    return;
  }
  list.innerHTML = tokens
    .map(
      (token) => `
        <div class="token-row">
          <div>
            <strong>${escapeHtml(token.name)}</strong>
            <div class="token-meta">
              ${escapeHtml(token.jti)} · ${escapeHtml((token.scopes || []).join(", ") || "无 scope")}<br />
              创建 ${formatAdminDate(token.created_at)} · 到期 ${formatAdminDate(token.expires_at)}
              ${token.last_used_at ? ` · 最近使用 ${formatAdminDate(token.last_used_at)}` : ""}
              ${token.revoked_at ? ` · 已撤销 ${formatAdminDate(token.revoked_at)}` : ""}
            </div>
          </div>
          <button class="btn ghost" type="button" data-revoke="${escapeHtml(token.jti)}" ${token.active ? "" : "disabled"}>
            ${token.active ? "撤销" : "已失效"}
          </button>
        </div>`
    )
    .join("");
}

async function loadTokens() {
  try {
    const result = await api("/api/admin/tokens", { auth: true });
    renderTokens(result.tokens || []);
  } catch (error) {
    if (error.status === 401) adminLogout();
    else showToast(`读取 Token 失败：${error.message}`, "error");
  }
}

async function createToken(event) {
  event.preventDefault();
  const name = $("#tokenName").value.trim();
  const days = Number($("#tokenDays").value);
  if (!name) return showToast("请填写 Token 名称", "error");
  if (!Number.isInteger(days) || days < 1 || days > 3650) {
    return showToast("有效期必须是 1-3650 天", "error");
  }
  const scopes = $("#tokenScopeRead").checked ? ["policy:read"] : [];
  try {
    const result = await api("/api/admin/tokens", {
      method: "POST",
      auth: true,
      body: JSON.stringify({ name, scopes, expires_in_days: days }),
    });
    const created = $("#tokenCreated");
    const value = $("#tokenValue");
    if (created) created.hidden = false;
    if (value) value.textContent = result.token;
    $("#tokenName").value = "";
    showToast("Token 已创建，请立即复制保存");
    await loadTokens();
  } catch (error) {
    showToast(`创建失败：${error.message}`, "error");
  }
}

async function revokeToken(jti) {
  if (!jti) return;
  if (!window.confirm("撤销后该 Token 立即失效，确定继续吗？")) return;
  try {
    await api(`/api/admin/tokens/${encodeURIComponent(jti)}`, {
      method: "DELETE",
      auth: true,
    });
    showToast("Token 已撤销");
    await loadTokens();
  } catch (error) {
    showToast(`撤销失败：${error.message}`, "error");
  }
}

async function copyCreatedToken() {
  const value = $("#tokenValue")?.textContent || "";
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    showToast("已复制到剪贴板");
  } catch {
    showToast("复制失败，请手动选择文本", "error");
  }
}

function bindAdmin() {
  $("#adminBtn")?.addEventListener("click", openAdmin);
  $("#adminClose")?.addEventListener("click", closeAdmin);
  $("#adminBackdrop")?.addEventListener("click", (event) => {
    if (event.target.id === "adminBackdrop") closeAdmin();
  });
  $("#adminLoginForm")?.addEventListener("submit", adminLogin);
  $("#adminLogout")?.addEventListener("click", adminLogout);
  $("#tokenForm")?.addEventListener("submit", createToken);
  $("#refreshTokens")?.addEventListener("click", loadTokens);
  $("#copyToken")?.addEventListener("click", copyCreatedToken);
  $("#tokenList")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-revoke]");
    if (button) revokeToken(button.dataset.revoke);
  });
  $("#adminSeedBtn")?.addEventListener("click", seedData);
  $("#adminReindexBtn")?.addEventListener("click", reindex);
  $("#adminClearBtn")?.addEventListener("click", clearData);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAdmin();
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bindAdmin();
  if (adminToken) await loadAdminSession();
});

