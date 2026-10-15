(function () {
  if (Dana.getToken()) { location.replace('dashboard.html'); return; }
  const $ = (id) => document.getElementById(id);

  function busy(btn, on, label) {
    btn.disabled = on; btn.style.opacity = on ? .6 : 1;
    if (label) btn.textContent = on ? 'کمی صبر کن...' : label;
  }

  async function login(email, password) {
    const r = await Dana.api('/auth/login', { method: 'POST', body: { email, password }, noAuthRedirect: true });
    localStorage.removeItem('dana-admin-token');
    Dana.setToken(r.access_token);
    location.href = 'dashboard.html';
  }

  $('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.submitter || e.target.querySelector('button[type=submit]');
    busy(btn, true, 'ورود');
    try { await login($('login-email').value.trim(), $('login-pass').value); }
    catch (err) { Dana.toast(err.message === 'Invalid email or password' ? 'ایمیل یا رمز عبور اشتباهه.' : err.message, 'error'); busy(btn, false, 'ورود'); }
  });

  $('signup-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.submitter || e.target.querySelector('button[type=submit]');
    const email = $('su-email').value.trim(), pass = $('su-pass').value;
    if (pass.length < 8) return Dana.toast('رمز عبور باید حداقل ۸ کاراکتر باشه.', 'error');
    if (pass !== $('su-pass2').value) return Dana.toast('رمز و تکرارش یکی نیست.', 'error');
    busy(btn, true, 'ساخت حساب');
    try {
      await Dana.api('/auth/register', { method: 'POST', body: { email, password: pass }, noAuthRedirect: true });
      await login(email, pass);
    } catch (err) {
      const m = err.message;
      Dana.toast(m === 'Email is already registered' ? 'این ایمیل قبلاً ثبت شده.' : m, 'error');
      busy(btn, false, 'ساخت حساب');
    }
  });
})();
