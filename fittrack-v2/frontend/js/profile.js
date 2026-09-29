// ============================================================
// profile.js — Profile page — talks to Flask API
// GET /api/profile          → load profile
// PUT /api/profile          → save personal info
// PUT /api/profile/metrics  → save body metrics
// PUT /api/profile/password → change password
// POST /api/profile/avatar  → upload profile picture (filename stored in DB)
// GET  /api/profile/avatar/<filename> → serve the image
// DELETE /api/profile/avatar → remove profile picture
// ============================================================

const API = 'http://127.0.0.1:5000/api';

document.addEventListener('DOMContentLoaded', async () => {
    if (!requireAuth()) return;
    await loadProfile();
});

async function loadProfile() {
    try {
        const data    = await apiFetch('/profile');
        const user    = data.user    || {};
        const profile = data.profile || {};

        // ── Form fields ──────────────────────────────────────
        setValue('pName',         user.name              || '');
        setValue('pEmail',        user.email             || '');
        setValue('pAge',          profile.age            || '');
        setValue('pGender',       user.gender            || '');
        setValue('pActivity',     profile.activity_level || 'moderate');
        setValue('pHeight',       profile.height         || '');
        setValue('pWeight',       profile.weight         || '');
        setValue('pTargetWeight', profile.target_weight  || '');
        setValue('pGoal',         user.goal              || 'weight_loss');

        // ── Hero section ─────────────────────────────────────
        const name     = user.name || 'User';
        const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        setText('profileName', name.toUpperCase());

        // ── Profile Picture — show image if saved, else initials ──
        renderAvatarHero(user.avatar_filename, initials);

        const goalLabels = {
            weight_loss: 'Weight Loss',
            muscle_gain: 'Muscle Gain',
            maintenance: 'Maintenance',
            endurance:   'Endurance'
        };
        const since = user.created_at
            ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
            : 'Feb 2026';
        setText('profileGoal', `Goal: ${goalLabels[user.goal] || 'Weight Loss'} · Member since ${since}`);

        // ── BMI ───────────────────────────────────────────────
        if (profile.weight && profile.height) {
            const bmi = computeBMI(parseFloat(profile.weight), parseFloat(profile.height));
            setText('profileBMI', bmi || '—');
            calcBMI();
        }

        // ── Live stats: workouts, streak, weight progress ────
        try {
            const stats = await apiFetch('/profile/stats');
            setText('profileWorkouts', stats.total_workouts ?? 0);
            setText('profileStreak',   stats.streak         ?? 0);
            setText('profileLost',     stats.progress       || '—');
        } catch {
            setText('profileWorkouts', 0);
            setText('profileStreak',   0);
        }

        // ── Sync user data to localStorage so all pages show correct avatar/name
        const cached = getCurrentUser() || {};
        const syncedAvatarUrl = user.avatar_filename
          ? `http://127.0.0.1:5000/api/profile/avatar/${user.avatar_filename}`
          : null;
        setCurrentUser({
          ...cached,
          name: user.name || cached.name,
          avatar_filename: user.avatar_filename || null,
          avatar_url: syncedAvatarUrl,
        });

        updateNavUser();

    } catch (err) {
        showToast('Could not load profile: ' + err.message, 'error');
    }
}

// ── Render avatar: image if saved, else initials ─────────
function renderAvatarHero(avatarFilename, initials) {
    const wrap = document.querySelector('.avatar-wrap');
    if (!wrap) return;

    // Remove old remove button if present
    const oldBtn = wrap.querySelector('.avatar-remove-btn');
    if (oldBtn) oldBtn.remove();

    const avatarEl = document.getElementById('profileAvatar');

    if (avatarFilename) {
        // Show the actual image
        avatarEl.innerHTML = `<img class="pfp-img" src="${API}/profile/avatar/${avatarFilename}" alt="Profile photo" onerror="this.src='assets/default-avatar.png'">`;
        avatarEl.style.background = 'transparent';
        avatarEl.style.padding    = '0';

        // Add remove button below avatar
        const removeBtn = document.createElement('button');
        removeBtn.className   = 'avatar-remove-btn';
        removeBtn.textContent = '✕ Remove photo';
        removeBtn.onclick     = (e) => { e.stopPropagation(); removeAvatar(); };
        wrap.appendChild(removeBtn);

        // Also update nav avatar with image
        const navAvatar = document.getElementById('navAvatar');
        if (navAvatar) {
            navAvatar.innerHTML = `<img src="${API}/profile/avatar/${avatarFilename}" style="width:32px;height:32px;border-radius:50%;object-fit:cover" onerror="this.src='assets/default-avatar.png'">`;
        }
    } else {
        // Show initials
        avatarEl.innerHTML   = `<img class="pfp-img" src="assets/default-avatar.png" alt="Default avatar" style="width:100%;height:100%;object-fit:cover;border-radius:50%">`;
        avatarEl.style.background = 'transparent';
        avatarEl.style.padding    = '0';
        setText('navAvatar', initials);
    }
}

// ── Upload avatar ─────────────────────────────────────────
async function uploadAvatar(input) {
    const file = input.files[0];
    if (!file) return;

    // Client-side size check (3MB)
    if (file.size > 3 * 1024 * 1024) {
        showToast('Image too large. Max 3MB.', 'error');
        input.value = '';
        return;
    }

    const formData = new FormData();
    formData.append('avatar', file);

    const token = localStorage.getItem('access_token');

    try {
        showToast('Uploading photo...', 'info');
        const res  = await fetch(`${API}/profile/avatar`, {
            method:  'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body:    formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload failed');

        // Update cached user — store both filename and full URL for global sync
        const cached = getCurrentUser() || {};
        const avatarUrl = `http://127.0.0.1:5000/api/profile/avatar/${data.filename}`;
        setCurrentUser({ ...cached, avatar_filename: data.filename, avatar_url: avatarUrl });

        // Re-render avatar immediately everywhere
        const name     = document.getElementById('pName')?.value || 'User';
        const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        renderAvatarHero(data.filename, initials);

        // Sync global navbar/sidebar
        if (typeof syncNavbarUser === 'function') syncNavbarUser();
        if (typeof updateNavUser  === 'function') updateNavUser();

        showToast('Profile photo updated! 📸', 'success');
    } catch (err) {
        showToast(err.message || 'Upload failed', 'error');
    }
    input.value = '';
}

// ── Remove avatar ─────────────────────────────────────────
async function removeAvatar() {
    if (!confirm('Remove your profile photo?')) return;
    try {
        const token = localStorage.getItem('access_token');
        const res   = await fetch(`${API}/profile/avatar`, {
            method:  'DELETE',
            headers: { 'Authorization': `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to remove');

        const cached = getCurrentUser() || {};
        delete cached.avatar_filename;
        delete cached.avatar_url;
        setCurrentUser(cached);

        const name     = document.getElementById('pName')?.value || 'User';
        const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        renderAvatarHero(null, initials);

        showToast('Profile photo removed', 'success');
    } catch (err) {
        showToast(err.message || 'Failed to remove', 'error');
    }
}

// ── Helpers ───────────────────────────────────────────────
function setValue(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function setText(id, val)  { const el = document.getElementById(id); if (el) el.textContent = val; }

function editProfile() {
    const inputs = document.querySelectorAll('#profileForm input:not([readonly]), #profileForm select');
    inputs.forEach(el => el.removeAttribute('disabled'));
    document.getElementById('saveProfileBtn')?.classList.remove('hidden');
}

async function saveProfile() {
    const name           = document.getElementById('pName')?.value.trim();
    const gender         = document.getElementById('pGender')?.value;
    const age            = parseInt(document.getElementById('pAge')?.value) || null;
    const activity_level = document.getElementById('pActivity')?.value;
    const goal           = document.getElementById('pGoal')?.value;

    try {
        const data = await apiFetch('/profile', {
            method: 'PUT',
            body: JSON.stringify({ name, gender, age, activity_level, goal })
        });
        const cached = getCurrentUser() || {};
        setCurrentUser({ ...cached, name: data.user.name, gender: data.user.gender, goal: data.user.goal });
        showToast('Profile saved! ✅', 'success');
        document.getElementById('saveProfileBtn')?.classList.add('hidden');
        setText('profileName', name.toUpperCase());
        updateNavUser();
    } catch (err) {
        showToast(err.message || 'Failed to save profile', 'error');
    }
}

async function saveMetrics() {
    const height        = parseFloat(document.getElementById('pHeight')?.value) || null;
    const weight        = parseFloat(document.getElementById('pWeight')?.value) || null;
    const target_weight = parseFloat(document.getElementById('pTargetWeight')?.value) || null;
    const goal          = document.getElementById('pGoal')?.value;

    if (!height || !weight) { showToast('Please enter height and weight', 'error'); return; }

    try {
        const data = await apiFetch('/profile/metrics', {
            method: 'PUT',
            body: JSON.stringify({ height, weight, target_weight, goal })
        });
        showToast('Body metrics saved! ⚖️', 'success');
        const bmi = data.bmi || computeBMI(weight, height);
        setText('profileBMI', bmi || '—');
        setText('calcBMI',    bmi || '—');
    } catch (err) {
        showToast(err.message || 'Failed to save metrics', 'error');
    }
}

function calcBMI() {
    const h   = parseFloat(document.getElementById('pHeight')?.value);
    const w   = parseFloat(document.getElementById('pWeight')?.value);
    const bmi = computeBMI(w, h);
    if (!bmi) return;
    const cat        = getBMICategory(bmi);
    const calcEl     = document.getElementById('calcBMI');
    setText('calcBMI', bmi);
    setText('bmiStatus', cat.label);
    if (calcEl) calcEl.style.color = cat.color;
    const pct        = Math.min(Math.max((bmi - 15) / (40 - 15), 0), 1) * 100;
    const indicator  = document.getElementById('bmiIndicator');
    if (indicator) indicator.style.left = pct + '%';
}

async function changePassword() {
    const cur  = document.getElementById('curPwd')?.value;
    const nw   = document.getElementById('newPwd')?.value;
    const conf = document.getElementById('confirmPwd')?.value;

    if (!cur || !nw || !conf) { showToast('Please fill in all password fields', 'error'); return; }
    if (nw.length < 8)        { showToast('New password must be at least 8 characters', 'error'); return; }
    if (nw !== conf)          { showToast('New passwords do not match', 'error'); return; }

    try {
        await apiFetch('/profile/password', {
            method: 'PUT',
            body: JSON.stringify({ currentPassword: cur, newPassword: nw })
        });
        showToast('Password updated successfully! 🔐', 'success');
        ['curPwd', 'newPwd', 'confirmPwd'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
    } catch (err) {
        showToast(err.message || 'Failed to update password', 'error');
    }
}
