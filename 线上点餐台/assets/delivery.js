/* 麦当劳 · 外卖到家工作台（麦乐送）
   单页五区：01 地址 / 02 配送方式 / 03 选餐 / 04 结算支付 / 05 订单状态与历史
   数据：data/delivery.json（MCP 地址 + 订单）、data/store.json（门店 / 优惠券）、data/menu.json（菜单） */
'use strict';

window.addEventListener('error', e => { document.title = 'ERR: ' + e.message + ' @' + (e.lineno || '?'); });

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = n => '¥' + (Number(n) || 0).toFixed(2);
const rid = () => Math.random().toString(36).slice(2, 8);
const QS = new URLSearchParams(location.search);
const QA = QS.has('selftest');

const LS_ADDR = 'mcd.dl.addresses', LS_ORDER = 'mcd.dl.orders';

const state = {
  config: {},
  stores: [], menu: { categories: [], meals: {} }, coupons: [],
  orders: [],            // MCP 历史订单
  localOrders: [],       // 本页演示订单
  addresses: [], addressId: null,
  shipMode: 'standard', timeMode: 'now', reserveTime: '', storeCode: null, tableware: false,
  cart: [], couponId: null, pay: 'wechat',
  filter: 'all', paying: false,
};

// ===== 昼夜（与点餐台/进入页同一口径） =====
const NIGHT_START = 18, NIGHT_END = 6;
function isNightTime() {
  if (QS.get('qa_night') === '1') return true;
  if (QS.get('qa_day') === '1') return false;
  const h = new Date().getHours();
  return h >= NIGHT_START || h < NIGHT_END;
}
function applyTheme(theme) {
  const night = theme === 'night';
  document.documentElement.dataset.theme = night ? 'night' : 'day';
  $('meta[name="theme-color"]').content = night ? '#141721' : '#f4efe3';
}

// ===== 通用 UI =====
function toast(msg) {
  const w = $('#toastWrap'); const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg; w.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = '.3s'; setTimeout(() => t.remove(), 300); }, 2000);
}
// 订单抽屉（顶栏「订单」入口）：历史订单不再平铺在页面上
function openSheet(title) {
  $('#sheetTitle').textContent = title;
  $('#sheetBody').innerHTML = '';
  $('#sheet').classList.remove('hidden');
  $('#sheetBackdrop').classList.remove('hidden');
  $('#sheetBody').scrollTop = 0;
}
function closeSheet() { $('#sheet').classList.add('hidden'); $('#sheetBackdrop').classList.add('hidden'); }
let modalTimer = null;
function hideModal() { if (modalTimer) { clearTimeout(modalTimer); modalTimer = null; } $('#modal').classList.add('hidden'); }
function showModal(title, html, onOk, okText = '好的', autoCloseMs = 0) {
  hideModal();
  const m = $('#modal');
  m.__onOk = onOk || null;
  m.innerHTML = `<div class="modal-card${autoCloseMs ? ' auto' : ''}"><h3>${esc(title)}</h3><p>${html}</p>${
    autoCloseMs ? `<div class="modal-timer"><i style="animation-duration:${autoCloseMs}ms"></i></div>`
      : `<button class="px-btn primary" id="modalOk">${okText}</button>`}</div>`;
  m.classList.remove('hidden');
  if (autoCloseMs) modalTimer = setTimeout(() => { hideModal(); const cb = m.__onOk; m.__onOk = null; cb && cb(); }, autoCloseMs);
  else $('#modalOk').addEventListener('click', () => { hideModal(); const cb = m.__onOk; m.__onOk = null; cb && cb(); });
}
$('#modal').addEventListener('click', e => { if (e.target === e.currentTarget) hideModal(); });

// ===== 持久化（自测时只走内存，避免污染真实浏览器数据） =====
function persist() {
  if (QA) return;
  try {
    localStorage.setItem(LS_ADDR, JSON.stringify(state.addresses));
    localStorage.setItem(LS_ORDER, JSON.stringify(state.localOrders));
  } catch (e) { /* 隐私模式忽略 */ }
}
function restore() {
  if (QA) return;
  try {
    const a = JSON.parse(localStorage.getItem(LS_ADDR) || 'null');
    if (Array.isArray(a)) state.addresses = a;
    const o = JSON.parse(localStorage.getItem(LS_ORDER) || 'null');
    if (Array.isArray(o)) state.localOrders = o;
  } catch (e) { /* ignore */ }
}

// ===== 01 地址 =====
function defaultAddr() { return state.addresses.find(a => a.isDefault) || state.addresses[0] || null; }
function ensureDefault() {
  if (!state.addresses.length) { state.addressId = null; return; }
  if (!state.addresses.some(a => a.isDefault)) state.addresses[0].isDefault = true;
  if (!state.addresses.some(a => a.id === state.addressId)) state.addressId = defaultAddr().id;
}
function renderAddresses() {
  ensureDefault();
  const box = $('#addrList');
  if (!state.addresses.length) {
    box.innerHTML = `<div class="addr-empty">还没保存收货地址<br>点右上「+ 新增」填写第一个配送地址</div>`;
    $('#addrNote').textContent = 'MCP delivery-query-addresses 当前返回空列表；新增后地址保存在本地浏览器，用于本页演示下单。';
  } else {
    box.innerHTML = state.addresses.map(a => `
      <div class="addr-card ${a.id === state.addressId ? 'active' : ''}">
        <button class="ac-pick" data-addr="${a.id}">
          <span class="ac-top">
            <span class="ac-name">${esc(a.name)}</span>
            <span class="ac-tel">${esc(a.phone)}</span>
            <span class="ac-tag ${a.isDefault ? 'def' : ''}">${a.isDefault ? '默认' : esc(a.tag || '家')}</span>
          </span>
          <span class="ac-addr">${esc(a.area)} ${esc(a.detail)}</span>
        </button>
        <span class="ac-ops">
          ${a.isDefault ? '<span class="ac-cur">当前默认</span>' : `<button data-def="${a.id}">设为默认</button>`}
          <button data-edit="${a.id}">编辑</button>
          <button data-del="${a.id}">删除</button>
        </span>
      </div>`).join('');
    $('#addrNote').textContent = `已保存 ${state.addresses.length} 个地址，当前配送到「${defaultAddr().name}」的地址（演示数据保存在本地）。`;
  }
  renderShipEta();
  syncAddrBtn();
}
let editId = null;   // 当前内联表单正在编辑的地址 id（null = 新增）
function syncAddrBtn() {
  const open = !$('#addrForm').classList.contains('hidden');
  $('#addAddr').textContent = open ? '收起' : '+ 新增';
  $('#addrList').classList.toggle('filling', open);
}
function closeAddrForm() {
  editId = null;
  const w = $('#addrForm');
  w.classList.add('hidden');
  w.innerHTML = '';
  syncAddrBtn();
}
function toggleAddrForm() {
  if (!$('#addrForm').classList.contains('hidden')) { closeAddrForm(); return; }
  openAddressForm();
}
function openAddressForm(id) {
  const w = $('#addrForm');
  // 再次点同一个「编辑」= 收起
  if (id && editId === id) { closeAddrForm(); return; }
  editId = id || null;
  const a = id ? state.addresses.find(x => x.id === id) : null;
  const areas = ['越秀区', '荔湾区', '海珠区', '天河区', '白云区', '番禺区'];
  w.innerHTML = `
    <div class="addr-form">
      <div class="af-head"><b>${a ? '编辑收货地址' : '新增收货地址'}</b><i>${a ? 'EDIT ADDRESS' : 'NEW ADDRESS'}</i></div>
      <label class="fld"><span>联系人</span><input id="fName" maxlength="16" placeholder="怎么称呼" value="${esc(a?.name || '')}"></label>
      <label class="fld"><span>手机号</span><input id="fPhone" inputmode="numeric" maxlength="11" placeholder="11 位手机号" value="${esc(a?.phone || '')}"></label>
      <label class="fld"><span>所在区域</span>
        <select id="fArea">${areas.map(x => `<option value="${x}" ${a?.area === x ? 'selected' : ''}>${x}</option>`).join('')}</select>
      </label>
      <label class="fld"><span>详细地址</span><textarea id="fDetail" rows="2" maxlength="80" placeholder="街道 / 门牌号 / 楼层房号">${esc(a?.detail || '')}</textarea></label>
      <div class="fld"><span>地址标签</span>
        <div class="tag-pick" id="fTags">${['家', '公司', '学校'].map(t =>
          `<button class="tag-btn ${(a?.tag || '家') === t ? 'active' : ''}" data-tag="${t}">${t}</button>`).join('')}</div>
      </div>
      <label class="chk"><input type="checkbox" id="fDefault" ${a?.isDefault ? 'checked' : ''}> 设为默认收货地址</label>
      <div class="af-row">
        <button class="px-btn" id="cancelAddr">取消</button>
        <button class="px-btn primary" id="saveAddr">${a ? '保存修改' : '保存并使用'}</button>
      </div>
    </div>`;
  w.classList.remove('hidden');

  let tag = a?.tag || '家';
  $$('#fTags .tag-btn', w).forEach(b => b.addEventListener('click', () => {
    tag = b.dataset.tag;
    $$('#fTags .tag-btn', w).forEach(x => x.classList.toggle('active', x === b));
  }));
  $('#cancelAddr', w).addEventListener('click', closeAddrForm);
  $('#saveAddr', w).addEventListener('click', () => {
    const data = {
      name: $('#fName', w).value.trim(),
      phone: $('#fPhone', w).value.trim(),
      area: $('#fArea', w).value,
      detail: $('#fDetail', w).value.trim(),
      tag,
      isDefault: $('#fDefault', w).checked,
    };
    if (saveAddress(data, id)) closeAddrForm();
  });
  // 回车提交
  $$('#fName,#fPhone', w).forEach(i => i.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); $('#saveAddr', w).click(); }
  }));
  w.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  syncAddrBtn();
  setTimeout(() => $('#fName', w)?.focus(), 80);
}
// 保存（新增或编辑），校验失败返回 false 并提示
function saveAddress(data, id) {
  if (!data.name) { toast('请填写联系人'); return false; }
  if (!/^1\d{10}$/.test(data.phone)) { toast('手机号需为 11 位且以 1 开头'); return false; }
  if (!data.detail || data.detail.length < 5) { toast('详细地址至少 5 个字'); return false; }
  let a;
  if (id) {
    a = state.addresses.find(x => x.id === id);
    Object.assign(a, data);
  } else {
    a = { id: 'A' + Date.now().toString(36) + rid(), ...data };
    state.addresses.push(a);
    // 第一个地址自动成为默认
    if (state.addresses.length === 1) a.isDefault = true;
  }
  if (a.isDefault) state.addresses.forEach(x => { if (x.id !== a.id) x.isDefault = false; });
  state.addressId = a.isDefault ? a.id : (state.addressId || a.id);
  ensureDefault();
  persist(); renderAddresses(); renderCart();
  toast(id ? '地址已更新' : '地址已保存');
  return true;
}
function deleteAddress(id) {
  const a = state.addresses.find(x => x.id === id);
  if (!a) return;
  showModal('删除地址', `确认删除「${esc(a.name)} · ${esc(a.detail)}」？`, () => {
    state.addresses = state.addresses.filter(x => x.id !== id);
    if (editId === id) closeAddrForm();
    if (state.addressId === id) state.addressId = defaultAddr()?.id || null;
    ensureDefault(); persist(); renderAddresses(); renderCart();
    toast('地址已删除');
  }, '删除');
}

// ===== 02 配送方式 =====
function shipModeName() { return state.config.shipModes?.find(m => m.id === state.shipMode)?.name || '标准配送'; }
function renderShip() {
  const modes = state.config.shipModes || [];
  $('#shipModes').innerHTML = modes.map(m => `
    <button class="ship-mode ${state.shipMode === m.id ? 'active' : ''}" data-ship="${m.id}">
      <b>${esc(m.name)}</b><em>${esc(m.desc)}</em>
    </button>`).join('');
  $('#storeSelect').innerHTML = state.stores.map(s =>
    `<option value="${s.storeCode}" ${s.storeCode === state.storeCode ? 'selected' : ''}>${esc(s.storeName)} · ${esc(s.hours || '')}</option>`).join('');
  $('#reserveRow').classList.toggle('hidden', state.timeMode !== 'reserve');
  renderShipEta();
}
function renderShipEta() {
  const c = state.config;
  const eta = state.timeMode === 'reserve' && state.reserveTime
    ? `预约 ${state.reserveTime} 送达`
    : `立即送达 · 约 ${c.etaMin || 30}–${c.etaMax || 40} 分钟`;
  $('#dlEta').textContent = eta;
  const note = $('#shipNote');
  if (note) note.textContent = state.timeMode === 'reserve' && state.reserveTime
    ? `预约单会在 ${state.reserveTime} 前送达；门店接单后骑手才会出发。`
    : '麦乐送由门店骑手直送，实际送达时间以门店接单为准。';
}

// ===== 03 选餐 =====
let currentCat = 0;
function renderCats() {
  $('#dlCats').innerHTML = state.menu.categories.map((c, i) =>
    `<button class="cat-item ${i === currentCat ? 'active' : ''}" data-cat="${i}">${esc(c.name.replace('/多人餐', ' 多人餐'))}</button>`).join('');
}
function cartLine(code) { return state.cart.find(c => c.code === code); }
function renderMenu() {
  const cat = state.menu.categories[currentCat];
  if (!cat) return;
  const meals = cat.codes.map(c => state.menu.meals[c]).filter(Boolean);
  $('#menuCount').textContent = `${meals.length} 款 · 共 ${Object.keys(state.menu.meals).length} 款`;
  $('#dlMeals').innerHTML = meals.map(m => {
    const line = cartLine(m.code);
    return `<div class="dl-meal">
      <img loading="lazy" src="${m.image}" alt="${esc(m.name)}" onerror="this.style.opacity='.15'">
      <div class="dm-name">${esc(m.name)}</div>
      <div class="dm-row">
        <span class="dm-price">${fmt(m.price)}</span>
        ${line ? `<span class="dm-qty"><button data-dec="${m.code}">−</button><span>${line.qty}</span><button data-inc="${m.code}">+</button></span>`
          : `<button class="dm-add" data-add="${m.code}" aria-label="加入购物袋">+</button>`}
      </div>
    </div>`;
  }).join('');
}

// ===== 04 购物袋 / 结算 / 支付 =====
const cartCount = () => state.cart.reduce((s, c) => s + c.qty, 0);
const cartTotal = () => state.cart.reduce((s, c) => s + c.price * c.qty, 0);
function deliveryFee(raw = cartTotal()) {
  const c = state.config;
  if (!raw) return 0;
  return raw >= (c.freeAt || 39) ? 0 : (c.deliveryFee || 9);
}
function couponValue() {
  const c = state.coupons.find(x => x.id === state.couponId);
  if (!c) return 0;
  if (cartTotal() < (c.minOrder || 0)) return 0;
  return Number(c.price) || 0;
}
function payable() { return Math.max(0, cartTotal() - couponValue() + deliveryFee()); }
function addToCart(code) {
  const m = state.menu.meals[code];
  if (!m) return;
  const line = cartLine(code);
  if (line) line.qty += 1;
  else state.cart.push({ code, name: m.name, price: Number(m.price) || 0, image: m.image, qty: 1 });
  renderCart(); renderMenu();
}
function changeQty(code, d) {
  const line = cartLine(code);
  if (!line) return;
  line.qty += d;
  if (line.qty <= 0) state.cart = state.cart.filter(c => c.code !== code);
  renderCart(); renderMenu();
}
function renderCart() {
  $('#dlCartCount').textContent = cartCount();
  $('#dbbCount').textContent = `购物袋 ${cartCount()} 件`;
  $('#dbbTotal').textContent = fmt(payable());

  $('#dlCartList').innerHTML = state.cart.length ? state.cart.map(c => `
    <div class="dl-ci">
      <span class="ci-name">${esc(c.name)}</span>
      <span class="ci-price">${fmt(c.price * c.qty)}</span>
      <span class="ci-q"><button data-dec="${c.code}">−</button><b>${c.qty}</b><button data-inc="${c.code}">+</button></span>
    </div>`).join('') : `<div class="dl-cart-empty">购物袋还是空的<br>← 在 03 选餐区挑点好吃的</div>`;

  // 外送页只列可用于外送的券；空购物袋不展示（避免误解为已抵扣）
  const eligible = state.cart.length
    ? state.coupons.filter(c => !/到店专用/.test(c.tag || '') && cartTotal() >= (c.minOrder || 0))
    : [];
  if (state.couponId && !eligible.some(c => c.id === state.couponId)) state.couponId = null;
  $('#dlCoupons').innerHTML = `
    <div class="cp-line"><span>优惠券</span>
      <select id="couponSel" ${eligible.length ? '' : 'disabled'}>
        <option value="">${eligible.length ? '不使用' : (state.cart.length ? '无可用外送券' : '加购后可用')}</option>
        ${eligible.map(c => `<option value="${c.id}" ${state.couponId === c.id ? 'selected' : ''}>${esc(c.name)} −${fmt(c.price)}</option>`).join('')}
      </select>
    </div>`;

  const fee = deliveryFee();
  $('#dlSum').innerHTML = `
    <div class="sum-row"><span>商品小计</span><b>${fmt(cartTotal())}</b></div>
    <div class="sum-row"><span>配送费${fee ? '' : `（满 ¥${state.config.freeAt} 免配送费）`}</span><b>${fee ? fmt(fee) : '¥0.00'}</b></div>
    <div class="sum-row"><span>优惠${state.couponId ? '' : '（未选券）'}</span><b>${couponValue() ? '−' + fmt(couponValue()) : '¥0.00'}</b></div>
    <div class="sum-row total"><span>应付</span><b>${fmt(payable())}</b></div>`;

  $('#payMethods').innerHTML = (state.config.payMethods || []).map(p => `
    <button class="pay-m ${state.pay === p.id ? 'active' : ''}" data-pay="${p.id}">
      <b>${esc(p.name)}</b><em>${esc(p.desc)}</em>
    </button>`).join('');

  const btn = $('#submitPay');
  const addr = state.addresses.find(a => a.id === state.addressId);
  btn.disabled = state.paying || !state.cart.length || !addr;
  btn.textContent = state.paying ? '支付处理中…' : (!addr ? '请先填写配送地址' : (!state.cart.length ? '购物袋为空' : `提交订单并支付 ${fmt(payable())}`));
}

// ===== 05 订单 =====
const LIVE_STEPS = ['已支付', '制作中', '配送中', '已送达'];
function advanceOrder(id, step) {
  const o = state.localOrders.find(x => x.id === id);
  if (!o) return;
  o.step = Math.max(o.step || 1, step);
  if (o.step >= 4) { o.status = '已完成'; }
  persist(); renderOrders();
}
function startProgress(id) {
  [2, 3, 4].forEach((step, i) => {
    setTimeout(() => advanceOrder(id, step), 4200 * (i + 1));
  });
}
function timeNow() {
  const d = new Date(), p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
async function submitOrder() {
  if (state.paying) return false;
  const addr = state.addresses.find(a => a.id === state.addressId);
  if (!addr) { toast('请先填写配送地址'); return false; }
  if (!state.cart.length) { toast('购物袋是空的'); return false; }
  state.paying = true; renderCart();
  await new Promise(r => setTimeout(r, 900));   // 模拟支付网关
  const pay = state.config.payMethods?.find(p => p.id === state.pay)?.name || '微信支付';
  const order = {
    id: 'D' + Date.now().toString().slice(-10),
    createTime: timeNow(),
    storeName: state.stores.find(s => s.storeCode === state.storeCode)?.storeName || '',
    storeCode: state.storeCode,
    address: `${addr.area} ${addr.detail}`,
    contact: `${addr.name} ${addr.phone}`,
    items: state.cart.map(c => ({ name: c.name, qty: c.qty, price: c.price })),
    total: payable(),
    pay, shipMode: shipModeName(),
    eta: state.timeMode === 'reserve' ? `预约 ${state.reserveTime}` : `约 ${state.config.etaMin}–${state.config.etaMax} 分钟`,
    status: '已支付', step: 1, source: 'local', beType: '2',
  };
  state.localOrders.unshift(order);
  state.cart = []; state.couponId = null; state.paying = false;
  persist(); renderCart(); renderMenu(); renderOrders();
  $('#zoneOrders').scrollIntoView({ behavior: 'smooth', block: 'start' });
  showModal('支付成功 · 订单已提交',
    `订单号 <b>${order.id}</b><br>${esc(order.storeName)}<br>${esc(order.address)}<br>共 ${fmt(order.total)} · ${esc(pay)}<br><br>门店已接单，骑手将从门店出发。`,
    null, '好的', 2600);
  startProgress(order.id);
  return true;
}
function orderCard(o) {
  const isLocal = o.source === 'local';
  const type = String(o.beType) === '2' ? '外送' : '到店';
  const items = (o.items || o.products || []).map(p => `${p.name}${p.qty > 1 ? ' ×' + p.qty : ''}` +
    (p.children?.length ? `（${p.children.join('/')}）` : ''));
  const done = /完成|送达/.test(o.status);
  return `<div class="order-card">
    <div class="oc-head"><span>${esc(o.id || o.orderId)}${isLocal ? '<i class="oc-tag local">本页下单</i>' : `<i class="oc-tag">${type}</i>`}</span><span class="oc-time">${esc(o.createTime)}</span></div>
    <span class="oc-status" style="border-color:${done ? 'var(--green)' : 'var(--red)'};color:${done ? 'var(--green)' : 'var(--red)'}">${esc(o.status)}</span>
    <div class="oc-items">${items.map(esc).join('<br>')}</div>
    <div class="oc-total">${fmt(o.total)}</div>
  </div>`;
}
function liveCard(o) {
  const step = o.step || 1;
  return `<div class="live-order">
    <div class="live-head"><b>${esc(o.id)} <span class="live-status">${esc(LIVE_STEPS[step - 1] || '已支付')}</span></b><em>${esc(o.eta)}</em></div>
    <div class="live-track">${LIVE_STEPS.map((s, i) =>
      `<span class="${i + 1 < step ? 'done' : i + 1 === step ? 'now' : ''}">${s}</span>`).join('')}</div>
    <div class="live-meta"><span>${esc(o.storeName)}</span><span>${esc(o.address)}</span><span>${esc(o.pay)} ${fmt(o.total)}</span></div>
  </div>`;
}
function allOrders() {
  return [...state.localOrders, ...state.orders]
    .sort((a, b) => String(b.createTime).localeCompare(String(a.createTime)));
}
function filteredOrders() {
  return allOrders().filter(o => {
    if (state.filter === 'active') return (o.step || 4) < 4 && o.source === 'local';
    if (state.filter === 'done') return (o.step || 4) >= 4 || /完成|送达/.test(o.status || '');
    return true;
  });
}
// 05 区：只渲染进行中订单的实时进度
function renderOrders() {
  const live = state.localOrders.filter(o => (o.step || 1) < 4);
  $('#activeOrders').innerHTML = live.length
    ? live.map(liveCard).join('')
    : '<div class="oc-empty">暂无进行中的订单<br>在 04 区提交订单后，这里会实时推进「已支付 → 制作中 → 配送中 → 已送达」</div>';
  $('#dlOrderCount').textContent = allOrders().length;
  // 抽屉开着时同步刷新，避免看到旧状态
  if (!$('#sheet').classList.contains('hidden')) renderOrderSheet();
}
// 订单抽屉：筛选 + 列表（进行中置顶，其后为历史）
const ORDER_FILTERS = [['all', '全部'], ['active', '进行中'], ['done', '已完成']];
function renderOrderSheet() {
  const list = filteredOrders();
  const live = state.localOrders.filter(o => (o.step || 1) < 4);
  const body = $('#sheetBody');
  if (!body) return;
  body.innerHTML = `
    <div class="od-head">
      <span class="od-count">共 ${allOrders().length} 笔 · 进行中 ${live.length} 笔</span>
      <div class="seg" id="orderFilter">
        ${ORDER_FILTERS.map(([k, t]) => `<button class="seg-btn ${state.filter === k ? 'active' : ''}" data-filter="${k}">${t}</button>`).join('')}
      </div>
    </div>
    ${list.length ? list.map(orderCard).join('') : '<div class="oc-empty">该筛选下暂无订单</div>'}
    <p class="zone-note">带「本页下单」标记的为本页演示订单，仅存于本地浏览器；其余来自 MCP order-list。</p>`;
  $$('#orderFilter .seg-btn', body).forEach(b => b.addEventListener('click', () => {
    state.filter = b.dataset.filter;
    renderOrderSheet();
  }));
}
function openOrders() {
  openSheet('我的订单');
  renderOrderSheet();
}

// ===== 步骤导航 =====
function bindSteps() {
  $$('.dl-step').forEach(b => b.addEventListener('click', () => {
    document.getElementById(b.dataset.zone)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    $$('.dl-step').forEach(x => x.classList.toggle('active', x === b));
  }));
}

// ===== 事件绑定 =====
function bindUI() {
  $('#backGate').addEventListener('click', () => { location.href = 'entry.html'; });
  $('#toDine').addEventListener('click', () => { location.href = 'index.html?mode=dinein'; });
  $('#ordersBtn').addEventListener('click', openOrders);
  $('#ordersFromZone').addEventListener('click', openOrders);
  $('#sheetClose').addEventListener('click', closeSheet);
  $('#sheetBackdrop').addEventListener('click', closeSheet);
  $('#cartJump').addEventListener('click', () => $('#zoneCart').scrollIntoView({ behavior: 'smooth', block: 'start' }));
  $('#dbbGo').addEventListener('click', () => $('#zoneCart').scrollIntoView({ behavior: 'smooth', block: 'start' }));
  $('#addAddr').addEventListener('click', toggleAddrForm);
  $('#clearCart').addEventListener('click', () => {
    if (!state.cart.length) return;
    state.cart = []; state.couponId = null; renderCart(); renderMenu(); toast('购物袋已清空');
  });
  $('#submitPay').addEventListener('click', () => submitOrder());

  // 地址卡：选择 / 设为默认 / 编辑 / 删除
  $('#addrList').addEventListener('click', e => {
    const del = e.target.closest('[data-del]');
    if (del) { deleteAddress(del.dataset.del); return; }
    const ed = e.target.closest('[data-edit]');
    if (ed) { openAddressForm(ed.dataset.edit); return; }
    const def = e.target.closest('[data-def]');
    if (def) {
      state.addresses.forEach(a => a.isDefault = a.id === def.dataset.def);
      state.addressId = def.dataset.def;
      persist(); renderAddresses(); renderCart(); toast('已设为默认地址');
      return;
    }
    const card = e.target.closest('[data-addr]');
    if (card) {
      state.addressId = card.dataset.addr;
      renderAddresses(); renderCart();
    }
  });

  // 配送方式
  $('#shipModes').addEventListener('click', e => {
    const b = e.target.closest('[data-ship]');
    if (!b) return;
    state.shipMode = b.dataset.ship;
    renderShip(); renderCart();
  });
  $('#timeSeg').addEventListener('click', e => {
    const b = e.target.closest('[data-time]');
    if (!b) return;
    state.timeMode = b.dataset.time;
    $$('#timeSeg .seg-btn').forEach(x => x.classList.toggle('active', x === b));
    renderShip();
  });
  $('#reserveTime').addEventListener('change', e => { state.reserveTime = e.target.value; renderShip(); });
  $('#storeSelect').addEventListener('change', e => { state.storeCode = e.target.value; });
  $('#tableware').addEventListener('change', e => { state.tableware = e.target.checked; });

  // 分类与商品
  $('#dlCats').addEventListener('click', e => {
    const b = e.target.closest('[data-cat]');
    if (!b) return;
    currentCat = +b.dataset.cat;
    renderCats(); renderMenu();
  });
  $('#dlMeals').addEventListener('click', e => {
    const add = e.target.closest('[data-add]');
    if (add) { addToCart(add.dataset.add); toast('已加入购物袋'); return; }
    const inc = e.target.closest('[data-inc]');
    if (inc) { addToCart(inc.dataset.inc); return; }
    const dec = e.target.closest('[data-dec]');
    if (dec) { changeQty(dec.dataset.dec, -1); }
  });

  // 购物袋 / 优惠券 / 支付方式
  $('#dlCartList').addEventListener('click', e => {
    const inc = e.target.closest('[data-inc]');
    if (inc) { addToCart(inc.dataset.inc); return; }
    const dec = e.target.closest('[data-dec]');
    if (dec) changeQty(dec.dataset.dec, -1);
  });
  $('#dlCoupons').addEventListener('change', e => {
    if (e.target.id === 'couponSel') { state.couponId = e.target.value || null; renderCart(); }
  });
  $('#payMethods').addEventListener('click', e => {
    const b = e.target.closest('[data-pay]');
    if (!b) return;
    state.pay = b.dataset.pay;
    renderCart();
  });

  // 订单筛选在抽屉内部绑定（见 renderOrderSheet），这里不再重复绑定

  document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeAddrForm(); closeSheet(); hideModal(); } });
}

// ===== 初始化 =====
(async function init() {
  applyTheme(isNightTime() ? 'night' : 'day');
  setInterval(() => applyTheme(isNightTime() ? 'night' : 'day'), 60000);

  const grab = async (url, fb) => {
    try { const r = await fetch(url, { cache: 'no-cache' }); if (!r.ok) throw new Error(r.status); return await r.json(); }
    catch (e) { console.warn('加载失败', url, e); return fb; }
  };
  const [store, menu, delivery] = await Promise.all([
    grab('data/store.json', { mcpStores: [], coupons: [] }),
    grab('data/menu.json', { categories: [], meals: {} }),
    grab('data/delivery.json', { config: {}, addresses: [], orders: [] }),
  ]);

  Object.entries(menu.meals || {}).forEach(([code, m]) => { if (!m.code) m.code = code; });
  state.menu = menu;
  state.coupons = store.coupons || [];
  state.config = delivery.config || {};
  state.orders = (delivery.orders || []).map(o => ({ ...o, source: 'mcp', status: o.orderStatus || '订单已完成' }));
  state.addresses = (delivery.addresses || []).slice();
  restore();
  state.stores = (store.mcpStores || []).filter(s => s.distance != null).slice(0, 6);
  state.storeCode = state.stores[0]?.storeCode || null;
  state.reserveTime = '18:30';

  bindUI(); bindSteps();
  renderAddresses(); renderShip(); renderCats(); renderMenu(); renderCart(); renderOrders();

  window.__dl = {
    state, saveAddress, deleteAddress, submitOrder, advanceOrder,
    addToCart, changeQty, deliveryFee, payable, renderCart, renderOrders,
    applyTheme, isNightTime, openAddressForm, closeAddrForm,
  };

  // ===== 自测（?selftest=1）=====
  if (QA) {
    setTimeout(async () => {
      const results = [];
      const ok = (n, c) => results.push((c ? 'PASS ' : 'FAIL ') + n);
      try {
        ok('dataLoaded', Object.keys(state.menu.meals).length > 0 && state.stores.length >= 3 && state.coupons.length >= 3);
        ok('mcpOrders', state.orders.length === 7 && state.orders[0].source === 'mcp');
        ok('addrEmpty', state.addresses.length === 0 && $('#addrList').innerHTML.includes('还没保存'));

        state.addresses = []; state.addressId = null;
        // 内联表单：点「+ 新增」→ 填 → 保存
        $('#addAddr').click();
        ok('formOpen', !$('#addrForm').classList.contains('hidden') && !!$('#fName', $('#addrForm')));
        $('#fName').value = '测试用户';
        $('#fPhone').value = '13800138000';
        $('#fDetail').value = '北京路 182 号 18F';
        $('#saveAddr').click();
        ok('formSave', state.addresses.length === 1 && state.addresses[0].name === '测试用户'
          && state.addresses[0].isDefault && state.addressId === state.addresses[0].id);
        ok('formClosed', $('#addrForm').classList.contains('hidden'));
        ok('formValidate', (() => {
          $('#addAddr').click(); $('#fName').value = '张三'; $('#fPhone').value = '138'; $('#saveAddr').click();
          const blocked = state.addresses.length === 1 && !$('#addrForm').classList.contains('hidden');
          closeAddrForm(); return blocked;
        })());
        ok('addrValidate', !saveAddress({ name: '', phone: '138', area: '越秀区', detail: 'x' }));
        ok('addrSecond', saveAddress({ name: '公司前台', phone: '13900139000', area: '天河区', detail: '珠江新城华夏路 8 号', tag: '公司', isDefault: false })
          && state.addresses.length === 2 && state.addresses.filter(a => a.isDefault).length === 1);
        openAddressForm(state.addresses[1].id);
        ok('formEdit', $('#fName', $('#addrForm')).value === '公司前台');
        closeAddrForm();
        state.addresses.forEach(a => a.isDefault = a.id === state.addresses[1].id);
        state.addressId = state.addresses[1].id;
        renderAddresses();
        ok('addrDefaultSwitch', $$('.addr-card .ac-tag.def').length === 1 && !$('.addr-card.active')?.textContent.includes('测试用户'));

        state.shipMode = 'contactless'; renderShip();
        ok('shipMode', state.shipMode === 'contactless' && $('#shipModes').innerHTML.includes('无接触'));
        state.timeMode = 'reserve'; state.reserveTime = '19:15'; renderShip();
        ok('reserveEta', $('#dlEta').textContent.includes('19:15'));
        state.timeMode = 'now'; renderShip();

        const first = state.menu.categories[0].codes[0];
        addToCart(first); addToCart(first);
        ok('cartAdd', state.cart.length === 1 && state.cart[0].qty === 2);
        ok('feeRule', deliveryFee(20) === 9 && deliveryFee(39) === 0 && deliveryFee(80) === 0);
        const raw = cartTotal(), fee = deliveryFee(raw);
        renderCart();
        ok('checkoutSum', $('#dlSum').innerHTML.includes(fmt(raw)) && $('#dlSum').innerHTML.includes(fee ? fmt(fee) : '¥0.00'));

        const addrBefore = state.addresses.length;
        const payableBefore = payable();
        const okSubmit = await submitOrder();
        ok('submitOrder', okSubmit && state.localOrders.length === 1 && state.cart.length === 0);
        ok('orderTotal', Math.abs(state.localOrders[0].total - payableBefore) < 0.01 && state.localOrders[0].source === 'local');
        ok('addrKept', state.addresses.length === addrBefore);

        const id = state.localOrders[0].id;
        advanceOrder(id, 3);
        ok('orderAdvance', state.localOrders[0].step === 3 && $('#activeOrders').innerHTML.includes('配送中'));
        advanceOrder(id, 4);
        ok('orderDone', state.localOrders[0].status === '已完成' && state.localOrders[0].step === 4);
        // 历史订单已收纳到顶栏「订单」抽屉：页面不再平铺
        ok('historyNotOnPage', !$('#orderHistory') && !$('#zoneOrders').innerHTML.includes('1030180470000795916953594601'));
        state.filter = 'all';
        $('#ordersBtn').click();
        ok('ordersSheet', !$('#sheet').classList.contains('hidden')
          && $('#sheetBody').innerHTML.includes(id)
          && $('#sheetBody').innerHTML.includes('1030180470000795916953594601'));
        $('#orderFilter [data-filter="done"]').click();
        ok('orderFilter', !$('#sheetBody').innerHTML.includes('oc-empty'));
        closeSheet();
        ok('ordersBadge', $('#dlOrderCount').textContent === String(state.localOrders.length + state.orders.length));

        applyTheme('night');
        ok('themeNight', document.documentElement.dataset.theme === 'night');
        applyTheme('day');
        ok('themeDay', document.documentElement.dataset.theme === 'day');
        ok('stepsNav', $$('.dl-step').length === 5);
        ok('fontScale', (() => {
          window.__fontscale.set(1.26);
          const big = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--fs'));
          const px = parseFloat(getComputedStyle($('.dl-step')).fontSize);
          window.__fontscale.set(1);
          const small = parseFloat(getComputedStyle($('.dl-step')).fontSize);
          return !!$('#fsBtn') && Math.abs(big - 1.26) < 0.001 && px > small;
        })());
        closeAddrForm();
        document.title = 'DL SELFTEST ' + results.join(' | ');
      } catch (e) {
        document.title = 'DL SELFTEST ERROR ' + e.message;
      }
    }, 500);
  }
})();
