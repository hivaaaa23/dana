document.addEventListener('DOMContentLoaded', async () => {
  const { api, toast } = Dana;
  const $ = (id) => document.getElementById(id);
  let keyConfigured = false;

  function setStatus(ok, text) {
    $('conn-status').innerHTML = `<span class="w-1.5 h-1.5 rounded-full ${ok ? 'bg-cyan' : 'bg-danger'}"></span> ${text}`;
  }
  function fillSelect(sel, values, current) {
    const all = [...new Set([current, ...values].filter(Boolean))];
    sel.innerHTML = all.map((v) => `<option ${v === current ? 'selected' : ''}>${Dana.esc(v)}</option>`).join('');
  }

  async function load() {
    const [key, st] = await Promise.all([api('/api-keys'), api('/api/settings')]);
    keyConfigured = key.configured;
    $('base-url').value = st.api_base_url || '';
    $('api-key').value = '';
    $('api-key').placeholder = key.configured ? 'کلید ذخیره شده (برای تغییر، کلید جدید را وارد کن)' : 'sk-...';
    fillSelect($('chat-model'), ['gpt-4o-mini', 'gpt-4o'], st.chat_model);
    fillSelect($('embed-model'), ['text-embedding-3-small', 'text-embedding-3-large'], st.embedding_model);
    $('last-test').style.display = 'none';
    setStatus(key.configured, key.configured ? 'API Key ثبت شده' : 'API Key ثبت نشده');
  }

  async function save() {
    const newKey = $('api-key').value.trim();
    if (!keyConfigured && !newKey) throw new Error('API Key را وارد کن.');
    if (newKey) await api('/api-keys', { method: 'PUT', body: { api_key: newKey } });
    await api('/api/settings', { method: 'PUT', body: {
      api_base_url: $('base-url').value.trim(),
      chat_model: $('chat-model').value,
      embedding_model: $('embed-model').value,
    } });
  }

  $('save-conn').addEventListener('click', async () => {
    try { await save(); toast('ذخیره شد.', 'ok'); await load(); }
    catch (e) { toast(e.message, 'error'); }
  });

  $('test-conn').addEventListener('click', async () => {
    const badge = $('last-test');
    try {
      await save();                                   // اول آنچه روی صفحه است ذخیره شود
      const r = await api('/api/settings/test-connection', { method: 'POST' });
      badge.style.display = ''; badge.className = 'inline-flex items-center gap-1.5 text-xs text-cyan bg-cyan/10 px-2.5 py-1.5 rounded-md';
      badge.textContent = 'اتصال موفق بود (' + Dana.fa(r.models.length) + ' مدل)';
      setStatus(true, 'متصل');
      // لیست واقعی مدل‌ها را جایگزین گزینه‌های ثابت کن
      const chatLike = r.models.filter((m) => !/embed/i.test(m)), embLike = r.models.filter((m) => /embed/i.test(m));
      fillSelect($('chat-model'), chatLike, $('chat-model').value);
      fillSelect($('embed-model'), embLike, $('embed-model').value);
      $('api-key').value = '';
      keyConfigured = true;
    } catch (e) {
      badge.style.display = ''; badge.className = 'inline-flex items-center gap-1.5 text-xs text-danger bg-danger/10 px-2.5 py-1.5 rounded-md';
      badge.textContent = e.message; setStatus(false, 'قطع');
    }
  });

  try { await load(); } catch (e) { toast(e.message, 'error'); }
});
