/**
 * 赛博人类 Web UI v2.0
 * 极简架构：今日浏览 / 想法 / 日记 / 投喂 / 统计 / 聊天 / 控制
 */

(function () {
    "use strict";

    const state = {
        currentTab: "browse",
        socketConnected: false,
        chatHistory: [],
    };

    let chartMemory = null;

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ── 深色模式 ──────────────────────────────────────────────────────────
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    $("#theme-toggle")?.addEventListener("click", () => {
        const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("theme", next);
    });

    // ── 时间显示 ──────────────────────────────────────────────────────────
    function updateTime() {
        const now = new Date();
        const el = $("#current-time");
        if (el) {
            el.textContent = now.toLocaleString("zh-CN", {
                month: "short", day: "numeric", weekday: "short",
                hour: "2-digit", minute: "2-digit", second: "2-digit",
            });
        }
    }
    updateTime();
    setInterval(updateTime, 1000);

    // ── API 调用 ────────────────────────────────────────────────────────────
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

    // ── 标签页切换 ────────────────────────────────────────────────────────
    $$(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            const tab = btn.dataset.tab;
            state.currentTab = tab;
            $$(".tab-btn").forEach((b) => b.classList.remove("active"));
            $$(".tab-panel").forEach((p) => p.classList.remove("active"));
            btn.classList.add("active");
            $(`#tab-${tab}`)?.classList.add("active");
            loadTabData(tab);
        });
    });

    // ── 数据加载 ──────────────────────────────────────────────────────────
    async function loadTabData(tab) {
        try {
            switch (tab) {
                case "browse":    await loadBrowses();   break;
                case "thoughts": await loadThoughts();  break;
                case "diary":     await loadDiary();     break;
                case "stats":     await loadStats();     break;
                case "timeline":  await loadTimeline();   break;
                case "feed":      await loadFeedHistory(); break;
            }
        } catch (e) {
            console.error(`Failed to load tab ${tab}:`, e);
        }
    }

    async function loadBrowses() {
        const el = $("#browse-list");
        if (!el) return;
        el.innerHTML = '<div class="loading">加载中...</div>';
        try {
            const data = await api("/api/today/browses");
            if (!data.data?.length) {
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
        } catch (e) {
            el.innerHTML = `<div class="card"><div class="card-body" style="color:#e74c3c">加载失败: ${escHtml(e.message)}</div></div>`;
        }
    }

    async function loadThoughts() {
        const el = $("#thoughts-list");
        if (!el) return;
        el.innerHTML = '<div class="card"><div class="card-body">加载中...</div></div>';
        try {
            const data = await api("/api/thoughts");
            if (!data.data?.length) {
                el.innerHTML = '<div class="card"><div class="card-body">还没有想法哦~</div></div>';
                return;
            }
            el.innerHTML = data.data.map((item) => {
                const impClass = item.importance >= 7 ? "tag-importance-high"
                    : item.importance >= 4 ? "tag-importance-mid" : "tag-importance-low";
                const tierLabel = item.tier === "短期" ? "短期" : item.tier === "中期" ? "中期" : "长期";
                const tagHtml = item.tags
                    ? item.tags.split(",").map(t => `<span class="tag">${escHtml(t.trim())}</span>`).join("")
                    : "";
                return `
                    <div class="card">
                        <div class="card-meta">${item.source || ""} · ${formatTime(item.timestamp)} · ${escHtml(item.emotion || "平静")}</div>
                        <div class="card-body">${escHtml(item.thought)}</div>
                        <div class="card-footer">
                            <span class="tag ${impClass}">重要度 ${item.importance}/10</span>
                            <span class="tag">${tierLabel}</span>
                            ${tagHtml}
                        </div>
                    </div>
                `;
            }).join("");
        } catch (e) {
            el.innerHTML = `<div class="card"><div class="card-body" style="color:#e74c3c">加载失败: ${escHtml(e.message)}</div></div>`;
        }
    }

    async function loadDiary() {
        const el = $("#diary-list");
        if (!el) return;
        try {
            const data = await api("/api/diary");
            if (!data.data?.length) {
                el.innerHTML = '<div class="card"><div class="card-body">还没有日记哦~</div></div>';
                return;
            }
            el.innerHTML = data.data.map((item) => `
                <div class="card">
                    <div class="card-meta">${item.date} · ${escHtml(item.mood || "平静")}</div>
                    <div class="card-body">${escHtml(item.summary)}</div>
                </div>
            `).join("");
        } catch (e) {
            el.innerHTML = `<div class="card"><div class="card-body" style="color:#e74c3c">加载失败: ${escHtml(e.message)}</div></div>`;
        }
    }

    async function loadStats() {
        try {
            const data = await api("/api/stats");
            const tokens = data.total_tokens || 0;
            const cost = (tokens * 0.000001).toFixed(4);
            $("#stat-browses").textContent = data.browse_count || 0;
            $("#stat-thoughts").textContent = data.thought_count || 0;
            $("#stat-diary").textContent = data.diary_count || 0;
            $("#stat-feed").textContent = data.feed_count || 0;
            $("#stat-tokens").textContent = tokens.toLocaleString();
            $("#stat-cost").textContent = `$${cost}`;

            // Memory tier pie chart
            const memEl = $("#chart-memory");
            if (memEl && window.echarts) {
                const tiers = data.tier_counts || {};
                const chart = echarts.init(memEl);
                chart.setOption({
                    title: { text: "记忆层级分布", left: "center", textStyle: { fontSize: 13, color: "#666" } },
                    tooltip: { trigger: "item" },
                    series: [{
                        type: "pie",
                        radius: ["40%", "65%"],
                        data: [
                            { value: tiers["短期"] || 0, name: "短期记忆" },
                            { value: tiers["中期"] || 0, name: "中期记忆" },
                            { value: tiers["长期"] || 0, name: "长期记忆" },
                        ],
                        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.3)" } },
                    }],
                    color: ["#667eea", "#48bb78", "#ed8936"],
                });
            }
        } catch (e) {
            console.error("loadStats failed:", e);
        }
    }

    async function loadTimeline(dateStr) {
        if (!dateStr) {
            const dateInput = $("#timeline-date");
            dateStr = dateInput?.value || new Date().toISOString().split("T")[0];
        }
        const cnt = $("#timeline-container");
        if (!cnt) return;

        try {
            const data = await api(`/api/timeline?date=${encodeURIComponent(dateStr)}`);
            const groups = data.groups || [];

            if (!groups.length) {
                cnt.innerHTML = '<div class="card"><div class="card-body">暂无活动记录</div></div>';
                return;
            }

            const typeConfig = {
                "routine": { icon: "📋", color: "#667eea" },
                "browse":  { icon: "🌐", color: "#43e97b" },
                "reflect": { icon: "💭", color: "#f093fb" },
                "sleep":   { icon: "😴", color: "#4facfe" },
                "pending":  { icon: "⏳", color: "#aaa" },
            };

            cnt.innerHTML = groups.map((g) => {
                const ts = g.time_slot || "";
                const label = g.label || "";
                const atype = g.activity_type || "";
                const content = g.content || "";
                const tc = typeConfig[atype] || { icon: "📌", color: "#999" };

                let html = `<div class="timeline-slot" style="margin-bottom:12px;border:1px solid #eee;border-radius:10px;padding:12px;border-left:4px solid ${tc.color}">`;
                html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">`;
                html += `<span style="font-size:1.2rem">${tc.icon}</span>`;
                html += `<span style="font-weight:700;min-width:50px;color:${tc.color}">${escHtml(ts)}</span>`;
                html += `<span style="font-weight:600">${escHtml(label)}</span>`;
                html += `</div>`;

                if (content && content !== "pending") {
                    html += `<div style="color:#555;font-size:0.85rem;margin-bottom:8px;padding:8px;background:#f9f9f9;border-radius:6px">${escHtml(content)}</div>`;
                }

                if (g.browses?.length) {
                    html += `<div style="margin-top:6px"><div style="font-size:0.75rem;color:#888;margin-bottom:4px">📖 浏览记录 (${g.browses.length})</div>`;
                    g.browses.forEach((b) => {
                        html += `<div style="font-size:0.8rem;padding:3px 6px;margin:2px 0;background:#f0faf0;border-radius:4px">
                            <span style="color:#666;min-width:40px">[${escHtml(b.source || "")}]</span>
                            <span>${escHtml((b.title || "").slice(0, 60))}</span>
                        </div>`;
                    });
                    html += `</div>`;
                }

                if (g.thoughts?.length) {
                    html += `<div style="margin-top:6px"><div style="font-size:0.75rem;color:#888;margin-bottom:4px">💡 想法 (${g.thoughts.length})</div>`;
                    g.thoughts.forEach((t) => {
                        html += `<div style="font-size:0.8rem;padding:3px 6px;margin:2px 0;background:#faf0ff;border-radius:4px">
                            ${escHtml((t.thought || "").slice(0, 80))}
                            ${t.importance ? `<span style="color:#f093fb;font-size:0.7rem">[${t.importance}/10]</span>` : ""}
                        </div>`;
                    });
                    html += `</div>`;
                }

                html += `</div>`;
                return html;
            }).join("");
        } catch (e) {
            cnt.innerHTML = `<div class="card"><div style="color:red">加载失败: ${escHtml(e.message)}</div></div>`;
        }
    }

    // ── 投喂功能 ────────────────────────────────────────────────────────
    const feedContent = $("#feed-content");
    const feedSubmitBtn = $("#btn-feed-submit");
    const feedStatus = $("#feed-status");

    feedSubmitBtn?.addEventListener("click", async () => {
        const content = feedContent?.value?.trim();
        if (!content) {
            if (feedStatus) { feedStatus.textContent = "请输入内容"; feedStatus.style.color = "#e74c3c"; }
            return;
        }
        if (feedStatus) { feedStatus.textContent = "AI 正在分析..."; feedStatus.style.color = "#888"; }
        feedSubmitBtn.disabled = true;
        try {
            const resp = await api("/api/feed", {
                method: "POST",
                body: JSON.stringify({ content }),
            });
            if (feedStatus) {
                feedStatus.textContent = `✅ 分析完成！标签: ${resp.tags} | 重要度: ${resp.importance}/10`;
                feedStatus.style.color = "#27ae60";
            }
            if (feedContent) feedContent.value = "";
            await loadFeedHistory();
            await loadThoughts();
        } catch (e) {
            if (feedStatus) { feedStatus.textContent = `❌ 失败: ${e.message}`; feedStatus.style.color = "#e74c3c"; }
        } finally {
            feedSubmitBtn.disabled = false;
        }
    });

    async function loadFeedHistory() {
        const el = $("#feed-history");
        if (!el) return;
        try {
            const data = await api("/api/feed/history");
            if (!data.data?.length) {
                el.innerHTML = '<div class="card"><div class="card-body">还没有投喂记录</div></div>';
                return;
            }
            el.innerHTML = data.data.map((item) => {
                const impClass = item.importance >= 7 ? "tag-importance-high"
                    : item.importance >= 4 ? "tag-importance-mid" : "tag-importance-low";
                const tagHtml = item.tags
                    ? item.tags.split(",").map(t => `<span class="tag">${escHtml(t.trim())}</span>`).join("")
                    : "";
                return `
                    <div class="card">
                        <div class="card-meta">${formatTime(item.timestamp)}</div>
                        <div class="card-body" style="font-size:0.8rem;color:#666;margin-bottom:6px">
                            ${escHtml((item.user_content || "").slice(0, 120))}${(item.user_content || "").length > 120 ? "..." : ""}
                        </div>
                        <div style="font-size:0.85rem;padding:8px;background:#f9f9f9;border-radius:6px;margin-bottom:6px">
                            💭 ${escHtml(item.ai_thought)}
                        </div>
                        <div class="card-footer">
                            <span class="tag ${impClass}">重要度 ${item.importance}/10</span>
                            ${tagHtml}
                        </div>
                    </div>
                `;
            }).join("");
        } catch (e) {
            el.innerHTML = `<div class="card"><div class="card-body" style="color:#e74c3c">加载失败: ${escHtml(e.message)}</div></div>`;
        }
    }

    // ── 聊天 ────────────────────────────────────────────────────────────
    const chatInput = $("#chat-input");
    const chatSend = $("#chat-send");
    const chatMessages = $("#chat-messages");

    async function sendChat() {
        const text = chatInput?.value?.trim();
        if (!text) return;
        if (chatInput) chatInput.value = "";
        addChatMsg("user", text);
        state.chatHistory.push({ role: "user", content: text });
        try {
            const resp = await api("/api/chat", {
                method: "POST",
                body: JSON.stringify({ message: text, history: state.chatHistory }),
            });
            addChatMsg("bot", resp.reply);
            state.chatHistory.push({ role: "assistant", content: resp.reply });
            if (state.chatHistory.length > 12) {
                state.chatHistory = state.chatHistory.slice(-12);
            }
        } catch (e) {
            addChatMsg("bot", `抱歉出了点问题: ${e.message}`);
        }
    }

    function addChatMsg(role, text) {
        const div = document.createElement("div");
        div.className = `chat-msg ${role}`;
        div.textContent = text;
        chatMessages?.appendChild(div);
        chatMessages?.scrollTo(0, chatMessages.scrollHeight);
    }

    chatSend?.addEventListener("click", sendChat);
    chatInput?.addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });

    // ── 控制面板 ────────────────────────────────────────────────────────
    $("#btn-simulate")?.addEventListener("click", async () => {
        logControl("正在启动全天模拟...");
        try {
            await api("/api/control/simulate", { method: "POST" });
            logControl("模拟已启动，进度可在各页面查看", "success");
        } catch (e) {
            logControl(`启动失败: ${e.message}`, "error");
        }
    });

    $("#btn-clear")?.addEventListener("click", async () => {
        if (!confirm("确定清除今日数据？")) return;
        logControl("正在清除今日数据...");
        try {
            await api("/api/control/clear", { method: "POST" });
            logControl("已清除今日数据", "success");
            loadTabData(state.currentTab);
        } catch (e) {
            logControl(`清除失败: ${e.message}`, "error");
        }
    });

    $("#btn-refresh")?.addEventListener("click", () => {
        loadTabData(state.currentTab);
        logControl("数据已刷新", "info");
    });

    $("#write-diary-btn")?.addEventListener("click", async () => {
        try {
            await api("/api/diary/today", { method: "POST" });
            logControl("日记已生成", "success");
            await loadDiary();
        } catch (e) {
            logControl(`日记生成失败: ${e.message}`, "error");
        }
    });

    function logControl(msg, level = "info") {
        const el = $("#control-log");
        if (!el) return;
        const div = document.createElement("div");
        div.className = `log-${level}`;
        div.textContent = `[${new Date().toLocaleTimeString("zh-CN")}] ${msg}`;
        el.appendChild(div);
        el.scrollTop = el.scrollHeight;
    }

    // ── 时间线日期选择 ──────────────────────────────────────────────────
    const timelineDateInput = $("#timeline-date");
    if (timelineDateInput) {
        timelineDateInput.value = new Date().toISOString().split("T")[0];
        timelineDateInput.addEventListener("change", () => {
            if (state.currentTab === "timeline") loadTimeline(timelineDateInput.value);
        });
    }
    $("#timeline-today-btn")?.addEventListener("click", () => {
        const ts = new Date().toISOString().split("T")[0];
        if (timelineDateInput) timelineDateInput.value = ts;
        if (state.currentTab === "timeline") loadTimeline(ts);
    });

    // ── WebSocket ────────────────────────────────────────────────────────
    function connectSocket() {
        try {
            const socket = io("/", { transports: ["websocket"], reconnectionDelay: 3000 });
            socket.on("connect", () => {
                state.socketConnected = true;
                console.log("[WS] 已连接");
            });
            socket.on("disconnect", () => {
                state.socketConnected = false;
            });
            socket.on("sim_complete", (data) => {
                logControl(`模拟完成！共 ${data.slots} 个时段`, "success");
            });
            socket.on("thought_update", () => {
                if (state.currentTab === "thoughts") loadThoughts();
            });
            socket.on("diary_update", () => {
                if (state.currentTab === "diary") loadDiary();
            });
        } catch (e) {
            console.warn("Socket.IO connection failed:", e);
        }
    }

    // ── 工具函数 ─────────────────────────────────────────────────────────
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

    // ── 启动 ─────────────────────────────────────────────────────────────
    async function init() {
        connectSocket();
        loadTabData("browse");
    }
    init();
})();
