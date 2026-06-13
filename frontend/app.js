const apiBase = '';

console.log('[app.js] loaded, apiBase=', apiBase);

async function ingestFile() {
  console.log('[app] ingestFile called');
  const input = document.getElementById('fileInput');
  if (!input) {
    console.error('[app] file input element not found');
    return;
  }
  if (!input.files.length) {
    console.warn('[app] no file selected');
    return alert('Select a file first');
  }
  const file = input.files[0];
  console.log('[app] selected file:', file.name, file.size, file.type);
  const form = new FormData();
  form.append('file', file);
  const status = document.getElementById('uploadStatus');
  if (status) status.innerText = 'Uploading...';

  try {
    console.log('[app] POST', apiBase + '/ingest');
    const resp = await fetch(apiBase + '/ingest', { method: 'POST', body: form });
    console.log('[app] fetch completed, status=', resp.status);
    if (!resp.ok) {
      const txt = await resp.text();
      console.error('[app] upload failed response:', resp.status, txt);
      if (status) status.innerText = 'Upload failed: ' + txt;
      return;
    }
    const j = await resp.json();
    console.log('[app] upload success json=', j);
    if (status) status.innerText = 'Done. Chunks: ' + j.chunks;
    const preview = document.getElementById('preview');
    if (preview) preview.innerText = j.preview || '(no preview)';
  } catch (err) {
    console.error('[app] upload error', err);
    if (status) status.innerText = 'Upload error: ' + err;
  }
}

async function runQuery() {
  const q = document.getElementById('queryInput').value;
  const resultsDiv = document.getElementById('results');
  resultsDiv.innerHTML = '<div class="muted">Querying…</div>';
  document.getElementById('notes').innerText = '(waiting)';

  try {
    const resp = await fetch(apiBase + '/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q }),
    });
    if (!resp.ok) {
      const err = await resp.text();
      resultsDiv.innerText = 'Error: ' + err;
      document.getElementById('notes').innerText = '(error)';
      return;
    }

    // Render as soon as we have the JSON payload
    const j = await resp.json();
    // Clear any chunk results and display only the exact answer at top
    if (resultsDiv) resultsDiv.innerHTML = '';
    const exact = document.getElementById('exactAnswer');
    if (exact) exact.innerText = j.notes ? j.notes : '(no notes)';
    // keep legacy notes element in sync (hidden by default)
    const notesEl = document.getElementById('notes');
    if (notesEl) notesEl.innerText = j.notes || '(no notes)';
  } catch (err) {
    resultsDiv.innerText = 'Query error: ' + err;
    document.getElementById('notes').innerText = '(error)';
  }
}

// Wire buttons
document.addEventListener('DOMContentLoaded', () => {
  const uploadBtn = document.getElementById('uploadBtn');
  const retrieveBtn = document.getElementById('retrieveBtn');
  const generateBtn = document.getElementById('generateBtn');
  if (uploadBtn) uploadBtn.addEventListener('click', ingestFile);
  if (retrieveBtn) retrieveBtn.addEventListener('click', runQuery);
  if (generateBtn) generateBtn.addEventListener('click', () => retrieveBtn.click());
});
