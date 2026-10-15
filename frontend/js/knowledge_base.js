document.addEventListener('DOMContentLoaded', () => {
  const { api, fa, esc, ago, toast } = Dana;
  const $ = (id) => document.getElementById(id);
  const list = $('doc-list'), modal = $('doc-modal');
  let editingId = null;

  const ICON_FILE = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="text-muted shrink-0"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>';
  const ICON_EDIT = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>';
  const ICON_DEL = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>';

  function row(d) {
    return `<div class="doc-row" data-status="ready" data-id="${d.id}">
      <div class="grid grid-cols-12 gap-3 px-5 py-3.5 items-center text-sm">
        <div class="col-span-6 flex items-center gap-2.5 min-w-0">${ICON_FILE}<span class="truncate">${esc(d.title)}</span></div>
        <div class="col-span-2 text-muted">${fa(d.chunk_count)}</div>
        <div class="col-span-3 text-muted">${esc(ago(d.created_at))}</div>
        <div class="col-span-1 flex items-center justify-end gap-1 text-muted">
          <button class="hover:text-ink p-1" data-act="edit" title="ویرایش" aria-label="ویرایش">${ICON_EDIT}</button>
          <button class="hover:text-danger p-1" data-act="del" title="حذف" aria-label="حذف">${ICON_DEL}</button>
        </div>
      </div></div>`;
  }

  async function load() {
    try {
      const r = await api('/api/knowledge-base');
      list.innerHTML = r.documents.length
        ? r.documents.map(row).join('')
        : '<div class="py-14 text-center text-muted text-sm">هنوز سندی اضافه نکردی. اولین سندت رو از باکس بالا آپلود کن یا با «افزودن سند» بنویس.</div>';
      $('doc-count').textContent = fa(r.total) + ' سند';
      $('delete-all').style.visibility = r.total ? 'visible' : 'hidden';
    } catch (e) { toast(e.message, 'error'); }
  }

  // ---- مودال افزودن/ویرایش ----
  function openModal(doc) {
    editingId = doc ? doc.id : null;
    $('modal-title').textContent = doc ? 'ویرایش سند' : 'افزودن سند';
    $('m-title').value = doc ? doc.title : '';
    $('m-content').value = doc ? doc.content : '';
    modal.showModal();
  }
  $('add-doc').addEventListener('click', () => openModal(null));
  $('m-cancel').addEventListener('click', () => modal.close());
  $('doc-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('m-save'); btn.disabled = true; btn.textContent = 'در حال پردازش...';
    const body = { title: $('m-title').value.trim(), content: $('m-content').value };
    try {
      if (editingId) await api('/api/knowledge-base/' + editingId, { method: 'PUT', body });
      else await api('/api/knowledge-base', { method: 'POST', body });
      modal.close(); toast('ذخیره شد.', 'ok'); load();
    } catch (err) { toast(err.message, 'error'); }
    btn.disabled = false; btn.textContent = 'ذخیره';
  });

  // ---- عملیات روی ردیف‌ها ----
  list.addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-act]'); if (!btn) return;
    const id = btn.closest('.doc-row').dataset.id;
    if (btn.dataset.act === 'del') {
      if (!confirm('این سند حذف بشه؟')) return;
      try { await api('/api/knowledge-base/' + id, { method: 'DELETE' }); toast('حذف شد.', 'ok'); load(); }
      catch (err) { toast(err.message, 'error'); }
    } else {
      try { openModal(await api('/api/knowledge-base/' + id)); }
      catch (err) { toast(err.message, 'error'); }
    }
  });
  $('delete-all').addEventListener('click', async () => {
    if (!confirm('کل مخزن دانش پاک بشه؟ این کار برگشت‌پذیر نیست.')) return;
    try { await api('/api/knowledge-base', { method: 'DELETE' }); toast('مخزن خالی شد.', 'ok'); load(); }
    catch (err) { toast(err.message, 'error'); }
  });

  // ---- آپلود فایل (TXT / MD / PDF / DOCX) → استخراج متن در سرور، هر فایل یک سند ----
  async function uploadFiles(files) {
    for (const f of files) {
      if (!/\.(txt|md|markdown|pdf|docx)$/i.test(f.name)) { toast(`«${f.name}» پشتیبانی نمی‌شه (TXT، MD، PDF، DOCX).`, 'error'); continue; }
      if (f.size > 10 * 1024 * 1024) { toast(`«${f.name}» بزرگ‌تر از ۱۰ مگابایته.`, 'error'); continue; }
      try {
        toast(`در حال پردازش «${f.name}»...`, 'info');
        const fd = new FormData();
        fd.append('file', f);
        await api('/api/knowledge-base/upload', { method: 'POST', body: fd });
        toast(`«${f.name}» اضافه شد.`, 'ok');
      } catch (err) { toast(`«${f.name}»: ${err.message}`, 'error'); }
    }
    load();
  }
  const dz = $('dropzone'), fileInput = $('file-input');
  fileInput.addEventListener('change', () => { uploadFiles([...fileInput.files]); fileInput.value = ''; });
  ['dragover', 'dragenter'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('drag'); }));
  dz.addEventListener('drop', (e) => uploadFiles([...e.dataTransfer.files]));

  load();
});
