document.addEventListener('DOMContentLoaded', async () => {
  const { api, esc, fa, toast } = Dana;
  const $ = (id) => document.getElementById(id);
  const log = $('chat-log');

  function bubble(role, html) {
    const d = document.createElement('div');
    d.className = `bubble bubble-${role} rounded-md px-4 py-2.5 text-sm ${role === 'user' ? 'ms-auto' : ''}`;
    d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d;
  }
  function welcome() {
    log.innerHTML = '';
    bubble('assistant', esc(window.__welcome || 'سلام! چطور می‌تونم کمکت کنم؟'));
  }
  try { window.__welcome = (await api('/api/settings')).widget_welcome_message; } catch (_) {}
  welcome();
  $('chat-clear').addEventListener('click', welcome);

  $('chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const inp = $('chat-input'), msg = inp.value.trim(); if (!msg) return;
    inp.value = ''; bubble('user', esc(msg));
    const wait = bubble('assistant', '<span class="text-muted">در حال فکر کردن...</span>');
    try {
      const r = await api('/api/chat', { method: 'POST', body: { message: msg } });
      const titles = [...new Set(r.sources.map((s) => s.document_title).filter(Boolean))];
      wait.innerHTML = esc(r.answer).replace(/\n/g, '<br>') + (titles.length
        ? `<div class="mt-2 pt-2 border-t border-line/60 text-[11px] text-muted">منبع: ${titles.map(esc).join('، ')}</div>` : '');
    } catch (err) { wait.innerHTML = `<span class="text-danger">${esc(err.message)}</span>`; }
    log.scrollTop = log.scrollHeight;
  });

  // ---- جستجوی معنایی ----
  const res = $('search-results');
  async function search() {
    const q = $('search-input').value.trim(); if (!q) { res.innerHTML = ''; return; }
    res.innerHTML = '<p class="text-muted text-sm">در حال جستجو...</p>';
    try {
      const r = await api('/api/chat/semantic-search', { method: 'POST', body: { query: q, top_k: 5 } });
      res.innerHTML = r.results.length ? r.results.map((x) => `
        <div class="bg-raised border border-line rounded-md p-3.5">
          <div class="flex items-center justify-between mb-2">
            <span class="score-badge text-xs ${x.score >= .75 ? 'text-cyan bg-cyan/10' : 'text-accent bg-accent/10'} px-2 py-0.5 rounded">${fa(x.score.toFixed(2))}</span>
            <span class="text-[11px] text-muted">${esc(x.document_title || '')}</span>
          </div>
          <p class="text-sm text-muted leading-7">${esc(x.content.length > 400 ? x.content.slice(0, 400) + '…' : x.content)}</p>
        </div>`).join('') : '<p class="text-muted text-sm">نتیجه‌ای پیدا نشد (مخزن خالیه؟).</p>';
    } catch (err) { res.innerHTML = `<p class="text-danger text-sm">${esc(err.message)}</p>`; }
  }
  $('search-form').addEventListener('submit', (e) => { e.preventDefault(); search(); });
});
