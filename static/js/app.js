/**
 * 赛博人类 Web UI 交互逻辑
 * 标签页切换、API 调用、WebSocket 实时推送、深色模式、图表
 */

(function () {
    "use strict";

    // ── 全局状态 ────────────────────────────────────────────────
    const state = {
        currentTab: "browse",
        socketConnected: false,
        chatHistory: [],
    };

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── 深色模式 ───────────────────────────────────────────────
    const themeToggle = $("#theme-toggle");
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);

    themeToggle.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
    });

    // ── 时间显示 ───────────────────────────────────────────────
    function updateTime() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString("zh-CN", {
            hour: "2-digit", minute: "2-digit", second: "2-digit",
        });
        const dateStr = now.toLocaleDateString("zh-CN", {
            month: "short", day: "numeric", weekday: "short",
        });
        const el = $("#current-time");
        if (el) el.textContent = `${dateStr} ${timeStr}`;
        const phoneEl = $("#phone-time");
        if (phoneEl) phoneEl.textContent = timeStr;
    }
    updateTime();
    setInterval(updateTime, 1000);

    // ── 标签页切换 ──────────────────────────────────────────────
    $$(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tab = btn.dataset.tab;
            state.currentTab = tab;
            $$(".tab-btn").forEach((b) => b.classList.remove("active"));
            $$(".tab-panel").forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            const panel = $(`#tab-${tab}`);
            if (panel) panel.classList.add("active");
            loadTabData(tab);
        });
    });

    // ── API 调用 ────────────────────────────────────────────────
    async function api(path, options = {}) {
        try {
            const resp = await fetch(path, {
                headers: { "Content-Type": "application/json" },
                ...options,
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.error || `HTTP ${resp.status}`);
            }
            return await resp.json();
        } catch (e) {
            console.error(`API ${path} failed:`, e);
            throw e;
        }
    }

    // ── 数据加载 ───────────────────────────────────────────────
    async function loadTabData(tab) {
        try {
            switch (tab) {
                case "browse":   await loadBrowses();    break;
                case "thoughts":  await loadThoughts();   break;
                case "diary":    await loadDiary();      break;
                case "stats":    await loadStats();      break;
                case "knowledge": await loadKnowledge();  break;
                case "phone":    await loadPhone();      break;
                case "timeline": await loadTimeline();    break;
                case "profile":  await loadProfile();   break;
            }
        } catch (e) {
            console.error(`Failed to load tab ${tab}:`, e);
        }
    }

    async function loadBrowses() {
        const data = await api("/cyber-human/api/today/browses");
        const el = $("#browse-list");
        if (!el) return;
        if (!data.data.length) {
            el.innerHTML = '<div class="card"><div class="card-body">今日还没有浏览记录</div></div>';
            return;
        }
        el.innerHTML = data.data.map((item) => `
            <div class="card">
                <div class="card-title">${escHtml(item.title)}</div>
                <div class="card-meta">${item.source} · ${formatTime(item.timestamp)}</div>
                <div class="card-body">${escHtml(item.summary || "无摘要")}</div>
            </div>
        `).join("");
    }

    async function loadThoughts() {
        const data = await api("/cyber-human/api/today/thoughts");
        const el = $("#thoughts-list");
        if (!el) return;
        if (!data.data.length) {
            el.innerHTML = '<div class="card"><div class="card-body">今日还没有想法</div></div>';
            return;
        }
        el.innerHTML = data.data.map((item) => {
            const impClass = item.importance >= 7 ? "tag-importance-high"
                : item.importance >= 4 ? "tag-importance-mid" : "tag-importance-low";
            return `
                <div class="card">
                    <div class="card-meta">${item.source} · ${formatTime(item.timestamp)} · ${escHtml(item.emotion || "平静")}</div>
                    <div class="card-body">${escHtml(item.thought)}</div>
                    <div class="card-footer">
                        <span class="tag ${impClass}">重要度 ${item.importance}/10</span>
                        <span class="tag">${escHtml(item.memory_tier === "short" ? "短期" : item.memory_tier === "mid" ? "中期" : "长期")}</span>
                    </div>
                </div>
            `;
        }).join("");
    }

    async function loadDiary() {
        const data = await api("/cyber-human/api/diary");
        const el = $("#diary-list");
        if (!el) return;
        if (!data.data.length) {
            el.innerHTML = '<div class="card"><div class="card-body">还没有日记哦~</div></div>';
            return;
        }
        el.innerHTML = data.data.map((item) => `
            <div class="card">
                <div class="card-meta">${item.date} · ${escHtml(item.mood || "平静")}</div>
                <div class="card-body">${escHtml(item.summary)}</div>
            </div>
        `).join("");
    }

    async function loadStats() {
        const data = await api("/cyber-human/api/stats");
        const tokens = data.total_tokens || 0;
        const cost = (tokens * 0.000001).toFixed(4);
        var todayTokens = data.today_tokens || 0;
        var todayCost = (todayTokens * 0.000001).toFixed(4);
        var apiCallsToday = data.api_calls_today || 0;
        var apiCallsTotal = data.api_calls_total || 0;
        var sourceCount = data.source_count || 0;
        var nightsCons = data.nights_consolidated || 0;
        var promotedMid = data.promoted_mid || 0;
        var promotedLong = data.promoted_long || 0;
        var forgotten = data.forgotten || 0;
        $("#stat-browses").textContent = data.browse_count || 0;
        $("#stat-thoughts").textContent = data.thought_count || 0;
        $("#stat-diary").textContent = data.diary_count || 0;
        $("#stat-tokens").textContent = tokens.toLocaleString();
        $("#stat-cost").textContent = `$${cost}`;
        const emotion = data.emotion;
        $("#stat-emotion").textContent = emotion ? `${emotion.current.state} ${emotion.current.emoji}` : "-";

        // Build enhanced stats HTML below the charts
        var chartContainer = document.getElementById("chart-container");
        if (chartContainer) {
            var detailHtml = '<div style="margin-top:16px">' +
                '<div class="card"><h2>Token 消耗</h2>' +
                '<div style="font-size:13px;color:#888;line-height:1.8">' +
                '<div>今日调用: <strong style="color:#fff">' + apiCallsToday + '</strong> 次 · 消耗 <strong style="color:#fff">' + todayTokens.toLocaleString() + '</strong> tokens</div>' +
                '<div>总调用: <strong style="color:#fff">' + apiCallsTotal + '</strong> 次 · 总消耗 <strong style="color:#fff">' + tokens.toLocaleString() + '</strong> tokens</div>' +
                '<div style="margin-top:6px;font-size:11px;color:#555">按 DeepSeek V4 价格估算：今日 ~$' + todayCost + ' · 总计 ~$' + cost + '</div>' +
                '</div></div>' +
                '<div class="card" style="margin-top:12px"><h2>记忆系统</h2>' +
                '<div class="stats-grid" style="grid-template-columns:repeat(4,1fr)">' +
                '<div class="stat-card"><div class="stat-num">' + nightsCons + '</div><div class="stat-label">夜间巩固</div></div>' +
                '<div class="stat-card"><div class="stat-num">' + promotedMid + '</div><div class="stat-label">升中期</div></div>' +
                '<div class="stat-card"><div class="stat-num">' + promotedLong + '</div><div class="stat-label">升长期</div></div>' +
                '<div class="stat-card"><div class="stat-num">' + forgotten + '</div><div class="stat-label">已遗忘</div></div>' +
                '</div></div>' +
                '</div>';
            var oldDetail = document.getElementById("stats-detail");
            if (oldDetail) oldDetail.remove();
            chartContainer.insertAdjacentHTML("afterend", "<div id=\"stats-detail\">" + detailHtml + "</div>");
        }
        initCharts(data);
    }

    async function loadKnowledge() {
        const data = await api("/cyber-human/api/knowledge");
        const el = $("#knowledge-list");
        if (!el) return;
        if (!data.data.length) {
            el.innerHTML = '<div class="card"><div class="card-body">知识库为空</div></div>';
            return;
        }
        el.innerHTML = data.data.map((item) => `
            <div class="card">
                <div class="card-title">${escHtml(item.concept)}</div>
                <div class="card-footer">
                    <span class="tag">${escHtml(item.category)}</span>
                    <span class="tag">置信 ${item.confidence}/5</span>
                </div>
                <div class="card-body">${escHtml(item.explanation)}</div>
            </div>
        `).join("");
    }

    async function loadTimeline(dateStr) {
        if (!dateStr) {
            var dateInput = document.getElementById("timeline-date");
            dateStr = dateInput ? dateInput.value : "";
        }
        if (!dateStr) {
            var now = new Date();
            dateStr = now.getFullYear() + "-" + String(now.getMonth()+1).padStart(2,"0") + "-" + String(now.getDate()).padStart(2,"0");
        }
        var url = "/cyber-human/api/timeline?date=" + encodeURIComponent(dateStr);
        var data = {};
        try {
            data = await api(url);
        } catch(e) {
            var cnt = document.getElementById("timeline-container");
            if (cnt) cnt.innerHTML = '<div class="card"><div style="color:red">加载失败: ' + e.message + '</div></div>';
            return;
        }
        var cnt = document.getElementById("timeline-container");
        if (!cnt) return;

        // Schedule summary section
        var scheduleHtml = "";
        if (data.schedule && data.schedule.length) {
            scheduleHtml = '<div class="card" style="margin-bottom:16px;border-left:3px solid #667eea">' +
                '<div class="card-title" style="font-size:1.1rem">日程安排</div>';
            data.schedule.forEach(function(s) {
                var activity = s.activity || s.title || s.description || "活动";
                var notes = s.notes || "";
                var energy = s.energy_level ? (" 能量" + s.energy_level) : "";
                var moodEmoji = s.mood || "";
                scheduleHtml += '<div style="padding:4px 0;display:flex;align-items:flex-start">' +
                    '<span style="min-width:55px;font-weight:600;color:#667eea">' + escHtml(s.time_slot || "") + '</span>' +
                    '<span style="flex:1;font-size:0.9rem">' + moodEmoji + escHtml(activity) + escHtml(energy) +
                    (notes ? '<br><span style="color:#999;font-size:0.8rem">' + escHtml(notes) + '</span>' : "") +
                    '</span></div>';
            });
            scheduleHtml += '</div>';
        }

        // Timeline items
        var items = [];
        (data.browses || []).forEach(function(b) {
            items.push({ time: b.timestamp, type: "browse", title: b.title, source: b.source });
        });
        (data.thoughts || []).forEach(function(t) {
            items.push({ time: t.timestamp, type: "thought", title: (t.thought||"").slice(0, 80), source: t.source });
        });
        items.sort(function(a,b) { return new Date(a.time) - new Date(b.time); });

        var itemsHtml = "";
        if (!items.length) {
            itemsHtml = '<div class="card"><div class="card-body">暂无活动记录</div></div>';
        } else {
            itemsHtml = '<div class="card"><div class="card-title" style="font-size:1.0rem">活动时间线</div>' +
                items.map(function(item) {
                    return '<div class="timeline-item ' + item.type + '">' +
                        '<div class="timeline-dot"></div>' +
                        '<div class="timeline-content">' +
                        '<div class="timeline-time">' + formatTime(item.time) + ' &middot; ' + escHtml(item.source) + '</div>' +
                        '<div class="card-body">' + escHtml(item.title) + '</div>' +
                        '</div></div>';
                }).join("") + '</div>';
        }

        cnt.innerHTML = scheduleHtml + itemsHtml;
    }

    async function loadPhone() {
        var data;
        try {
            data = await api("/cyber-human/api/notifications");
        } catch(e) {
            var el = document.getElementById("phone-content");
            if (el) el.innerHTML = '<p class="phone-placeholder">加载失败</p>';
            return;
        }
        var el = document.getElementById("phone-content");
        if (!el) return;
        if (!data.data || !data.data.length) {
            el.innerHTML = '<p class="phone-placeholder">小雪球的手机还没收到推送</p>';
            return;
        }
        el.innerHTML = data.data.map(function(n) {
            var clickable = n.url ? ' onclick="window.open(\'' + escHtml(n.url) + '\', \'_blank\')" style="cursor:pointer"' : '';
            return '<div' + clickable + ' style="background:#1c1c1e;border-radius:12px;padding:12px;margin-bottom:8px;border-left:3px solid ' + (n.color || '#5a9eff') + '">' +
                '<div style="color:#888;font-size:11px">' + escHtml(n.app) + '</div>' +
                '<div style="color:#fff;margin:4px 0;font-size:13px">' + escHtml(n.title) + '</div>' +
                '<div style="color:#aaa;font-size:11px">' + escHtml(n.time || '') + '</div>' +
                '</div>';
        }).join("");
    }

    // ── 图表 ─────────────────────────────────────────────────
    let chartMemory, chartKnowledge;

    function initCharts(data) {
        const memEl = $("#chart-memory");
        const knlEl = $("#chart-knowledge");

        if (!chartMemory && memEl) {
            chartMemory = echarts.init(memEl);
        }
        if (!chartKnowledge && knlEl) {
            chartKnowledge = echarts.init(knlEl);
        }

        const tiers = data.tier_counts || {};
        const memOption = {
            title: { text: "记忆层级分布", left: "center", textStyle: { fontSize: 13, color: "#666" } },
            tooltip: { trigger: "item" },
            series: [{
                type: "pie",
                radius: ["40%", "65%"],
                data: [
                    { value: tiers.short || 0, name: "短期记忆" },
                    { value: tiers.mid || 0, name: "中期记忆" },
                    { value: tiers.long || 0, name: "长期记忆" },
                ],
                emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.3)" } },
            }],
            color: ["#667eea", "#48bb78", "#ed8936"],
        };

        const knData = data.knowledge || {};
        const knCategories = knData.by_category || {};
        const knOption = {
            title: { text: "知识分类统计", left: "center", textStyle: { fontSize: 13, color: "#666" } },
            tooltip: { trigger: "axis" },
            xAxis: { type: "category", data: Object.keys(knCategories), axisLabel: { rotate: 30, fontSize: 10 } },
            yAxis: { type: "value" },
            series: [{
                type: "bar",
                data: Object.values(knCategories),
                itemStyle: { color: "#667eea", borderRadius: [4, 4, 0, 0] },
            }],
        };

        if (chartMemory) chartMemory.setOption(memOption);
        if (chartKnowledge) chartKnowledge.setOption(knOption);
    }


    // -- Profile tab --
    async function loadProfile() {
        const data = await api("/cyber-human/api/profile");
        const el = $("#profile-content");
        if (!el) return;
        const traits = (data.traits || []).map(function(t) {
            return '<span class="tag">' + escHtml(t) + '</span>';
        }).join("");
        const thoughts = (data.recent_thoughts || []).map(function(t) {
            return '<div class="card" style="margin-bottom:8px"><div class="card-body">' +
                escHtml(t.thought) + '</div><div class="card-meta">' +
                formatTime(t.time) + '</div></div>';
        }).join("");
        el.innerHTML = [
            '<div class="card"><div style="text-align:center;padding:10px">',
            '<div style="font-size:64px;margin-bottom:8px">&#x1F429;</div>',
            '<h2 style="margin:4px 0">' + escHtml(data.name || '\u5c0f\u96ea\u7403') + '</h2>',
            '<p style="color:#888;font-size:13px">' + escHtml(data.sig || '') + '</p>',
            '</div></div>',
            '<div class="stats-grid" style="grid-template-columns:repeat(2,1fr);margin-bottom:16px">',
            '<div class="stat-card"><div class="stat-num">' + (data.age || 19) + '</div><div class="stat-label">\u5e74\u9f84</div></div>',
            '<div class="stat-card"><div class="stat-num">' + escHtml(data.school || '\u6c5f\u5357\u5927\u5b66') + '</div><div class="stat-label">\u5b66\u6821</div></div>',
            '<div class="stat-card"><div class="stat-num">' + escHtml(data.major || '\u98df\u54c1\u79d1\u5b66') + '</div><div class="stat-label">\u4e13\u4e1a</div></div>',
            '<div class="stat-card"><div class="stat-num">' + escHtml(data.city || '\u65e0\u9521') + '</div><div class="stat-label">\u57ce\u5e02</div></div>',
            '</div>',
            '<div class="card"><h2>&#x1F9EC; \u6027\u683c\u6807\u7b7e</h2>',
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">',
            traits || '\u6682\u65e0',
            '</div></div>',
            '<div class="card"><h2>&#x1F4CA; \u7edf\u8ba1</h2><div class="stats-grid" style="grid-template-columns:repeat(4,1fr)">',
            '<div class="stat-card"><div class="stat-num">' + (data.stats.browse||0) + '</div><div class="stat-label">\u6d4f\u89c8</div></div>',
            '<div class="stat-card"><div class="stat-num">' + (data.stats.thoughts||0) + '</div><div class="stat-label">\u60f3\u6cd5</div></div>',
            '<div class="stat-card"><div class="stat-num">' + (data.stats.diaries||0) + '</div><div class="stat-label">\u65e5\u8bb0</div></div>',
            '<div class="stat-card"><div class="stat-num">' + (data.stats.knowledge||0) + '</div><div class="stat-label">\u77e5\u8bc6</div></div>',
            '</div></div>',
            '<div class="card"><h2>&#x1F4AD; \u6700\u8fd1\u60f3\u6cd5</h2>',
            thoughts || '<div class="card-body">\u8fd8\u6ca1\u6709\u60f3\u6cd5</div>',
            '</div>',
        ].join("");
    }

    // -- Search tab --
    async function doSearch(query) {
        if (!query.trim()) return;
        if (typeof api !== "function") return;
        const el = $("#search-results");
        if (!el) return;
        el.innerHTML = '<div class="loading">\u641c\u7d22\u4e2d...</div>';
        try {
            const data = await api("/cyber-human/api/search?q=" + encodeURIComponent(query));
            if (!data.data.length) {
                el.innerHTML = '<div class="card"><div class="card-body">\u6ca1\u6709\u627e\u5230\u7ed3\u679c</div></div>';
                return;
            }
            const labels = {browse:"\u6d4f\u89c8", thought:"\u60f3\u6cd5", diary:"\u65e5\u8bb0", knowledge:"\u77e5\u8bc6"};
            el.innerHTML = data.data.map(function(r) {
                return '<div class="card"><div class="card-meta">' +
                    '<span class="tag tag-' + r.type + '">' + (labels[r.type]||r.type) + '</span> \u00b7 ' +
                    formatTime(r.time) + '</div><div class="card-body">' +
                    escHtml(r.text) + '</div></div>';
            }).join("");
        } catch(e) {
            el.innerHTML = '<div class="card"><div style="color:red">\u641c\u7d22\u5931\u8d25: ' + e.message + '</div></div>';
        }
    }

    // ── 聊天 ──────────────────────────────────────────────────
    const chatInput = $("#chat-input");
    const chatSend = $("#chat-send");
    const chatMessages = $("#chat-messages");

    async function sendChat() {
        const text = chatInput.value.trim();
        if (!text) return;
        chatInput.value = "";
        addChatMsg("user", text);
        state.chatHistory.push({ role: "user", content: text });
        try {
            const resp = await api("/cyber-human/api/chat", {
                method: "POST",
                body: JSON.stringify({ message: text, history: state.chatHistory }),
            });
            addChatMsg("bot", resp.reply);
            state.chatHistory.push({ role: "assistant", content: resp.reply });
        } catch (e) {
            addChatMsg("bot", `抱歉出了点问题: ${e.message}`);
        }
    }

    function addChatMsg(role, text) {
        const div = document.createElement("div");
        div.className = `chat-msg ${role}`;
        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    chatSend.addEventListener("click", sendChat);
    chatInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });

    // ── 控制面板 ──────────────────────────────────────────────
    $("#btn-simulate")?.addEventListener("click", async () => {
        var dateInput = document.getElementById("sim-date");
        var simDate = dateInput ? dateInput.value : "";
        var label = simDate || "今天";
        logControl("正在启动" + label + "全天模拟...");
        try {
            var body = simDate ? JSON.stringify({date: simDate}) : undefined;
            var opts = { method: "POST", headers: {"Content-Type": "application/json"} };
            if (body) opts.body = body;
            var r = await api("/cyber-human/api/control/simulate_day", opts);
            logControl(label + "模拟已启动（" + (r.date || "today") + "），进度可在各页面查看", "success");
        } catch (e) {
            logControl("启动失败: " + e.message, "error");
        }
    });

    $("#btn-clear-browses")?.addEventListener("click", async () => {
        if (!confirm("确定清除今日浏览记录？")) return;
        logControl("正在清除...");
        try {
            var r = await api("/cyber-human/api/control/clear_browses", { method: "POST" });
            logControl("已清除 " + (r.cleared || 0) + " 条记录", "success");
            loadTabData("browse");
        } catch (e) {
            logControl(`清除失败: ${e.message}`, "error");
        }
    });

    $("#btn-clear-all")?.addEventListener("click", async () => {
        if (!confirm("确定要清空所有数据吗？此操作不可撤销！")) return;
        logControl("正在清空所有数据...");
        try {
            var r = await api("/cyber-human/api/control/clear_data", { method: "POST" });
            logControl("已清空：" + JSON.stringify(r.cleared || r), "success");
            loadTabData(state.currentTab);
        } catch (e) {
            logControl(`清空失败: ${e.message}`, "error");
        }
    });

    $("#btn-refresh")?.addEventListener("click", () => {
        loadTabData(state.currentTab);
        logControl("数据已刷新", "info");
    });

    function logControl(msg, level = "info") {
        const el = $("#control-log");
        if (!el) return;
        const time = new Date().toLocaleTimeString("zh-CN");
        const div = document.createElement("div");
        div.className = `log-${level}`;
        div.textContent = `[${time}] ${msg}`;
        el.appendChild(div);
        el.scrollTop = el.scrollHeight;
    }

    // ── 写日记 ───────────────────────────────────────────────
    $("#write-diary-btn")?.addEventListener("click", async () => {
        try {
            await api("/cyber-human/api/diary/today", { method: "POST" });
            logControl("日记已生成", "success");
            await loadDiary();
        } catch (e) {
            logControl(`日记生成失败: ${e.message}`, "error");
        }
    });

    // ── WebSocket ─────────────────────────────────────────────
    function connectSocket() {
        const protocol = location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${location.host}/socket.io/?EIO=4&transport=websocket`;
        try {
            const socket = io("/", {
                transports: ["websocket"],
                reconnectionDelay: 3000,
            });

            socket.on("connect", () => {
                state.socketConnected = true;
                console.log("Socket.IO connected");
            });

            socket.on("disconnect", () => {
                state.socketConnected = false;
                console.log("Socket.IO disconnected");
            });

            socket.on("diary_update", (data) => {
                logControl(`收到日记更新: ${data.date}`, "success");
                if (state.currentTab === "diary") loadDiary();
            });

            socket.on("thought_update", (data) => {
                if (state.currentTab === "thoughts") loadThoughts();
            });

            socket.on("emotion_update", (data) => {
                const badge = $("#emotion-badge");
                if (badge) badge.textContent = data.current.emoji;
                if (state.currentTab === "stats") loadStats();
            });

            socket.on("sim_complete", (data) => {
                logControl(`模拟完成！共 ${data.slots} 个时段`, "success");
            });

            socket.on("sim_error", (data) => {
                logControl(`模拟错误: ${data.error}`, "error");
            });

        } catch (e) {
            console.warn("Socket.IO connection failed:", e);
        }
    }

    // ── 工具函数 ──────────────────────────────────────────────
    function escHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function formatTime(ts) {
        if (!ts) return "";
        try {
            return new Date(ts).toLocaleString("zh-CN", {
                month: "short", day: "numeric",
                hour: "2-digit", minute: "2-digit",
            });
        } catch {
            return ts;
        }
    }

    // ── 启动 ──────────────────────────────────────────────────

    // -- Search events --
    const searchInput = $("#search-input");
    const searchBtn = $("#search-btn");
    if (searchInput && searchBtn) {
        searchBtn.addEventListener("click", function() { doSearch(searchInput.value); });
        searchInput.addEventListener("keydown", function(e) {
            if (e.key === "Enter") doSearch(searchInput.value);
        });
    }

    // -- Timeline date picker --
    var timelineDateInput = document.getElementById("timeline-date");
    var timelineTodayBtn = document.getElementById("timeline-today-btn");
    if (timelineDateInput) {
        var todayStr = new Date().toISOString().split("T")[0];
        timelineDateInput.value = todayStr;
        timelineDateInput.addEventListener("change", function() {
            if (state.currentTab === "timeline") loadTimeline(timelineDateInput.value);
        });
    }
    if (timelineTodayBtn) {
        timelineTodayBtn.addEventListener("click", function() {
            if (timelineDateInput) {
                var ts = new Date().toISOString().split("T")[0];
                timelineDateInput.value = ts;
                if (state.currentTab === "timeline") loadTimeline(ts);
            }
        });
    }

    async function init() {
        await api("/cyber-human/api/emotion").then((data) => {
            const badge = $("#emotion-badge");
            if (badge && data.current) badge.textContent = data.current.emoji;
        }).catch(() => {});
        connectSocket();
        loadTabData("browse");
    }

    init();

})();
