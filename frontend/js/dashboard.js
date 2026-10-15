document.addEventListener('DOMContentLoaded', async () => {
  const { api, fa, esc, ago } = Dana;
  const $ = (id) => document.getElementById(id);
  const size = (chars) => chars < 1024 ? fa(chars) + ' کاراکتر'
    : chars < 1048576 ? fa((chars / 1024).toFixed(1)) + ' کیلوکاراکتر'
    : fa((chars / 1048576).toFixed(2)) + ' میلیون کاراکتر';
  try {
    const [kb, key, st, stats] = await Promise.all([
      api('/api/knowledge-base'), api('/api-keys'), api('/api/settings'), api('/api/stats'),
    ]);
    $('stat-docs').textContent = fa(stats.documents);
    $('stat-chunks').textContent = fa(stats.chunks);
    $('stat-chats').textContent = fa(stats.chats_7d);
    $('stat-widget-chats').textContent = fa(stats.widget_chats_7d) + ' مورد از طریق ویجت';
    $('stat-size').textContent = size(stats.content_chars);
    $('stat-model').textContent = key.configured ? st.chat_model : 'تنظیم نشده';
    $('stat-model').className = 'text-2xl font-bold ' + (key.configured ? 'text-cyan' : 'text-danger');
    $('stat-key').textContent = key.configured ? 'ثبت شده' : 'ثبت نشده';
    $('stat-key').className = 'text-2xl font-bold ' + (key.configured ? 'text-cyan' : 'text-danger');
    $('conn-dot').className = 'w-1.5 h-1.5 rounded-full ' + (key.configured ? 'bg-cyan' : 'bg-danger');
    $('conn-text').textContent = key.configured ? 'API Key ثبت شده' : 'API Key ثبت نشده';

    const recent = kb.documents.slice(0, 5);
    $('recent').innerHTML = recent.length
      ? recent.map((d) => `<li class="flex items-center gap-2 text-muted"><span class="text-cyan">${esc(ago(d.created_at))}</span> سند «${esc(d.title)}» اضافه شد</li>`).join('')
      : '<li class="text-muted">هنوز سندی اضافه نکردی.</li>';
  } catch (e) { Dana.toast(e.message, 'error'); }
});
