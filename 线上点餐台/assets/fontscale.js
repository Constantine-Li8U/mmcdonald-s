/* ==========================================================================
   全局字号调节（entry / index / delivery 三页共用）
   - 只改 :root 的 --fs 系数；CSS 里所有字号都是 calc(Npx * var(--fs))
   - 选择结果写入 localStorage，跨页、跨会话生效
   ========================================================================== */
(function () {
  'use strict';

  var KEY = 'mcd.fontScale';
  var STEPS = [
    { v: 0.9, label: '紧凑', note: '0.90×' },
    { v: 1, label: '标准', note: '1.00×' },
    { v: 1.12, label: '大', note: '1.12×' },
    { v: 1.26, label: '特大', note: '1.26×' },
  ];
  var root = document.documentElement;

  function read() {
    var raw = parseFloat(localStorage.getItem(KEY));
    if (!isFinite(raw)) return 1;
    // 只接受档位内的值，避免手改 localStorage 造成布局崩坏
    var hit = STEPS.find(function (s) { return Math.abs(s.v - raw) < 0.001; });
    return hit ? hit.v : 1;
  }

  var current = read();
  function apply(v) {
    current = v;
    root.style.setProperty('--fs', String(v));
    root.setAttribute('data-fs', String(v));
    try { localStorage.setItem(KEY, String(v)); } catch (e) { /* 隐私模式忽略 */ }
    var pop = document.getElementById('fsPop');
    if (pop) {
      [].forEach.call(pop.querySelectorAll('.fs-opt'), function (b) {
        b.classList.toggle('active', Math.abs(parseFloat(b.dataset.fs) - v) < 0.001);
      });
    }
  }
  apply(current); // 尽早生效，避免首屏字号跳一下

  function build() {
    var host = document.querySelector('.topnav') || document.querySelector('.gate-status');
    if (!host || document.getElementById('fsCtl')) return;

    var ctl = document.createElement('div');
    ctl.className = 'fs-ctl';
    ctl.id = 'fsCtl';
    ctl.innerHTML =
      '<button class="fs-btn" id="fsBtn" aria-haspopup="true" aria-expanded="false" title="调节全站字号">' +
        'Aa<b id="fsNow">' + Math.round(current * 100) + '%</b><i>字</i>' +
      '</button>' +
      '<div class="fs-pop hidden" id="fsPop" role="menu">' +
        '<div class="fs-pop-head"><span>FONT SIZE</span><b>全站字号</b></div>' +
        STEPS.map(function (s) {
          return '<button class="fs-opt' + (Math.abs(s.v - current) < 0.001 ? ' active' : '') + '" ' +
            'data-fs="' + s.v + '" role="menuitem">' + s.label + '<em>' + s.note + '</em></button>';
        }).join('') +
        '<div class="fs-sample">示例：麦当劳 McDONALD\'S 28.50</div>' +
        '<div class="fs-pop-note">设置会记住，进入页 / 堂食台 / 外卖台共用。</div>' +
      '</div>';
    host.appendChild(ctl);

    var btn = ctl.querySelector('#fsBtn');
    var pop = ctl.querySelector('#fsPop');

    function syncLabel() {
      var n = ctl.querySelector('#fsNow');
      if (n) n.textContent = Math.round(current * 100) + '%';
    }
    function close() {
      pop.classList.add('hidden');
      btn.setAttribute('aria-expanded', 'false');
    }
    function toggle() {
      var open = pop.classList.toggle('hidden') === false;
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    btn.addEventListener('click', function (e) { e.stopPropagation(); toggle(); });
    pop.addEventListener('click', function (e) {
      var b = e.target.closest('.fs-opt');
      if (!b) return;
      apply(parseFloat(b.dataset.fs));
      syncLabel();
      close();
    });
    document.addEventListener('click', function (e) {
      if (!ctl.contains(e.target)) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
      // Ctrl/Cmd + = / - / 0：快捷调节（不拦截浏览器自身缩放之外的组合）
      if (!(e.ctrlKey || e.metaKey)) return;
      var i = STEPS.findIndex(function (s) { return Math.abs(s.v - current) < 0.001; });
      if (e.key === '=' || e.key === '+') { e.preventDefault(); apply(STEPS[Math.min(STEPS.length - 1, i + 1)].v); syncLabel(); }
      else if (e.key === '-') { e.preventDefault(); apply(STEPS[Math.max(0, i - 1)].v); syncLabel(); }
      else if (e.key === '0') { e.preventDefault(); apply(1); syncLabel(); }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', build);
  else build();

  window.__fontscale = {
    steps: STEPS,
    get: function () { return current; },
    set: apply,
  };
})();
