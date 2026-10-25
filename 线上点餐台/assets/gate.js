/* 麦当劳 · 像素进入页（Gateway）
   堂食 / 外卖到家 双入口 + MCP 营养计算器 + 优惠券 / 积分 / 活动日历
   视觉与交互全部复用点餐台的变量、像素按钮、底部抽屉与弹窗。 */
'use strict';

window.addEventListener('error', e => {
  document.title = 'ERR: ' + e.message + ' @' + (e.lineno || '?');
});

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => '¥' + (Number(n) || 0).toFixed(2);

const state = {
  coupons: [], account: null, stores: [],
  nutrition: [], campaign: [],
  theme: 'day', mode: null,
  nc: { q: '', group: '全部', goal: 600, picked: [] },   // picked: [{name, kcal, protein, fat, carb, sodium, qty}]
  calFilter: 'all',
};

// ===== 昼夜：与点餐台同一判定口径（设备本地时间 18:00–06:00 为夜） =====
const NIGHT_START = 18, NIGHT_END = 6;
function isNightTime() {
  const p = new URLSearchParams(location.search);
  if (p.get('qa_night') === '1') return true;
  if (p.get('qa_day') === '1') return false;
  const h = new Date().getHours();
  return h >= NIGHT_START || h < NIGHT_END;
}
function applyTheme(theme) {
  state.theme = theme === 'night' ? 'night' : 'day';
  const night = state.theme === 'night';
  document.documentElement.dataset.theme = state.theme;
  $('meta[name="theme-color"]').content = night ? '#141721' : '#f4efe3';
  const chip = $('#phaseChip');
  if (chip) chip.innerHTML = `<i class="gs-dot ${night ? 'is-night' : ''}"></i>${night ? '夜间 · 灯光已点亮' : '日间 · 自然光'}`;
}

// ===== 本地时间 =====
function tickClock() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  const c = $('#clock');
  if (c) c.textContent = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

// ===== 底部抽屉 / 弹窗 / 吐司（与 app.js 同款） =====
function openSheet(title, html) {
  $('#sheetTitle').textContent = title;
  $('#sheetBody').innerHTML = html;
  $('#sheet').classList.remove('hidden');
  $('#sheetBackdrop').classList.remove('hidden');
  $('#sheetBody').scrollTop = 0;
}
function closeSheet() {
  $('#sheet').classList.add('hidden');
  $('#sheetBackdrop').classList.add('hidden');
}
function toast(msg) {
  const w = $('#toastWrap');
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  w.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = '.3s'; setTimeout(() => t.remove(), 300); }, 2000);
}
let modalTimer = null;
function hideModal() {
  if (modalTimer) { clearTimeout(modalTimer); modalTimer = null; }
  $('#modal').classList.add('hidden');
}
function showModal(title, html, autoCloseMs = 0) {
  hideModal();
  const m = $('#modal');
  m.innerHTML = `<div class="modal-card${autoCloseMs ? ' auto' : ''}"><h3>${esc(title)}</h3><p>${html}</p>
    ${autoCloseMs ? `<div class="modal-timer"><i style="animation-duration:${autoCloseMs}ms"></i></div>` : '<button class="px-btn primary" id="modalOk">好的</button>'}</div>`;
  m.classList.remove('hidden');
  if (autoCloseMs) modalTimer = setTimeout(hideModal, autoCloseMs);
  else $('#modalOk').addEventListener('click', hideModal);
}

// ===== 进入点餐台 =====
// 堂食 → 3D 点餐台；外卖到家 → 独立的麦乐送工作台（单页五区）
function orderUrl(mode) {
  return mode === 'delivery' ? 'delivery.html' : 'index.html?mode=dinein';
}
function enter(mode) {
  if (state.entering) return;
  state.entering = true;
  state.mode = mode;
  try { sessionStorage.setItem('mcd.mode', mode); } catch (e) { /* 隐私模式忽略 */ }
  const btn = mode === 'delivery' ? $('#btnDelivery') : $('#btnDineIn');
  btn?.classList.add('pressed');
  $('#gate').classList.add('leaving');
  setTimeout(() => { location.href = orderUrl(mode); }, 320);
}

// ===== 优惠券 =====
function renderCoupons() {
  const list = state.coupons;
  openSheet('我的优惠券', `
    <div class="cal-summary"><span>卡包共 <b>${list.length}</b> 张</span><span>可用 <b>${list.filter(c => c.usable).length}</b> 张</span><span>数据来自麦当劳 MCP query-my-coupons</span></div>
    ${list.map(c => `
      <div class="coupon-card">
        <img src="${c.image}" alt="${esc(c.name)}" onerror="this.style.opacity='.15'">
        <div><div class="cc-name">${esc(c.name)}</div><div class="cc-price">${fmt(c.price)}</div><div class="cc-valid">${esc(c.valid)}</div></div>
        <span class="cc-tag">${esc(c.tag)}</span>
      </div>`).join('')}
    <div class="row" style="margin-top:8px;gap:12px;flex-wrap:wrap">
      <button class="px-btn primary" data-go="dinein">堂食去用券</button>
      <button class="px-btn gold" data-go="delivery">外卖去用券</button>
    </div>
    <p class="nc-hint">下单时在「确认订单」里选择可用券，满减自动结算。</p>`);
}

// ===== 积分 =====
function renderPoints() {
  const a = state.account || { availablePoint: 0, accumulativePoint: 0, expiredPoint: 0 };
  openSheet('积分中心', `
    <div class="pts-hero"><div class="pts-num">${Number(a.availablePoint).toFixed(1)}</div><div class="pts-label">麦享会可用积分</div></div>
    <div class="pts-grid">
      <div class="pts-box"><b>${a.accumulativePoint}</b>累计积分</div>
      <div class="pts-box"><b>${a.expiredPoint}</b>已过期</div>
      <div class="pts-box"><b>1:1</b>消费得积分</div>
      <div class="pts-box"><b>10.4</b>即将过期</div>
    </div>
    <div class="section-title">积分能做什么</div>
    <p class="nc-hint">每消费 1 元得 1 积分；积分可在麦当劳 App 兑换优惠、参与「积分抢先购」周边活动（本页活动日历中标注了抢先购时间）。</p>
    <div class="row" style="gap:12px;flex-wrap:wrap"><button class="px-btn primary" data-go="dinein">去点餐赚积分</button></div>`);
}

// ===== 活动日历 =====
function dayDiff(dateStr) {
  const t = new Date(); t.setHours(0, 0, 0, 0);
  const d = new Date(dateStr + 'T00:00:00');
  return Math.round((d - t) / 86400000);
}
function calStatus(dateStr) {
  const n = dayDiff(dateStr);
  if (n < 0) return { key: 'past', label: '已结束', cls: 'past' };
  if (n === 0) return { key: 'today', label: '今天', cls: 'today' };
  if (n === 1) return { key: 'soon', label: '明天', cls: 'soon' };
  return { key: 'soon', label: `${n} 天后`, cls: 'soon' };
}
const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
function md(dateStr) { const [, m, d] = dateStr.split('-'); return `${+m}/${+d}`; }
function renderCalendar() {
  const items = state.campaign.slice().sort((a, b) => a.date.localeCompare(b.date));
  const todayN = items.filter(x => dayDiff(x.date) === 0).length;
  const soonN = items.filter(x => dayDiff(x.date) > 0).length;
  const pastN = items.filter(x => dayDiff(x.date) < 0).length;
  const shown = items.filter(x => state.calFilter === 'today' ? dayDiff(x.date) === 0
    : state.calFilter === 'soon' ? dayDiff(x.date) > 0 : true);

  const groups = {};
  shown.forEach(x => (groups[x.date] = groups[x.date] || []).push(x));

  openSheet('活动日历 · 抢先知', `
    <div class="cal-summary"><span>本月 <b>${items.length}</b> 场</span><span>今天 <b>${todayN}</b> 场</span><span>即将 <b>${soonN}</b> 场</span>${pastN ? `<span>已结束 <b>${pastN}</b> 场</span>` : ''}<span>来源 MCP campaign-calendar</span></div>
    <div class="nc-chips" style="margin-top:2px">
      ${[['all', '全部'], ['today', '今天'], ['soon', '即将']].map(([k, l]) =>
        `<button class="nc-chip ${state.calFilter === k ? 'active' : ''}" data-cal-filter="${k}">${l}</button>`).join('')}
    </div>
    ${Object.keys(groups).length ? Object.entries(groups).map(([date, list]) => {
      const st = calStatus(date);
      const wd = WEEK[new Date(date + 'T00:00:00').getDay()];
      return `<div class="cal-day"><span class="cal-date">${md(date)}</span><span class="cal-week">${wd}</span><span class="cal-tag ${st.cls}">${st.label}</span></div>` +
        list.map(x => `
          <div class="cal-item">
            <div class="cal-thumb">${x.img ? `<img src="${x.img}" alt="" loading="lazy" onerror="this.parentNode.innerHTML='<span>M</span>'">` : '<span>M</span>'}</div>
            <div>
              <h4>${esc(x.title)}</h4>
              <p>${esc(x.brief)}</p>
              ${x.more?.length ? `<div class="cal-more">另于 ${x.more.map(md).join(' / ')} 返场</div>` : ''}
            </div>
            <span class="cal-kind">${esc(x.kind)}</span>
          </div>`).join('');
    }).join('') : '<div class="empty">该筛选下暂无活动</div>'}
    <p class="nc-hint">活动内容与图片来自麦当劳 MCP 活动日历；「抢先知」指未来日期的活动与周边开售时间，到店/APP 规则以官方为准。</p>`);
}

// ===== 营养计算器（MCP list-nutrition-foods） =====
const NC_GROUPS = ['全部', '汉堡 · 主食', '小食 · 炸物', '甜品 · 冰品', '饮品 · 咖啡', '饮品 · 汽水', '早餐 · 粥点', '套餐 · 组合'];
const NC_PRESETS = [
  { label: '早餐经典', items: ['猪柳蛋麦满分', '大杯鲜萃咖啡'] },
  { label: '一人食', items: ['巨无霸', '中薯条', '可乐中杯'] },
  { label: '轻负担', items: ['板烧鸡腿堡', '苹果片', '无糖可口可乐中杯'] },
];
const NC_REF = { protein: 60, fat: 65, carb: 300, sodium: 2000 };

function ncItem(name) { return state.nutrition.find(x => x.name === name); }
function ncFiltered() {
  const q = state.nc.q.trim().toLowerCase();
  return state.nutrition.filter(x =>
    (state.nc.group === '全部' || x.group === state.nc.group) &&
    (!q || x.name.toLowerCase().includes(q)));
}
function ncTotals() {
  const t = { kcal: 0, protein: 0, fat: 0, carb: 0, sodium: 0, count: 0 };
  state.nc.picked.forEach(p => {
    t.kcal += p.kcal * p.qty; t.protein += p.protein * p.qty; t.fat += p.fat * p.qty;
    t.carb += p.carb * p.qty; t.sodium += p.sodium * p.qty; t.count += p.qty;
  });
  return t;
}
function ncAdd(name) {
  const it = ncItem(name);
  if (!it) return;
  const line = state.nc.picked.find(p => p.name === name);
  if (line) line.qty += 1;
  else state.nc.picked.push({ name: it.name, kcal: it.kcal, protein: it.protein, fat: it.fat, carb: it.carb, sodium: it.sodium, qty: 1 });
  ncRenderPanel();
  ncRenderList();
}
function ncBump(name, d) {
  const line = state.nc.picked.find(p => p.name === name);
  if (!line) return;
  line.qty += d;
  if (line.qty <= 0) state.nc.picked = state.nc.picked.filter(p => p.name !== name);
  ncRenderPanel();
  ncRenderList();
}
function ncPreset(idx) {
  const p = NC_PRESETS[idx];
  if (!p) return;
  state.nc.picked = [];
  p.items.forEach(n => {
    const it = ncItem(n);
    if (it) state.nc.picked.push({ name: it.name, kcal: it.kcal, protein: it.protein, fat: it.fat, carb: it.carb, sodium: it.sodium, qty: 1 });
  });
  ncRenderPanel();
  ncRenderList();
  toast(`已载入搭配：${p.label}`);
}
function ncRenderList() {
  const box = $('#ncList');
  if (!box) return;
  const rows = ncFiltered();
  const CAP = 80;
  box.innerHTML = rows.length ? rows.slice(0, CAP).map(x => {
    const picked = state.nc.picked.find(p => p.name === x.name);
    return `<button class="nc-row" data-nc-add="${esc(x.name)}">
      <span class="ncr-name">${esc(x.name)}</span>
      <span class="ncr-kcal">${x.kcal} kcal</span>
      <span class="ncr-add">${picked ? '+' : '+'}</span>
    </button>`;
  }).join('') + (rows.length > CAP ? `<div class="nc-empty">还有 ${rows.length - CAP} 项，用搜索缩小范围</div>` : '')
    : '<div class="nc-empty">没有匹配的餐品，换个关键词试试</div>';
  const cnt = $('#ncCount');
  if (cnt) cnt.innerHTML = `共 <b>${rows.length}</b> 项`;
}
function ncVerdict(t) {
  if (!t.count) return '先在上面挑几样，这里会实时算出整餐热量与三大营养素。';
  const g = state.nc.goal || 600;
  const pct = Math.round(t.kcal / g * 100);
  if (pct < 45) return `约 ${pct}% 目标热量 · 偏轻，可以再加一份小食或饮品。`;
  if (pct <= 105) return `约 ${pct}% 目标热量 · 落在目标区间内，搭配合理。`;
  if (pct <= 140) return `约 ${pct}% 目标热量 · 略超目标，建议换小杯饮品或少一份小食。`;
  return `约 ${pct}% 目标热量 · 已明显超标，可拆成两餐或与人分食。`;
}
function ncRenderPanel() {
  const box = $('#ncPanel');
  if (!box) return;
  const t = ncTotals();
  const goal = state.nc.goal || 600;
  const pct = Math.min(100, Math.round(t.kcal / goal * 100));
  const over = t.kcal > goal;
  const p = v => Math.round(v / goal * 100);
  box.innerHTML = `
    <div class="nc-total"><b>${Math.round(t.kcal)}</b><small>kcal · 已选 ${t.count} 件</small></div>
    <div class="nc-track ${over ? 'over' : ''}"><i style="width:${pct}%"></i></div>
    <div class="nc-goalline"><span>占目标 ${p(Math.max(0, t.kcal))}%${over ? ' · 已超出' : ''}</span><span>目标 ${goal} kcal</span></div>
    <div class="nc-nut">
      <div><b>${t.protein.toFixed(1)} g</b>蛋白质 · ${Math.round(t.protein / NC_REF.protein * 100)}% NRV</div>
      <div><b>${t.fat.toFixed(1)} g</b>脂肪 · ${Math.round(t.fat / NC_REF.fat * 100)}% NRV</div>
      <div><b>${t.carb.toFixed(1)} g</b>碳水 · ${Math.round(t.carb / NC_REF.carb * 100)}% NRV</div>
      <div><b>${Math.round(t.sodium)} mg</b>钠 · ${Math.round(t.sodium / NC_REF.sodium * 100)}% NRV</div>
    </div>
    <div class="nc-picked">
      ${t.count ? state.nc.picked.map(x => `
        <div class="nc-pick">
          <span>${esc(x.name)}</span>
          <span class="ncp-q">
            <button data-nc-dec="${esc(x.name)}">−</button><b>${x.qty}</b><button data-nc-inc="${esc(x.name)}">+</button>
          </span>
        </div>`).join('') : '<div class="nc-empty" style="padding:12px">还没有选择餐品</div>'}
    </div>
    <div class="nc-verdict">${ncVerdict(t)}</div>`;
}
function renderNutrition() {
  openSheet('营养计算器 · MCP', `
    <div class="nc-top">
      <label class="nc-search"><span>⌕</span><input id="ncSearch" placeholder="搜索餐品，例如 巨无霸 / 薯条 / 奶铁" value="${esc(state.nc.q)}"></label>
      <label class="nc-goal">目标 <input id="ncGoal" type="number" min="100" max="3000" step="50" value="${state.nc.goal}"> kcal</label>
      <span class="nc-goal" id="ncCount">共 <b>${ncFiltered().length}</b> 项</span>
    </div>
    <div class="nc-chips">
      ${NC_GROUPS.map(g => `<button class="nc-chip ${state.nc.group === g ? 'active' : ''}" data-nc-group="${esc(g)}">${esc(g)}</button>`).join('')}
    </div>
    <div class="nc-presets">
      <span class="nc-label">快捷搭配</span>
      ${NC_PRESETS.map((p, i) => `<button class="nc-chip" data-nc-preset="${i}">${esc(p.label)}</button>`).join('')}
      <button class="nc-chip" data-nc-clear="1">清空</button>
    </div>
    <div class="nc-body">
      <div class="nc-list" id="ncList"></div>
      <div class="nc-panel" id="ncPanel"></div>
    </div>
    <p class="nc-hint">数据来自麦当劳 MCP list-nutrition-foods（${state.nutrition.length} 项，按每份计）。NRV% 参考成人 2000 kcal 日需量：蛋白 60 g / 脂肪 65 g / 碳水 300 g / 钠 2000 mg。</p>`);
  ncRenderList();
  ncRenderPanel();
}

// ===== 账号条：像素头像 + 大字账户名（数据来自 MCP query-my-account） =====
function fillAccount() {
  const a = state.account || {};
  // MCP 只返回会员号与积分，没有昵称；账户名固定为「麦门会员」，会员号显示后 8 位
  const raw = String(a.accountId || '');
  const tail = raw ? raw.slice(-8) : '—';
  const name = $('#accName');
  if (name) name.textContent = '麦门会员';
  const idEl = $('#accId');
  if (idEl) idEl.textContent = tail;
  const pt = $('#accPoints');
  if (pt) pt.textContent = Number(a.availablePoint || 0).toFixed(1);
  const badge = $('#accBadge');
  if (badge) badge.textContent = Number(a.accumulativePoint || 0) >= 200 ? 'GOLD MEMBER' : 'MEMBER';
}

// ===== 工具条数值 =====
function fillToolNumbers() {
  fillAccount();
  const c = $('#toolCoupons');
  if (c) c.textContent = `${state.coupons.length} 张`;
  const ch = $('#toolCouponsHint');
  if (ch) ch.textContent = state.coupons.length ? `最高立减 ${fmt(Math.max(...state.coupons.map(x => x.price)))}` : '卡包为空';
  const p = $('#toolPoints');
  if (p) p.textContent = Number(state.account?.availablePoint || 0).toFixed(1);
  const cal = $('#toolCalHint');
  if (cal) {
    const soon = state.campaign.filter(x => dayDiff(x.date) >= 0);
    const todayN = state.campaign.filter(x => dayDiff(x.date) === 0).length;
    cal.textContent = `今天 ${todayN} 场 · 共 ${soon.length} 场`;
  }
  const nut = $('#toolNutHint');
  if (nut) nut.textContent = `${state.nutrition.length} 项营养数据`;
}

// ===== 事件绑定 =====
function bindUI() {
  $('#btnDineIn').addEventListener('click', () => enter('dinein'));
  $('#btnDelivery').addEventListener('click', () => enter('delivery'));

  $$('.gate-tools .tool').forEach(b => b.addEventListener('click', () => {
    const t = b.dataset.tool;
    if (t === 'coupon') renderCoupons();
    else if (t === 'points') renderPoints();
    else if (t === 'calendar') renderCalendar();
    else if (t === 'nutrition') renderNutrition();
  }));

  $('#sheetClose').addEventListener('click', closeSheet);
  $('#sheetBackdrop').addEventListener('click', closeSheet);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeSheet(); hideModal(); } });

  // 抽屉内统一事件委托（列表会整块重绘）
  const body = $('#sheetBody');
  body.addEventListener('click', e => {
    const go = e.target.closest('[data-go]');
    if (go) { closeSheet(); enter(go.dataset.go); return; }

    const add = e.target.closest('[data-nc-add]');
    if (add) { ncAdd(add.dataset.ncAdd); return; }

    const dec = e.target.closest('[data-nc-dec]');
    if (dec) { ncBump(dec.dataset.ncDec, -1); return; }

    const inc = e.target.closest('[data-nc-inc]');
    if (inc) { ncBump(inc.dataset.ncInc, +1); return; }

    const grp = e.target.closest('[data-nc-group]');
    if (grp) {
      state.nc.group = grp.dataset.ncGroup;
      $$('[data-nc-group]').forEach(x => x.classList.toggle('active', x === grp));
      ncRenderList();
      return;
    }

    const pre = e.target.closest('[data-nc-preset]');
    if (pre) { ncPreset(+pre.dataset.ncPreset); return; }

    const clr = e.target.closest('[data-nc-clear]');
    if (clr) { state.nc.picked = []; ncRenderList(); ncRenderPanel(); return; }

    const cal = e.target.closest('[data-cal-filter]');
    if (cal) { state.calFilter = cal.dataset.calFilter; renderCalendar(); return; }
  });
  body.addEventListener('input', e => {
    if (e.target.id === 'ncSearch') { state.nc.q = e.target.value; ncRenderList(); }
    if (e.target.id === 'ncGoal') {
      const v = Math.max(100, Math.min(3000, Number(e.target.value) || 600));
      state.nc.goal = v;
      ncRenderPanel();
    }
  });
}

// ===== 初始化 =====
(async function init() {
  applyTheme(isNightTime() ? 'night' : 'day');
  setInterval(() => { applyTheme(isNightTime() ? 'night' : 'day'); }, 60000);
  tickClock();
  setInterval(tickClock, 1000);

  const grab = async (url, fallback) => {
    try { const r = await fetch(url, { cache: 'no-cache' }); if (!r.ok) throw new Error(r.status); return await r.json(); }
    catch (e) { console.warn('数据加载失败', url, e); return fallback; }
  };
  const [store, nutrition, campaign] = await Promise.all([
    grab('data/store.json', { coupons: [], account: {}, mcpStores: [] }),
    grab('data/nutrition.json', { items: [] }),
    grab('data/campaign.json', { items: [] }),
  ]);
  state.coupons = store.coupons || [];
  state.account = store.account || {};
  state.stores = store.mcpStores || [];
  state.nutrition = nutrition.items || [];
  state.campaign = campaign.items || [];

  const sc = $('#storeChip');
  if (sc) sc.textContent = `门店 ${state.stores.length} 家可选`;
  fillToolNumbers();
  bindUI();

  // 记住上次选择（仅用于恢复状态提示，不自动跳过进入页）
  const last = sessionStorage.getItem('mcd.mode');
  if (last === 'delivery' || last === 'dinein') document.body.dataset.lastMode = last;

  window.__gate = { state, enter, applyTheme, isNightTime, renderNutrition, renderCalendar, ncAdd, ncTotals, orderUrl };

  // ===== 自测（?selftest=1）=====
  if (new URLSearchParams(location.search).has('selftest')) {
    setTimeout(async () => {
      try {
        const results = [];
        const ok = (n, c) => results.push((c ? 'PASS ' : 'FAIL ') + n);
        ok('couponsLoaded', state.coupons.length >= 3);
        ok('nutritionLoaded', state.nutrition.length >= 150);
        ok('campaignLoaded', state.campaign.length >= 10);
        ok('toolNumbers', $('#toolCoupons').textContent.includes('3') && $('#toolNutHint').textContent.includes(String(state.nutrition.length)));

        ok('modeButtons', !!$('#btnDineIn[data-mode="dinein"]') && !!$('#btnDelivery[data-mode="delivery"]'));
        ok('orderUrl', orderUrl('dinein').includes('mode=dinein') && orderUrl('delivery') === 'delivery.html');

        // 账号条：圆形像素头像 + 大字账户名，且位于品牌海报（最大红色区）上方
        const bar = $('#accountBar'), poster = $('.brand-poster');
        ok('accountBar', !!bar && !!$('.acc-avatar svg') && $('#accName').textContent.trim().length >= 2);
        ok('accountData', $('#accId').textContent === String(state.account.accountId || '').slice(-8)
          && $('#accPoints').textContent === Number(state.account.availablePoint || 0).toFixed(1));
        ok('accountAbovePoster', !!bar && !!poster && (bar.compareDocumentPosition(poster) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
          && bar.getBoundingClientRect().bottom <= poster.getBoundingClientRect().top + 1);

        // 字号调节：全局 --fs 生效且可跨档切换
        ok('fontScale', (() => {
          window.__fontscale.set(1.26);
          const big = parseFloat(getComputedStyle($('#accName')).fontSize);
          window.__fontscale.set(1);
          const normal = parseFloat(getComputedStyle($('#accName')).fontSize);
          return !!$('#fsBtn') && big > normal;
        })());

        renderNutrition();
        ok('nutritionSheet', $$('#ncList .nc-row').length > 0);
        $$('#ncList .nc-row')[0].click();
        ok('ncAdd', state.nc.picked.length === 1 && ncTotals().kcal > 0);
        $('[data-nc-preset="0"]').click();
        ok('ncPreset', state.nc.picked.length === 2 && ncTotals().kcal > 0);
        const before = ncTotals().kcal;
        $('[data-nc-inc]')?.click();
        ok('ncQty', ncTotals().kcal > before);
        $('[data-nc-group="饮品 · 咖啡"]')?.click();
        ok('ncGroup', state.nc.group === '饮品 · 咖啡' && $$('#ncList .nc-row').length > 0);
        $('[data-nc-clear]')?.click();
        ok('ncClear', state.nc.picked.length === 0);

        renderCalendar();
        ok('calendarSheet', $$('.cal-day').length >= 2 && $$('.cal-item').length >= 10);
        ok('calendarTodayTag', !!$('.cal-tag.today'));
        renderCoupons();
        ok('couponSheet', $$('.coupon-card').length === state.coupons.length);
        renderPoints();
        ok('pointsSheet', !!$('.pts-hero'));

        applyTheme('night');
        ok('themeNight', document.documentElement.dataset.theme === 'night' && $('#phaseChip').textContent.includes('夜间'));
        applyTheme('day');
        ok('themeDay', document.documentElement.dataset.theme === 'day' && $('#phaseChip').textContent.includes('日间'));
        ok('autoTimeJudge', typeof isNightTime() === 'boolean');
        closeSheet();
        document.title = 'GATE SELFTEST ' + results.join(' | ');
      } catch (e) { document.title = 'GATE SELFTEST ERROR ' + e.message; }
    }, 400);
  }
})();
