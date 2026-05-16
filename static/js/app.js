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
            }
        } catch (e) {
            console.error(`Failed to load tab ${tab}:`, e);
        }
    }

    async function loadBrowses() {
        const data = await api("/api/today/browses");
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
        const data = await api("/api/today/thoughts");
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
        const data = await api("/api/diary");
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
        const data = await api("/api/stats");
        const tokens = data.total_tokens || 0;
        const cost = (tokens * 0.000001).toFixed(4);
        $("#stat-browses").textContent = data.browse_count || 0;
        $("#stat-thoughts").textContent = data.thought_count || 0;
        $("#stat-diary").textContent = data.diary_count || 0;
        $("#stat-tokens").textContent = tokens.toLocaleString();
        $("#stat-cost").textContent = `$${cost}`;
        const emotion = data.emotion;
        $("#stat-emotion").textContent = emotion ? `${emotion.current.state} ${emotion.current.emoji}` : "-";
        initCharts(data);
    }

    async function loadKnowledge() {
        const data = await api("/api/knowledge");
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

    async function loadTimeline() {
        const data = await api("/api/timeline");
        const el = $("#timeline-container");
        if (!el) return;
        const items = [];
        data.browses.forEach((b) => {
            items.push({ time: b.timestamp, type: "browse", title: b.title, source: b.source });
        });
        data.thoughts.forEach((t) => {
            items.push({ time: t.timestamp, type: "thought", title: t.thought.slice(0, 80), source: t.source });
        });
        items.sort((a, b) => new Date(a.time) - new Date(b.time));
        if (!items.length) {
            el.innerHTML = '<div class="card"><div class="card-body">今日时间线为空</div></div>';
            return;
        }
        el.innerHTML = items.map((item) => `
            <div class="timeline-item ${item.type}">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-time">${formatTime(item.time)} · ${escHtml(item.source)}</div>
                    <div class="card-body">${escHtml(item.title)}</div>
                </div>
            </div>
        `).join("");
    }

    async function loadPhone() {
        const data = await api("/api/today/thoughts");
        const el = $("#phone-content");
        if (!el) return;
        if (!data.data.length) {
            el.innerHTML = '<p class="phone-placeholder">暂无通知</p>';
            return;
        }
        el.innerHTML = data.data.slice(0, 5).map((t) => `
            <div class="card" style="margin-bottom:8px;">
                <div class="card-title" style="font-size:0.85rem">${escHtml(t.source)}</div>
                <div class="card-body" style="font-size:0.8rem">${escHtml(t.thought.slice(0, 60))}...</div>
            </div>
        `).join("");
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
        const data = await api("/api/profile");
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
            const data = await api("/api/search?q=" + encodeURIComponent(query));
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
            const resp = await api("/api/chat", {
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
        logControl("正在启动全天模拟...");
        try {
            await api("/api/control/simulate_day", { method: "POST" });
            logControl("模拟已启动，进度可在各页面查看", "success");
        } catch (e) {
            logControl(`启动失败: ${e.message}`, "error");
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
            await api("/api/diary/today", { method: "POST" });
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

    async function init() {
        await api("/api/emotion").then((data) => {
            const badge = $("#emotion-badge");
            if (badge && data.current) badge.textContent = data.current.emoji;
        }).catch(() => {});
        connectSocket();
        loadTabData("browse");
    }

    init();

})();
