/* پنل ادمین — همه‌ی صفحه‌های admin_*.html */
document.addEventListener('DOMContentLoaded', async () => {
  const { api, fa, esc, ago, toast } = Dana;
  const $ = (id) => document.getElementById(id);

  // هر درخواستی که 403 بدهد یعنی ادمین نیستی
  async function adminApi(path, opts) {
    try { return await api(path, opts); }
    catch (e) {
      if (/Admin access required/.test(e.message)) { location.replace('403.html'); }
      throw e;
    }
  }
  const initial = (email) => esc((email || '?')[0].toUpperCase());
  const dateFa = (iso) => iso ? new Date(/[Zz]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z').toLocaleDateString('fa-IR') : '—';
  const timeFa = (iso) => iso ? new Date(/[Zz]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z').toLocaleString('fa-IR') : '—';
  const badge = (active) => active
    ? '<span class="inline-flex items-center gap-1.5 text-xs text-cyan bg-cyan/10 px-2 py-1 rounded-md"><span class="w-1.5 h-1.5 rounded-full bg-cyan"></span> فعال</span>'
    : '<span class="inline-flex items-center gap-1.5 text-xs text-danger bg-danger/10 px-2 py-1 rounded-md"><span class="w-1.5 h-1.5 rounded-full bg-danger"></span> مسدود</span>';
  const FLAG_FA = {
    ignore_instructions: 'نادیده‌گرفتن دستورها',
    reveal_system_prompt: 'درخواست System Prompt',
    role_override: 'تغییر نقش / جیلبریک',
    role_token_injection: 'تزریق توکن نقش',
    exfiltrate_secrets: 'درخواست کلید/رمز',
  };
  const logRow = (l) => `
    <div class="bg-surface border ${l.flagged ? 'border-accent/60' : l.ok ? 'border-line' : 'border-danger/40'} rounded-md p-4 space-y-2">
      <div class="min-w-0">
        <p class="text-sm"><span class="ltr-num text-muted">${esc(l.email)}</span> · <span class="text-xs text-muted">${esc(timeFa(l.created_at))}</span></p>
        ${l.flagged ? `<p class="mt-1"><span class="inline-flex items-center gap-1.5 text-xs text-accent bg-accent/10 border border-accent/30 rounded px-2 py-0.5">⚠ مشکوک به Prompt Injection · ${esc(FLAG_FA[l.flag_reason] || l.flag_reason || '')}</span></p>` : ''}
        <p class="text-xs text-muted mt-1">${l.source === 'widget' ? 'ویجت' : 'آزمایشگاه'} · ${l.ok ? 'پاسخ داده شد (' + fa(l.sources_count) + ' منبع)' : '<span class="text-danger">پاسخ‌دهی ناموفق</span>'}</p>
      </div>
      ${l.question ? `<p class="text-sm bg-raised rounded-md px-3 py-2 whitespace-pre-wrap break-words"><span class="text-xs text-muted">سوال:</span> ${esc(l.question)}</p>` : ''}
      ${l.answer ? `<p class="text-sm bg-raised rounded-md px-3 py-2 whitespace-pre-wrap break-words"><span class="text-xs text-muted">پاسخ:</span> ${esc(l.answer)}</p>` : ''}
    </div>`;

  // ---------------- داشبورد ----------------
  if ($('a-users')) {
    try {
      const [s, f] = await Promise.all([adminApi('/api/admin/stats'), adminApi('/api/admin/logs?only_failed=true&limit=5')]);
      $('a-users').textContent = fa(s.users);
      $('a-active').textContent = fa(s.active_users_7d);
      $('a-docs').textContent = fa(s.documents);
      $('a-chats').textContent = fa(s.chats_total);
      $('a-failed').textContent = fa(s.chats_failed_7d);
      $('a-recent').innerHTML = s.recent_users.map((u) => `
        <li class="flex items-center justify-between">
          <div class="flex items-center gap-2.5 min-w-0">
            <div class="w-8 h-8 shrink-0 rounded-full bg-raised border border-line flex items-center justify-center text-xs">${initial(u.email)}</div>
            <a href="admin_user_detail.html?id=${u.id}" class="truncate ltr-num hover:text-cyan">${esc(u.email)}</a>
          </div>
          <span class="text-xs text-muted shrink-0">${esc(ago(u.created_at))}</span>
        </li>`).join('') || '<li class="text-muted">کاربری نیست.</li>';
      $('a-failed-list').innerHTML = f.logs.map((l) => `
        <li class="flex items-start gap-2.5"><span class="w-1.5 h-1.5 rounded-full bg-danger mt-1.5 shrink-0"></span>
          <div class="min-w-0"><p class="truncate ltr-num">${esc(l.email)}</p><p class="text-xs text-muted mt-0.5">${esc(ago(l.created_at))}</p></div></li>`).join('')
        || '<li class="text-muted">خطایی ثبت نشده.</li>';
    } catch (e) { toast(e.message, 'error'); }
  }

  // ---------------- لیست کاربران ----------------
  if ($('u-list')) {
    const LIMIT = 20; let offset = 0, total = 0, timer;
    async function load() {
      const qs = new URLSearchParams({ limit: LIMIT, offset });
      if ($('u-q').value.trim()) qs.set('q', $('u-q').value.trim());
      if ($('u-status').value) qs.set('status', $('u-status').value);
      if ($('u-role').value) qs.set('role', $('u-role').value);
      try {
        const r = await adminApi('/api/admin/users?' + qs);
        total = r.total;
        $('u-list').innerHTML = r.users.map((u) => `
          <div class="doc-row" data-id="${u.id}"><div class="grid grid-cols-12 gap-3 px-5 py-3.5 items-center text-sm">
            <div class="col-span-4 flex items-center gap-2.5 min-w-0">
              <div class="w-8 h-8 shrink-0 rounded-full bg-raised border border-line flex items-center justify-center text-xs">${initial(u.email)}</div>
              <p class="truncate ltr-num">${esc(u.email)}</p>
            </div>
            <div class="col-span-2 text-muted">${esc(dateFa(u.created_at))}</div>
            <div class="col-span-2 text-muted ltr-num">${fa(u.documents)}</div>
            <div class="col-span-1"><span class="text-xs ${u.role === 'admin' ? 'text-accent' : 'text-muted'}">${u.role === 'admin' ? 'ادمین' : 'کاربر'}</span></div>
            <div class="col-span-1">${badge(u.is_active)}</div>
            <div class="col-span-2 flex items-center justify-end gap-3 text-xs">
              <a href="admin_user_detail.html?id=${u.id}" class="text-cyan hover:underline">مشاهده</a>
              <button data-toggle="${u.is_active ? 0 : 1}" class="${u.is_active ? 'text-danger' : 'text-cyan'} hover:underline">${u.is_active ? 'مسدود' : 'رفع مسدودی'}</button>
            </div></div></div>`).join('') || '<div class="py-10 text-center text-muted text-sm">کاربری پیدا نشد.</div>';
        $('u-count').textContent = fa(total) + ' کاربر';
        $('u-prev').style.visibility = offset > 0 ? 'visible' : 'hidden';
        $('u-next').style.visibility = offset + LIMIT < total ? 'visible' : 'hidden';
      } catch (e) { toast(e.message, 'error'); }
    }
    ['u-status', 'u-role'].forEach((id) => $(id).addEventListener('change', () => { offset = 0; load(); }));
    $('u-q').addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { offset = 0; load(); }, 300); });
    $('u-prev').addEventListener('click', () => { offset = Math.max(0, offset - LIMIT); load(); });
    $('u-next').addEventListener('click', () => { offset += LIMIT; load(); });
    $('u-list').addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-toggle]'); if (!b) return;
      const id = b.closest('.doc-row').dataset.id, activate = b.dataset.toggle === '1';
      if (!activate && !confirm('این حساب مسدود بشه؟ ویجتش هم از کار می‌افته.')) return;
      try { await adminApi('/api/admin/users/' + id, { method: 'PATCH', body: { is_active: activate } }); load(); }
      catch (err) { toast(err.message, 'error'); }
    });
    load();
  }

  // ---------------- جزئیات کاربر ----------------
  if ($('d-email')) {
    const id = new URLSearchParams(location.search).get('id');
    if (!id) { location.replace('admin_users.html'); return; }
    let me = null, u = null;
    function render() {
      $('d-title').textContent = u.email;
      $('d-avatar').textContent = (u.email[0] || '?').toUpperCase();
      $('d-email').textContent = u.email;
      $('d-since').textContent = 'عضویت از ' + dateFa(u.created_at);
      $('d-status').innerHTML = badge(u.is_active);
      $('user-role').value = u.role;
      $('d-toggle').textContent = u.is_active ? 'مسدودسازی این حساب' : 'رفع مسدودیت این حساب';
      $('d-docs').textContent = fa(u.documents); $('d-chunks').textContent = fa(u.chunks); $('d-chats').textContent = fa(u.chats_total);
      $('d-sysprompt').textContent = u.system_prompt || 'هنوز تنظیم نشده (پیش‌فرض).';
      $('d-key').textContent = u.api_key_configured ? '· API Key ثبت شده' : '· API Key ثبت نشده';
      $('d-doclist').innerHTML = u.document_list.map((d) => `
        <div class="px-5 py-3 flex items-center justify-between"><span class="truncate">${esc(d.title)}</span>
        <span class="text-xs text-muted shrink-0">${fa(d.chunk_count)} Chunk</span></div>`).join('')
        || '<div class="px-5 py-6 text-muted text-center">سندی ندارد.</div>';
      const self = me && me.id === u.id;
      $('user-role').disabled = self; $('d-toggle').disabled = self;
      $('d-self').classList.toggle('hidden', !self);
      // فقط برای کاربر عادیِ فعال (سمت سرور هم همین قانون اعمال می‌شود)
      $('d-imp-box').classList.toggle('hidden', self || u.role === 'admin' || !u.is_active);
    }
    async function patch(body) {
      try { Object.assign(u, await adminApi('/api/admin/users/' + id, { method: 'PATCH', body })); render(); toast('ذخیره شد.', 'ok'); }
      catch (e) { toast(e.message, 'error'); render(); }
    }
    document.addEventListener('dana:user', (e) => { me = e.detail; if (u) render(); });
    $('d-impersonate').addEventListener('click', async () => {
      if (!confirm('وارد حساب ' + u.email + ' می‌شوی. این کار در لاگ حسابرسی ثبت می‌شود. ادامه؟')) return;
      try {
        const r = await adminApi('/api/admin/users/' + id + '/impersonate', { method: 'POST' });
        Dana.startImpersonation(r.access_token);
        location.href = 'dashboard.html';
      } catch (e) { toast(e.message, 'error'); }
    });
    $('user-role').addEventListener('change', (e) => patch({ role: e.target.value }));
    $('d-toggle').addEventListener('click', () => {
      if (u.is_active && !confirm('این حساب مسدود بشه؟')) return;
      patch({ is_active: !u.is_active });
    });
    try { u = await adminApi('/api/admin/users/' + id); me = window.DanaUser || me; render(); }
    catch (e) { toast(e.message, 'error'); }
  }

  // ---------------- لاگ‌ها ----------------
  if ($('l-list')) {
    async function load() {
      try {
        const r = await adminApi('/api/admin/logs?limit=100' + ($('l-failed').checked ? '&only_failed=true' : '') + ($('l-flagged').checked ? '&only_flagged=true' : ''));
        if ($('l-note')) {
          $('l-note').textContent = r.content_logging
            ? 'لاگ مکالمات همراه با متن سوال و پاسخ ذخیره می‌شود (رمزنگاری‌شده در دیتابیس)'
              + (r.retention_days ? '؛ بعد از ' + fa(r.retention_days) + ' روز به‌صورت خودکار پاک می‌شود.' : '.')
            : 'لاگ سبک مکالمات (زمان، منبع و موفق/ناموفق بودن). متن پیام‌ها ذخیره نمی‌شود تا حریم خصوصی کاربران نهایی ویجت حفظ شود.';
        }
        $('l-list').innerHTML = r.logs.map(logRow).join('') || '<div class="py-10 text-center text-muted text-sm">لاگی نیست.</div>';
      } catch (e) { toast(e.message, 'error'); }
    }
    $('l-failed').addEventListener('change', load);
    $('l-flagged').addEventListener('change', load);
    load();
  }
});
