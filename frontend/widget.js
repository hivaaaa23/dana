/* Dana - embeddable chat widget
 * Usage: <script src="https://YOUR-HOST/widget.js" data-key="gk_..." defer></script>
 * Look & feel (title, color, position, welcome message) is read from the dashboard settings.
 * Chat history lives only in memory of the current page.
 * NOTE: all non-ASCII text is unicode-escaped on purpose, so the widget renders correctly on
 * host pages/servers that do not declare UTF-8 for this script.
 */
(function () {
  'use strict';
  var script = document.currentScript || document.querySelector('script[data-key][src*="widget.js"]');
  if (!script) return;
  var KEY = script.getAttribute('data-key');
  if (!KEY) { console.warn('[dana] data-key is missing.'); return; }
  if (window.__danaWidgetLoaded) return;
  window.__danaWidgetLoaded = true;
  var BASE = new URL(script.src, location.href).origin;

  function api(path, opts) {
    return fetch(BASE + path, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) { var e = new Error(typeof d.detail === 'string' ? d.detail : '\u062e\u0637\u0627 \u062f\u0631 \u0627\u0631\u062a\u0628\u0627\u0637 \u0628\u0627 \u0633\u0631\u0648\u0631'); e.status = r.status; throw e; }
        return d;
      });
    });
  }

  api('/api/widget/config?key=' + encodeURIComponent(KEY)).then(init).catch(function (e) {
    console.warn('[dana] widget failed to load:', e.message);
  });

  function init(cfg) {
    var color = /^#[0-9a-fA-F]{6}$/.test(cfg.color || '') ? cfg.color : '#6D28D9';
    var side = cfg.position === 'bottom-right' ? 'right' : 'left';

    var host = document.createElement('div');
    host.style.cssText = 'all:initial;position:fixed;z-index:2147483000;bottom:20px;' + side + ':20px;';
    document.body.appendChild(host);
    var root = host.attachShadow({ mode: 'open' });

    root.innerHTML =
      '<style>' +
      ':host{font-family:Vazirmatn,Tahoma,system-ui,sans-serif}' +
      '*{box-sizing:border-box}' +
      '.fab{width:56px;height:56px;border-radius:50%;border:0;background:' + color + ';color:#fff;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center}' +
      '.panel{display:none;flex-direction:column;position:absolute;bottom:68px;' + side + ':0;width:360px;max-width:calc(100vw - 32px);height:480px;max-height:calc(100vh - 110px);background:#fff;color:#1c1c28;border-radius:14px;box-shadow:0 12px 40px rgba(0,0,0,.25);overflow:hidden;direction:rtl}' +
      '.panel.open{display:flex}' +
      '.head{background:' + color + ';color:#fff;padding:14px 16px;font-weight:700;font-size:15px;display:flex;justify-content:space-between;align-items:center}' +
      '.x{background:none;border:0;color:#fff;font-size:22px;line-height:1;cursor:pointer}' +
      '.log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f6f6fa}' +
      '.m{max-width:85%;padding:9px 12px;border-radius:12px;font-size:14px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word}' +
      '.m.bot{background:#fff;border:1px solid #e4e4ee;align-self:flex-start}' +
      '.m.me{background:' + color + ';color:#fff;align-self:flex-end}' +
      '.m.err{background:#fdecea;color:#b3261e;border:1px solid #f5c2be;align-self:flex-start}' +
      '.row{display:flex;gap:8px;padding:10px;border-top:1px solid #e4e4ee;background:#fff}' +
      'input{flex:1;border:1px solid #d6d6e2;border-radius:10px;padding:9px 12px;font:inherit;font-size:14px;outline:none;direction:rtl}' +
      'input:focus{border-color:' + color + '}' +
      '.send{border:0;border-radius:10px;background:' + color + ';color:#fff;padding:0 16px;font:inherit;font-size:14px;cursor:pointer}' +
      '.send:disabled{opacity:.5;cursor:default}' +
      '</style>' +
      '<div class="panel" role="dialog" aria-label="\u0686\u062a">' +
      '  <div class="head"><span class="t"></span><button class="x" aria-label="\u0628\u0633\u062a\u0646">\u00d7</button></div>' +
      '  <div class="log" aria-live="polite"></div>' +
      '  <form class="row"><input type="text" maxlength="1000" placeholder="\u067e\u06cc\u0627\u0645\u062a \u0631\u0627 \u0628\u0646\u0648\u06cc\u0633..." aria-label="\u067e\u06cc\u0627\u0645"><button class="send" type="submit">\u0627\u0631\u0633\u0627\u0644</button></form>' +
      '</div>' +
      '<button class="fab" aria-label="\u0628\u0627\u0632 \u06a9\u0631\u062f\u0646 \u0686\u062a"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.4 8.4 0 0 1-8.9 8.4 8.7 8.7 0 0 1-3.8-.8L3 20l1-5.2a8.4 8.4 0 1 1 17-3.3Z"/></svg></button>';

    var $ = function (s) { return root.querySelector(s); };
    var panel = $('.panel'), log = $('.log'), input = $('input'), send = $('.send');
    $('.t').textContent = cfg.title || '\u062f\u0633\u062a\u06cc\u0627\u0631 \u0647\u0648\u0634\u0645\u0646\u062f';

    function add(cls, text) {
      var d = document.createElement('div');
      d.className = 'm ' + cls; d.textContent = text;   // textContent: no HTML is ever executed
      log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
    }
    add('bot', cfg.welcome_message || '\u0633\u0644\u0627\u0645! \u0686\u0637\u0648\u0631 \u0645\u06cc\u200c\u062a\u0648\u0627\u0646\u0645 \u06a9\u0645\u06a9 \u06a9\u0646\u0645\u061f');

    function toggle(open) { panel.classList.toggle('open', open); if (open) input.focus(); }
    $('.fab').addEventListener('click', function () { toggle(!panel.classList.contains('open')); });
    $('.x').addEventListener('click', function () { toggle(false); });

    $('.row').addEventListener('submit', function (e) {
      e.preventDefault();
      var msg = input.value.trim();
      if (!msg || send.disabled) return;
      input.value = ''; add('me', msg);
      send.disabled = true;
      var wait = add('bot', '...');
      api('/api/widget/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: KEY, message: msg })
      }).then(function (r) { wait.textContent = r.answer; })
        .catch(function (err) { wait.className = 'm err'; wait.textContent = err.message; })
        .then(function () { send.disabled = false; log.scrollTop = log.scrollHeight; input.focus(); });
    });
  }
})();
