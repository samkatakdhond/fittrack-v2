// ============================================================
// dashboard.js — fully data-driven, no static/random values
// ============================================================

const CALORIE_RING_CIRCUMFERENCE = 226; // 2 * π * 36

document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  const dateEl = document.getElementById('dashDate');
  if (dateEl) dateEl.textContent = formatDate();
  await loadDashboard();
});

async function loadDashboard() {
  try {
    const [summary, chartData, achievementsData] = await Promise.all([
      apiFetch('/dashboard/summary'),
      apiFetch('/dashboard/weekly-chart'),
      apiFetch('/dashboard/achievements'),
    ]);

    renderStatCards(summary);
    renderActivityRings(summary);
    renderTodayWorkouts(summary.today_workouts || []);
    renderWeeklyGoals(summary);
    renderWeeklyChart(chartData);
    await renderWeightChart();
    renderAchievements(achievementsData.achievements || []);
    updateMLInsights();

  } catch (err) {
    showToast('Could not load dashboard: ' + err.message, 'error');
  }
}

// ── Stat Cards ─────────────────────────────────────────────
function renderStatCards(data) {
  const goal = data.calorie_goal || 2000;
  const pct  = Math.min(Math.round(((data.calories_in || 0) / goal) * 100), 999);
  const bmi  = data.bmi;
  const bmiCat = bmi ? getBMICategory(bmi) : null;

  const container = document.getElementById('statCards');
  if (container) {
    container.innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">Calories In</span><div class="card-icon orange">🔥</div></div>
        <div class="card-value">${(data.calories_in || 0).toLocaleString()}</div>
        <div class="card-sub">Goal: ${goal.toLocaleString()} kcal · ${pct}% reached</div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Calories Burned</span><div class="card-icon green">⚡</div></div>
        <div class="card-value">${(data.calories_burned || 0).toLocaleString()}</div>
        <div class="card-sub">Today's workout output</div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">Workouts (Week)</span><div class="card-icon blue">💪</div></div>
        <div class="card-value">${data.weekly_workouts || 0}</div>
        <div class="card-sub">Goal: ${data.weekly_workout_goal || 5} sessions</div>
      </div>
      <div class="card">
        <div class="card-header"><span class="card-title">BMI</span><div class="card-icon ${bmiCat ? '' : 'yellow'}">⚖️</div></div>
        <div class="card-value" style="${bmiCat ? 'color:' + bmiCat.color : ''}">${bmi || '—'}</div>
        <div class="card-sub">${bmiCat ? bmiCat.label : 'Set height & weight in profile'}</div>
      </div>`;
  }
  // Also update ring-area elements that still reference by id
  setEl('totalCalories',  (data.calories_in     || 0).toLocaleString());
  setEl('caloriesBurned', (data.calories_burned || 0).toLocaleString());
  setEl('weeklyWorkouts',  data.weekly_workouts  || 0);
  setEl('bmiValue', bmi || '—');
  setEl('bmiCategory', bmiCat ? bmiCat.label : 'Set height & weight in profile');
  if (bmi) {
    const bmiEl = document.getElementById('bmiValue');
    if (bmiEl && bmiCat) bmiEl.style.color = bmiCat.color;
  }
}

// ── Activity Rings ──────────────────────────────────────────
function renderActivityRings(data) {
  const goal        = data.calorie_goal || 2000;
  const calIn       = data.calories_in  || 0;
  const calBurned   = data.calories_burned || 0;
  const bmi         = data.bmi;

  // Calorie ring (intake vs goal)
  updateRing('calorieRing',  'calorieRingVal',  calIn,    goal,      '%',    '#f4501e');
  // Burn ring (burned vs 500kcal goal)
  updateRing('burnRing',     'burnRingVal',     calBurned, 500,      ' kcal','#22c55e');
  // BMI ring (0–40 scale, healthy at 18.5–25)
  if (bmi) {
    updateRingRaw('bmiRing', 'bmiRingVal', Math.min(bmi, 40), 40, bmi.toString(), '#3b82f6');
  } else {
    setEl('bmiRingVal', 'N/A');
  }
}

function updateRing(ringId, labelId, value, max, unit, color) {
  const pct    = Math.min(value / max, 1);
  const offset = CALORIE_RING_CIRCUMFERENCE * (1 - pct);
  const label  = Math.round(pct * 100) + unit;
  _applyRing(ringId, labelId, offset, label, color);
}

function updateRingRaw(ringId, labelId, value, max, label, color) {
  const pct    = Math.min(value / max, 1);
  const offset = CALORIE_RING_CIRCUMFERENCE * (1 - pct);
  _applyRing(ringId, labelId, offset, label, color);
}

function _applyRing(ringId, labelId, offset, label, color) {
  const ring = document.getElementById(ringId);
  if (ring) { ring.style.strokeDashoffset = offset; ring.setAttribute('stroke', color); }
  setEl(labelId, label);
}

// ── Today's Workouts ────────────────────────────────────────
function renderTodayWorkouts(workouts) {
  const container = document.getElementById('todayWorkouts');
  if (!container) return;

  if (!workouts.length) {
    if (typeof showEmptyState === 'function') {
      showEmptyState(container, { icon:'🏃', title:'No Workouts Today', sub:'Log a session to start tracking!', btnLabel:'+ Log Workout', btnAction:'openWorkoutModal()' });
    } else {
      container.innerHTML = `<div style="text-align:center;padding:1.5rem;color:var(--text-muted)"><div style="font-size:2rem">🏃</div><div style="font-family:var(--font-condensed);font-size:0.78rem;letter-spacing:1px">NO WORKOUTS LOGGED TODAY</div></div>`;
    }
    return;
  }

  const icons = { Cardio: '🏃', Strength: '🏋️', Yoga: '🧘', HIIT: '⚡', Swimming: '🏊', Default: '💪' };

  container.innerHTML = workouts.map(w => {
    const icon   = icons[w.type] || icons.Default;
    const badge  = w.status === 'Done'
      ? '<span class="badge badge-green">Done</span>'
      : '<span class="badge badge-orange">Upcoming</span>';
    return `
      <div class="workout-entry">
        <div class="we-icon">${icon}</div>
        <div class="we-info">
          <div class="we-name">${w.type}</div>
          <div class="we-meta">${w.duration} min · ${w.intensity} · ${w.calories} kcal</div>
        </div>
        ${badge}
      </div>`;
  }).join('');
}

// ── Weekly Goals ────────────────────────────────────────────
function renderWeeklyGoals(data) {
  const wCompleted = data.weekly_workouts       || 0;
  const wGoal      = data.weekly_workout_goal   || 5;
  const calWeek    = data.weekly_calories_in    || 0;
  const calTarget  = data.weekly_cal_target     || 14000;

  const wPct  = Math.min(Math.round((wCompleted / wGoal)  * 100), 100);
  const cPct  = Math.min(Math.round((calWeek    / calTarget) * 100), 100);

  renderProgressBar('goalWorkouts', `Workouts`, `${wCompleted}/${wGoal}`, wPct,  'var(--accent)');
  renderProgressBar('goalCalories', `Calories`, `${calWeek.toLocaleString()}/${calTarget.toLocaleString()}`, cPct, 'var(--green)');
}

function renderProgressBar(id, label, valLabel, pct, color) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `
    <div class="progress-bar-wrap">
      <div class="progress-label"><span>${label}</span><span>${valLabel}</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
}

// ── Weekly Chart ────────────────────────────────────────────
let weeklyChartInstance = null;
function renderWeeklyChart(chartData) {
  const ctx = document.getElementById('weeklyChart');
  if (!ctx) return;
  if (weeklyChartInstance) weeklyChartInstance.destroy();

  weeklyChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: chartData.labels || ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
      datasets: [
        {
          label: 'Calories Burned',
          data: chartData.burned || new Array(7).fill(0),
          backgroundColor: 'rgba(34,197,94,0.5)',
          borderColor: '#22c55e', borderWidth: 2, borderRadius: 4
        },
        {
          label: 'Calories Intake',
          data: chartData.intake || new Array(7).fill(0),
          backgroundColor: 'rgba(244,80,30,0.35)',
          borderColor: '#f4501e', borderWidth: 2, borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { labels: { color: '#888', font: { family: "'Barlow Condensed'", size: 11, weight: '700' } } } },
      scales: {
        x: { ticks: { color: '#555', font: { family: "'Barlow Condensed'", weight: '700' } }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#555' }, grid: { color: 'rgba(255,255,255,0.04)' } }
      }
    }
  });
}

// ── Weight Chart (real data) ────────────────────────────────
let weightChartInstance = null;
async function renderWeightChart() {
  const ctx = document.getElementById('weightChart');
  if (!ctx) return;
  if (weightChartInstance) weightChartInstance.destroy();

  try {
    const data = await apiFetch('/dashboard/weight-history');
    const logs = data.weight_logs || [];

    if (!logs.length) {
      // Show empty state instead of fake data
      const wrapper = ctx.closest('.card');
      if (wrapper) {
        const canvas = wrapper.querySelector('canvas');
        if (canvas) canvas.style.display = 'none';
        const existing = wrapper.querySelector('.weight-empty');
        if (!existing) {
          const msg = document.createElement('div');
          msg.className = 'weight-empty';
          msg.style.cssText = 'text-align:center;padding:2rem;color:var(--text-muted)';
          msg.innerHTML = `<div style="font-size:2rem;margin-bottom:0.5rem">⚖️</div>
            <div style="font-family:var(--font-condensed);font-size:0.82rem;letter-spacing:1px">NO WEIGHT DATA AVAILABLE YET</div>
            <div style="font-size:0.76rem;margin-top:0.3rem">Log your weight in Profile → Metrics to start tracking progress.</div>`;
          wrapper.appendChild(msg);
        }
        // Update badge
        const badge = wrapper.querySelector('.stat-badge');
        if (badge) badge.textContent = 'No data yet';
      }
      return;
    }

    const labels  = logs.map(l => { const d = new Date(l.date); return `${d.getDate()}/${d.getMonth()+1}`; });
    const weights = logs.map(l => parseFloat(l.weight));

    // Calculate actual change
    const change = weights.length >= 2 ? (weights[weights.length-1] - weights[0]).toFixed(1) : null;
    if (change !== null) {
      const badge = document.getElementById('weightBadge') || document.querySelector('#weightProgressCard .stat-badge');
      if (badge) {
        const sign = change > 0 ? '+' : '';
        badge.textContent = `${sign}${change} kg total`;
        badge.className = `stat-badge ${change <= 0 ? 'up' : 'down'}`;
      }
    }

    weightChartInstance = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Weight (kg)',
          data: weights,
          borderColor: '#f4501e',
          backgroundColor: 'rgba(244,80,30,0.08)',
          tension: 0.4, fill: true,
          pointRadius: 3, pointHoverRadius: 5,
          pointBackgroundColor: '#f4501e'
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#555', maxTicksLimit: 10, font: { family: "'Barlow Condensed'" } }, grid: { color: 'rgba(255,255,255,0.03)' } },
          y: { ticks: { color: '#555', callback: v => v + 'kg' }, grid: { color: 'rgba(255,255,255,0.04)' } }
        }
      }
    });

    // show canvas in case it was hidden
    ctx.style.display = '';
  } catch (e) {
    console.warn('Weight chart error:', e);
  }
}

// ── Achievements ─────────────────────────────────────────────
function renderAchievements(achievements) {
  const grid = document.getElementById('badgeGrid');
  if (!grid) return;

  const earnedCount = achievements.filter(a => a.earned).length;
  const badgeCountEl = document.getElementById('badgeCount');
  if (badgeCountEl) badgeCountEl.textContent = `${earnedCount} Earned`;

  grid.innerHTML = achievements.map(a => `
    <div class="badge-item ${a.earned ? 'earned' : ''}" title="${a.earned ? 'Earned: ' + new Date(a.earned_at).toLocaleDateString() : 'Not yet earned'}">
      <div class="badge-emoji">${a.emoji}</div>
      <div class="badge-name">${a.name}</div>
      ${a.earned ? '' : '<div style="font-size:0.65rem;margin-top:0.2rem;opacity:0.5">Locked</div>'}
    </div>`
  ).join('');
}

// ── ML Insights ──────────────────────────────────────────────
async function updateMLInsights() {
  const container = document.getElementById('mlInsights');
  if (!container) return;
  try {
    const data = await apiFetch('/ml/insights');
    const insights = data.insights || [];
    if (!insights.length) {
      container.innerHTML = '<div class="insight-item"><span class="insight-icon">📋</span><span>Log workouts and meals to get personalised insights!</span></div>';
      return;
    }
    const typeIcons = { success: '✅', info: '💡', prediction: '📊', tip: '🎯' };
    container.innerHTML = insights.map(i =>
      `<div class="insight-item"><span class="insight-icon">${typeIcons[i.type] || '🤖'}</span><span>${i.message}</span></div>`
    ).join('');
  } catch {
    container.innerHTML = '<div class="insight-item"><span class="insight-icon">🤖</span><span>Log workouts and meals to get insights!</span></div>';
  }
}

// ── Helpers ──────────────────────────────────────────────────
function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

// ── Quick Log Modals ─────────────────────────────────────────
function openWorkoutModal() { openModal('workoutModal'); }
function openMealModal()    { openModal('mealModal'); }

async function logWorkout() {
  const type      = document.getElementById('wType')?.value;
  const duration  = parseInt(document.getElementById('wDuration')?.value) || 30;
  const intensity = document.getElementById('wIntensity')?.value;
  const calories  = estimateCaloriesBurned(duration, intensity);

  try {
    const res = await apiFetch('/workouts', {
      method: 'POST',
      body: JSON.stringify({ type, duration, intensity, calories, completed: true, tz_offset: getTzOffset() })
    });
    closeModal('workoutModal');
    showToast(`${type} logged! +${calories} kcal burned 🔥`, 'success');
    if (res.new_achievements && res.new_achievements.length) {
      res.new_achievements.forEach(key => showToast(`🏆 Achievement unlocked: ${key.replace(/_/g,' ')}`, 'success'));
    }
    await loadDashboard();
  } catch (err) {
    showToast(err.message || 'Failed to log workout', 'error');
  }
}

async function logMeal() {
  const type     = document.getElementById('mType')?.value;
  const calories = parseInt(document.getElementById('mCalories')?.value) || 0;
  const name     = document.getElementById('mFood')?.value || type;

  try {
    await apiFetch('/meals', {
      method: 'POST',
      body: JSON.stringify({ type, name, calories, tz_offset: getTzOffset() })
    });
    closeModal('mealModal');
    showToast(`${name} logged! +${calories} kcal 🥗`, 'success');
    await loadDashboard();
  } catch (err) {
    showToast(err.message || 'Failed to log meal', 'error');
  }
}
