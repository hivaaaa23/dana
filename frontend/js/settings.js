document.addEventListener('DOMContentLoaded', async () => {
  const { api, toast, fa } = Dana;
  const $ = (id) => document.getElementById(id);
  let widgetKey = '';

  function updatePreview() {
    const c = $('widget-color').value;
    const bubble = $('mock-bubble');
    bubble.style.background = c;
    const right = $('widget-position').value === 'bottom-right';
    bubble.style.left = right ? 'auto' : '0.75rem';
    bubble.style.right = right ? '0.75rem' : 'auto';
    $('mock-title').textContent = $('widget-title').value || '';
  }
  function buildEmbed() {
    const base = Dana.BASE || location.origin;
    $('embed-code').textContent =
`<script
  src="${base}/widget.js"
  data-key="${widgetKey}"
  defer></script>`;
  }
  function fill(st) {
    widgetKey = st.widget_key || '';
    $('system-prompt').value = st.system_prompt || '';
    $('temperature').value = st.temperature;
    $('temp-out').textContent = fa(String(st.temperature).replace('.', '٫'));
    $('top-k').value = st.top_k;
    $('topk-out').textContent = fa(st.top_k);
    $('widget-color').value = st.widget_color || '#6D28D9';
    $('widget-title').value = st.widget_title || '';
    $('widget-welcome').value = st.widget_welcome_message || '';
    $('widget-position').value = st.widget_position || 'bottom-left';
    $('allowed-origins').value = st.allowed_origins || '';
    $('origins-warn').classList.toggle('hidden', !!$('allowed-origins').value.trim());
    updatePreview(); buildEmbed();
  }

  try { fill(await api('/api/settings')); } catch (e) { toast(e.message, 'error'); }

  $('temperature').addEventListener('input', (e) => {
    $('temp-out').textContent = fa(e.target.value.replace('.', '٫'));
  });
  $('allowed-origins').addEventListener('input', () =>
    $('origins-warn').classList.toggle('hidden', !!$('allowed-origins').value.trim()));
  $('top-k').addEventListener('input', (e) => { $('topk-out').textContent = fa(e.target.value); });
  ['widget-color', 'widget-title', 'widget-position'].forEach((id) =>
    $(id).addEventListener('input', updatePreview));

  $('save-settings').addEventListener('click', async () => {
    try {
      fill(await api('/api/settings', { method: 'PUT', body: {
        system_prompt: $('system-prompt').value,
        temperature: parseFloat($('temperature').value),
        top_k: parseInt($('top-k').value, 10),
        widget_color: $('widget-color').value,
        widget_title: $('widget-title').value,
        widget_welcome_message: $('widget-welcome').value,
        widget_position: $('widget-position').value,
        allowed_origins: $('allowed-origins').value,
      } }));
      toast('تنظیمات ذخیره شد.', 'ok');
    } catch (e) { toast(e.message, 'error'); }
  });

  $('regen-key').addEventListener('click', async () => {
    if (!confirm('کلید ویجت عوض بشه؟ ویجت‌هایی که با کلید قبلی نصب شده‌ن از کار می‌افتن تا کد جدید رو روی سایت بذاری.')) return;
    try {
      const st = await api('/api/settings/widget-key/regenerate', { method: 'POST' });
      widgetKey = st.widget_key; buildEmbed(); toast('کلید جدید ساخته شد.', 'ok');
    } catch (e) { toast(e.message, 'error'); }
  });

  $('copy-embed').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('embed-code').textContent); toast('کپی شد.', 'ok'); }
    catch (_) { toast('کپی نشد؛ دستی انتخاب کن.', 'error'); }
  });
});
