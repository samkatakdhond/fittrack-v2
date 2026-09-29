// ============================================================
// utils.js — Shared utilities for FitTrack Pro
// All data now goes to Flask API at localhost:5000
// ============================================================

const API_BASE = 'http://127.0.0.1:5000/api';

/* ---- TIMEZONE OFFSET ---- */
// Returns minutes ahead of UTC (e.g. IST = +330, US/ET = -300)
function getTzOffset() { return -new Date().getTimezoneOffset(); }

/* ---- API HELPER ---- */
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  // Attach tz_offset on every GET so the server resolves the user's local "today"
  let url = `${API_BASE}${endpoint}`;
  if (!options.method || options.method === 'GET') {
    const sep = url.includes('?') ? '&' : '?';
    url += `${sep}tz_offset=${getTzOffset()}`;
  }

  const res = await fetch(url, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Something went wrong');
  return data;
}

/* ---- TOKEN / SESSION HELPERS ---- */
function getToken()           { return localStorage.getItem('access_token'); }
function setToken(token)      { localStorage.setItem('access_token', token); }
function removeToken()        { localStorage.removeItem('access_token'); }
function getCurrentUser()     { try { return JSON.parse(localStorage.getItem('currentUser')); } catch { return null; } }
function setCurrentUser(user) { localStorage.setItem('currentUser', JSON.stringify(user)); }
function removeCurrentUser()  { localStorage.removeItem('currentUser'); }
function isLoggedIn()         { return !!getToken(); }

/* ---- LOGOUT ---- */
async function logout() {
  try { await apiFetch('/auth/logout', { method: 'POST' }); } catch {}
  removeToken();
  removeCurrentUser();
  showToast('Logged out successfully', 'success');
  setTimeout(() => window.location.href = 'login.html', 800);
}

/* ---- TOAST NOTIFICATIONS ---- */
function showToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icons = { success: '✅', error: '❌', info: '🔥' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideInToast 0.3s ease reverse';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ---- GLOBAL THEME SYSTEM ---- */
function applyTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'light' : 'dark');
  const btn = document.getElementById('darkModeBtn');
  if (btn) btn.textContent = dark ? '☀️' : '🌙';
}
function toggleDarkMode() {
  const isDark = localStorage.getItem('darkMode') === 'true';
  localStorage.setItem('darkMode', String(!isDark));
  applyTheme(!isDark);
}
// Apply theme immediately on every page load (before DOMContentLoaded to avoid flash)
(function() {
  const dark = localStorage.getItem('darkMode') === 'true';
  document.documentElement.setAttribute('data-theme', dark ? 'light' : 'dark');
})();
// Update button icon after DOM ready
document.addEventListener('DOMContentLoaded', () => {
  const dark = localStorage.getItem('darkMode') === 'true';
  const btn = document.getElementById('darkModeBtn');
  if (btn) btn.textContent = dark ? '☀️' : '🌙';
});

/* ---- NAV USER DISPLAY ---- */
function updateNavUser() {
  const user = getCurrentUser();
  if (!user) return;
  const name = user.name || 'User';
  const navAvatar = document.getElementById('navAvatar');
  const navName   = document.getElementById('navName');
  if (navName) navName.textContent = name.split(' ')[0];
  if (navAvatar) {
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    // Prefer avatar_url (full URL), then build from avatar_filename
    const avatarSrc = user.avatar_url ||
      (user.avatar_filename ? `http://127.0.0.1:5000/api/profile/avatar/${user.avatar_filename}` : null);
    if (avatarSrc) {
      const img = document.createElement('img');
      img.src = avatarSrc;
      img.alt = initials;
      img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%';
      img.onerror = function() {
        navAvatar.textContent = initials;
      };
      navAvatar.textContent = '';
      navAvatar.appendChild(img);
    } else {
      navAvatar.textContent = initials;
    }
  }

  // Make nav user chip clickable → go to profile
  const chip = document.querySelector('.nav-user-chip');
  if (chip && !chip.dataset.profileLinked) {
    chip.dataset.profileLinked = '1';
    chip.style.cursor = 'pointer';
    chip.title = 'Go to Profile';
    chip.addEventListener('click', () => { window.location.href = 'profile.html'; });
  }
}
document.addEventListener('DOMContentLoaded', updateNavUser);

/* ---- AUTH GUARD ---- */
function requireAuth() {
  if (!isLoggedIn()) { window.location.href = 'login.html'; return false; }
  return true;
}

/* ---- PASSWORD TOGGLE ---- */
function togglePwd(inputId, btn) {
  const inp = document.getElementById(inputId);
  if (!inp) return;
  if (inp.type === 'password') { inp.type = 'text'; btn.textContent = '🙈'; }
  else { inp.type = 'password'; btn.textContent = '👁'; }
}

/* ---- MODAL HELPERS ---- */
function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

/* ---- BMI CALCULATOR ---- */
function computeBMI(weightKg, heightCm) {
  if (!weightKg || !heightCm) return null;
  return Math.round(weightKg / Math.pow(heightCm / 100, 2) * 10) / 10;
}
function getBMICategory(bmi) {
  if (bmi < 18.5) return { label: 'Underweight', color: '#3b82f6' };
  if (bmi < 25)   return { label: 'Normal weight', color: '#22c55e' };
  if (bmi < 30)   return { label: 'Overweight', color: '#facc15' };
  return { label: 'Obese', color: '#f4501e' };
}

/* ---- CALORIE ESTIMATOR ---- */
function estimateCaloriesBurned(durationMin, intensity) {
  const rates = { Low: 4, Medium: 7, High: 11 };
  return Math.round((rates[intensity] || 7) * durationMin);
}

/* ---- DATE HELPERS ---- */
function formatDate(date = new Date()) {
  return date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}
function getTodayKey() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

/* ---- LOCAL STORAGE (UI state only, not user data) ---- */
const Storage = {
  get: (key)      => { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } },
  set: (key, val) => { try { localStorage.setItem(key, JSON.stringify(val)); return true; } catch { return false; } },
  remove: (key)   => localStorage.removeItem(key)
};

/* ════════════════════════════════════════════════════════
   SIDEBAR — Smooth animated toggle (shared across all pages)
════════════════════════════════════════════════════════ */
let _sidebarAnimTimer = null;

function _triggerSidebarLinkAnimation() {
  const shell = document.getElementById('appShell');
  if (!shell) return;
  // Remove then re-add the class so the keyframes restart every open
  shell.classList.remove('sidebar-animating');
  // Force reflow so removing+adding in the same tick works
  void shell.offsetHeight;
  shell.classList.add('sidebar-animating');
  clearTimeout(_sidebarAnimTimer);
  // Clean up the class after all animations finish (~400ms)
  _sidebarAnimTimer = setTimeout(() => shell.classList.remove('sidebar-animating'), 420);
}

function toggleSidebar() {
  const shell = document.getElementById('appShell');
  if (!shell) return;

  if (window.innerWidth > 1024) {
    // Desktop: slide in / collapse
    const isCollapsing = !shell.classList.contains('sidebar-collapsed');
    shell.classList.toggle('sidebar-collapsed');
    localStorage.setItem('sidebarCollapsed', shell.classList.contains('sidebar-collapsed'));
    // Play link animation only when opening (not collapsing)
    if (!isCollapsing) _triggerSidebarLinkAnimation();
  } else {
    // Mobile: overlay drawer
    const isOpening = !shell.classList.contains('sidebar-open');
    shell.classList.toggle('sidebar-open');
    if (isOpening) _triggerSidebarLinkAnimation();
  }
}

function closeSidebar() {
  const shell = document.getElementById('appShell');
  if (!shell) return;
  shell.classList.remove('sidebar-open');
}

// Close mobile sidebar when clicking outside
document.addEventListener('click', (e) => {
  const shell = document.getElementById('appShell');
  if (!shell || !shell.classList.contains('sidebar-open')) return;
  const sidebar  = document.getElementById('appSidebar');
  const toggle   = document.getElementById('sidebarToggle');
  if (sidebar && !sidebar.contains(e.target) && toggle && !toggle.contains(e.target)) {
    closeSidebar();
  }
});

// Restore desktop collapsed state on page load
document.addEventListener('DOMContentLoaded', () => {
  if (window.innerWidth > 1024 && localStorage.getItem('sidebarCollapsed') === 'true') {
    const shell = document.getElementById('appShell');
    if (shell) shell.classList.add('sidebar-collapsed');
  }
});

/* ════════════════════════════════════════════════════════
   SKELETON LOADERS — show while data loads
════════════════════════════════════════════════════════ */

/**
 * Replace element content with a skeleton placeholder.
 * @param {string} id   - element id
 * @param {string} type - 'val' | 'text' | 'chart' | 'rows'
 */
function showSkeleton(id, type = 'text') {
  const el = document.getElementById(id);
  if (!el) return;
  el._originalHTML = el.innerHTML;
  if (type === 'val') {
    el.innerHTML = '<span class="skeleton skeleton-val" style="display:inline-block;height:2.5rem;width:70px">&nbsp;</span>';
  } else if (type === 'chart') {
    el.innerHTML = '<div class="skeleton skeleton-chart">&nbsp;</div>';
  } else if (type === 'rows') {
    el.innerHTML = `
      <div class="skeleton-row">
        <div class="skeleton skeleton-text">&nbsp;</div>
        <div class="skeleton skeleton-text w-60">&nbsp;</div>
        <div class="skeleton skeleton-text w-40">&nbsp;</div>
      </div>`;
  } else {
    el.innerHTML = '<span class="skeleton skeleton-text">&nbsp;</span>';
  }
}

function hideSkeleton(id) {
  const el = document.getElementById(id);
  if (!el || !el._originalHTML) return;
  // Don't restore — caller will fill with real data
}

/* ════════════════════════════════════════════════════════
   EMPTY STATES — show when no data available
════════════════════════════════════════════════════════ */

/**
 * Render a standard empty-state inside an element.
 * @param {string|Element} target  - element id or element
 * @param {Object} opts            - { icon, title, sub, btnLabel, btnAction }
 */
function showEmptyState(target, opts = {}) {
  const el = typeof target === 'string' ? document.getElementById(target) : target;
  if (!el) return;
  const {
    icon = '📭',
    title = 'No data yet',
    sub = '',
    btnLabel = null,
    btnAction = null,
  } = opts;
  el.innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <div class="empty-state-title">${title}</div>
      ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
      ${btnLabel ? `<button class="btn btn-outline btn-sm" onclick="${btnAction || ''}">${btnLabel}</button>` : ''}
    </div>`;
}

