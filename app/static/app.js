const API = '/api/v1';

function getToken() { return localStorage.getItem('token'); }
function getUser() { return JSON.parse(localStorage.getItem('user') || '{}'); }

function apiHeaders() {
  const h = { 'Content-Type': 'application/json' };
  const t = getToken();
  if (t) h['Authorization'] = `Bearer ${t}`;
  return h;
}

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, { ...opts, headers: { ...apiHeaders(), ...opts.headers } });
  if (res.status === 401 && !window.location.pathname.startsWith('/login')) {
    localStorage.clear();
    window.location.href = '/login';
    return null;
  }
  if (res.status === 204) return null;
  let data;
  try { data = await res.json(); } catch { data = null; }
  if (!res.ok) {
    let msg = `Request failed: ${res.status}`;
    if (data && Array.isArray(data.detail)) {
      msg = data.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
    } else if (data && typeof data.detail === 'string') {
      msg = data.detail;
    } else if (data && data.detail) {
      msg = JSON.stringify(data.detail);
    } else {
      msg = res.statusText || `Server error (${res.status})`;
    }
    throw new Error(msg);
  }
  return data;
}

// ----- LANGUAGE -----
function currentLang() {
  return localStorage.getItem('lang') || 'en';
}

function __(en, zh) {
  return currentLang() === 'zh' ? zh : en;
}

function applyLang(lang) {
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
  document.querySelectorAll('.lang-btn').forEach(el => {
    el.classList.toggle('active', el.dataset.lang === lang);
  });
  document.querySelectorAll('[data-en]').forEach(el => {
    el.textContent = el.getAttribute('data-' + lang) || el.textContent;
  });
  document.querySelectorAll('[data-placeholder-en]').forEach(el => {
    el.placeholder = el.getAttribute('data-placeholder-' + lang) || el.placeholder;
  });
}

async function setLang(lang) {
  applyLang(lang);
  try {
    await api('/auth/language', {
      method: 'PUT',
      body: JSON.stringify({ language: lang }),
    });
  } catch (e) { /* ignore */ }
}

// Apply saved language on page load
(function initLang() {
  const lang = currentLang();
  document.documentElement.lang = lang;
  document.querySelectorAll('.lang-btn').forEach(el => {
    el.classList.toggle('active', el.dataset.lang === lang);
  });
  document.querySelectorAll('[data-en]').forEach(el => {
    el.textContent = el.getAttribute('data-' + lang) || el.textContent;
  });
  document.querySelectorAll('[data-placeholder-en]').forEach(el => {
    el.placeholder = el.getAttribute('data-placeholder-' + lang) || el.placeholder;
  });
})();

// ----- AUTH -----
async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const res = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || __('Login failed','登入失敗'));
  }
  const data = await res.json();
  localStorage.setItem('token', data.access_token);
  localStorage.setItem('user', JSON.stringify(data.user));
  setTokenCookie(data.access_token);
  return data;
}

function setTokenCookie(token) {
  document.cookie = `token=${token}; path=/; max-age=86400; SameSite=Lax`;
}

function clearTokenCookie() {
  document.cookie = 'token=; path=/; max-age=0; SameSite=Lax';
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? match[2] : null;
}

function hasToken() {
  return !!(getToken() || getCookie('token'));
}

function logout() {
  localStorage.clear();
  clearTokenCookie();
  window.location.href = '/login';
}

// ----- TICKETS -----
async function fetchTickets(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); });
  return api(`/ticket?${q}`);
}

async function fetchTicket(id) {
  return api(`/ticket/${id}`);
}

async function updateTicket(id, data) {
  return api(`/ticket/${id}`, { method: 'PUT', body: JSON.stringify(data) });
}

async function createTicket(data) {
  return api('/ticket', { method: 'POST', body: JSON.stringify(data) });
}

// ----- COMMENTS -----
async function fetchComments(ticketId) {
  return api(`/comment/${ticketId}`);
}

async function createComment(ticketId, data) {
  return api(`/comment/${ticketId}`, { method: 'POST', body: JSON.stringify(data) });
}

// ----- CONFIG -----
async function fetchConfig() {
  return api('/config');
}

async function completeSetup() {
  return api('/config/complete-setup', { method: 'POST' });
}

// ----- DASHBOARD -----
async function loadDashboard() {
  try {
    const tickets = await fetchTickets({ pageSize: 10 });
    const total = tickets.total || 0;
    document.getElementById('stat-open').textContent = total;
    const tbody = document.getElementById('recent-tickets');
    tbody.innerHTML = '';
    if (!tickets.tickets || tickets.tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-state"><p>${__('No tickets yet','尚無工單')}</p></td></tr>`;
      return;
    }
    tickets.tickets.forEach(t => {
      const sourceBadge = t.createdBy?.role === 'api'
        ? '<span class="badge badge-orange" style="margin-left:6px;font-size:10px;">API</span>'
        : '<span class="badge badge-blue" style="margin-left:6px;font-size:10px;">Human</span>';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><a href="/ticket/${t.id}">#${t.number}</a></td>
        <td><a href="/ticket/${t.id}">${esc(t.title)}${(t.dedupCount||0) > 1 ? ' <span class="badge badge-orange" style="margin-left:6px;">×' + t.dedupCount + '</span>' : ''}${sourceBadge}</a></td>
        <td>${priorityBadge(t.priority)}</td>
        <td>${statusBadge(t.status)}</td>
        <td>${t.assignedTo ? esc(t.assignedTo.name) : '<span class="text-muted">' + __('Unassigned','未指派') + '</span>'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    document.getElementById('recent-tickets').innerHTML = `<tr><td colspan="5" class="empty-state"><p>${__('Error','錯誤')}: ${e.message}</p></td></tr>`;
  }
}

// ----- TICKET LIST PAGE -----
let ticketListParams = {};

async function loadTicketList() {
  try {
    const params = { ...ticketListParams, pageSize: 50 };
    if (document.getElementById('filter-status')) params.status = document.getElementById('filter-status').value;
    if (document.getElementById('filter-priority')) params.priority = document.getElementById('filter-priority').value;
    if (document.getElementById('filter-search')) params.search = document.getElementById('filter-search').value;

    const data = await fetchTickets(params);
    const tbody = document.getElementById('ticket-list');
    tbody.innerHTML = '';
    if (!data.tickets || data.tickets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="empty-state"><p>${__('No tickets found','無工單')}</p></td></tr>`;
      return;
    }
    data.tickets.forEach(t => {
        const sourceBadge = t.createdBy?.role === 'api'
          ? '<span class="badge badge-orange" style="margin-left:6px;font-size:10px;">API</span>'
          : '<span class="badge badge-blue" style="margin-left:6px;font-size:10px;">Human</span>';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><a href="/ticket/${t.id}">#${t.number}</a></td>
        <td><a href="/ticket/${t.id}">${esc(t.title)}${(t.dedupCount||0) > 1 ? ' <span class="badge badge-orange" style="margin-left:6px;">×' + t.dedupCount + '</span>' : ''}${sourceBadge}</a></td>
        <td>${priorityBadge(t.priority)}</td>
        <td>${statusBadge(t.status)}</td>
        <td>${typeBadge(t.type)}</td>
        <td>${t.assignedTo ? avatar(t.assignedTo) : '<span class="text-muted">—</span>'}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (e) {
    document.getElementById('ticket-list').innerHTML = `<tr><td colspan="6" class="empty-state"><p>${__('Error','錯誤')}: ${e.message}</p></td></tr>`;
  }
}

function applyFilters() { loadTicketList(); }

// ----- TICKET DETAIL PAGE -----
async function loadTicketDetail(ticketId) {
  try {
    const [ticket, comments] = await Promise.all([
      fetchTicket(ticketId),
      fetchComments(ticketId),
    ]);

    document.getElementById('ticket-number').textContent = `#${ticket.number}`;
    document.getElementById('ticket-title').textContent = ticket.title;
    document.getElementById('ticket-detail').textContent = ticket.detail || __('No description provided.','無描述');

    // Dedup badge
    const alertCard = document.getElementById('sidebar-alert-count');
    const dedupCount = document.getElementById('dedup-count');
    const dedupLastSeen = document.getElementById('dedup-last-seen');
    const dedupTimeline = document.getElementById('dedup-timeline');
    if (ticket.dedupCount > 1) {
      alertCard.style.display = '';
      dedupCount.textContent = `× ${ticket.dedupCount}`;
      dedupLastSeen.textContent = ticket.lastSeenAt
        ? `${__('Last seen','最後告警')}: ${formatDate(ticket.lastSeenAt)}`
        : '';
      // Render timeline
      if (ticket.dedupTimestamps && ticket.dedupTimestamps.length > 0) {
        dedupTimeline.innerHTML = ticket.dedupTimestamps.map((ts, i) =>
          `<div style="display:flex;justify-content:space-between;padding:2px 0;">
            <span>#${i + 1}</span>
            <span>${formatDate(ts)}</span>
          </div>`
        ).join('');
      }
    } else {
      alertCard.style.display = 'none';
    }
    const srcBadge = ticket.createdBy?.role === 'api'
      ? '<span class="badge badge-orange" style="margin-left:6px;">API</span>'
      : '<span class="badge badge-blue" style="margin-left:6px;">Human</span>';
    document.getElementById('ticket-badges').innerHTML = `
      ${priorityBadge(ticket.priority)}
      ${statusBadge(ticket.status)}
      ${typeBadge(ticket.type)}
      ${srcBadge}
    `;
    document.getElementById('ticket-created').textContent = `${__('Created','建立')}: ${formatDate(ticket.createdAt)} ${__('by','由')} ${ticket.createdBy?.name || __('Unknown','未知')}`;

    // Sidebar fields
    const assigneeSelect = document.getElementById('field-assignee');
    const prioritySelect = document.getElementById('field-priority');
    const statusSelect = document.getElementById('field-status');

    if (assigneeSelect) assigneeSelect.value = ticket.assignedTo?.id || '';
    if (prioritySelect) prioritySelect.value = ticket.priority;
    if (statusSelect) statusSelect.value = ticket.status;

    // Close button
    const closeBtn = document.getElementById('btn-close-ticket');
    if (closeBtn) {
      if (ticket.status === 'done') {
        closeBtn.textContent = __('Re-open','重新開啟');
        closeBtn.className = 'btn btn-outline';
      } else {
        closeBtn.textContent = __('Close Issue','結案');
        closeBtn.className = 'btn btn-primary';
      }
      closeBtn.onclick = async () => {
        const newStatus = ticket.status === 'done' ? 'needs_support' : 'done';
        await updateTicket(ticketId, { status: newStatus });
        loadTicketDetail(ticketId);
      };
    }

    // Comments
    const container = document.getElementById('comments-list');
    container.innerHTML = '';
    if (comments && comments.length > 0) {
      comments.forEach(c => {
        const div = document.createElement('div');
        div.className = 'comment';
        div.innerHTML = `
          <div class="comment-header">
            <span class="comment-author">${c.user ? esc(c.user.name) : __('Unknown','未知')}</span>
            <span class="comment-date">${formatDate(c.createdAt)}</span>
          </div>
          <div class="comment-text">${esc(c.text)}</div>
        `;
        container.appendChild(div);
      });
    } else {
      container.innerHTML = `<p class="text-muted">${__('No comments yet.','尚無留言')}</p>`;
    }
  } catch (e) {
    document.querySelector('.ticket-detail').innerHTML = `<div class="alert alert-error">${__('Error','錯誤')}: ${e.message}</div>`;
  }
}

async function postComment(ticketId) {
  const textarea = document.getElementById('comment-text');
  const text = textarea.value.trim();
  if (!text) return;
  try {
    await createComment(ticketId, { text, public: false });
    textarea.value = '';
    loadTicketDetail(ticketId);
  } catch (e) {
    alert(e.message);
  }
}

async function updateTicketField(ticketId, field, value) {
  try {
    await updateTicket(ticketId, { [field]: value });
  } catch (e) {
    alert(e.message);
  }
}

// ----- EXPORT CSV -----
function exportCSV(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) q.set(k, v); });
  const token = getToken();
  const url = `${API}/ticket/export/csv?${q}`;
  const a = document.createElement('a');
  a.href = url;
  a.download = 'tickets.csv';
  const xhr = new XMLHttpRequest();
  xhr.open('GET', url);
  xhr.setRequestHeader('Authorization', `Bearer ${token}`);
  xhr.responseType = 'blob';
  xhr.onload = () => {
    const blob = new Blob([xhr.response], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'tickets.csv';
    a.click();
    URL.revokeObjectURL(url);
  };
  xhr.send();
}

// ----- HELPERS -----
function esc(s) {
  if (!s) return '';
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

function formatDate(s) {
  if (!s) return '';
  const d = new Date(s);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function priorityBadge(p) {
  const map = { low: 'badge-blue', medium: 'badge-yellow', high: 'badge-red' };
  const labels = { low: __('Low','低'), medium: __('Medium','中'), high: __('High','高') };
  return `<span class="badge ${map[p] || 'badge-blue'}">${labels[p] || p || __('Low','低')}</span>`;
}

function statusBadge(s) {
  const labels = {
    needs_support: __('Open','待處理'),
    in_progress: __('In Progress','處理中'),
    hold: __('Hold','暫停'),
    in_review: __('In Review','審核中'),
    done: __('Closed','已結案'),
  };
  const map = {
    needs_support: 'badge-green',
    in_progress: 'badge-yellow',
    hold: 'badge-orange',
    in_review: 'badge-blue',
    done: 'badge-red',
  };
  const cls = map[s] || 'badge-green';
  const label = labels[s] || s;
  const dotCls = s === 'done' ? 'badge-dot-red' : s === 'in_progress' ? 'badge-dot-yellow' : 'badge-dot-green';
  return `<span class="badge ${cls}"><span class="badge-dot ${dotCls}"></span>${label}</span>`;
}

function typeBadge(t) {
  const labels = { support: __('Support','技術支援'), bug: __('Bug','錯誤'), feature: __('Feature','功能請求'), incident: __('Incident','事件') };
  return `<span class="badge badge-orange">${labels[t] || t || 'support'}</span>`;
}

function avatar(user) {
  if (!user) return '';
  const initial = (user.name || user.email || '?')[0].toUpperCase();
  const colors = ['avatar-green', 'avatar-blue', 'avatar-orange'];
  const c = colors[Math.floor(Math.random() * colors.length)];
  return `<span class="avatar ${c}">${initial}</span>`;
}
