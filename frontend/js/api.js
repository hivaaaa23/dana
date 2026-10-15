/* ===== دانا — لایه‌ی مشترک ارتباط با بک‌اند ===== */
(function () {
  const TOKEN_KEY = 'dana-token';
  const ADMIN_BACKUP_KEY = 'dana-admin-token';  // توکن اصلی ادمین، تا پایان حالت «ورود به جای کاربر»
  // اگر صفحه از روی فایل (file://) باز شد، به سرور محلی وصل می‌شویم؛ وگرنه همان origin
  const BASE = window.DANA_API_BASE ||
    (location.protocol === 'file:' ? 'http://127.0.0.1:8000' : '');

  const Dana = {
    BASE,
    getToken: () => localStorage.getItem(TOKEN_KEY),
    setToken: (t) => localStorage.setItem(TOKEN_KEY, t),
    clearToken: () => localStorage.removeItem(TOKEN_KEY),

    // ورود به جای کاربر: توکن اصلی ادمین کنار می‌رود و توکن کوتاه‌مدت جایگزین می‌شود
    startImpersonation(token) {
      const current = Dana.getToken();
      if (current && !localStorage.getItem(ADMIN_BACKUP_KEY)) localStorage.setItem(ADMIN_BACKUP_KEY, current);
      Dana.setToken(token);
    },
    endImpersonation() {
      const back = localStorage.getItem(ADMIN_BACKUP_KEY);
      localStorage.removeItem(ADMIN_BACKUP_KEY);
      if (back) { Dana.setToken(back); location.href = 'admin_users.html'; }
      else Dana.logout();
    },

    // اعداد فارسی
    fa: (n) => String(n).replace(/[0-9]/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[d]),
    esc: (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])),

    // تاریخ نسبی ساده
    ago(iso) {
      if (!iso) return '—';
      const d = new Date(iso.endsWith('Z') || /[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z');
      const mins = Math.floor((Date.now() - d.getTime()) / 60000);
      if (mins < 1) return 'همین الان';
      if (mins < 60) return Dana.fa(mins) + ' دقیقه پیش';
      const h = Math.floor(mins / 60);
      if (h < 24) return Dana.fa(h) + ' ساعت پیش';
      const days = Math.floor(h / 24);
      if (days === 1) return 'دیروز';
      if (days < 30) return Dana.fa(days) + ' روز پیش';
      return d.toLocaleDateString('fa-IR');
    },

    toast(msg, type) {
      let box = document.getElementById('g-toasts');
      if (!box) {
        box = document.createElement('div');
        box.id = 'g-toasts';
        document.body.appendChild(box);
      }
      const t = document.createElement('div');
      t.className = 'g-toast ' + (type || 'info');
      t.textContent = msg;
      box.appendChild(t);
      setTimeout(() => t.classList.add('out'), 3200);
      setTimeout(() => t.remove(), 3700);
    },

    async api(path, opts) {
      opts = opts || {};
      const headers = { Accept: 'application/json' };
      const token = Dana.getToken();
      if (token) headers.Authorization = 'Bearer ' + token;
      let body = opts.body;
      if (body !== undefined && !(body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
        body = JSON.stringify(body);
      }
      let res;
      try {
        res = await fetch(BASE + path, { method: opts.method || 'GET', headers, body });
      } catch (e) {
        throw new Error('ارتباط با سرور برقرار نشد. مطمئن شو بک‌اند روشنه.');
      }
      if (res.status === 401 && !opts.noAuthRedirect) {
        Dana.clearToken();
        location.href = 'login.html';
        throw new Error('نشست منقضی شد؛ دوباره وارد شو.');
      }
      if (res.status === 204) return null;
      let data = null;
      try { data = await res.json(); } catch (_) { /* بدنه‌ی خالی */ }
      if (!res.ok) {
        let msg = data && data.detail;
        if (Array.isArray(msg)) msg = msg.map((m) => m.msg || m).join('، ');
        throw new Error(msg || ('خطای سرور (' + res.status + ')'));
      }
      return data;
    },

    logout() { Dana.clearToken(); localStorage.removeItem(ADMIN_BACKUP_KEY); location.href = 'login.html'; },
  };
  window.Dana = Dana;

  // ---- محافظ صفحه: هر صفحه‌ای جز login بدون توکن به ورود برمی‌گردد ----
  const isLogin = /login\.html$/.test(location.pathname);
  if (!isLogin && !Dana.getToken()) {
    location.replace('login.html');
    return;
  }

  document.addEventListener('DOMContentLoaded', async () => {
    // دکمه‌ی خروج
    document.querySelectorAll('[data-logout]').forEach((a) =>
      a.addEventListener('click', (e) => { e.preventDefault(); Dana.logout(); }));
    // آواتار = حرف اول ایمیل
    if (!isLogin) {
      try {
        const me = await Dana.api('/auth/me');
        window.DanaUser = me;
        if (me.impersonated) {
          const bar = document.createElement('div');
          bar.id = 'impersonation-bar';
          bar.setAttribute('dir', 'rtl');
          bar.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;display:flex;align-items:center;justify-content:center;gap:12px;padding:6px 12px;background:#e8a33d;color:#1a1a1a;font-size:13px;font-weight:600';
          const txt = document.createElement('span');
          txt.textContent = 'حالت «ورود به جای کاربر» — ' + me.email;
          const btn = document.createElement('button');
          btn.type = 'button'; btn.textContent = 'خروج از این حالت';
          btn.style.cssText = 'background:#1a1a1a;color:#fff;border-radius:6px;padding:2px 10px;font-size:12px';
          btn.addEventListener('click', Dana.endImpersonation);
          bar.append(txt, btn);
          document.body.prepend(bar);
          document.body.style.paddingTop = '34px';
        }
        document.querySelectorAll('[data-avatar]').forEach((el) => {
          el.textContent = (me.email || '?')[0].toUpperCase();
          el.title = me.email;
        });
        if (me.role === 'admin' && !document.querySelector('a[href="admin_dashboard.html"]')) {
          const nav = document.querySelector('aside nav');
          if (nav) nav.insertAdjacentHTML('beforeend',
            '<a href="admin_dashboard.html" class="nav-item flex items-center gap-2.5 px-3 py-2.5 rounded-md text-muted hover:text-ink">پنل مدیریت</a>');
        }
        document.dispatchEvent(new CustomEvent('dana:user', { detail: me }));
      } catch (_) { /* خطا قبلاً مدیریت شده */ }
    }
  });
})();
