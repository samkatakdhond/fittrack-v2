// ============================================================
// workout.js — Workout page
// Day detection uses JS getDay(): 0=Sun, 1=Mon … 6=Sat
// Week grid is rendered dynamically in Mon–Sun visual order
// but mapped correctly to getDay() indexes.
// ============================================================

const DAY_NAMES = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const DAY_FULL  = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];

// Visual display order for the week grid: Mon(1) Tue(2) Wed(3) Thu(4) Fri(5) Sat(6) Sun(0)
// This matches what users expect to see (Mon-first calendar)
const VISUAL_ORDER = [1, 2, 3, 4, 5, 6, 0]; // getDay() indexes in Mon→Sun order

// ── Plan Data (keyed by getDay() index: 0=Sun … 6=Sat) ──────
const PLANS = {
  beginner: {
    label: 'Beginner', badge: 'badge-green',
    days: {
      0: { icon:'🚶', label:'Walk',     rest:false },
      1: { icon:'🏋️', label:'Strength', rest:false },
      2: { icon:'🚶', label:'Cardio',   rest:false },
      3: { icon:'😴', label:'Rest',     rest:true  },
      4: { icon:'🏋️', label:'Strength', rest:false },
      5: { icon:'🧘', label:'Yoga',     rest:false },
      6: { icon:'😴', label:'Rest',     rest:true  },
    },
    exercises: {
      0: { title:'SUNDAY — ACTIVE WALK',   list:[
        {n:'01', name:'Brisk Walk',        meta:'30 min · Steady pace · Cardio',               badge:'Cardio',   bc:'badge-blue'  },
        {n:'02', name:'Light Stretching',  meta:'10 min · Full body · Flexibility',             badge:'Recovery', bc:'badge-blue'  },
      ]},
      1: { title:'MONDAY — STRENGTH A',    list:[
        {n:'01', name:'Bodyweight Squat',  meta:'3 sets × 12 reps · Rest: 60s · Quads, Glutes', badge:'Compound',  bc:'badge-orange'},
        {n:'02', name:'Push-Up',           meta:'3 sets × 10 reps · Rest: 60s · Chest, Triceps',badge:'Compound',  bc:'badge-orange'},
        {n:'03', name:'Dumbbell Row',      meta:'3 sets × 10 reps · Rest: 60s · Back, Biceps',  badge:'Isolation', bc:'badge-blue'  },
        {n:'04', name:'Plank Hold',        meta:'3 sets × 30s · Rest: 45s · Core',              badge:'Core',      bc:'badge-blue'  },
        {n:'05', name:'Glute Bridge',      meta:'3 sets × 15 reps · Rest: 45s · Glutes',        badge:'Isolation', bc:'badge-blue'  },
      ]},
      2: { title:'TUESDAY — CARDIO',       list:[
        {n:'01', name:'Jumping Jacks',     meta:'3 sets × 60s · Rest: 30s · Full Body',         badge:'Cardio',   bc:'badge-blue'  },
        {n:'02', name:'High Knees',        meta:'3 sets × 45s · Rest: 30s · Legs, Cardio',      badge:'Cardio',   bc:'badge-blue'  },
        {n:'03', name:'Mountain Climbers', meta:'3 sets × 40s · Rest: 30s · Core, Cardio',      badge:'Cardio',   bc:'badge-blue'  },
      ]},
      3: { title:'WEDNESDAY — REST DAY',   list:[
        {n:'01', name:'Light Walk',        meta:'Optional · 20 min · Recovery',                  badge:'Optional', bc:'badge-blue'  },
        {n:'02', name:'Foam Rolling',      meta:'10 min · Full body · Mobility',                 badge:'Recovery', bc:'badge-blue'  },
      ]},
      4: { title:'THURSDAY — STRENGTH B',  list:[
        {n:'01', name:'Reverse Lunge',     meta:'3 sets × 10 reps · Rest: 60s · Legs',          badge:'Compound',  bc:'badge-orange'},
        {n:'02', name:'Incline Push-Up',   meta:'3 sets × 12 reps · Rest: 60s · Chest',         badge:'Compound',  bc:'badge-orange'},
        {n:'03', name:'Superman Hold',     meta:'3 sets × 15 reps · Rest: 45s · Lower Back',    badge:'Core',      bc:'badge-blue'  },
        {n:'04', name:'Bicycle Crunch',    meta:'3 sets × 20 reps · Rest: 45s · Core',          badge:'Core',      bc:'badge-blue'  },
      ]},
      5: { title:'FRIDAY — YOGA & FLEX',   list:[
        {n:'01', name:'Sun Salutation',    meta:'5 rounds · Flow sequence · Full Body',          badge:'Yoga',     bc:'badge-blue'  },
        {n:'02', name:'Warrior Pose',      meta:'Hold 30s each side · Balance · Legs',           badge:'Yoga',     bc:'badge-blue'  },
        {n:'03', name:"Child's Pose",      meta:'Hold 60s · Lower Back, Hips',                  badge:'Recovery', bc:'badge-blue'  },
      ]},
      6: { title:'SATURDAY — REST DAY',    list:[
        {n:'01', name:'Full Rest',         meta:'Recovery day — sleep, hydrate, eat well',       badge:'Rest',     bc:'badge-blue'  },
      ]},
    }
  },

  intermediate: {
    label: 'Intermediate', badge: 'badge-yellow',
    days: {
      0: { icon:'😴', label:'Rest',   rest:true  },
      1: { icon:'🏋️', label:'Push',  rest:false },
      2: { icon:'💪', label:'Pull',  rest:false },
      3: { icon:'🦵', label:'Legs',  rest:false },
      4: { icon:'😴', label:'Rest',  rest:true  },
      5: { icon:'🏋️', label:'Push',  rest:false },
      6: { icon:'🏃', label:'Cardio',rest:false },
    },
    exercises: {
      0: { title:'SUNDAY — REST DAY',    list:[{n:'01',name:'Full Rest',meta:'Recovery day — sleep, hydrate',badge:'Rest',bc:'badge-blue'}]},
      1: { title:'MONDAY — PUSH DAY',    list:[
        {n:'01',name:'Bench Press',      meta:'4 sets × 8 reps · Rest: 90s · Chest, Triceps',   badge:'Compound',  bc:'badge-orange'},
        {n:'02',name:'Overhead Press',   meta:'4 sets × 8 reps · Rest: 90s · Shoulders',        badge:'Compound',  bc:'badge-orange'},
        {n:'03',name:'Incline DB Press', meta:'3 sets × 10 reps · Rest: 75s · Upper Chest',     badge:'Isolation', bc:'badge-blue'  },
        {n:'04',name:'Lateral Raises',   meta:'3 sets × 15 reps · Rest: 60s · Delts',           badge:'Isolation', bc:'badge-blue'  },
        {n:'05',name:'Tricep Dips',      meta:'3 sets × 12 reps · Rest: 60s · Triceps',         badge:'Isolation', bc:'badge-blue'  },
      ]},
      2: { title:'TUESDAY — PULL DAY',   list:[
        {n:'01',name:'Pull-Up',          meta:'4 sets × 6 reps · Rest: 90s · Back, Biceps',     badge:'Compound',  bc:'badge-orange'},
        {n:'02',name:'Barbell Row',      meta:'4 sets × 8 reps · Rest: 90s · Back',             badge:'Compound',  bc:'badge-orange'},
        {n:'03',name:'Face Pull',        meta:'3 sets × 15 reps · Rest: 60s · Rear Delts',      badge:'Isolation', bc:'badge-blue'  },
        {n:'04',name:'Bicep Curl',       meta:'3 sets × 12 reps · Rest: 60s · Biceps',          badge:'Isolation', bc:'badge-blue'  },
      ]},
      3: { title:'WEDNESDAY — LEGS',     list:[
        {n:'01',name:'Barbell Squat',    meta:'4 sets × 8 reps · Rest: 2 min · Quads',          badge:'Compound',  bc:'badge-orange'},
        {n:'02',name:'Romanian Deadlift',meta:'4 sets × 8 reps · Rest: 2 min · Hamstrings',     badge:'Compound',  bc:'badge-orange'},
        {n:'03',name:'Leg Press',        meta:'3 sets × 12 reps · Rest: 90s · Quads',           badge:'Isolation', bc:'badge-blue'  },
        {n:'04',name:'Calf Raise',       meta:'4 sets × 20 reps · Rest: 60s · Calves',          badge:'Isolation', bc:'badge-blue'  },
      ]},
      4: { title:'THURSDAY — REST DAY',  list:[{n:'01',name:'Full Rest',meta:'Recovery day',badge:'Rest',bc:'badge-blue'}]},
      5: { title:'FRIDAY — PUSH DAY B',  list:[
        {n:'01',name:'Dumbbell Press',   meta:'4 sets × 10 reps · Rest: 75s · Chest',           badge:'Compound',  bc:'badge-orange'},
        {n:'02',name:'Arnold Press',     meta:'3 sets × 10 reps · Rest: 75s · Shoulders',       badge:'Compound',  bc:'badge-orange'},
        {n:'03',name:'Cable Flyes',      meta:'3 sets × 15 reps · Rest: 60s · Chest',           badge:'Isolation', bc:'badge-blue'  },
      ]},
      6: { title:'SATURDAY — CARDIO',    list:[
        {n:'01',name:'Interval Run',     meta:'20 min · HIIT · Cardio',                         badge:'Cardio',   bc:'badge-blue'  },
        {n:'02',name:'Jump Rope',        meta:'5 min · Steady · Cardio',                        badge:'Cardio',   bc:'badge-blue'  },
      ]},
    }
  },

  advanced: {
    label: 'Advanced', badge: 'badge-orange',
    days: {
      0: { icon:'😴', label:'Rest',     rest:true  },
      1: { icon:'💀', label:'Squat',    rest:false },
      2: { icon:'🏋️', label:'Bench',    rest:false },
      3: { icon:'⚡', label:'Deadlift', rest:false },
      4: { icon:'😴', label:'Rest',     rest:true  },
      5: { icon:'💀', label:'Squat+',   rest:false },
      6: { icon:'🏋️', label:'OHP+',     rest:false },
    },
    exercises: {
      0: { title:'SUNDAY — REST DAY',          list:[{n:'01',name:'Full Rest',meta:'Recovery day',badge:'Rest',bc:'badge-blue'}]},
      1: { title:'MONDAY — SQUAT DAY',         list:[
        {n:'01',name:'Back Squat',             meta:'5 sets × 5 reps · Rest: 3 min · Full Legs',    badge:'Heavy',    bc:'badge-orange'},
        {n:'02',name:'Romanian Deadlift',      meta:'4 sets × 6 reps · Rest: 2.5 min · Hamstrings', badge:'Compound', bc:'badge-orange'},
        {n:'03',name:'Leg Press',              meta:'4 sets × 10 reps · Rest: 2 min · Quads',       badge:'Isolation',bc:'badge-blue'  },
        {n:'04',name:'Nordic Curl',            meta:'3 sets × 6 reps · Rest: 90s · Hamstrings',     badge:'Isolation',bc:'badge-blue'  },
        {n:'05',name:'Ab Wheel Rollout',       meta:'4 sets × 8 reps · Rest: 60s · Core',           badge:'Core',     bc:'badge-blue'  },
      ]},
      2: { title:'TUESDAY — BENCH DAY',        list:[
        {n:'01',name:'Barbell Bench Press',    meta:'5 sets × 5 reps · Rest: 3 min · Chest',        badge:'Heavy',    bc:'badge-orange'},
        {n:'02',name:'Weighted Dip',           meta:'4 sets × 8 reps · Rest: 2 min · Chest, Tri',   badge:'Compound', bc:'badge-orange'},
        {n:'03',name:'Incline DB Press',       meta:'3 sets × 10 reps · Rest: 90s · Upper Chest',   badge:'Isolation',bc:'badge-blue'  },
        {n:'04',name:'Tricep Pushdown',        meta:'3 sets × 15 reps · Rest: 60s · Triceps',       badge:'Isolation',bc:'badge-blue'  },
      ]},
      3: { title:'WEDNESDAY — DEADLIFT DAY',   list:[
        {n:'01',name:'Conventional Deadlift',  meta:'5 sets × 3 reps · Rest: 4 min · Full Body',    badge:'Heavy',    bc:'badge-orange'},
        {n:'02',name:'Barbell Row',            meta:'4 sets × 6 reps · Rest: 2 min · Back',          badge:'Compound', bc:'badge-orange'},
        {n:'03',name:'Pull-Up',               meta:'4 sets × 8 reps · Rest: 90s · Back, Biceps',    badge:'Compound', bc:'badge-orange'},
        {n:'04',name:'Face Pull',             meta:'3 sets × 20 reps · Rest: 60s · Rear Delts',     badge:'Isolation',bc:'badge-blue'  },
      ]},
      4: { title:'THURSDAY — REST DAY',        list:[{n:'01',name:'Full Rest',meta:'Recovery day',badge:'Rest',bc:'badge-blue'}]},
      5: { title:'FRIDAY — SQUAT+ DAY',        list:[
        {n:'01',name:'Front Squat',            meta:'4 sets × 5 reps · Rest: 3 min · Quads',         badge:'Heavy',    bc:'badge-orange'},
        {n:'02',name:'Hack Squat',             meta:'4 sets × 8 reps · Rest: 2 min · Quads',         badge:'Compound', bc:'badge-orange'},
        {n:'03',name:'Leg Extension',          meta:'3 sets × 15 reps · Rest: 60s · Quads',          badge:'Isolation',bc:'badge-blue'  },
      ]},
      6: { title:'SATURDAY — OHP+ DAY',        list:[
        {n:'01',name:'Overhead Press',         meta:'5 sets × 5 reps · Rest: 3 min · Shoulders',     badge:'Heavy',    bc:'badge-orange'},
        {n:'02',name:'Push Press',             meta:'4 sets × 6 reps · Rest: 2.5 min · Shoulders',   badge:'Compound', bc:'badge-orange'},
        {n:'03',name:'Lateral Raise',          meta:'4 sets × 15 reps · Rest: 60s · Delts',          badge:'Isolation',bc:'badge-blue'  },
      ]},
    }
  }
};

// ── State ────────────────────────────────────────────────────
const TODAY_IDX    = new Date().getDay();   // 0=Sun … 6=Sat — computed ONCE at load
let selectedDayIdx = TODAY_IDX;            // tracks which day card is clicked
let activePlan     = 'beginner';

// ── Bootstrap ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  buildAllWeekGrids();                 // render grids dynamically with correct TODAY
  renderExercisesForDay('beginner', TODAY_IDX);
  await renderRecentWorkouts();
  await renderWeekSummary();
});

// ── Build week grid for every plan dynamically ────────────────
// Grid shows Mon → Sun visually. TODAY gets the active-day highlight + TODAY badge.
function buildAllWeekGrids() {
  ['beginner', 'intermediate', 'advanced'].forEach(planId => {
    const container = document.getElementById(`week-grid-${planId}`);
    if (!container) return;

    const plan = PLANS[planId];
    container.innerHTML = VISUAL_ORDER.map(dayIdx => {
      const d       = plan.days[dayIdx];
      const isToday = dayIdx === TODAY_IDX;
      return `
        <div class="day-card ${d.rest ? 'rest' : ''} ${isToday ? 'active-day' : ''}"
             onclick="selectDay('${planId}', ${dayIdx}, this)"
             title="${DAY_FULL[dayIdx]}${isToday ? ' (Today)' : ''}">
          <div class="day-name">
            ${DAY_NAMES[dayIdx]}
            ${isToday ? '<span class="today-dot"></span>' : ''}
          </div>
          <div class="day-icon">${d.icon}</div>
          <div class="day-label">${d.label}</div>
          ${isToday ? '<div class="today-badge">TODAY</div>' : ''}
        </div>`;
    }).join('');
  });
}

// ── Select a day card manually ───────────────────────────────
function selectDay(planId, dayIdx, clickedCard) {
  if (planId !== activePlan) return; // only respond if this plan is active

  // Update highlight
  const grid = document.getElementById(`week-grid-${planId}`);
  if (grid) {
    grid.querySelectorAll('.day-card').forEach(c => c.classList.remove('active-day'));
    clickedCard.classList.add('active-day');
  }

  selectedDayIdx = dayIdx;
  renderExercisesForDay(planId, dayIdx);
}

// ── Switch plan tab ──────────────────────────────────────────
function switchPlan(btn, planId) {
  document.querySelectorAll('.plan-tab').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.plan-content').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('plan-' + planId)?.classList.add('active');
  activePlan = planId;
  // Reset to today whenever switching plan
  selectedDayIdx = TODAY_IDX;
  // Re-highlight today in this plan's grid
  const grid = document.getElementById(`week-grid-${planId}`);
  if (grid) {
    grid.querySelectorAll('.day-card').forEach((card, i) => {
      const dayIdx = VISUAL_ORDER[i];
      card.classList.toggle('active-day', dayIdx === TODAY_IDX);
    });
  }
  renderExercisesForDay(planId, TODAY_IDX);
}

// ── Render exercise list for a specific day ──────────────────
function renderExercisesForDay(planId, dayIdx) {
  const plan      = PLANS[planId];
  const dayData   = plan?.exercises[dayIdx];
  const container = document.getElementById(`exercises-${planId}`);
  const heading   = document.getElementById(`heading-${planId}`);
  if (!container) return;

  const isToday   = dayIdx === TODAY_IDX;
  const dayLabel  = isToday ? 'TODAY' : DAY_FULL[dayIdx].toUpperCase();

  if (heading) {
    heading.textContent = dayData?.title ?? `${DAY_FULL[dayIdx].toUpperCase()} — REST DAY`;
    heading.style.color = isToday ? 'var(--accent)' : '';
  }

  if (!dayData?.list?.length) {
    container.innerHTML = `
      <div style="color:var(--text-muted);padding:2rem;text-align:center">
        <div style="font-size:2.5rem">😴</div>
        <div style="font-family:var(--font-condensed);letter-spacing:1px;margin-top:0.75rem;font-size:1rem">REST DAY — RECOVERY IS PROGRESS</div>
        <div style="font-size:0.8rem;margin-top:0.4rem;opacity:0.6">Sleep well, hydrate, and eat enough protein.</div>
      </div>`;
    return;
  }

  container.innerHTML = dayData.list.map(ex => `
    <div class="exercise-item">
      <div class="ex-num">${ex.n}</div>
      <div class="ex-info">
        <div class="ex-name">${ex.name}</div>
        <div class="ex-meta">${ex.meta}</div>
      </div>
      <div class="ex-badge-col"><span class="badge ${ex.bc}">${ex.badge}</span></div>
    </div>`).join('');
}

// ── Log Quick Workout ────────────────────────────────────────
async function logQuickWorkout() {
  const type      = document.getElementById('qType')?.value;
  const duration  = parseInt(document.getElementById('qDuration')?.value);
  const intensity = document.getElementById('qIntensity')?.value;

  if (!duration || duration < 1) { showToast('Please enter a valid duration', 'error'); return; }

  const calories = estimateCaloriesBurned(duration, intensity);
  try {
    const res = await apiFetch('/workouts', {
      method: 'POST',
      body: JSON.stringify({ type, duration, intensity, calories, completed: true, tz_offset: getTzOffset() })
    });
    showToast(`${type} logged! 🔥 ${calories} kcal burned`, 'success');
    if (res.new_achievements?.length) {
      res.new_achievements.forEach(k => showToast(`🏆 Achievement: ${k.replace(/_/g,' ')}`, 'success'));
    }
    document.getElementById('qDuration').value = '';
    await renderRecentWorkouts();
    await renderWeekSummary();
  } catch (err) {
    showToast(err.message || 'Failed to log workout', 'error');
  }
}

// ── Recent Sessions ──────────────────────────────────────────
async function renderRecentWorkouts() {
  const container = document.getElementById('recentWorkouts');
  if (!container) return;
  try {
    const data     = await apiFetch('/workouts?days=14');
    const workouts = data.workouts || [];
    const icons    = { Cardio:'🏃', Strength:'🏋️', Yoga:'🧘', HIIT:'⚡', Swimming:'🏊', Cycling:'🚴' };

    if (!workouts.length) {
      container.innerHTML = '<div style="color:var(--text-muted);padding:1rem;font-size:0.85rem">No workouts logged yet. Log your first session above!</div>';
      return;
    }

    const todayStr = getTodayKey();
    const yesterdayStr = (() => {
      const d = new Date(); d.setDate(d.getDate() - 1);
      return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    })();

    container.innerHTML = workouts.slice(0, 6).map(w => {
      let dateLabel;
      if (w.date === todayStr)          dateLabel = '🟢 Today';
      else if (w.date === yesterdayStr) dateLabel = 'Yesterday';
      else {
        const d = new Date(w.date + 'T00:00:00');
        dateLabel = d.toLocaleDateString('en-GB', { day:'numeric', month:'short' });
      }
      return `
        <div class="recent-item">
          <div class="recent-item-icon">${icons[w.type] || '💪'}</div>
          <div class="ri-info">
            <div class="ri-name">${w.type} Training</div>
            <div class="ri-meta">${w.duration} min · ${w.intensity} · ${w.calories} kcal · ${dateLabel}</div>
          </div>
        </div>`;
    }).join('');
  } catch {
    container.innerHTML = '<div style="color:var(--text-muted);padding:1rem">Could not load workouts.</div>';
  }
}

// ── Week Summary ─────────────────────────────────────────────
async function renderWeekSummary() {
  try {
    const data = await apiFetch('/workouts/stats?days=7');
    setEl('weekSessions', (data.total_sessions ?? '—') + ' Sessions');
    setEl('weekDuration', data.total_duration ? data.total_duration + ' min' : '—');
    setEl('weekCalories', data.total_calories ? data.total_calories.toLocaleString() + ' kcal' : '—');
  } catch {}
}

function setEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
