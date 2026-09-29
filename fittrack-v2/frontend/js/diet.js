// ============================================================
// diet.js — Nutrition tracking — talks to Flask API
// GET /api/meals   POST /api/meals   DELETE /api/meals/:id
// FIXES:
//   3. Calorie goal was hardcoded 2000 everywhere — now loaded
//      from /api/profile and used throughout (remaining, chart,
//      insights, net calories).
//   5. Net calories was hardcoded (-560) — now calculated as
//      (calories_in - calories_burned_today) using real data.
// ============================================================

let mealData      = { breakfast: [], lunch: [], dinner: [], snack: [] };
let macroChart    = null;
let userCalGoal   = 2000;   // will be overwritten from profile API
let caloriesBurnedToday = 0; // loaded from dashboard summary

document.addEventListener('DOMContentLoaded', async () => {
    if (!requireAuth()) return;
    await loadUserGoal();   // load real calorie goal FIRST
    await loadMeals();
    initMacroChart();
    renderDietPlans();
});

// FIX 3: Load user's real calorie goal from profile
async function loadUserGoal() {
    try {
        const [profileData, summaryData] = await Promise.all([
            apiFetch('/profile'),
            apiFetch('/dashboard/summary')
        ]);
        const profile = profileData.profile || {};
        userCalGoal         = profile.daily_calorie_goal || 2000;
        caloriesBurnedToday = summaryData.calories_burned || 0;
    } catch {
        userCalGoal         = 2000;
        caloriesBurnedToday = 0;
    }
}

async function loadMeals() {
    try {
        const today = getTodayKey();
        const data  = await apiFetch(`/meals?date=${today}`);
        const meals = data.meals || [];

        mealData = { breakfast: [], lunch: [], dinner: [], snack: [] };
        meals.forEach(m => {
            const type = m.type;
            if (mealData[type]) mealData[type].push(m);
        });

        renderAll();
        updateMacroChart();
    } catch (err) {
        showToast('Could not load meals: ' + err.message, 'error');
    }
}

function openAddMeal(type) {
    const sel = document.getElementById('mealType');
    if (sel) sel.value = type;
    document.getElementById('addMealCard')?.scrollIntoView({ behavior: 'smooth' });
    document.getElementById('foodName')?.focus();
}

async function addMealEntry() {
    const type = document.getElementById('mealType')?.value;
    const name = document.getElementById('foodName')?.value.trim();
    const cal  = parseInt(document.getElementById('foodCal')?.value);
    const cat  = document.getElementById('foodCat')?.value;

    if (!name)           { showToast('Please enter a food name',    'error'); return; }
    if (!cal || cal < 1) { showToast('Please enter valid calories', 'error'); return; }

    try {
        const data = await apiFetch('/meals', {
            method: 'POST',
            body: JSON.stringify({ type, name, calories: cal, category: cat, tz_offset: getTzOffset() })
        });
        const meal = data.meal;
        if (!mealData[type]) mealData[type] = [];
        mealData[type].push(meal);
        renderAll();
        updateMacroChart();
        showToast(`${name} added! +${cal} kcal 🥗`, 'success');
        document.getElementById('foodName').value = '';
        document.getElementById('foodCal').value  = '';
    } catch (err) {
        showToast(err.message || 'Failed to add meal', 'error');
    }
}

async function deleteMealEntry(type, id) {
    try {
        await apiFetch(`/meals/${id}`, { method: 'DELETE' });
        mealData[type] = (mealData[type] || []).filter(e => e.id !== id);
        renderAll();
        updateMacroChart();
    } catch (err) {
        showToast(err.message || 'Failed to delete meal', 'error');
    }
}

function renderAll() {
    ['breakfast', 'lunch', 'dinner', 'snack'].forEach(type => {
        const container = document.getElementById(`${type}-entries`);
        if (!container) return;
        const entries = mealData[type] || [];
        if (!entries.length) {
            container.innerHTML = '<div style="color:var(--text-muted);font-size:0.82rem;padding:0.5rem 0">No meals logged yet</div>';
            return;
        }
        container.innerHTML = entries.map(e => `
            <div class="meal-entry">
                <span>${e.category || '🍽️'}</span>
                <span class="me-name">${e.name}</span>
                <span class="me-cal">${e.calories} kcal</span>
                <button class="me-delete" onclick="deleteMealEntry('${type}', ${e.id})">✕</button>
            </div>`).join('');
    });

    const total   = Object.values(mealData).flat().reduce((s, e) => s + e.calories, 0);
    const goal    = userCalGoal;                              // FIX 3: real goal
    const remain  = Math.max(0, goal - total);
    // FIX 5: net = calories consumed minus calories burned today
    const net     = total - caloriesBurnedToday;
    const netSign = net >= 0 ? '+' : '';

    const calInEl  = document.getElementById('calIn');
    const calRemEl = document.getElementById('calRemain');
    const totalEl  = document.getElementById('totalCalDisplay');
    const netEl    = document.getElementById('netCalories');

    if (calInEl)  calInEl.textContent  = total + ' kcal';
    if (calRemEl) calRemEl.textContent = remain + ' kcal';    // FIX 3
    if (totalEl)  totalEl.textContent  = total + ' kcal logged';
    if (netEl)    netEl.textContent    = netSign + net + ' kcal';  // FIX 5

    updateDietInsights(total, goal);
}

function initMacroChart() {
    const ctx = document.getElementById('macroChart');
    if (!ctx) return;
    macroChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, userCalGoal],                       // FIX 3: real goal
                backgroundColor: ['#f4501e', 'rgba(255,255,255,0.05)'],
                borderWidth: 0,
                cutout: '75%'
            }]
        },
        options: {
            responsive: false,
            plugins: { legend: { display: false }, tooltip: { enabled: false } }
        }
    });
}

function updateMacroChart() {
    if (!macroChart) return;
    const total = Object.values(mealData).flat().reduce((s, e) => s + e.calories, 0);
    const goal  = userCalGoal;                                // FIX 3: real goal
    macroChart.data.datasets[0].data = [total, Math.max(0, goal - total)];
    macroChart.update();
}

// FIX 3: insight thresholds now relative to real user goal
function updateDietInsights(total, goal) {
    const container = document.getElementById('dietInsights');
    if (!container) return;
    const msgs   = [];
    const low    = Math.round(goal * 0.75);   // 75% of goal = too low
    const high   = Math.round(goal * 1.10);   // 110% of goal = over

    if (total === 0)
        msgs.push('Start logging your meals to get AI insights!');
    else if (total < low)
        msgs.push(`⚠️ Calorie intake is low today (${total} / ${goal} kcal). Make sure you're eating enough.`);
    else if (total > high)
        msgs.push(`📊 You're over your daily goal (${total} / ${goal} kcal). Consider lighter snacks.`);
    else
        msgs.push(`✅ You're in a healthy calorie range for your goal! (${total} / ${goal} kcal)`);

    msgs.push('💡 Tip: Eating protein with every meal helps preserve muscle during weight loss.');
    msgs.push('💧 Remember to drink at least 8 glasses of water today.');
    container.innerHTML = msgs.map(m => `<div>${m}</div>`).join('');
}

function renderDietPlans() {
    const user  = getCurrentUser() || {};
    const goal  = user.goal || 'weight_loss';
    const plans = getDietPlans();
    const container = document.getElementById('dietPlans');
    if (!container) return;
    container.innerHTML = Object.entries(plans).map(([key, plan]) => `
        <div class="diet-plan-card ${key === goal ? 'active' : ''}">
            <div class="flex-between">
                <div class="diet-plan-title">${plan.icon} ${plan.label}</div>
                ${key === goal ? '<span class="badge badge-orange">YOUR PLAN</span>' : ''}
            </div>
            <div style="color:var(--text-secondary);font-size:0.85rem;margin-top:0.3rem">${plan.description}</div>
            <div class="flex" style="gap:1rem;margin-top:0.75rem;font-size:0.8rem">
                <span class="text-accent font-condensed">${plan.calories} kcal/day</span>
                <span class="text-muted">·</span>
                <span class="text-secondary">${plan.macros}</span>
            </div>
            <div class="food-tags">${plan.foods.map(f => `<span class="food-tag">${f}</span>`).join('')}</div>
        </div>`).join('');
}

function getDietPlans() {
    return {
        weight_loss: { icon: '🔥', label: 'Weight Loss Plan', description: 'High protein, low-calorie meals to promote fat loss while preserving muscle.', calories: '1600-1800', macros: '40% Protein · 30% Carbs · 30% Fats', foods: ['Oats', 'Eggs', 'Chicken Breast', 'Broccoli', 'Salmon', 'Greek Yogurt', 'Spinach', 'Sweet Potato'] },
        muscle_gain: { icon: '💪', label: 'Muscle Gain Plan', description: 'High protein, high carbohydrate meals to fuel muscle growth and recovery.',   calories: '2500-3000', macros: '35% Protein · 45% Carbs · 20% Fats', foods: ['Rice', 'Chicken', 'Eggs', 'Milk', 'Beef', 'Pasta', 'Banana', 'Oats', 'Nuts', 'Avocado'] },
        maintenance: { icon: '⚖️', label: 'Maintenance Plan', description: 'Balanced nutrition to maintain your current weight and energy levels.',        calories: '2000-2200', macros: '30% Protein · 40% Carbs · 30% Fats', foods: ['Mixed Grains', 'Lean Meat', 'Fish', 'Vegetables', 'Fruits', 'Legumes', 'Dairy', 'Nuts'] },
        endurance:   { icon: '🏃', label: 'Endurance Plan',   description: 'Carbohydrate-rich meals to fuel long cardio sessions and recovery.',           calories: '2200-2600', macros: '25% Protein · 55% Carbs · 20% Fats', foods: ['Pasta', 'Rice', 'Bread', 'Banana', 'Dates', 'Sweet Potato', 'Oats', 'Sports Drink'] }
    };
}
