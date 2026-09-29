// ============================================================
// auth.js — Register, Login, Forgot Password
// POST /api/auth/register        → sends OTP, redirects to verify-otp.html
// POST /api/auth/login           → standard JWT login (requires verified)
// POST /api/auth/forgot-password → sends reset OTP
// ============================================================

/* ── REGISTER ── */
const registerForm = document.getElementById('registerForm');
if (registerForm) {
  const pwd = document.getElementById('password');
  if (pwd) {
    pwd.addEventListener('input', () => {
      const val  = pwd.value;
      const fill = document.getElementById('strengthFill');
      const text = document.getElementById('strengthText');
      if (!fill) return;
      if (val.length < 6)                              { fill.className='strength-fill weak';   text.textContent='Too weak'; }
      else if (val.length < 10 || !/[0-9]/.test(val)) { fill.className='strength-fill medium'; text.textContent='Medium strength'; }
      else                                             { fill.className='strength-fill strong'; text.textContent='Strong password!'; }
    });
  }

  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    let valid = true;
    const clearErrors = () => document.querySelectorAll('.form-error').forEach(el => el.classList.remove('show'));
    const showError   = (id, msg) => { const el=document.getElementById(id); if(el){el.textContent=msg;el.classList.add('show');} valid=false; };
    clearErrors();

    const name     = document.getElementById('name')?.value.trim();
    const email    = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;
    const confirm  = document.getElementById('confirmPassword')?.value;
    const goal     = document.getElementById('goal')?.value;
    const gender   = document.getElementById('gender')?.value;
    const terms    = document.getElementById('terms')?.checked;

    if (!name)                                          showError('nameError',            'Please enter your full name');
    if (!email || !/^[^@]+@[^@]+\.[^@]+$/.test(email)) showError('emailError',           'Please enter a valid email address');
    if (!password || password.length < 8)               showError('passwordError',        'Password must be at least 8 characters');
    if (password !== confirm)                           showError('confirmPasswordError', 'Passwords do not match');
    if (!goal)                                          showError('goalError',            'Please select a fitness goal');
    if (!terms)                                         showError('termsError',           'You must accept the terms and conditions');
    if (!valid) return;

    const btn     = document.getElementById('submitBtn');
    const btnText = document.getElementById('submitText');
    const spinner = document.getElementById('submitSpinner');
    btn.disabled  = true;
    btnText.textContent = 'Sending OTP…';
    spinner?.classList.remove('hidden');

    try {
      const height        = document.getElementById('height')?.value        || null;
      const weight        = document.getElementById('weight')?.value        || null;
      const target_weight = document.getElementById('target_weight')?.value || null;
      const age           = document.getElementById('age')?.value           || null;
      const activity      = document.getElementById('activity_level')?.value || 'moderate';

      await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, goal, gender,
                               height, weight, target_weight, age, activity_level: activity }),
      });
      showToast('OTP sent! Check your email 📧', 'success');
      setTimeout(() => {
        window.location.href = `verify-otp.html?purpose=register&email=${encodeURIComponent(email)}`;
      }, 1000);
    } catch (err) {
      if (err.message.toLowerCase().includes('email')) {
        showError('emailError', err.message);
      } else {
        showToast(err.message || 'Registration failed', 'error');
      }
      btn.disabled = false;
      btnText.textContent = 'Create My Account';
      spinner?.classList.add('hidden');
    }
  });
}

/* ── LOGIN ── */
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    let valid = true;
    const clearErrors = () => document.querySelectorAll('.form-error').forEach(el => el.classList.remove('show'));
    const showError   = (id, msg) => { const el=document.getElementById(id); if(el){el.textContent=msg;el.classList.add('show');} valid=false; };
    clearErrors();
    const loginError = document.getElementById('loginError');
    if (loginError) loginError.classList.remove('show');

    const email    = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;

    if (!email || !/^[^@]+@[^@]+\.[^@]+$/.test(email)) showError('emailError',    'Please enter a valid email');
    if (!password)                                       showError('passwordError', 'Please enter your password');
    if (!valid) return;

    const btn     = document.getElementById('submitBtn');
    const btnText = document.getElementById('submitText');
    const spinner = document.getElementById('submitSpinner');
    btn.disabled  = true;
    btnText.textContent = 'Logging in…';
    spinner?.classList.remove('hidden');

    try {
      const data = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      setToken(data.access_token);
      // Build avatar_url from filename so all pages can show profile image
      const user = data.user || {};
      if (user.avatar_filename && !user.avatar_url) {
        user.avatar_url = `http://127.0.0.1:5000/api/profile/avatar/${user.avatar_filename}`;
      }
      setCurrentUser(user);
      if (document.getElementById('rememberMe')?.checked) {
        localStorage.setItem('rememberEmail', email);
      }
      showToast(`Welcome back, ${data.user.name.split(' ')[0]}! 🔥`, 'success');
      setTimeout(() => window.location.href = 'dashboard.html', 1000);
    } catch (err) {
      // If account is unverified, offer to resend OTP
      if (err.unverified) {
        if (loginError) {
          loginError.innerHTML = `❌ Account not verified. 
            <a href="verify-otp.html?purpose=register&email=${encodeURIComponent(email)}" 
               style="color:var(--accent)">Resend OTP</a>`;
          loginError.classList.add('show');
        }
      } else {
        if (loginError) {
          loginError.textContent = '❌  ' + (err.message || 'Invalid email or password');
          loginError.classList.add('show');
        }
      }
      btn.disabled = false;
      btnText.textContent = 'Log In';
      spinner?.classList.add('hidden');
    }
  });

  const remembered = localStorage.getItem('rememberEmail');
  if (remembered) { const f = document.getElementById('email'); if(f) f.value=remembered; }
}

/* ── FORGOT PASSWORD ── */
const forgotForm = document.getElementById('forgotForm');
if (forgotForm) {
  forgotForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email    = document.getElementById('forgotEmail')?.value.trim();
    const errorEl  = document.getElementById('forgotError');
    const btn      = document.getElementById('forgotBtn');
    const btnText  = document.getElementById('forgotBtnText');

    if (!email || !/^[^@]+@[^@]+\.[^@]+$/.test(email)) {
      if(errorEl){ errorEl.textContent='Please enter a valid email'; errorEl.classList.add('show'); }
      return;
    }
    if(errorEl) errorEl.classList.remove('show');
    btn.disabled = true; btnText.textContent = 'Sending OTP…';

    try {
      await apiFetch('/auth/forgot-password', {
        method:'POST', body: JSON.stringify({email}),
      });
      showToast('OTP sent! Check your inbox 📧', 'success');
      setTimeout(() => {
        window.location.href = `verify-otp.html?purpose=reset&email=${encodeURIComponent(email)}`;
      }, 1000);
    } catch (err) {
      if(errorEl){ errorEl.textContent = err.message || 'Failed to send OTP'; errorEl.classList.add('show'); }
      btn.disabled = false; btnText.textContent = 'Send Reset OTP';
    }
  });
}
