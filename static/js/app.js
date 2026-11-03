let currentPlayer = null;
let playerId = localStorage.getItem('rpg_player_id');
let abilitiesCache = [];
let genresCache = [];
let selectedGenre = null;
let selectedSecondary = null;

// --- ПОЛЬЗОВАТЕЛЬ ---
// Токен объединяет сессии одного игрока (нужен для сохранений).
function ensureUserToken() {
    let token = localStorage.getItem('rpg_user_token');
    if (!token) {
        token = (window.crypto && crypto.randomUUID)
            ? crypto.randomUUID()
            : `u_${Date.now()}_${Math.random().toString(36).slice(2)}`;
        localStorage.setItem('rpg_user_token', token);
    }
    return token;
}

// --- ЖАНРЫ ---
async function loadGenres() {
    try {
        const response = await fetch('/genres');
        const data = await response.json();
        genresCache = data.genres || [];
        renderGenreGrids();
    } catch (e) {
        console.error('Не удалось загрузить жанры:', e);
    }
}

function genreName(code) {
    const found = genresCache.find(g => g.code === code);
    return found ? found.name : null;
}

function renderGenreGrids() {
    const primaryGrid = document.getElementById('genre-grid');
    const secondaryGrid = document.getElementById('genre-secondary-grid');
    if (!primaryGrid || !secondaryGrid) return;

    primaryGrid.innerHTML = '';
    secondaryGrid.innerHTML = '';

    genresCache.forEach(genre => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'genre-card';
        card.dataset.code = genre.code;
        card.innerHTML = `<b>${genre.name}</b><span>${genre.description}</span>`;
        card.onclick = () => selectGenre(genre.code);
        primaryGrid.appendChild(card);
    });

    genresCache.forEach(genre => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'genre-chip';
        chip.dataset.code = genre.code;
        chip.textContent = genre.name;
        chip.onclick = () => selectSecondary(genre.code);
        secondaryGrid.appendChild(chip);
    });

    refreshGenreSelection();
}

function selectGenre(code) {
    selectedGenre = code;
    if (selectedSecondary === code) selectedSecondary = null;
    refreshGenreSelection();
}

function selectSecondary(code) {
    selectedSecondary = (selectedSecondary === code) ? null : code;
    refreshGenreSelection();
}

function refreshGenreSelection() {
    document.querySelectorAll('#genre-grid .genre-card').forEach(card => {
        card.classList.toggle('is-selected', card.dataset.code === selectedGenre);
    });
    document.querySelectorAll('#genre-secondary-grid .genre-chip').forEach(chip => {
        chip.classList.toggle('is-selected', chip.dataset.code === selectedSecondary);
        chip.classList.toggle('is-disabled', chip.dataset.code === selectedGenre);
    });

    const pickBtn = document.getElementById('book-pick-btn');
    if (pickBtn) {
        pickBtn.disabled = !selectedGenre;
        pickBtn.innerText = selectedGenre
            ? 'Выбрать файл .txt'
            : 'Сначала выберите жанр';
    }
}

function applyStatLabels(primary, secondary) {
    const primaryProfile = genresCache.find(g => g.code === primary);
    let labels = primaryProfile && primaryProfile.stat_labels ? { ...primaryProfile.stat_labels } : null;
    const secondaryProfile = genresCache.find(g => g.code === secondary);
    if (secondaryProfile && secondaryProfile.stat_labels) {
        labels = { ...(labels || {}), ...secondaryProfile.stat_labels };
    }

    document.querySelectorAll('.stat-row[data-stat]').forEach(row => {
        const labelEl = row.querySelector('.stat-name');
        if (!labelEl) return;
        const base = labelEl.dataset.base || labelEl.innerText;
        labelEl.innerText = (labels && labels[row.dataset.stat]) || base;
    });
}


// --- ОНБОРДИНГ ---
async function createPlayer() {
    const nameInput = document.getElementById('player-name-input');
    const name = nameInput.value.trim();
    if (!name) return alert("Введите имя!");

    try {
        if (playerId) {
            // Свежий герой уже создан (например, после «Сменить книгу») — задаём имя.
            const response = await fetch(`/player/${playerId}/name`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name})
            });
            if (!response.ok) throw new Error("Не удалось сохранить имя");
        } else {
            const response = await fetch('/player/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: name, user_token: ensureUserToken()})
            });
            const newPlayer = await response.json();
            localStorage.setItem('rpg_player_id', newPlayer.id);
            playerId = newPlayer.id;
        }

        document.getElementById('step-name').style.display = 'none';
        document.getElementById('step-book').style.display = 'block';
    } catch (e) {
        alert("Ошибка при создании персонажа.");
    }
}

async function startNewGame() {
    if (!playerId) return;

    const confirmed = confirm(
        "Начнётся новая игра с новым героем.\nТекущая сессия будет сохранена.\n\nПродолжить?"
    );
    if (!confirmed) return;

    try {
        const response = await fetch(`/player/${playerId}/new_game`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_token: ensureUserToken()})
        });
        if (!response.ok) throw new Error("Не удалось начать новую игру");

        const data = await response.json();
        if (data.player_id) {
            localStorage.setItem('rpg_player_id', data.player_id);
            playerId = data.player_id;
        }
        location.reload();
    } catch (e) {
        alert(`Ошибка: ${e.message}`);
    }
}

async function uploadBook() {
    const fileInput = document.getElementById('book-file');
    const file = fileInput.files[0];
    if (!file) return;

    if (!selectedGenre) {
        alert('Сначала выберите жанр книги.');
        return;
    }

    document.getElementById('book-pick-btn').style.display = 'none';
    document.getElementById('book-progress').style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);
    formData.append('genre', selectedGenre);
    if (selectedSecondary) formData.append('genre_secondary', selectedSecondary);

    try {
        const response = await fetch(`/upload_book/${playerId}`, {
            method: 'POST',
            body: formData
        });
        if (response.ok) {
            location.reload();
        } else {
            alert("Ошибка при загрузке книги.");
            location.reload();
        }
    } catch (e) {
        alert("Ошибка сети при загрузке книги.");
        location.reload();
    }
}

// --- ОСНОВНАЯ ИГРА ---
async function loadPlayer() {
    if (!playerId) {
        document.getElementById('onboarding-screen').style.display = 'flex';
        return;
    }

    try {
        const response = await fetch(`/player/${playerId}`);
        if (!response.ok) {
            localStorage.removeItem('rpg_player_id');
            location.reload();
            return;
        }
        currentPlayer = await response.json();

        if (!currentPlayer.name) {
            // Новый герой без имени — начинаем с первого шага.
            document.getElementById('onboarding-screen').style.display = 'flex';
            document.getElementById('step-name').style.display = 'block';
            document.getElementById('step-book').style.display = 'none';
            return;
        }

        if (!currentPlayer.book_file) {
            document.getElementById('onboarding-screen').style.display = 'flex';
            document.getElementById('step-name').style.display = 'none';
            document.getElementById('step-book').style.display = 'block';
            return;
        }

        document.getElementById('onboarding-screen').style.display = 'none';
        document.getElementById('game-screen').style.display = 'grid';

        const prevSnapshot = fx.snapshot;

        document.getElementById('c-name').innerText = currentPlayer.name;
        document.getElementById('c-level').innerText = currentPlayer.level;
        document.getElementById('c-loc').innerText = currentPlayer.location;

        if (!genresCache.length) await loadGenres();

        const primaryName = genreName(currentPlayer.genre);
        const secondaryName = currentPlayer.genre_secondary ? genreName(currentPlayer.genre_secondary) : null;
        const genreLabel = primaryName
            ? (secondaryName ? `${primaryName} · ${secondaryName}` : primaryName)
            : '—';
        document.getElementById('c-genre').innerText = genreLabel;
        applyStatLabels(currentPlayer.genre, currentPlayer.genre_secondary);
        
        document.getElementById('s-str').innerText = currentPlayer.strength;
        document.getElementById('s-agi').innerText = currentPlayer.agility;
        document.getElementById('s-vit').innerText = currentPlayer.vitality;
        document.getElementById('s-int').innerText = currentPlayer.intelligence;
        document.getElementById('s-per').innerText = currentPlayer.perception;
        document.getElementById('s-lck').innerText = currentPlayer.luck;
        
        document.getElementById('c-points').innerText = currentPlayer.stat_points;
        document.getElementById('c-ab-points').innerText = currentPlayer.ability_points;
        
        const plusButtons = document.querySelectorAll('.btn-plus');
        plusButtons.forEach(btn => { btn.disabled = currentPlayer.stat_points <= 0; });

        document.getElementById('hp-bar').style.width = `${(currentPlayer.hp / currentPlayer.max_hp) * 100}%`;
        document.getElementById('hp-text').innerText = `${currentPlayer.hp} / ${currentPlayer.max_hp} HP`;
        document.getElementById('xp-bar').style.width = `${(currentPlayer.xp / currentPlayer.next_level_xp) * 100}%`;
        document.getElementById('xp-text').innerText = `${currentPlayer.xp} / ${currentPlayer.next_level_xp} XP`;

        const hpRatio = currentPlayer.max_hp > 0 ? currentPlayer.hp / currentPlayer.max_hp : 0;
        document.getElementById('hp-bar').parentElement.classList.toggle('is-low', hpRatio > 0 && hpRatio <= 0.3);

        // Сумка
        const bag = document.getElementById('bag-container');
        bag.innerHTML = '';
        if (currentPlayer.inventory && currentPlayer.inventory.length > 0) {
            currentPlayer.inventory.forEach(item => {
                const div = document.createElement('div');
                div.className = 'bag-item';
                div.innerText = item;
                div.style.cursor = 'pointer';
                div.title = 'ЛКМ - надеть, ПКМ - выбросить';
                div.onclick = () => {
                    const slot = prompt("В какой слот надеть? (weapon, armor, helmet, boots, ring)", "weapon");
                    if (slot) equipItem(item, slot);
                };
                div.oncontextmenu = (e) => {
                    e.preventDefault();
                    if(confirm(`Выбросить ${item}?`)) dropItem(item);
                };
                bag.appendChild(div);
            });
        } else {
            bag.innerHTML = '<div style="grid-column: span 4; text-align:center; color:#555; font-size:0.8em; padding: 10px;">Пусто</div>';
        }
        
        // Экипировка
        const eq = currentPlayer.equipment || {};
        const iconSlot = (type) => `<span class="eq-ico" style="--ico:url('/static/icons/${type}.svg')"></span>`;
        document.querySelectorAll('.eq-slot').forEach(slot => {
            const type = slot.getAttribute('data-type');
            if (type) {
                if (eq[type]) {
                    slot.innerHTML = `<span style="font-size:0.75em; color:#fff; text-align:center; line-height:1.1; word-break:break-word;">${eq[type]}</span>`;
                    slot.style.cursor = 'pointer';
                    slot.onclick = () => unequipItem(type);
                } else {
                    slot.innerHTML = iconSlot(type);
                    slot.style.cursor = 'default';
                    slot.onclick = null;
                }
            }
        });

        // Красивые подсказки слотов (переносим title в data-tip)
        document.querySelectorAll('.eq-slot[title]').forEach(slot => {
            slot.dataset.tip = slot.title;
            slot.removeAttribute('title');
        });

        // Способности
        await refreshAbilities();

        // Восстановление сюжета
        const storyDiv = document.getElementById('story');
        if (currentPlayer.history && currentPlayer.history.length > 0) {
            const recentHistory = currentPlayer.history.slice(-2);
            let html = "";
            recentHistory.forEach(log => {
                if (log.startsWith("Игрок: ")) html += `<div class="past-action">> ${log.replace("Игрок: ", "")}</div>`;
                else if (log.startsWith("Мастер: ")) html += `<div>${log.replace("Мастер: ", "").replace(/\n/g, '<br>')}</div>`;
            });
            if (html) storyDiv.innerHTML = html;
        } else {
            storyDiv.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 250px; text-align: center;">
                    <h2 style="color: #e0b050; margin-bottom: 10px;">Глава 1. Пробуждение</h2>
                    <p style="color: #aaa; font-size: 1.1em; margin-bottom: 25px; max-width: 400px;">Тьма рассеивается. Вы не помните, как здесь оказались. Ваша история только начинается...</p>
                    <button class="btn-action" style="width: auto; padding: 15px 40px; font-size: 1.2em;" onclick="submitAction('Начать приключение')">Начать путь</button>
                </div>
            `;
        }

        // Мягкое появление нового текста
        const historyKey = `${(currentPlayer.history || []).length}|${(currentPlayer.history || []).slice(-1)[0] || ''}`;
        if (storyDiv.dataset.historyKey !== historyKey) {
            storyDiv.dataset.historyKey = historyKey;
            storyDiv.classList.remove('story-fresh');
            void storyDiv.offsetWidth;
            storyDiv.classList.add('story-fresh');
        }

        // Реакция интерфейса на изменения (урон, лечение, опыт, уровень)
        fx.diff(prevSnapshot, currentPlayer);
        fx.snapshot = fx.capture(currentPlayer);

        // Если есть враг, показываем боевой экран
        if (currentPlayer.enemy && currentPlayer.enemy.name && currentPlayer.enemy.hp > 0) {
            openCombatScreen(currentPlayer.enemy);
        }

    } catch (error) { console.error("Ошибка:", error); }
}

async function upgrade(statName) {
    if (!currentPlayer || currentPlayer.stat_points <= 0) return;
    try {
        const response = await fetch(`/player/${playerId}/upgrade`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({stat_name: statName})
        });
        if (response.ok) await loadPlayer();
    } catch (e) { console.error(e); }
}

async function learnAbility(abilityId) {
    try {
        const response = await fetch(`/abilities/${playerId}/learn`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ability_id: abilityId})
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || 'Не удалось изучить способность');
            return;
        }
        await loadPlayer();
    } catch (e) { console.error(e); }
}

async function useAbility(abilityId) {
    const ab = abilitiesCache.find(a => a.id === abilityId);
    let target = '';
    if (ab && ab.effect === 'charm') {
        target = (prompt('С кем взаимодействовать?', '') || '').trim();
    }

    try {
        const response = await fetch(`/abilities/${playerId}/use`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ability_id: abilityId, target: target})
        });
        const data = await response.json();
        if (!response.ok) {
            alert(data.detail || 'Не удалось применить способность');
            return;
        }

        const storyDiv = document.getElementById('story');
        const label = ab ? ab.name : 'Способность';
        if (data.story) {
            storyDiv.innerHTML = `<div class="past-action">> 📖 ${label}</div><div>${data.story.replace(/\n/g, '<br>')}</div>`;
        }
        await loadPlayer();
        showEffects(data.effects || []);
    } catch (e) { console.error(e); }
}

function showEffects(effects) {
    const log = document.getElementById('effects-log');
    if (!log) return;
    log.innerHTML = '';
    effects.forEach(effect => {
        const span = document.createElement('span');
        span.className = 'effect-badge';
        span.innerText = effect;
        log.appendChild(span);
    });
}

async function refreshAbilities() {
    if (!playerId) return;
    try {
        const response = await fetch(`/abilities/${playerId}`);
        if (!response.ok) return;
        const data = await response.json();
        abilitiesCache = data.abilities || [];
        renderAbilities();
        renderCombatAbilities();
    } catch (e) { console.error('Не удалось загрузить способности:', e); }
}

function abilityStars(ab) {
    const filled = '★'.repeat(ab.rank || 0);
    const empty = '☆'.repeat(Math.max(0, (ab.max_rank || 1) - (ab.rank || 0)));
    return filled + empty;
}

function renderAbilities() {
    const list = document.getElementById('abilities-list');
    if (!list) return;
    list.innerHTML = '';

    if (!abilitiesCache.length) {
        list.innerHTML = '<div class="ability-empty">Способности появятся здесь</div>';
        return;
    }

    abilitiesCache.forEach(ab => {
        const card = document.createElement('div');
        card.className = 'ability-card ' + (ab.learned ? 'is-learned' : 'is-locked') + (ab.source === 'book' ? ' is-book' : '');

        const head = document.createElement('div');
        head.className = 'ability-head';
        head.innerHTML = `<b>${ab.name}</b>` + (ab.learned ? `<span class="ability-rank">${abilityStars(ab)}</span>` : '');
        card.appendChild(head);

        const desc = document.createElement('div');
        desc.className = 'ability-desc';
        desc.innerText = ab.description || '';
        card.appendChild(desc);

        const meta = document.createElement('div');
        meta.className = 'ability-meta';
        if (ab.learned) {
            meta.innerText = ab.cooldown_left > 0
                ? `Перезарядка: ${ab.cooldown_left}`
                : `Готово · ранг ${ab.rank}/${ab.max_rank}`;
        } else {
            meta.innerText = `Стоимость: ${ab.cost} очк.`;
        }
        card.appendChild(meta);

        const actions = document.createElement('div');
        actions.className = 'ability-actions';

        if (ab.learned && ab.usable && ab.field) {
            const useBtn = document.createElement('button');
            useBtn.className = 'ability-btn';
            useBtn.innerText = 'Использовать';
            useBtn.onclick = () => useAbility(ab.id);
            actions.appendChild(useBtn);
        }

        if (!ab.learned || !ab.maxed) {
            const learnBtn = document.createElement('button');
            learnBtn.className = 'ability-btn ability-btn-learn';
            learnBtn.innerText = ab.learned ? `Улучшить (${ab.cost})` : `Изучить (${ab.cost})`;
            const points = currentPlayer ? currentPlayer.ability_points : 0;
            learnBtn.disabled = points < ab.cost;
            learnBtn.onclick = () => learnAbility(ab.id);
            actions.appendChild(learnBtn);
        }

        if (actions.children.length) card.appendChild(actions);
        list.appendChild(card);
    });
}

async function equipItem(itemName, slot) {
    try {
        const response = await fetch(`/player/${playerId}/equip`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_name: itemName, slot: slot})
        });
        if (response.ok) await loadPlayer();
    } catch (e) { console.error(e); }
}

async function unequipItem(slot) {
    try {
        const response = await fetch(`/player/${playerId}/unequip`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({item_name: "", slot: slot})
        });
        if (response.ok) await loadPlayer();
    } catch (e) { console.error(e); }
}

async function dropItem(itemName) {
    try {
        const response = await fetch(`/player/${playerId}/drop`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ability_name: itemName})
        });
        if (response.ok) await loadPlayer();
    } catch (e) { console.error(e); }
}

async function submitAction(forcedText = null) {
    const input = document.getElementById('custom-input');
    const actionText = forcedText || input.value.trim();
    if (!actionText) return;

    const storyDiv = document.getElementById('story');
    const effectsLog = document.getElementById('effects-log');
    storyDiv.innerHTML = "<span class='loading'>Мастер Игры описывает последствия...</span>";
    effectsLog.innerHTML = '';
    input.disabled = true;
    
    try {
        const response = await fetch(`/story/${playerId}?choice=${encodeURIComponent(actionText)}`);
        const data = await response.json();
        
        if (data.effects && data.effects.length > 0) {
            data.effects.forEach(effect => {
                const span = document.createElement('span');
                span.className = 'effect-badge';
                span.innerText = effect;
                effectsLog.appendChild(span);
            });
        }
        await loadPlayer();
    } catch (error) {
        storyDiv.innerHTML = "<span style='color: #ff5555;'>Ошибка сервера. Проверьте терминал.</span>";
    } finally {
        input.disabled = false;
        input.value = '';
        input.focus();
    }
}

document.getElementById('custom-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') submitAction();
});

async function resetGame() {
    if (confirm("Начать заново? Весь прогресс будет потерян.")) {
        await fetch(`/reset/${playerId}`);
        location.reload();
    }
}

// Журнал квестов
function openQuests() {
    const modal = document.getElementById('quest-modal');
    const container = document.getElementById('quest-list-container');
    container.innerHTML = '';

    if (!currentPlayer || !currentPlayer.quests || currentPlayer.quests.length === 0) {
        container.innerHTML = '<div style="color: #888; text-align: center;">Пока нет активных заданий.</div>';
    } else {
        currentPlayer.quests.forEach(quest => {
            const div = document.createElement('div');
            const isCompleted = quest.status === 'completed';
            const color = isCompleted ? '#666' : '#e0b050';
            const statusText = isCompleted ? '✅ Выполнен' : '⏳ Активен';
            
            div.style.cssText = `background: #252525; padding: 15px; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid ${color}; opacity: ${isCompleted ? '0.6' : '1'};`;
            div.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong style="color: ${color}; font-size: 1.1em;">${quest.title || 'Без названия'}</strong>
                    <span style="font-size: 0.8em; color: #aaa;">${statusText}</span>
                </div>
                <div style="font-size: 0.9em; margin-bottom: 10px;">${quest.description || 'Нет описания.'}</div>
                <div style="font-size: 0.8em; color: #888; border-top: 1px dashed #444; padding-top: 5px;">
                    📍 Где: ${quest.location || 'Неизвестно'} | 👤 Кто дал: ${quest.giver || 'Неизвестно'}
                </div>
            `;
            container.appendChild(div);
        });
    }
    modal.style.display = 'flex';
}

function closeQuests() {
    document.getElementById('quest-modal').style.display = 'none';
}

// --- ЛОГИКА JRPG БОЯ ---
function openCombatScreen(enemy) {
    const screen = document.getElementById('combat-screen');
    screen.style.display = 'flex';
    screen.classList.remove('is-open');
    void screen.offsetWidth;
    screen.classList.add('is-open');
    updateCombatUI(enemy);
    renderCombatAbilities();
}

function updateCombatUI(enemy) {
    if (!enemy || !enemy.name) {
        closeCombat();
        return;
    }
    
    document.getElementById('combat-enemy-name').innerText = enemy.name;
    const maxHp = enemy.max_hp || enemy.hp;
    document.getElementById('combat-enemy-hp-text').innerText = `${enemy.hp} / ${maxHp} HP`;
    document.getElementById('combat-enemy-hp-bar').style.width = `${Math.max(0, (enemy.hp / maxHp) * 100)}%`;
    document.getElementById('combat-player-hp').innerText = currentPlayer.hp;
}

async function doCombatAbility(abilityId) {
    const logDiv = document.getElementById('combat-log');
    logDiv.innerHTML = "<span style='color: #e0b050;'>Применение способности...</span>";

    document.querySelectorAll('#combat-actions button, #combat-abilities button').forEach(b => b.disabled = true);

    try {
        const response = await fetch(`/combat/${playerId}/ability?ability_id=${encodeURIComponent(abilityId)}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (!response.ok) {
            logDiv.innerHTML = `<span style='color: #ff5555;'>${data.detail || 'Не удалось применить способность.'}</span>`;
            return;
        }

        if (data.text) {
            logDiv.innerHTML = data.text.replace(/\n/g, '<br>');
        }
        if (data.effects && data.effects.length > 0) {
            logDiv.innerHTML += '<br>' + data.effects.map(e => `<span class="effect-badge">${e}</span>`).join(' ');
        }

        await loadPlayer();

        if (data.enemy && data.enemy.hp > 0) {
            updateCombatUI(data.enemy);
        } else {
            setTimeout(() => {
                logDiv.innerHTML += "<br><br><span style='color: #4CAF50; font-weight: bold;'>Враг повержен! Бой окончен.</span>";
                setTimeout(closeCombat, 2000);
            }, 800);
        }

        if (data.player_hp <= 0) {
            logDiv.innerHTML += "<br><br><span style='color: #ff3333; font-weight: bold;'>Вы погибли...</span>";
            setTimeout(() => { location.reload(); }, 3000);
        }
    } catch (e) {
        logDiv.innerHTML = "<span style='color: #ff5555;'>Ошибка боя.</span>";
    } finally {
        document.querySelectorAll('#combat-actions button, #combat-abilities button').forEach(b => b.disabled = false);
        renderCombatAbilities();
    }
}

function renderCombatAbilities() {
    const box = document.getElementById('combat-abilities');
    if (!box) return;

    const usable = abilitiesCache.filter(a => a.learned && a.combat);
    if (!usable.length) {
        box.innerHTML = '';
        box.style.display = 'none';
        return;
    }

    box.style.display = 'flex';
    box.innerHTML = '';
    usable.forEach(ab => {
        const btn = document.createElement('button');
        btn.className = 'btn-action';
        btn.innerText = ab.cooldown_left > 0 ? `${ab.name} (${ab.cooldown_left})` : ab.name;
        btn.disabled = ab.cooldown_left > 0;
        btn.onclick = () => doCombatAbility(ab.id);
        box.appendChild(btn);
    });
}

async function doCombatAction(actionText) {
    const logDiv = document.getElementById('combat-log');
    logDiv.innerHTML = "<span style='color: #e0b050;'>Ожидание удара...</span>";
    
    document.querySelectorAll('#combat-actions button').forEach(b => b.disabled = true);

    try {
        const response = await fetch(`/combat/${playerId}/action?action=${encodeURIComponent(actionText)}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.text) {
            logDiv.innerHTML = data.text.replace(/\n/g, '<br>');
        }
        
        await loadPlayer(); 
        
        if (data.enemy && data.enemy.hp > 0) {
            updateCombatUI(data.enemy);
        } else {
            setTimeout(() => {
                logDiv.innerHTML += "<br><br><span style='color: #4CAF50; font-weight: bold;'>Враг повержен! Бой окончен.</span>";
                setTimeout(closeCombat, 2000);
            }, 1000);
        }
        
        if (data.player_hp <= 0) {
            logDiv.innerHTML += "<br><br><span style='color: #ff3333; font-weight: bold;'>Вы погибли...</span>";
            setTimeout(() => { location.reload(); }, 3000);
        }

    } catch (e) {
        logDiv.innerHTML = "<span style='color: #ff5555;'>Ошибка боя.</span>";
    } finally {
        document.querySelectorAll('#combat-actions button').forEach(b => b.disabled = false);
    }
}

function closeCombat() {
    document.getElementById('combat-screen').classList.remove('is-open');
    document.getElementById('combat-screen').style.display = 'none';
    loadPlayer();
}

function tryFlee() {
    const logDiv = document.getElementById('combat-log');
    logDiv.innerHTML = "Вы пытаетесь сбежать...";
    setTimeout(() => {
        closeCombat();
    }, 1000);
}

// ============================================================
// UI ENHANCEMENTS: частицы, рябь, всплывающие числа, уровень
// ============================================================
const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const fx = {
    snapshot: null,

    capture(p) {
        if (!p) return null;
        return {
            hp: p.hp,
            maxHp: p.max_hp,
            xp: p.xp,
            level: p.level,
            stats: {
                strength: p.strength,
                agility: p.agility,
                vitality: p.vitality,
                intelligence: p.intelligence,
                perception: p.perception,
                luck: p.luck
            },
            enemyHp: p.enemy ? p.enemy.hp : null,
            enemyName: p.enemy ? p.enemy.name : null
        };
    },

    diff(prev, p) {
        if (!prev || !p) return;

        const hpBar = document.getElementById('hp-bar');
        const hpBox = hpBar && hpBar.parentElement;

        // Здоровье
        if (hpBox && typeof prev.hp === 'number' && prev.hp !== p.hp) {
            if (p.hp < prev.hp) {
                hpBox.classList.remove('bar-flash');
                void hpBox.offsetWidth;
                hpBox.classList.add('bar-flash');
                this.floatAt(hpBar, `−${prev.hp - p.hp}`, 'dmg');
            } else {
                this.floatAt(hpBar, `+${p.hp - prev.hp}`, 'heal');
            }
        }

        // Опыт
        if (typeof prev.xp === 'number' && p.xp > prev.xp) {
            const xpBar = document.getElementById('xp-bar');
            if (xpBar) {
                const box = xpBar.parentElement;
                box.classList.remove('xp-flash');
                void box.offsetWidth;
                box.classList.add('xp-flash');
            }
        }

        // Новый уровень
        if (typeof prev.level === 'number' && p.level > prev.level) {
            this.levelUp(p.level);
        }

        // Урон по врагу
        if (prev.enemyName && p.enemy && prev.enemyName === p.enemy.name &&
            typeof prev.enemyHp === 'number' && p.enemy.hp < prev.enemyHp) {
            const enemyBar = document.getElementById('combat-enemy-hp-bar');
            const enemyName = document.getElementById('combat-enemy-name');
            if (enemyName) {
                enemyName.classList.remove('shake');
                void enemyName.offsetWidth;
                enemyName.classList.add('shake');
            }
            if (enemyBar) this.floatAt(enemyBar, `−${prev.enemyHp - p.enemy.hp}`, 'dmg');
        }

        // Повышение характеристик
        const statMap = {
            strength: 's-str',
            agility: 's-agi',
            vitality: 's-vit',
            intelligence: 's-int',
            perception: 's-per',
            luck: 's-lck'
        };
        Object.entries(statMap).forEach(([key, id]) => {
            const before = prev.stats ? prev.stats[key] : null;
            if (before != null && p[key] > before) {
                const el = document.getElementById(id);
                if (el) {
                    el.classList.remove('bump');
                    void el.offsetWidth;
                    el.classList.add('bump');
                }
            }
        });
    },

    floatAt(el, text, cls) {
        if (!el || REDUCED_MOTION) return;
        const rect = el.getBoundingClientRect();
        const div = document.createElement('div');
        div.className = `floater ${cls || ''}`;
        div.textContent = text;
        div.style.left = `${rect.left + rect.width / 2}px`;
        div.style.top = `${rect.top - 8}px`;
        document.body.appendChild(div);
        div.addEventListener('animationend', () => div.remove());
        setTimeout(() => div.remove(), 1400);
    },

    levelUp(level) {
        if (REDUCED_MOTION) return;
        const div = document.createElement('div');
        div.className = 'levelup';
        div.textContent = `УРОВЕНЬ ${level}`;
        document.body.appendChild(div);
        div.addEventListener('animationend', () => div.remove());
        setTimeout(() => div.remove(), 2000);
    }
};

// --- Фоновая «пыль» на canvas ---
(function initEmbers() {
    const canvas = document.getElementById('embers');
    if (!canvas || REDUCED_MOTION) return;

    const ctx = canvas.getContext('2d');
    const COUNT = 46;
    let w = 0, h = 0, dpr = 1, particles = [], raf = null;

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        w = canvas.clientWidth;
        h = canvas.clientHeight;
        canvas.width = Math.max(1, Math.floor(w * dpr));
        canvas.height = Math.max(1, Math.floor(h * dpr));
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function spawn(initial) {
        return {
            x: Math.random() * w,
            y: initial ? Math.random() * h : h + 10 + Math.random() * 40,
            r: 0.6 + Math.random() * 1.8,
            vy: 0.12 + Math.random() * 0.5,
            vx: (Math.random() - 0.5) * 0.22,
            a: 0.1 + Math.random() * 0.35,
            tw: Math.random() * Math.PI * 2
        };
    }

    function frame() {
        ctx.clearRect(0, 0, w, h);
        for (const p of particles) {
            p.y -= p.vy;
            p.x += p.vx;
            p.tw += 0.02;
            if (p.y < -12 || p.x < -24 || p.x > w + 24) {
                Object.assign(p, spawn(false));
            }
            const alpha = p.a * (0.6 + 0.4 * Math.sin(p.tw));
            const radius = p.r * 4;
            const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius);
            g.addColorStop(0, `rgba(240, 205, 141, ${alpha})`);
            g.addColorStop(1, 'rgba(240, 205, 141, 0)');
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
            ctx.fill();
        }
        raf = requestAnimationFrame(frame);
    }

    resize();
    particles = Array.from({ length: COUNT }, () => spawn(true));
    frame();

    window.addEventListener('resize', () => {
        resize();
        particles = Array.from({ length: COUNT }, () => spawn(true));
    });

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            cancelAnimationFrame(raf);
        } else {
            cancelAnimationFrame(raf);
            frame();
        }
    });
})();

// --- Рябь при нажатии на кнопки ---
document.addEventListener('pointerdown', (e) => {
    if (REDUCED_MOTION) return;
    const btn = e.target.closest('.btn-action, .btn-plus, .btn-reset, .menu-btn, .icon-btn');
    if (!btn) return;

    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 1.8;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = `${size}px`;
    ripple.style.height = `${size}px`;
    ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
});

// Запуск при открытии страницы
loadGenres();
loadPlayer();