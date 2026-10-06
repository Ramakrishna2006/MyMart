/* ==========================================================================
   Tiny dependency-free SVG charts (works offline - no CDN needed)
     barChart(el, [{label, value}], {format})
     lineChart(el, [{label, value}], {format})
     donutChart(el, [{label, value}], {format})
     hbarList(el, [{label, value}], {format})
   ========================================================================== */
const CHART_COLORS = ["#0c8a4f", "#f59e0b", "#2563eb", "#db2777", "#7c3aed", "#0891b2", "#65a30d", "#ea580c", "#475569", "#dc2626", "#0d9488", "#9333ea"];

function _fmt(opts) { return opts.format || (v => Number(v).toLocaleString("en-IN")); }

function barChart(el, data, opts = {}) {
  const fmt = _fmt(opts);
  const W = 640, H = opts.height || 240, pad = { t: 22, r: 10, b: 46, l: 10 };
  const max = Math.max(1, ...data.map(d => d.value));
  const bw = (W - pad.l - pad.r) / Math.max(1, data.length);
  const bars = data.map((d, i) => {
    const h = (d.value / max) * (H - pad.t - pad.b);
    const x = pad.l + i * bw + bw * 0.15, y = H - pad.b - h, w = bw * 0.7;
    const label = d.label.length > 14 ? d.label.slice(0, 13) + "…" : d.label;
    return `<g><title>${esc(d.label)}: ${fmt(d.value)}</title>
      <rect x="${x}" y="${y}" width="${w}" height="${Math.max(h, 1)}" rx="5" fill="${opts.color || CHART_COLORS[0]}" opacity=".9"></rect>
      <text x="${x + w / 2}" y="${y - 6}" text-anchor="middle" font-weight="700">${fmt(d.value)}</text>
      <text x="${x + w / 2}" y="${H - pad.b + 16}" text-anchor="middle">${esc(label)}</text></g>`;
  }).join("");
  el.innerHTML = `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img">
    <line x1="0" x2="${W}" y1="${H - pad.b}" y2="${H - pad.b}" stroke="#dfe6e2"></line>${bars}</svg></div>`;
}

function lineChart(el, data, opts = {}) {
  const fmt = _fmt(opts);
  const W = opts.width || 640, H = opts.height || 240, pad = { t: 26, r: 30, b: 34, l: 30 };
  const max = Math.max(1, ...data.map(d => d.value)) * 1.1;
  const step = (W - pad.l - pad.r) / Math.max(1, data.length - 1);
  const pts = data.map((d, i) => [pad.l + i * step, H - pad.b - (d.value / max) * (H - pad.t - pad.b)]);
  const path = pts.map((p, i) => (i ? "L" : "M") + p[0] + " " + p[1]).join(" ");
  const area = path + ` L ${pts.at(-1)[0]} ${H - pad.b} L ${pts[0][0]} ${H - pad.b} Z`;
  const grid = [0.25, 0.5, 0.75, 1].map(f => {
    const y = H - pad.b - f * (H - pad.t - pad.b);
    return `<line x1="${pad.l}" x2="${W - pad.r}" y1="${y}" y2="${y}" stroke="#eef2f0"></line>`;
  }).join("");
  el.innerHTML = `<div class="chart"><svg viewBox="0 0 ${W} ${H}">
    <defs><linearGradient id="lg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#0c8a4f" stop-opacity=".25"/><stop offset="1" stop-color="#0c8a4f" stop-opacity="0"/></linearGradient></defs>
    ${grid}<path d="${area}" fill="url(#lg)"></path>
    <path d="${path}" fill="none" stroke="#0c8a4f" stroke-width="3" stroke-linejoin="round"></path>
    ${pts.map((p, i) => `<g><title>${esc(data[i].label)}: ${fmt(data[i].value)}</title>
      <circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#fff" stroke="#0c8a4f" stroke-width="3"></circle>
      <text x="${p[0]}" y="${p[1] - 12}" text-anchor="middle" font-weight="700">${fmt(data[i].value)}</text>
      <text x="${p[0]}" y="${H - 10}" text-anchor="middle">${esc(data[i].label)}</text></g>`).join("")}
    </svg></div>`;
}

function donutChart(el, data, opts = {}) {
  const fmt = _fmt(opts);
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const R = 70, r = 44, C = 90;
  const color = (d, i) => (opts.colors && opts.colors[d.label]) || CHART_COLORS[i % CHART_COLORS.length];
  let angle = -Math.PI / 2;
  const arcs = data.map((d, i) => {
    const a = (d.value / total) * Math.PI * 2;
    const large = a > Math.PI ? 1 : 0;
    const p = (rad, rr) => [C + rr * Math.cos(rad), C + rr * Math.sin(rad)];
    const [x1, y1] = p(angle, R), [x2, y2] = p(angle + a - 0.0001, R);
    const [x3, y3] = p(angle + a - 0.0001, r), [x4, y4] = p(angle, r);
    angle += a;
    return `<path d="M${x1} ${y1} A${R} ${R} 0 ${large} 1 ${x2} ${y2} L${x3} ${y3} A${r} ${r} 0 ${large} 0 ${x4} ${y4} Z" fill="${color(d, i)}"><title>${esc(d.label)}: ${fmt(d.value)}</title></path>`;
  }).join("");
  el.innerHTML = `<div class="row" style="align-items:center;gap:20px">
    <svg viewBox="0 0 180 180" width="170" height="170">${arcs}
      <text x="90" y="86" text-anchor="middle" font-size="12" fill="#637069">${esc(opts.centerLabel || "Total")}</text>
      <text x="90" y="104" text-anchor="middle" font-size="16" font-weight="800" fill="#17211b">${fmt(total)}</text></svg>
    <div class="legend" style="flex-direction:column;gap:6px">${data.map((d, i) =>
      `<span><i style="background:${color(d, i)}"></i>${esc(d.label)} - <b>${fmt(d.value)}</b> (${Math.round(d.value * 100 / total)}%)</span>`).join("")}</div></div>`;
}

function hbarList(el, data, opts = {}) {
  const fmt = _fmt(opts);
  const max = Math.max(1, ...data.map(d => d.value));
  el.innerHTML = data.map(d => `
    <div class="hbar"><span class="label" title="${esc(d.label)}">${esc(d.label)}</span>
      <div class="bar"><div style="width:${(d.value / max) * 100}%"></div></div>
      <span class="val">${fmt(d.value)}</span></div>`).join("");
}
