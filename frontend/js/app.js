/* ==========================================================================
   MyMart - shared frontend code (loaded on every page)
   - api()        : small wrapper around fetch() for the Flask REST API
   - Auth state   : MyMart.user (null when logged out)
   - Navbar/footer rendering, toasts, money formatting, product cards
   ========================================================================== */

const MyMart = { user: null, cartCount: 0 };

/* ---------- API helper ---------- */
async function api(path, { method = "GET", body, raw = false } = {}) {
  const opts = { method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (raw) return res;
  let data = {};
  try { data = await res.json(); } catch (e) { /* empty body */ }
  if (!res.ok) {
    const err = new Error(data.error || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return data;
}

/* ---------- Formatting ---------- */
const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 });
function money(v) { return inr.format(Number(v || 0)).replace(/\.00$/, ""); }
function moneyShort(v) {
  v = Number(v || 0);
  if (v >= 1e5) return "₹" + (v / 1e5).toFixed(2) + "L";
  if (v >= 1e3) return "₹" + (v / 1e3).toFixed(1) + "k";
  return "₹" + Math.round(v);
}
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function fmtDate(iso, withTime = true) {
  if (!iso) return "-";
  const d = new Date(iso.replace(" ", "T"));
  const opts = { day: "2-digit", month: "short", year: "numeric" };
  if (withTime) Object.assign(opts, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleString("en-IN", opts);
}
function qs(name) { return new URLSearchParams(location.search).get(name); }
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* ---------- Toasts ---------- */
function toast(message, type = "") {
  let box = $("#toasts");
  if (!box) { box = document.createElement("div"); box.id = "toasts"; document.body.appendChild(box); }
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.textContent = message;
  box.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

/* ---------- Navbar & footer ---------- */
function renderNavbar() {
  const el = $("#navbar");
  if (!el) return;
  const page = location.pathname.replace(/^\//, "") || "shop";
  const link = (href, label, key) =>
    `<a href="${href}" class="${page === key ? "active" : ""}">${label}</a>`;
  const u = MyMart.user;
  el.className = "navbar";
  el.innerHTML = `
    <div class="container">
      <a class="brand" href="/"><img class="logo" src="/static/img/logo.svg" alt="" width="36" height="36"> My Mart</a>
      <button class="nav-toggle" aria-label="Menu" onclick="document.querySelector('.nav-links').classList.toggle('open')">☰</button>
      <nav class="nav-links">
        ${link("/", "🏪 Shop", "shop")}
        ${link("/dataset", "📊 Dataset", "dataset")}
        ${link("/about", "ℹ️ About", "about")}
        ${u && u.is_admin ? link("/admin", "🛠️ Admin", "admin") : ""}
        ${u ? link("/orders", "📦 My Orders", "orders") : ""}
        <a href="/cart" class="${page === "cart" ? "active" : ""}">🛒 Cart <span class="badge-count" id="cart-count">${MyMart.cartCount}</span></a>
        ${u
          ? `<span class="user-chip">👤 ${esc(u.name.split(" ")[0])}</span>
             <button class="linklike" id="logout-btn">Logout</button>`
          : link("/login", "Login", "login") + link("/register", "Sign up", "register")}
      </nav>
    </div>`;
  const lo = $("#logout-btn");
  if (lo) lo.onclick = async () => {
    await api("/api/auth/logout", { method: "POST" });
    toast("Logged out");
    setTimeout(() => (location.href = "/"), 400);
  };
}

function renderFooter() {
  const el = $("#footer");
  if (!el) return;
  el.className = "site-footer";
  el.innerHTML = `
    <div class="container">
      <div><strong style="color:#fff;display:inline-flex;align-items:center;gap:8px"><img src="/static/img/logo.svg" alt="" width="22" height="22"> My Mart</strong><br>Online grocery store - Flask + SQLite + vanilla JS.</div>
      <div><a href="/dataset">Dataset explorer</a> · <a href="/about">How it works</a> · <a href="/api/health">API status</a></div>
      <div class="small">Demo project · payments are simulated · data is synthetic</div>
    </div>`;
}

function setCartCount(n) {
  MyMart.cartCount = n;
  const el = $("#cart-count");
  if (el) el.textContent = n;
}

async function refreshCartCount() {
  if (!MyMart.user) return setCartCount(0);
  try { setCartCount((await api("/api/cart")).items_count); } catch (e) { setCartCount(0); }
}

/* Runs before every page script. Resolves once we know who is logged in. */
const ready = (async () => {
  try { MyMart.user = (await api("/api/auth/me")).user; } catch (e) { MyMart.user = null; }
  await refreshCartCount();
  renderNavbar();
  renderFooter();
  return MyMart.user;
})();

function requireLogin() {
  if (!MyMart.user) {
    location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search);
    return false;
  }
  return true;
}

/* ---------- Cart actions ---------- */
async function addToCart(productId, quantity = 1, btn) {
  if (!MyMart.user) {
    toast("Please log in to add items to your cart");
    setTimeout(() => (location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search)), 700);
    return;
  }
  if (btn) btn.disabled = true;
  try {
    const cart = await api("/api/cart", { method: "POST", body: { product_id: productId, quantity } });
    setCartCount(cart.items_count);
    toast(cart.message || "Added to cart", "success");
    return cart;
  } catch (e) {
    toast(e.message, "error");
  } finally {
    if (btn) btn.disabled = false;
  }
}

/* ---------- Product card (used by shop + product pages) ---------- */
function productCard(p) {
  const stock = p.stock === 0
    ? `<span class="stock-out">Out of stock</span>`
    : p.stock <= 10 ? `<span class="stock-low">Only ${p.stock} left</span>` : "";
  const thumb = p.image_url ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" loading="lazy">` : p.emoji;
  return `
    <article class="product">
      <a class="thumb" href="/product?id=${p.id}">
        ${thumb}
        ${p.discount_pct ? `<span class="discount-tag">${p.discount_pct}% OFF</span>` : ""}
        <span class="veg-dot ${p.is_veg ? "" : "nonveg"}" title="${p.is_veg ? "Vegetarian" : "Non-vegetarian"}"></span>
      </a>
      <div class="body">
        <div class="brand-name">${esc(p.brand || "")}</div>
        <a class="name" href="/product?id=${p.id}">${esc(p.name)}</a>
        <div class="unit">${esc(p.unit || "")}</div>
        <div class="rating"><b>${p.rating.toFixed(1)} ★</b>${p.rating_count.toLocaleString("en-IN")} ratings</div>
        ${stock}
        <div class="price-row">
          <span class="price">${money(p.price)}</span>
          ${p.mrp > p.price ? `<span class="mrp">${money(p.mrp)}</span>` : ""}
          <button class="btn btn-sm" ${p.stock === 0 ? "disabled" : ""} onclick="addToCart(${p.id}, 1, this)">Add +</button>
        </div>
      </div>
    </article>`;
}

function statusBadge(s) { return `<span class="status status-${esc(s)}">${esc(s)}</span>`; }

function pagination(el, data, onPage) {
  if (!data.pages || data.pages <= 1) { el.innerHTML = ""; return; }
  el.innerHTML = `
    <button class="btn btn-light btn-sm" ${data.page <= 1 ? "disabled" : ""} data-p="${data.page - 1}">← Prev</button>
    <span class="muted small">Page ${data.page} of ${data.pages} · ${data.total} results</span>
    <button class="btn btn-light btn-sm" ${data.page >= data.pages ? "disabled" : ""} data-p="${data.page + 1}">Next →</button>`;
  $$("button[data-p]", el).forEach(b => (b.onclick = () => onPage(Number(b.dataset.p))));
}

function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
