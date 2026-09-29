// ============================================================
// navbar.js — Global Navbar + Sidebar Loader
// Fetches components/navbar.html and components/sidebar.html,
// injects them into #navbarMount and #sidebarMount,
// then syncs user data (avatar, name) globally on every page.
// ============================================================

(function () {
  /* ── Determine current page for active link ────────────── */
  const pageName = location.pathname.split('/').pop().replace('.html', '') || 'dashboard';

  /* ── Resolve base path (works from any subdirectory) ───── */
  function base(path) {
    // All pages are at the same level, so just use relative path
    return path;
  }

  /* ── Load a component HTML into a mount point ─────────── */
  async function loadComponent(mountId, componentPath) {
    const mount = document.getElementById(mountId);
    if (!mount) return;
    try {
      const res = await fetch(base(componentPath));
      if (!res.ok) throw new Error('Component not found');
      mount.innerHTML = await res.text();
    } catch (e) {
      console.warn('Could not load component:', componentPath, e);
    }
  }

  /* ── Apply active sidebar link based on current page ───── */
  function setActiveSidebarLink() {
    document.querySelectorAll('.app-sidebar .sidebar-link[data-page]').forEach(link => {
      const page = link.getAttribute('data-page');
      link.classList.toggle('active', page === pageName || pageName.startsWith(page));
    });
  }

  /* ── Sync user avatar + name across navbar & sidebar ───── */
  function syncUserUI() {
    const user = (() => {
      try { return JSON.parse(localStorage.getItem('currentUser')); } catch { return null; }
    })();
    if (!user) return;

    const name = user.name || 'User';
    const firstName = name.split(' ')[0];
    const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    const avatarSrc = user.avatar_url ||
      (user.avatar_filename ? `http://127.0.0.1:5000/api/profile/avatar/${user.avatar_filename}` : null);

    // ── Navbar ──
    const navName   = document.getElementById('navName');
    const navAvatar = document.getElementById('navAvatar');
    if (navName)   navName.textContent = firstName;
    if (navAvatar) {
      if (avatarSrc) {
        const img = document.createElement('img');
        img.src = avatarSrc; img.alt = initials;
        img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:50%';
        img.onerror = () => { navAvatar.textContent = initials; };
        navAvatar.textContent = '';
        navAvatar.appendChild(img);
      } else {
        navAvatar.textContent = initials;
      }
    }

    // ── Sidebar profile mini ──
    const sidebarName   = document.getElementById('sidebarProfileName');
    const sidebarAvatar = document.getElementById('sidebarAvatarMini');
    if (sidebarName)   sidebarName.textContent = name;
    if (sidebarAvatar) {
      if (avatarSrc) {
        const img = document.createElement('img');
        img.src = avatarSrc; img.alt = initials;
        img.onerror = () => { sidebarAvatar.textContent = initials; };
        sidebarAvatar.textContent = '';
        sidebarAvatar.appendChild(img);
      } else {
        sidebarAvatar.textContent = initials;
      }
    }

    // ── Theme button icon ──
    const isDark = localStorage.getItem('darkMode') === 'true';
    const btn = document.getElementById('darkModeBtn');
    if (btn) btn.textContent = isDark ? '☀️' : '🌙';

    // ── Show export menu only on dashboard ──
    const exportWrap = document.getElementById('navExportWrap');
    if (exportWrap) {
      exportWrap.style.display = pageName === 'dashboard' ? '' : 'none';
    }

    // ── Restore sidebar collapsed state on desktop ──
    if (window.innerWidth > 1024 && localStorage.getItem('sidebarCollapsed') === 'true') {
      const shell = document.getElementById('appShell');
      if (shell) shell.classList.add('sidebar-collapsed');
    }
  }

  /* ── Export menu toggle (dashboard only) ──────────────── */
  window.toggleExportMenu = function () {
    document.getElementById('exportMenu')?.classList.toggle('open');
  };
  document.addEventListener('click', function (e) {
    const menu = document.getElementById('exportMenu');
    const btn  = document.getElementById('exportToggleBtn');
    if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
      menu.classList.remove('open');
    }
  });

  /* ── Export with auth headers (dashboard only) ─────────── */
  function initExportLinks() {
    const t = localStorage.getItem('access_token');
    ['csvLink', 'pdfLink'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener('click', async function (e) {
        e.preventDefault();
        try {
          const resp = await fetch(this.href, { headers: { Authorization: 'Bearer ' + t } });
          if (!resp.ok) { showToast && showToast('Export failed', 'error'); return; }
          const blob = await resp.blob();
          const url  = URL.createObjectURL(blob);
          const a = document.createElement('a'); a.href = url;
          const cd = resp.headers.get('content-disposition') || '';
          a.download = cd.split('filename=')[1]?.replace(/"/g, '') || 'fittrack_export';
          document.body.appendChild(a); a.click();
          document.body.removeChild(a); URL.revokeObjectURL(url);
          document.getElementById('exportMenu')?.classList.remove('open');
        } catch (err) { showToast && showToast('Export error: ' + err.message, 'error'); }
      });
    });
  }

  /* ── Boot: load both components in parallel ────────────── */
  document.addEventListener('DOMContentLoaded', async () => {
    await Promise.all([
      loadComponent('navbarMount',  'components/navbar.html'),
      loadComponent('sidebarMount', 'components/sidebar.html'),
    ]);
    setActiveSidebarLink();
    syncUserUI();
    initExportLinks();

    // Re-sync when localStorage changes (profile update in another tab)
    window.addEventListener('storage', (e) => {
      if (e.key === 'currentUser') syncUserUI();
    });
  });

  // Expose so profile.js can call it after avatar upload
  window.syncNavbarUser = syncUserUI;
})();
