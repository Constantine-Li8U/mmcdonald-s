/* 麦当劳 · 像素 3D 点餐台 —— 应用逻辑 v3（无卡片布局 / MCP 门店选择 / 仅环绕旋转） */
'use strict';

window.addEventListener('error', e => {
  document.title = 'ERR: ' + e.message + ' @' + (e.lineno || '?');
  const w = document.getElementById('toastWrap');
  if (w) { const t = document.createElement('div'); t.className = 'toast'; t.textContent = '脚本错误：' + e.message; w.appendChild(t); }
});
window.addEventListener('unhandledrejection', e => { document.title = 'REJ: ' + (e.reason?.message || e.reason); });

// ===== 就餐方式：由进入页（entry.html）传入 =====
// 未带 ?mode= 且不是自测 → 回到进入页，保证「先选堂食/外卖，再进点餐台」。
const QS = new URLSearchParams(location.search);
const MODE_PARAM = QS.get('mode');
const GATE_BYPASS = QS.has('selftest');
const DELIVERY_FEE = 9, DELIVERY_FREE_AT = 39;   // 外卖配送费：满 ¥39 免配
if (!MODE_PARAM && !GATE_BYPASS) location.replace('entry.html');

// ===== 全局状态 =====
const state = {
  models: {},        // storeCode -> 3D 模型配置
  mcpStores: [],     // MCP 真实门店列表
  menu: { categories: [], meals: {} },
  coupons: [], account: null,
  currentStore: null,     // 当前选中的 MCP 门店
  currentModel: null,     // 当前展示的 3D 模型（无模型门店为 null）
  currentCategory: null,
  cart: [], selectedCoupon: null,
  activeOrder: null, orders: [],
  points: 106.3, pointsToday: 0, gameBest: 0,
  theme: 'day', // 由设备本地时间自动判定，无手动开关
  mode: MODE_PARAM === 'delivery' ? 'delivery' : 'dinein', // 堂食 / 外卖到家
};

// 昼夜判定：以访问者设备本地时间为准（18:00 — 次日 06:00 为夜间）
const NIGHT_START = 18, NIGHT_END = 6;
function isNightTime() {
  if (location.search.includes('qa_night=1')) return true;
  if (location.search.includes('qa_day=1')) return false;
  const h = new Date().getHours();
  return h >= NIGHT_START || h < NIGHT_END;
}
const THEME_EXPOSURE = { day: '0.7', night: '1.1' };

// ===== 就餐方式 =====
const isDelivery = () => state.mode === 'delivery';
// 外卖配送费：满 ¥39 免配，否则 ¥9；堂食恒为 0
function calcDeliveryFee(raw, mode = state.mode) {
  if (mode !== 'delivery') return 0;
  return Number(raw) >= DELIVERY_FREE_AT ? 0 : DELIVERY_FEE;
}
// 把就餐方式写进界面：顶栏胶囊 / 门店标签 / 点餐条标题
function applyMode() {
  const d = isDelivery();
  const chip = $('#modeChip');
  if (chip) {
    chip.textContent = d ? '外卖到家 · 送餐上门' : '堂食 · 到店自取';
    chip.classList.toggle('nav-delivery', d);
  }
  const label = $('#storeLabel');
  if (label) label.textContent = d ? '出餐门店 STORE' : '选择你的餐厅 STORE';
  const eyebrow = $('.order-title span');
  if (eyebrow) eyebrow.textContent = d ? 'DELIVERY ORDER' : 'ORDER ONLINE';
  document.body.dataset.mode = state.mode;
}

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = n => '¥' + (Number(n) || 0).toFixed(2);
const rid = () => Math.random().toString(36).slice(2, 9);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

function toast(msg) {
  const w = $('#toastWrap');
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  w.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = '.3s'; setTimeout(() => t.remove(), 300); }, 2200);
}

// ===== 数据加载 =====
async function loadData() {
  const [store, menu] = await Promise.all([
    // no-cache：每次回源校验，避免调整门店/相机参数后仍读到浏览器启发式缓存
    fetch('data/store.json', { cache: 'no-cache' }).then(r => r.json()),
    fetch('data/menu.json', { cache: 'no-cache' }).then(r => r.json()),
  ]);
  state.models = store.models;
  state.mcpStores = store.mcpStores;
  state.coupons = store.coupons;
  state.account = store.account;
  state.points = store.account.availablePoint;
  // 关键：menu.json 的菜品对象本身不带 code，编码是 meals 的键。
  // 这里把 code 回填到每个菜品上，否则渲染出的 data-add / data-code 全是 "undefined"，
  // 点「+」只会弹 toast 而不会真正入库，商品详情也打不开。
  Object.entries(menu.meals).forEach(([code, m]) => { if (!m.code) m.code = code; });
  state.menu = menu;
  state.currentCategory = menu.categories[0];
  $('#pointsVal').textContent = state.points;
  $('#couponCount').textContent = state.coupons.length;
}

// ===== Sheet（底部抽屉）=====
function openSheet(title, html) {
  $('#sheetTitle').textContent = title;
  $('#sheetBody').innerHTML = html;
  $('#sheet').classList.remove('hidden');
  $('#sheetBackdrop').classList.remove('hidden');
  $('#sheetBody').scrollTop = 0;
}
function closeSheet() { $('#sheet').classList.add('hidden'); $('#sheetBackdrop').classList.add('hidden'); }

// 欢迎提示的存活时长（毫秒）。1.6s：弹出后自动消失，无需用户点击。
// 仅 ?welcome=<毫秒> 时会被 QA 临时改写，正常访问恒为 1600。
let WELCOME_MS = 1600;

// ===== 门店选择 =====
function renderStoreSelect() {
  const sel = $('#storeSelect');
  const with3d = state.mcpStores.filter(s => s.model);
  const plain = state.mcpStores.filter(s => !s.model);
  sel.innerHTML =
    `<optgroup label="◆ 已有 3D 实景模型">` +
    with3d.map(s => `<option value="${s.storeCode}">${esc(s.storeName)} 〔3D〕</option>`).join('') +
    `</optgroup><optgroup label="◇ MCP 附近门店">` +
    plain.map(s => `<option value="${s.storeCode}">${esc(s.storeName)}</option>`).join('') +
    `</optgroup>`;
  sel.value = state.currentStore?.storeCode || state.mcpStores[0].storeCode;
  sel.addEventListener('change', () => selectStore(sel.value));
}

function storeIntroText(s) {
  if (s.model) return state.models[s.model].intro;
  return '该门店来自麦当劳 MCP 实时门店列表（到店自取），可正常点餐；3D 实景建模正在陆续开发中。';
}

function renderStoreInfo() {
  const s = state.currentStore;
  if (!s) return;
  const m = s.model ? state.models[s.model] : null;
  $('#stName').innerHTML = esc(m ? m.name : s.storeName) + (s.model ? '<em>〔3D 实景〕</em>' : '<em>〔暂无 3D 模型〕</em>');
  $('#stIntro').textContent = storeIntroText(s);
  $('#stMeta').innerHTML = [
    `地址 <b>${esc(s.address)}</b>`,
    s.distance != null ? `距离 <b>约 ${s.distance} m</b>` : '',
    `营业 <b>${esc(s.hours)}</b>`,
    s.source ? `<b>${esc(s.source)}</b>` : '',
  ].filter(Boolean).map(x => `<span>${x}</span>`).join('');
  $('#stTags').innerHTML = (m ? m.tags : ['MCP 实时数据', '到店自取', '可预约']).map(t => `<span>${esc(t)}</span>`).join('') +
    (s.model ? '<span class="tag3d">3D MODEL READY</span>' : '');
}

// ===== 3D 场景 =====
// 昼夜双模型：日间版（无人工照明）与夜间版（灯光点亮）叠放，按本地时间交叉淡化。
const mvDay = $('#mvDay');
const mvNight = $('#mvNight');
let mv = mvDay;            // 当前激活的 viewer（其余代码沿用 mv）
let switching = false;

function viewerFor(theme) { return theme === 'night' ? mvNight : mvDay; }
function srcFor(model, theme) {
  if (theme === 'night') return model.glbNight || model.glb;
  return model.glbDay || model.glb;
}
const bothViewers = [mvDay, mvNight];

function orbitRange(model) {
  const r = model.orbitRadius; // 例：62m / 29m
  return { min: `auto 12deg ${r}`, max: `auto 88deg ${r}` };
}

function applyModelView(model) {
  const r = orbitRange(model);
  bothViewers.forEach(v => {
    const theme = v === mvNight ? 'night' : 'day';
    v.setAttribute('src', srcFor(model, theme));
    v.setAttribute('camera-orbit', model.cameraOrbit);
    v.setAttribute('camera-target', model.cameraTarget);
    v.setAttribute('min-camera-orbit', r.min);
    v.setAttribute('max-camera-orbit', r.max);
    v.jumpCameraToGoal?.();
  });
  setActiveViewer(state.theme);
  syncViewerClasses();
  renderViewTools(model);
  applyTheme(state.theme, false);
}

// 主题切换时把机位同步给另一个 viewer，再交叉淡化
function setActiveViewer(theme) {
  const next = viewerFor(theme);
  if (next === mv) return;
  try {
    const o = mv.getCameraOrbit?.(), t = mv.getCameraTarget?.();
    if (o && t) {
      next.setAttribute('camera-orbit', `${o.theta}rad ${o.phi}rad ${o.radius}m`);
      next.setAttribute('camera-target', `${t.x}m ${t.y}m ${t.z}m`);
    }
  } catch (e) { /* viewer 未就绪时保持各自默认机位 */ }
  mv = next;
  syncViewerClasses();
}
function syncViewerClasses() {
  bothViewers.forEach(v => v.classList.toggle('on', v === mv));
}

function renderViewTools(model) {
  $('#viewTools').innerHTML = (model.views || []).map((v, i) => `<button data-view="${v.id}" class="${i === 0 ? 'active' : ''}">${esc(v.label)}</button>`).join('');
  $$('#viewTools button').forEach(b => b.addEventListener('click', () => {
    const v = (model.views || []).find(x => x.id === b.dataset.view);
    if (!v) return;
    $$('#viewTools button').forEach(x => x.classList.toggle('active', x === b));
    mv.setAttribute('camera-orbit', v.orbit);
    mv.setAttribute('camera-target', v.target);
    mv.jumpCameraToGoal?.();
  }));
}

function waitModelLoad() {
  return new Promise(res => {
    if (mv.loaded) return res();
    const t = setTimeout(res, 4000);
    mv.addEventListener('load', () => { clearTimeout(t); res(); }, { once: true });
  });
}

// ===== 无 3D 门店：照片 / 占位轮播 =====
let carTimer = null, carCount = 0, carIdx = 0;
function slideItems(s) {
  if (Array.isArray(s.photos) && s.photos.length) return s.photos.map(p => ({ type: 'img', src: p }));
  return [1, 2, 3].map(i => ({ type: 'ph', i }));
}
function startCarousel(s) {
  stopCarousel();
  const items = slideItems(s);
  carCount = items.length; carIdx = 0;
  $('#pcTrack').innerHTML = items.map((it, i) => it.type === 'img'
    ? `<div class="pc-slide ${i === 0 ? 'active' : ''}"><img src="${it.src}" alt="${esc(s.storeName)} 实景照片 ${i + 1}" onerror="this.style.opacity='.1'"></div>`
    : `<div class="pc-slide placeholder ${i === 0 ? 'active' : ''}"><div class="placeholder-inner"><div class="ph-m">M</div><h3>${esc(s.storeName)}</h3><p>该门店暂未开发 3D 模型<br>实景照片整理中，敬请期待</p><span class="ph-tag">PHOTO COMING SOON</span></div></div>`).join('');
  $('#pcLabel').textContent = s.photos?.length ? '门店实景 · 该店暂无 3D 模型' : '实景资料整理中 · 自动轮播';
  $('#pcIdx').textContent = `1 / ${carCount}`;
  $('#photoCarousel').classList.remove('hidden');
  $('#pcCaption')?.classList.remove('hidden');
  $('#heroRight').classList.add('no-model');
  $('#modelNote').classList.add('hidden');
  if (carCount > 1) {
    carTimer = setInterval(() => {
      const slides = $$('#pcTrack .pc-slide');
      if (!slides.length) return;
      slides[carIdx].classList.remove('active');
      carIdx = (carIdx + 1) % carCount;
      slides[carIdx].classList.add('active');
      $('#pcIdx').textContent = `${carIdx + 1} / ${carCount}`;
    }, 3200);
  }
}
function stopCarousel() {
  if (carTimer) { clearInterval(carTimer); carTimer = null; }
  $('#photoCarousel').classList.add('hidden');
  $('#pcCaption')?.classList.add('hidden');
  $('#pcTrack').innerHTML = '';
}

async function loadModelForStore(s) {
  const model = s.model ? state.models[s.model] : null;
  if (!model) { // 无 3D 模型：照片轮播替代
    state.currentModel = null;
    startCarousel(s);
    return;
  }
  if (switching) return;
  switching = true;
  stopCarousel();
  $('#modelNote').classList.add('hidden');
  $('#heroRight').classList.remove('no-model');
  state.currentModel = model;
  applyModelView(model);
  await waitModelLoad();
  syncViewerClasses();
  switching = false;
}

function welcomeName(s) {
  let n = s.storeName.replace(/^麦当劳/, '').replace(/（[^）]*）$/, '').replace(/餐厅$/, '');
  if (!/店$/.test(n)) n += '店';
  return n;
}

function showWelcome(s) {
  showModal('WELCOME · 麦门', `欢迎来到${esc(welcomeName(s))}，麦门永存！`, null, '开始点餐', WELCOME_MS);
}

async function selectStore(storeCode, notify = true) {
  const s = state.mcpStores.find(x => x.storeCode === storeCode);
  if (!s || s.storeCode === state.currentStore?.storeCode) return;
  state.currentStore = s;
  const sel = $('#storeSelect');
  if (sel && sel.value !== storeCode) sel.value = storeCode;
  renderStoreInfo();
  await loadModelForStore(s);
  if (notify) showWelcome(s);
  toast(s.model ? '已切换 3D 实景门店' : '该门店暂无 3D 模型，已切换实景轮播');
}

// ===== 昼夜（自动）=====
let exposureAnim = null;
function animateExposure(target) {
  if (exposureAnim) cancelAnimationFrame(exposureAnim);
  const from = parseFloat(mv.getAttribute('exposure') || '1') || 1;
  const to = parseFloat(target);
  if (Math.abs(from - to) < 0.01) { bothViewers.forEach(v => v.setAttribute('exposure', String(to))); return; }
  const t0 = performance.now(), dur = 1400; // 1.4s 平滑过渡，避免突兀闪烁
  const step = now => {
    const k = Math.min(1, (now - t0) / dur);
    const e = k * k * (3 - 2 * k); // smoothstep
    const val = (from + (to - from) * e).toFixed(3);
    bothViewers.forEach(v => v.setAttribute('exposure', val));
    exposureAnim = k < 1 ? requestAnimationFrame(step) : null;
  };
  exposureAnim = requestAnimationFrame(step);
}
function applyTheme(theme, animate = true) {
  state.theme = theme === 'night' ? 'night' : 'day';
  const night = state.theme === 'night';
  document.documentElement.dataset.theme = state.theme;
  $('meta[name="theme-color"]').content = night ? '#141721' : '#f4efe3';
  const am = $('#autoMode');
  if (am) am.textContent = night ? '夜间 · 灯光已自动点亮' : '日间 · 自然光';
  // 昼夜两版模型交叉淡化；曝光与投影同步给两个 viewer
  if (state.currentModel) setActiveViewer(state.theme);
  if (animate) animateExposure(THEME_EXPOSURE[state.theme]);
  else bothViewers.forEach(v => v.setAttribute('exposure', THEME_EXPOSURE[state.theme]));
  bothViewers.forEach(v => {
    v.setAttribute('shadow-intensity', night ? '1.5' : '1.05');
    v.setAttribute('shadow-softness', night ? '0.95' : '0.75');
  });
}
// 后台定时校时：页面跨时段停留时自动切换
function watchLocalTime() {
  setInterval(() => {
    const want = isNightTime() ? 'night' : 'day';
    if (want !== state.theme) applyTheme(want);
  }, 30000);
}

// ===== 菜单（底部点餐条）=====
function renderCategoryBar() {
  $('#catBar').innerHTML = state.menu.categories.map((c, i) =>
    `<button class="cat-item ${c.name === state.currentCategory?.name ? 'active' : ''}" data-cat="${i}">${esc(c.name.replace('/多人餐', ' 多人餐'))}</button>`).join('');
  $$('.cat-item').forEach(b => b.addEventListener('click', () => {
    state.currentCategory = state.menu.categories[+b.dataset.cat];
    renderCategoryBar(); renderMealRail();
  }));
}

function renderMealRail() {
  const cat = state.currentCategory;
  const meals = cat.codes
    .map(c => { const m = state.menu.meals[c]; return m ? { ...m, code: m.code || c } : null; })
    .filter(Boolean);
  $('#mealRail').innerHTML = meals.map((m, i) => `
    <div class="meal-item" data-code="${m.code}" tabindex="0" role="button" aria-label="查看${esc(m.name)}">
      ${i < 2 ? '<span class="rank">HOT</span>' : ''}
      <img loading="lazy" src="${m.image}" alt="${esc(m.name)}" onerror="this.style.opacity='.15'">
      <div class="mi-name">${esc(m.name)}</div>
      <div class="mi-row"><span class="mi-price">${fmt(m.price)}</span><button class="mi-add" data-add="${m.code}" aria-label="加入购物袋">+</button></div>
    </div>`).join('');
  $$('.meal-item').forEach(el => {
    el.addEventListener('click', e => { if (!e.target.dataset.add) openDetail(el.dataset.code); });
    el.addEventListener('keydown', e => { if (e.key === 'Enter') openDetail(el.dataset.code); });
  });
  $$('.mi-add').forEach(b => b.addEventListener('click', e => {
    e.stopPropagation();
    // 快捷加购 = 该商品的默认搭配，与详情页直接点「加入购物袋」得到同一行，可正确合并数量
    if (addToCart(b.dataset.add, defaultOpts(b.dataset.add))) toast('已加入购物袋');
  }));
}

// ===== 商品详情 =====
let detailItem = null;
function openDetail(code) {
  const m = state.menu.meals[code];
  if (!m) return;
  detailItem = { code, opts: {}, qty: 1 };
  const combos = buildCombos(m);
  combos.forEach(c => { const d = c.options.find(o => o.default); if (d) detailItem.opts[c.key] = d.name; });
  const extra = combos.reduce((s, c) => s + (c.options.find(o => o.name === detailItem.opts[c.key])?.price || 0), 0);
  openSheet('商品详情', `
    <div class="detail-hero"><img src="${m.image}" alt="${esc(m.name)}" onerror="this.style.opacity='.15'"></div>
    <div class="detail-name">${esc(m.name)}</div>
    <div class="detail-price">${fmt(m.price)}</div>
    <div class="detail-desc">${esc(descFor(m))}</div>
    ${combos.map(c => `<div class="opt-group"><h4>${esc(c.label)}</h4>${c.options.map(o => `
      <div class="opt-item ${o.default ? 'selected' : ''}" data-key="${c.key}" data-val="${esc(o.name)}">
        <span>${esc(o.name)}</span><span class="opt-price">${o.price > 0 ? '+' + o.price : '默认'}</span>
      </div>`).join('')}</div>`).join('')}
    <div class="qty"><button id="qtyMinus">−</button><span class="q" id="qtyVal">1</span><button id="qtyPlus">+</button></div>
    <button class="px-btn gold" id="detailAdd">加入购物袋 · ${fmt((m.price + extra) * detailItem.qty)}</button>`);
  const refresh = () => {
    const ex = combos.reduce((s, c) => s + (c.options.find(o => o.name === detailItem.opts[c.key])?.price || 0), 0);
    $('#detailAdd').textContent = '加入购物袋 · ' + fmt((m.price + ex) * detailItem.qty);
  };
  $$('.opt-item').forEach(it => it.addEventListener('click', () => {
    detailItem.opts[it.dataset.key] = it.dataset.val;
    $$(`.opt-item[data-key="${it.dataset.key}"]`).forEach(x => x.classList.toggle('selected', x === it));
    refresh();
  }));
  $('#qtyMinus').addEventListener('click', () => { detailItem.qty = Math.max(1, detailItem.qty - 1); $('#qtyVal').textContent = detailItem.qty; refresh(); });
  $('#qtyPlus').addEventListener('click', () => { detailItem.qty = Math.min(20, detailItem.qty + 1); $('#qtyVal').textContent = detailItem.qty; refresh(); });
  $('#detailAdd').addEventListener('click', () => {
    // 加料/升级差价必须带进购物袋，否则详情页金额与袋内合计对不上
    const ex = combos.reduce((s, c) => s + (c.options.find(o => o.name === detailItem.opts[c.key])?.price || 0), 0);
    for (let i = 0; i < detailItem.qty; i++) addToCart(detailItem.code, { ...detailItem.opts }, ex);
    toast(`已加入购物袋 ${detailItem.qty} 份`);
    closeSheet(); renderMealRail();
  });
}
// 套餐类商品的默认搭配（与详情页初始选中项一致）
function defaultOpts(code) {
  const m = state.menu.meals[code];
  if (!m || !/三件套|套餐|随心拼|双人餐|乐园餐/.test(m.name)) return {};
  const o = {};
  buildCombos(m).forEach(c => { const d = c.options.find(x => x.default); if (d) o[c.key] = d.name; });
  return o;
}

function buildCombos(m) {
  if (/三件套|套餐|随心拼|双人餐|乐园餐/.test(m.name)) return [
    { key: 'main', label: '主餐', options: [{ name: '默认主餐', price: 0, default: true }, { name: '升级巨无霸', price: 6 }, { name: '升级板烧鸡腿堡', price: 4 }] },
    { key: 'side', label: '小食', options: [{ name: '中薯条', price: 0, default: true }, { name: '大薯条', price: 3 }, { name: '麦乐鸡(5块)', price: 5 }] },
    { key: 'drink', label: '饮品', options: [{ name: '中杯可乐', price: 0, default: true }, { name: '大杯可乐', price: 2.5 }, { name: '橙汁', price: 3 }] },
  ];
  return [
    { key: 'size', label: '规格', options: [{ name: '标准装', price: 0, default: true }, { name: '加大装', price: 4 }] },
    { key: 'extra', label: '加料', options: [{ name: '不加', price: 0, default: true }, { name: '双份芝士', price: 3 }, { name: '加培根', price: 4 }] },
  ];
}
function descFor(m) {
  if (/三件套|套餐/.test(m.name)) return '精选主餐搭配中薯与饮品，可在下方自定义主餐、小食与饮品。';
  if (/咖啡|雪冰|奶铁|美式|卡布|浓缩|燕麦/.test(m.name)) return '麦咖啡精选，现磨现制，浓郁醇香。';
  if (/麦旋风|新地|冰淇淋/.test(m.name)) return '经典冰淇淋甜点，绵密顺滑。';
  if (/薯条|薯饼|鸡翅|鸡块|鸡排|脆汁鸡|V翅/.test(m.name)) return '金黄酥脆，现炸小食，快乐加餐。';
  if (/周边|帽|徽章|丝巾|水手帽|百宝袋/.test(m.name)) return '限定周边，收藏必备。';
  return '麦当劳人气单品，严选食材，用心制作。';
}

// ===== 购物车 =====
// 数据模型：state.cart 是一组「行」，每行 = { code, opts, qty, price(单价), name, image, lineId }。
// 同商品同规格再点一次只累加 qty，不重复插行；渲染 / 结算 / 下单全部只读 state.cart，
// 因此「菜单加购 → 购物袋显示 → 结算金额」始终同源，不会出现加了却看不到的情况。
function sameOpts(a, b) { return JSON.stringify(a || {}) === JSON.stringify(b || {}); }

function addToCart(code, opts, extra = 0) {
  const m = state.menu.meals[code];
  if (!m) { console.warn('addToCart: 未知菜品编码', code); toast('该商品暂不可售，请换一个试试'); return false; }
  const price = (Number(m.price) || 0) + (Number(extra) || 0); // 含加料/升级差价，与详情页显示金额一致
  const line = state.cart.find(c => c.code === String(code) && sameOpts(c.opts, opts) && c.price === price);
  if (line) line.qty += 1;
  else state.cart.push({ code: String(code), opts: opts || {}, qty: 1, lineId: rid(), price, name: m.name, image: m.image });
  updateCartBadge();
  return true;
}
function changeQty(lineId, d) {
  const line = state.cart.find(c => c.lineId === lineId);
  if (!line) return;
  line.qty += d;
  if (line.qty <= 0) state.cart = state.cart.filter(c => c.lineId !== lineId);
  updateCartBadge(); renderCart();
}
const cartCount = () => state.cart.reduce((s, c) => s + c.qty, 0);
function cartTotal() { return state.cart.reduce((s, c) => s + c.price * c.qty, 0); }
function updateCartBadge() {
  const n = cartCount();
  $('#cartCount').textContent = n;
  $('#cartBrief').textContent = `购物袋 ${n} 件`;
  $('#cartBriefTotal').textContent = fmt(cartTotal());
}
function renderCart() {
  if (!state.cart.length) {
    openSheet('购物袋', `<div class="empty">购物袋还是空的<br>↓ 回到下方菜单挑点好吃的 ↓</div><button class="px-btn gold" id="goMenu">去点餐</button>`);
    $('#goMenu').addEventListener('click', closeSheet);
    return;
  }
  openSheet('购物袋', state.cart.map(c => `
    <div class="cart-item">
      <img src="${c.image}" onerror="this.style.opacity='.15'">
      <div><div class="ci-name">${esc(c.name)}</div><div class="ci-opt">${esc(Object.values(c.opts).join(' / ') || '默认搭配')}</div></div>
      <div class="ci-price">${fmt(c.price * c.qty)}</div>
      <div class="ci-qty"><button data-dec="${c.lineId}">−</button><span>${c.qty}</span><button data-inc="${c.lineId}">+</button></div>
    </div>`).join('') + `
    <div class="cart-foot"><span class="cart-total">共 ${cartCount()} 件<b>${fmt(cartTotal())}</b></span><button class="px-btn primary" id="goCheckout">去结算</button></div>`);
  $$('[data-dec]').forEach(b => b.addEventListener('click', () => changeQty(b.dataset.dec, -1)));
  $$('[data-inc]').forEach(b => b.addEventListener('click', () => changeQty(b.dataset.inc, +1)));
  $('#goCheckout').addEventListener('click', renderCheckout);
}

// ===== 结算下单 =====
function renderCheckout() {
  state.selectedCoupon = null;
  const raw = cartTotal();
  const fee = calcDeliveryFee(raw);
  const d = isDelivery();
  const couponable = state.coupons.filter(c => c.usable && c.price && raw >= (c.minOrder || 0));
  const payOf = coupon => Math.max(0, raw - (coupon ? coupon.price : 0) + fee);
  openSheet('确认订单', `
    <div class="section-title">${d ? '出餐门店 · 配送到家' : '取餐门店'}</div>
    <div class="chk-item"><span>${esc(state.currentStore?.storeName || '')}</span><span>${d ? '外卖配送' : '到店自取'}</span></div>
    ${d ? `<div class="chk-item"><span>配送至</span><span>广州市越秀区北京路 182 号 18F</span></div>
    <div class="chk-item"><span>预计送达</span><span>约 30–40 分钟</span></div>` : ''}
    <div class="section-title">优惠券</div>
    ${couponable.length ? couponable.map(c => `<div class="coupon-pick" data-coupon="${c.id}"><span>${esc(c.name)}</span><span class="cp-tag">${esc(c.tag)}</span><span class="spacer"></span><span style="color:var(--red)">-¥${c.price}</span></div>`).join('') : '<div class="chk-item"><span>暂无可用券</span></div>'}
    <div class="section-title">明细</div>
    ${state.cart.map(c => `<div class="chk-item"><span>${esc(c.name)} ${esc(Object.values(c.opts).join('/') || '')}${c.qty > 1 ? ' ×' + c.qty : ''}</span><span>${fmt(c.price * c.qty)}</span></div>`).join('')}
    ${d ? `<div class="chk-item"><span>配送费${fee ? '' : '（已满 ¥' + DELIVERY_FREE_AT + ' 免配送费）'}</span><span>${fee ? fmt(fee) : '¥0.00'}</span></div>` : ''}
    <div class="chk-total"><span>合计</span><b id="chkTotal">${fmt(payOf(null))}</b></div>
    <div class="row"><button class="px-btn" id="backCart">返回</button><button class="px-btn primary" id="submitOrder">提交订单</button></div>`);
  $$('.coupon-pick').forEach(cp => cp.addEventListener('click', () => {
    state.selectedCoupon = state.selectedCoupon === cp.dataset.coupon ? null : cp.dataset.coupon;
    $$('.coupon-pick').forEach(x => x.classList.toggle('selected', x.dataset.coupon === state.selectedCoupon));
    const c = state.coupons.find(c => c.id === state.selectedCoupon);
    $('#chkTotal').textContent = fmt(payOf(c));
  }));
  $('#backCart').addEventListener('click', renderCart);
  $('#submitOrder').addEventListener('click', submitOrder);
}
function submitOrder() {
  const raw = cartTotal();
  const c = state.coupons.find(c => c.id === state.selectedCoupon);
  const fee = calcDeliveryFee(raw);
  const total = Math.max(0, raw - (c ? c.price : 0) + fee);
  const order = {
    id: 'A-' + Math.floor(100 + Math.random() * 900),
    time: new Date().toLocaleString('zh-CN'),
    store: state.currentStore?.storeName || '',
    mode: state.mode,
    items: state.cart.map(c => c.name + (Object.values(c.opts).length ? '（' + Object.values(c.opts).join('/') + '）' : '') + (c.qty > 1 ? ' ×' + c.qty : '')),
    total, raw, fee, discount: c ? c.price : 0, status: 'going', step: 0,
  };
  state.activeOrder = order;
  state.orders.unshift({ ...order, status: 'done' });
  state.cart = [];
  updateCartBadge();
  const earn = Math.round(total);
  state.points += earn; state.pointsToday += earn;
  $('#pointsVal').textContent = state.points;
  closeSheet();
  const tail = isDelivery()
    ? `配送费 ${fee ? fmt(fee) : '已免'} · 预计 30–40 分钟送达<br>骑手接单后可在订单里查看进度。`
    : '厨房已开始备餐，请关注左下角取餐进度。';
  showModal(isDelivery() ? '外卖下单成功' : '下单成功',
    `订单号 <b>${order.id}</b><br>${isDelivery() ? '出餐门店' : '门店'} ${esc(order.store)}<br>共 ${fmt(total)}${c ? '（已用券）' : ''} · 获得 ${earn} 积分<br><br>${tail}`,
    () => startCooking(order));
}
function startCooking(order) {
  const right = $('#heroRight');
  const tip = document.createElement('div');
  tip.className = 'cook-tip';
  tip.id = 'cookTip';
  right.appendChild(tip);
  const steps = ['接单', '备餐', '制作', '出餐', '取餐'];
  let step = 0; const totalSteps = 4; const duration = 9000; const tick = duration / totalSteps;
  const render = () => {
    tip.innerHTML = `<b>${order.id}</b> ${['接单中', '备餐中', '制作中', '出餐中', '餐品就绪'][step]}
      <div class="progress-inline"><span>${steps.map((s, i) => i <= step ? '■' : '□').join('')}</span><div class="pc-bar"><div class="pc-fill" style="width:${step / totalSteps * 100}%"></div></div></div>`;
  };
  render();
  const timer = setInterval(() => {
    step++;
    if (step >= totalSteps) {
      clearInterval(timer);
      tip.querySelector('.pc-fill').style.width = '100%';
      tip.innerHTML = `<b>${order.id}</b> 餐品已就绪 · 请到柜台取餐 🎉`;
      setTimeout(() => { tip.remove(); toast(`订单 ${order.id} 已交付`); renderOrders(); }, 3200);
      return;
    }
    render();
  }, tick);
}

// ===== 订单 / 优惠券 / 积分 =====
function renderOrders() {
  if (!state.orders.length) { openSheet('订单历史', '<div class="empty">还没有订单<br>下单后会记录在这里</div>'); return; }
  openSheet('订单历史', state.orders.map(o => `
    <div class="order-card">
      <div class="oc-head"><span>${esc(o.id)}</span><span class="oc-time">${esc(o.time)}</span></div>
      <span class="oc-status">已完成</span>
      <div class="oc-items">${o.items.map(esc).join('<br>')}</div>
      <div class="oc-total">${fmt(o.total)}${o.discount ? `（已优惠 ${fmt(o.discount)}）` : ''}</div>
    </div>`).join(''));
}
function renderCoupons() {
  openSheet('我的优惠券', state.coupons.map(c => `
    <div class="coupon-card">
      <img src="${c.image}" onerror="this.style.opacity='.15'">
      <div><div class="cc-name">${esc(c.name)}</div><div class="cc-price">${fmt(c.price)}</div><div class="cc-valid">${esc(c.valid)}</div></div>
      <span class="cc-tag">${esc(c.tag)}</span>
    </div>`).join('') + '<div class="section-title">以上优惠券来自麦当劳会员卡包（MCP 真实数据）</div>');
}
function renderPoints() {
  openSheet('积分中心', `
    <div class="pts-hero"><div class="pts-num">${state.points.toFixed(1)}</div><div class="pts-label">麦享会可用积分</div></div>
    <div class="pts-grid">
      <div class="pts-box"><b>${state.account.accumulativePoint}</b>累计积分</div>
      <div class="pts-box"><b>${state.account.expiredPoint}</b>已过期积分</div>
      <div class="pts-box"><b>${state.pointsToday}</b>今日下单获得</div>
      <div class="pts-box"><b>${state.gameBest}</b>小游戏最高分</div>
    </div>
    <div class="section-title">积分玩法</div>
    <div class="game-tip">每消费 1 元得 1 积分；玩「接薯条」小游戏每 1 分奖励 0.5 积分；积分可在麦当劳 App 兑换优惠。</div>`);
}

// ===== 小游戏：接薯条 =====
let gameRunning = false, gameScore = 0, gameReq = null;
function startGame() {
  openSheet('接薯条小游戏', `
    <div class="game-wrap"><canvas id="gameCanvas"></canvas></div>
    <div class="game-score"><span>得分 <span id="gameScore">0</span></span><span>最高 <span id="gameBest">${state.gameBest}</span></span></div>
    <div class="game-tip">左右拖动薯条盒接住下落的薯条，接漏扣生命 · 30 秒挑战</div>
    <button class="px-btn gold" id="gameStart">开始游戏</button>`);
  $('#gameStart').addEventListener('click', () => initGameCanvas(true));
}
function initGameCanvas(forceStart) {
  const cv = $('#gameCanvas'); if (!cv) return;
  if (gameRunning && !forceStart) return;
  const ctx = cv.getContext('2d');
  const W = cv.clientWidth || 460, H = 230;
  cv.width = W; cv.height = H;
  gameRunning = true; gameScore = 0;
  let basket = { x: W / 2, w: 72 }, fries = [], life = 3, start = performance.now();
  let dragging = false;
  const moveTo = x => { basket.x = Math.max(basket.w / 2, Math.min(W - basket.w / 2, x)); };
  const onMove = e => { const r = cv.getBoundingClientRect(); moveTo((e.touches ? e.touches[0].clientX : e.clientX) - r.left); };
  cv.addEventListener('mousedown', () => dragging = true);
  cv.addEventListener('mousemove', e => { if (dragging) onMove(e); });
  cv.addEventListener('touchstart', e => { dragging = true; onMove(e); });
  cv.addEventListener('touchmove', e => { if (dragging) onMove(e); });
  cv.addEventListener('mouseup', () => dragging = false);
  cv.addEventListener('touchend', () => dragging = false);
  if (gameReq) cancelAnimationFrame(gameReq);
  const loop = now => {
    const time = 30 - (now - start) / 1000;
    if (time <= 0 || life <= 0) { endGame(); return; }
    ctx.fillStyle = '#f7f2e6'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(48,40,26,.06)';
    for (let gx = 0; gx < W; gx += 16) for (let gy = 0; gy < H; gy += 16) ctx.fillRect(gx, gy, 2, 2);
    if (Math.random() < 0.05) fries.push({ x: Math.random() * (W - 20) + 10, y: -10, s: Math.random() * 2 + 2 });
    fries.forEach(f => f.y += f.s);
    fries = fries.filter(f => f.y < H + 20);
    fries.forEach(f => {
      ctx.fillStyle = '#e6a400'; ctx.fillRect(f.x - 4, f.y, 8, 20);
      ctx.fillStyle = '#ffc72c'; ctx.fillRect(f.x - 4, f.y, 8, 6);
    });
    const rest = [];
    fries.forEach(f => {
      if (f.y + 18 > H - 34 && f.y + 18 < H - 18 && Math.abs(f.x - basket.x) < basket.w / 2) gameScore++;
      else if (f.y > H - 12) life--;
      else rest.push(f);
    });
    fries = rest;
    ctx.fillStyle = '#da291c'; ctx.fillRect(basket.x - basket.w / 2, H - 30, basket.w, 22);
    ctx.fillStyle = '#ffc72c';
    ctx.fillRect(basket.x - basket.w / 2 + 8, H - 38, 8, 8); ctx.fillRect(basket.x + basket.w / 2 - 16, H - 38, 8, 8);
    ctx.fillStyle = '#241f18'; ctx.font = '12px Zpix, monospace'; ctx.textAlign = 'left';
    ctx.fillText('得分 ' + gameScore, 10, 18);
    ctx.textAlign = 'right'; ctx.fillText('生命 ' + '♥'.repeat(Math.max(0, life)), W - 10, 18);
    ctx.textAlign = 'center'; ctx.fillText(Math.ceil(time) + 's', W / 2, 18);
    $('#gameScore').textContent = gameScore;
    gameReq = requestAnimationFrame(loop);
  };
  gameReq = requestAnimationFrame(loop);
}
function endGame() {
  gameRunning = false;
  if (gameReq) cancelAnimationFrame(gameReq);
  const earn = Math.round(gameScore * 0.5);
  state.points += earn; state.pointsToday += earn;
  if (gameScore > state.gameBest) state.gameBest = gameScore;
  $('#pointsVal').textContent = state.points;
  showModal('游戏结束', `得分 <b>${gameScore}</b> 分<br>奖励 ${earn} 积分（已入账）`, () => { renderPoints(); });
}

// ===== 弹层 =====
// autoCloseMs > 0：轻提示型弹窗，弹出后自动消失（无「确定」按钮，底部一条倒计时进度条）。
// autoCloseMs = 0：需要用户确认的弹窗（下单成功 / 游戏结束等），保留按钮。
let modalTimer = null;
function hideModal({ fire = true } = {}) {
  if (modalTimer) { clearTimeout(modalTimer); modalTimer = null; }
  const m = $('#modal');
  if (m.classList.contains('hidden')) return;
  m.classList.add('hidden');
  const cb = m.__onOk;
  m.__onOk = null;
  if (fire && cb) cb();
}
function showModal(title, html, onOk, okText = '好的', autoCloseMs = 0) {
  hideModal({ fire: false });
  const m = $('#modal');
  m.__onOk = onOk || null;
  const bar = autoCloseMs
    ? `<div class="modal-timer" aria-hidden="true"><i style="animation-duration:${autoCloseMs}ms"></i></div>`
    : `<button class="px-btn primary" id="modalOk">${okText}</button>`;
  m.innerHTML = `<div class="modal-card${autoCloseMs ? ' auto' : ''}"><h3>${esc(title)}</h3><p>${html}</p>${bar}</div>`;
  m.classList.remove('hidden');
  if (autoCloseMs) {
    modalTimer = setTimeout(() => hideModal(), autoCloseMs);
  } else {
    $('#modalOk').addEventListener('click', () => hideModal());
  }
}
$('#modal').addEventListener('click', e => { if (e.target === e.currentTarget) hideModal(); });

// ===== 绑定 =====
function bindUI() {
  $('#sheetClose').addEventListener('click', closeSheet);
  $('#sheetBackdrop').addEventListener('click', closeSheet);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeSheet(); hideModal(); } });
  // 顶栏就餐方式胶囊：回到进入页重新选择
  $('#modeChip').addEventListener('click', () => { location.href = 'entry.html'; });
  $('#pointsChip').addEventListener('click', renderPoints);
  $('#couponChip').addEventListener('click', renderCoupons);
  $('#ordersChip').addEventListener('click', renderOrders);
  $('#cartChip').addEventListener('click', renderCart);
  $('#openCartBtn').addEventListener('click', renderCart);
  $('#brandBtn').addEventListener('click', () => { $('#mealRail').scrollTo({ left: 0 }); });
}

// ===== 初始化 =====
(async function init() {
  if (!MODE_PARAM && !GATE_BYPASS) return; // 已跳回进入页：不再初始化点餐台
  await loadData();
  state.currentStore = state.mcpStores[0]; // 默认富士山 3D 场景特辑
  renderStoreSelect();
  renderStoreInfo();
  renderCategoryBar();
  renderMealRail();
  updateCartBadge();
  bindUI();
  applyMode(); // 堂食 / 外卖到家：顶栏胶囊、门店标签、点餐条标题
  applyTheme(isNightTime() ? 'night' : 'day', false); // 依据设备本地时间自动设定
  watchLocalTime();
  try {
    await customElements.whenDefined('model-viewer');
    await loadModelForStore(state.currentStore);
  } catch (e) {
    console.error('3D init error', e);
    toast('3D 场景初始化失败：' + e.message);
  }
  // 深链：?store=1400086（不弹欢迎窗，便于分享与调试）
  const deepStore = new URLSearchParams(location.search).get('store');
  if (deepStore && state.mcpStores.some(s => s.storeCode === deepStore)) await selectStore(deepStore, false);
  // QA：?welcome=1 强制弹一次欢迎提示（用于验证「1~2 秒自动消失」，正常访问不会触发）
  //      ?welcome=<毫秒> 可临时拉长时长，便于截图核对
  const welcomeQ = new URLSearchParams(location.search).get('welcome');
  if (welcomeQ !== null) {
    if (welcomeQ !== '1' && Number(welcomeQ) > 0) WELCOME_MS = Number(welcomeQ); // 1 = 用默认 1600ms
    showWelcome(state.currentStore);
  }
  window.__app = { state, selectStore, applyTheme, isNightTime, openDetail, renderCart, startGame, applyMode, calcDeliveryFee };
  if (QS.has('debug')) {
    setTimeout(() => {
      const o = mv.getCameraOrbit?.();
      const dim = mv.getDimensions?.();
      const r = mv.getBoundingClientRect();
      document.title = 'DBG orbit=' + mv.getAttribute('camera-orbit') +
        ' real=' + (o ? o.radius.toFixed(1) : '?') + 'm' +
        ' dim=' + (dim ? `${dim.x.toFixed(1)}x${dim.y.toFixed(1)}x${dim.z.toFixed(1)}` : '?') +
        ' rect=' + Math.round(r.width) + 'x' + Math.round(r.height) +
        ' fov=' + mv.getAttribute('field-of-view');
    }, 7000);
  }
  // ===== 自测（?selftest=1）=====
  if (location.search.includes('selftest')) {
    setTimeout(async () => {
      try {
        const results = [];
        const ok = (name, cond) => results.push((cond ? 'PASS ' : 'FAIL ') + name);
        ok('mcpStores', state.mcpStores.length >= 8);
        ok('defaultFuji', state.currentStore.storeCode === '19541' && !!state.currentModel);
        await selectStore('1400067'); // 无 3D 模型门店（有实景照片）
        const car = $('#photoCarousel');
        ok('noModelCarousel', !state.currentModel && !car.classList.contains('hidden') && $$('#pcTrack .pc-slide').length === 3);
        ok('welcomeModal', $('#modal').innerHTML.includes('欢迎来到广州海珠广场店，麦门永存！'));
        ok('welcomeNoButton', !$('#modalOk') && !!$('.modal-timer')); // 自动消失型：无「确定」按钮
        await new Promise(r => setTimeout(r, 1900));
        ok('welcomeAutoDismiss', $('#modal').classList.contains('hidden')); // 约 1.6s 后自动关闭
        await selectStore('1400477'); // 沙面（有模型）
        ok('hasModel', state.currentStore.storeCode === '1400477' && state.currentModel?.glb.includes('Shamian') && car.classList.contains('hidden'));
        // 新增的两座 3D 建模门店：圣托利温泉庄园 / McDonald's Kew
        const group3d = $$('#storeSelect optgroup')[0];
        ok('store3dCount', !!group3d && group3d.querySelectorAll('option').length === 5);
        const radiusOf = a => String(a || '').split(' ').pop();
        await selectStore('9900001');
        ok('modelSantorini', state.currentStore.storeCode === '9900001'
          && state.currentModel?.glb.includes('Santorini_McDonalds')
          && String(mv.getAttribute('src')).includes('Santorini_McDonalds')
          && car.classList.contains('hidden'));
        const rSantorini = radiusOf(mv.getAttribute('max-camera-orbit'));
        await selectStore('9900002');
        ok('modelUKKew', state.currentStore.storeCode === '9900002'
          && state.currentModel?.glb.includes('UKKew_McDonalds')
          && String(mv.getAttribute('src')).includes('UKKew_McDonalds'));
        const rKew = radiusOf(mv.getAttribute('max-camera-orbit'));
        ok('radiusPerStore', rSantorini === '54m' && rKew === '44m');
        await selectStore('1400477');
        const orbit = a => a.split(' ').pop();
        ok('zoomLocked', mv.hasAttribute('disable-zoom') && mv.hasAttribute('disable-pan') && orbit(mv.getAttribute('min-camera-orbit')) === orbit(mv.getAttribute('max-camera-orbit')));
        // ===== 购物袋：走真实 UI 路径（点菜单上的「+」/ 进详情页加入）=====
        const addBtn = $('#mealRail .mi-add');
        const uiCode = addBtn && addBtn.dataset.add;
        ok('mealCodeValid', !!uiCode && uiCode !== 'undefined' && !!state.menu.meals[uiCode]);
        addBtn.click();
        ok('uiAddToCart', state.cart.length === 1 && state.cart[0].code === uiCode);
        renderCart();
        ok('uiCartSheet', $('#sheetBody').innerHTML.includes(esc(state.menu.meals[uiCode].name)));
        closeSheet();
        state.cart = []; updateCartBadge();
        openDetail(uiCode);
        ok('openDetail', !!$('#detailAdd'));
        $('#detailAdd').click(); // 详情页加入购物袋（会关闭抽屉）
        ok('detailAddToCart', state.cart.length === 1 && state.cart[0].code === uiCode);
        state.cart = []; updateCartBadge();
        addToCart('9900016075', { main: '默认主餐' });
        addToCart('4810', {});
        ok('addToCart', state.cart.length === 2);
        // 同商品同规格再加一次 → 合并数量而不是重复插行
        const cartBackup = state.cart.slice();
        state.cart = [];
        addToCart('4810', {}); addToCart('4810', {});
        ok('qtyMerge', state.cart.length === 1 && state.cart[0].qty === 2 && cartCount() === 2);
        state.cart = cartBackup; updateCartBadge();
        renderCart();
        ok('renderCart', $('#sheetBody').innerHTML.includes('龙焰芝士棒'));
        renderCheckout();
        ok('renderCheckout', !!$('#submitOrder'));
        $('.coupon-pick')?.click();
        ok('couponPick', !!state.selectedCoupon);
        $('#submitOrder').click();
        ok('submitOrder', state.orders.length === 1 && Math.abs(state.activeOrder.discount - 20.48) < 0.01);
        $('#modalOk')?.click(); // 关闭下单弹窗 → 触发取餐进度
        const tip = $('#cookTip'); ok('cookProgress', !!tip); tip && tip.remove();
        ok('pointsAward', state.points > 106.3);
        ok('cartCleared', state.cart.length === 0);
        renderOrders(); ok('renderOrders', $('#sheetBody').innerHTML.includes(state.activeOrder.id));
        renderCoupons(); ok('renderCoupons', $('#sheetBody').innerHTML.includes('码'));
        renderPoints(); ok('renderPoints', $('#sheetBody').innerHTML.includes('麦享会'));
        applyTheme('night', false);
        ok('nightTheme', document.documentElement.dataset.theme === 'night' && mv.getAttribute('exposure') === '1.1' && $('#autoMode').textContent.includes('夜间'));
        applyTheme('day', false);
        ok('dayTheme', document.documentElement.dataset.theme === 'day' && mv.getAttribute('exposure') === '0.7' && $('#autoMode').textContent.includes('日间'));
        ok('autoTimeJudge', typeof isNightTime() === 'boolean');
        // 全局字号调节：--fs 改写后真实字号变化
        ok('fontScale', (() => {
          window.__fontscale.set(1.26);
          const big = parseFloat(getComputedStyle($('.mi-name')).fontSize);
          window.__fontscale.set(1);
          const normal = parseFloat(getComputedStyle($('.mi-name')).fontSize);
          return !!$('#fsBtn') && big > normal;
        })());

        // ===== 就餐方式（由进入页传入）=====
        ok('modeDefault', state.mode === 'dinein' && $('#modeChip').textContent.includes('堂食'));
        ok('deliveryFeeRule', calcDeliveryFee(20, 'delivery') === 9 && calcDeliveryFee(39, 'delivery') === 0 && calcDeliveryFee(20, 'dinein') === 0);
        state.mode = 'delivery'; applyMode();
        ok('deliveryLabels', $('#modeChip').textContent.includes('外卖') && $('#storeLabel').textContent.includes('出餐门店'));
        addToCart('4810', {});
        const rawT = cartTotal(), feeT = calcDeliveryFee(rawT);
        renderCheckout();
        ok('deliveryCheckout', $('#sheetBody').innerHTML.includes('配送费') && $('#sheetBody').innerHTML.includes('预计送达')
          && $('#chkTotal').textContent === fmt(rawT + feeT));
        closeSheet();
        state.mode = 'dinein'; applyMode(); state.cart = []; updateCartBadge();
        ok('modeReset', state.mode === 'dinein' && $('#modeChip').textContent.includes('堂食'));
        document.title = 'SELFTEST ' + results.join(' | ');
      } catch (e) { document.title = 'SELFTEST ERROR ' + e.message; }
    }, 2500);
  }
})();
