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

    // ── 手机子标签页切换（通知 / 朋友圈）──────────────
    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".phone-nav-btn");
        if (!btn) return;
        const subTab = btn.dataset.phoneTab;
        $$(".phone-nav-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        loadPhoneSubTab(subTab);
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
        const el = $("#thoughts-list");
        if (!el) return;
        el.innerHTML = '<div class="card"><div class="card-body">加载中...</div></div>';
        try {
            const data = await api("/api/today/thoughts");
            if (!data.data || !data.data.length) {
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
        } catch (e) {
            el.innerHTML = `<div class="card"><div class="card-body" style="color:#e74c3c">加载失败: ${escHtml(e.message)}</div></div>`;
        }
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

    async function loadTimeline(dateStr) {
        if (!dateStr) {
            var dateInput = document.getElementById("timeline-date");
            dateStr = dateInput ? dateInput.value : "";
        }
        if (!dateStr) {
            var now = new Date();
            dateStr = now.getFullYear() + "-" + String(now.getMonth()+1).padStart(2,"0") + "-" + String(now.getDate()).padStart(2,"0");
        }
        var url = "/api/timeline?date=" + encodeURIComponent(dateStr);
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

        // Show notice if date was auto-corrected
        if (data.shown_date && data.shown_date !== dateStr) {
            var noticeEl = document.getElementById("timeline-notice");
            if (noticeEl) noticeEl.remove();
            var notice = document.createElement("div");
            notice.id = "timeline-notice";
            notice.style.cssText = "background:#fff3cd;color:#856404;padding:8px 12px;border-radius:6px;font-size:0.8rem;margin-bottom:12px";
            notice.textContent = "⚠️ " + dateStr + " 无活动记录，已自动切换到最近有数据的日期: " + data.shown_date;
            cnt.parentNode.insertBefore(notice, cnt);
        } else {
            var noticeEl = document.getElementById("timeline-notice");
            if (noticeEl) noticeEl.remove();
        }

        // Activity type icons/colors
        var typeConfig = {
            "routine": { icon: "📋", color: "#667eea" },
            "browse":  { icon: "🌐", color: "#43e97b" },
            "reflect": { icon: "💭", color: "#f093fb" },
            "sleep":   { icon: "😴", color: "#4facfe" },
            "pending": { icon: "⏳", color: "#aaa" },
        };

        var groups = data.groups || [];
        if (!groups.length) {
            cnt.innerHTML = '<div class="card"><div class="card-body">暂无活动记录</div></div>';
            return;
        }

        var html = groups.map(function(g) {
            var ts = g.time_slot || "";
            var label = g.label || "";
            var atype = g.activity_type || "";
            var content = g.content || "";
            var isEvent = g.is_event;
            var eventType = g.event_type || "";
            var tc = typeConfig[atype] || { icon: "📌", color: "#999" };
            var hasBrowses = g.browses && g.browses.length;
            var hasThoughts = g.thoughts && g.thoughts.length;

            // Slot header
            var slotHtml = '<div class="timeline-slot" style="margin-bottom:12px;border:1px solid #eee;border-radius:10px;padding:12px;border-left:4px solid ' + tc.color + '">' +
                '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">' +
                '<span style="font-size:1.2rem">' + tc.icon + '</span>' +
                '<span style="font-weight:700;min-width:50px;color:' + tc.color + '">' + escHtml(ts) + '</span>' +
                '<span style="font-weight:600">' + escHtml(label) + '</span>' +
                '<span class="tag" style="background:' + tc.color + '20;color:' + tc.color + ';font-size:0.7rem;padding:2px 8px;border-radius:4px">' + escHtml(atype) + '</span>';

            if (isEvent) {
                slotHtml += '<span class="tag" style="background:#ff6b6b20;color:#ff6b6b;font-size:0.7rem;padding:2px 8px;border-radius:4px">🎲 事件</span>';
            }
            slotHtml += '</div>';

            // Content
            if (content && content != "pending") {
                slotHtml += '<div style="color:#555;font-size:0.85rem;margin-bottom:8px;padding:8px;background:#f9f9f9;border-radius:6px">' + escHtml(content) + '</div>';
            } else if (content == "pending") {
                slotHtml += '<div style="color:#bbb;font-size:0.8rem;font-style:italic;margin-bottom:8px">⏳ 待执行</div>';
            }

            // Browses within this slot
            if (hasBrowses) {
                slotHtml += '<div style="margin-top:6px">';
                slotHtml += '<div style="font-size:0.75rem;color:#888;margin-bottom:4px">📖 浏览记录 (' + g.browses.length + ')</div>';
                g.browses.forEach(function(b) {
                    var title = b.title || "";
                    var src = b.source || "";
                    var url = b.url || "";
                    var linkHtml = url ? '<a href="' + escHtml(url) + '" target="_blank" style="color:#43e97b;text-decoration:none">🔗</a>' : "";
                    slotHtml += '<div style="font-size:0.8rem;padding:3px 6px;margin:2px 0;background:#f0faf0;border-radius:4px;display:flex;gap:6px">' +
                        '<span style="color:#666;min-width:40px">[' + escHtml(src) + ']</span>' +
                        '<span style="flex:1">' + escHtml(title.slice(0, 60)) + '</span>' +
                        '<span>' + linkHtml + '</span></div>';
                });
                slotHtml += '</div>';
            }

            // Thoughts within this slot
            if (hasThoughts) {
                slotHtml += '<div style="margin-top:6px">';
                slotHtml += '<div style="font-size:0.75rem;color:#888;margin-bottom:4px">💡 想法 (' + g.thoughts.length + ')</div>';
                g.thoughts.forEach(function(t) {
                    var thoughtText = (t.thought || "").slice(0, 80);
                    var imp = t.importance || "";
                    slotHtml += '<div style="font-size:0.8rem;padding:3px 6px;margin:2px 0;background:#faf0ff;border-radius:4px">' +
                        escHtml(thoughtText) +
                        (imp ? ' <span style="color:#f093fb;font-size:0.7rem">[' + imp + '/10]</span>' : '') +
                        '</div>';
                });
                slotHtml += '</div>';
            }

            slotHtml += '</div>';
            return slotHtml;
        }).join("");

        // Also add ungrouped items if any
        var ungroupedHtml = "";
        if (data.browses && data.browses.length) {
            var groupedBrowseCount = 0;
            (data.groups || []).forEach(function(g) {
                if (g.browses) groupedBrowseCount += g.browses.length;
            });
            if (groupedBrowseCount < data.browses.length) {
                ungroupedHtml += '<div class="card" style="margin-top:12px"><div class="card-title" style="font-size:0.9rem">📖 其他浏览记录</div>';
                data.browses.forEach(function(b) {
                    var title = b.title || "";
                    var src = b.source || "";
                    ungroupedHtml += '<div style="font-size:0.8rem;padding:4px;border-bottom:1px solid #f0f0f0">[' + escHtml(src) + '] ' + escHtml(title.slice(0, 80)) + '</div>';
                });
                ungroupedHtml += '</div>';
            }
        }

        cnt.innerHTML = html + ungroupedHtml;
    }

    let phoneSubTab = "notifications";
    async function loadPhoneSubTab(subTab) {
        phoneSubTab = subTab;
        const el = document.getElementById("phone-content");
        if (!el) return;

        if (subTab === "moments") {
            el.innerHTML = '<p class="phone-placeholder">加载中...</p>';
            try {
                const data = await api("/api/moments");
                if (!data.data || !data.data.length) {
                    el.innerHTML = '<p class="phone-placeholder">朋友圈还没有动态</p>';
                    return;
                }
                el.innerHTML = data.data.map((m) => {
                    const liked = m.liked_by_xiaoqiu ? "&#x2764;&#xFE0F;" : "&#x1F90D;";
                    const t = m.timestamp ? m.timestamp.replace("T", " ").slice(0, 16) : "";
                    return `<div style="background:#1c1c1e;border-radius:12px;padding:14px;margin-bottom:12px">
                        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
                            <span style="font-size:18px">${m.friend_name === '小雨' ? '&#x1F338;' : m.friend_name === '阿泽' ? '&#x1F43E;' : m.friend_name === '小美' ? '&#x1F9D1;&#x200D;&#x1F3A8;' : m.friend_name === '班长林哥' ? '&#x1F9D4;&#x200D;&#x2642;&#xFE0F;' : '&#x1F970;'}</span>
                            <div>
                                <div style="color:#fff;font-size:13px;font-weight:600">${escHtml(m.friend_name)}</div>
                                <div style="color:#aaa;font-size:11px">${escHtml(t)}</div>
                            </div>
                        </div>
                        <div style="color:#ddd;font-size:13px;line-height:1.6;margin-bottom:8px">${escHtml(m.content)}</div>
                        <div style="display:flex;gap:16px;color:#888;font-size:12px">
                            <span class="moments-like" data-id="${m.id}" data-liked="${m.liked_by_xiaoqiu}" style="cursor:pointer">${liked} ${m.likes}</span>
                            <span class="moments-comment" data-id="${m.id}" style="cursor:pointer">&#x1F4AC; 评论</span>
                        </div>
                        <div class="moments-comment-area" id="mc-${m.id}" style="display:none;margin-top:8px;padding-top:8px;border-top:1px solid #333">
                            <div class="moments-comment-list" id="mcl-${m.id}" style="margin-bottom:6px"></div>
                        </div>
                    </div>`;
                }).join("");
                // 点赞按钮
                $$(".moments-like").forEach((btn) => {
                    btn.addEventListener("click", async () => {
                        const id = btn.dataset.id;
                        try {
                            await api(`/api/moments/${id}/like`, { method: "POST" });
                            loadPhoneSubTab("moments");
                        } catch(e) { console.error(e); }
                    });
                });
                // 评论按钮
                $$(".moments-comment").forEach((btn) => {
                    btn.addEventListener("click", async () => {
                        const id = btn.dataset.id;
                        const area = document.getElementById(`mc-${id}`);
                        const list = document.getElementById(`mcl-${id}`);
                        if (!area || area.style.display === "block") {
                            area.style.display = "none";
                            return;
                        }
                        area.style.display = "block";
                        if (list) list.innerHTML = '<div style="color:#666;font-size:11px">加载中...</div>';
                        try {
                            const cdata = await api(`/api/moments/${id}/comments`);
                            if (list) {
                                list.innerHTML = (cdata.data || []).map((c) =>
                                    `<div style="color:#aaa;font-size:12px;margin-bottom:4px"><b>${escHtml(c.commenter)}:</b> ${escHtml(c.content)}</div>`
                                ).join("") || '<div style="color:#666;font-size:11px">暂无评论</div>';
                            }
                        } catch(e) { if (list) list.innerHTML = '<div style="color:#666;font-size:11px">加载失败</div>'; }
                    });
                });
            } catch(e) {
                el.innerHTML = '<p class="phone-placeholder">加载失败</p>';
            }
            return;
        }

        // 通知页（原 loadPhone 逻辑）
        // el 已在上方（第372行）通过 const 声明，此处直接复用
        try {
            data = await api("/api/notifications");
        } catch(e) {
            if (el) el.innerHTML = '<p class="phone-placeholder">加载失败</p>';
            return;
        }
        if (!el) return;
        if (!data.data || !data.data.length) {
            el.innerHTML = '<p class="phone-placeholder">小雪球的手机还没收到推送</p>';
            return;
        }
        el.innerHTML = data.data.map(function(n) {
            var safeUrl = isSafeUrl(n.url);
            var clickable = safeUrl ? ' onclick="window.open(\'' + escHtml(n.url) + '\', \'_blank\')" style="cursor:pointer"' : '';
            return '<div' + clickable + ' style="background:#1c1c1e;border-radius:12px;padding:12px;margin-bottom:8px;border-left:3px solid ' + (n.color || '#5a9eff') + '">' +
                '<div style="color:#888;font-size:11px">' + escHtml(n.app) + '</div>' +
                '<div style="color:#fff;margin:4px 0;font-size:13px">' + escHtml(n.title) + '</div>' +
                '<div style="color:#aaa;font-size:11px">' + escHtml(n.time || '') + '</div>' +
                '</div>';
        }).join("");
    }

    async function loadPhone() {
        await loadPhoneSubTab(phoneSubTab);
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
            // Keep only last 6 messages to prevent unbounded growth
            if (state.chatHistory.length > 6) {
                state.chatHistory = state.chatHistory.slice(-6);
            }
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
            var r = await api("/api/control/simulate_day", opts);
            logControl(label + "模拟已启动（" + (r.date || "today") + "），进度可在各页面查看", "success");
        } catch (e) {
            logControl("启动失败: " + e.message, "error");
        }
    });

    $("#btn-clear-browses")?.addEventListener("click", async () => {
        if (!confirm("确定清除今日浏览记录？")) return;
        logControl("正在清除...");
        try {
            var r = await api("/api/control/clear_browses", { method: "POST" });
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
            var r = await api("/api/control/clear_data", { method: "POST" });
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
                console.log("[WS] 已连接 ✅");
            });

            socket.on("disconnect", () => {
                state.socketConnected = false;
                console.log("[WS] 连接已断开");
            });

            socket.on("diary_update", (data) => {
                console.log("[WS] diary_update →", data);
                logControl(`收到日记更新: ${data.date}`, "success");
                if (state.currentTab === "diary") loadDiary();
            });

            socket.on("thought_update", (data) => {
                console.log("[WS] thought_update →", data);
                if (state.currentTab === "thoughts") loadThoughts();
            });

            socket.on("emotion_update", (data) => {
                console.log("[WS] emotion_update →", data);
                const badge = $("#emotion-badge");
                if (badge) badge.textContent = data.current.emoji;
                if (state.currentTab === "stats") loadStats();
            });

            socket.on("sim_complete", (data) => {
                console.log("[WS] sim_complete →", data);
                logControl(`模拟完成！共 ${data.slots} 个时段`, "success");
            });

            socket.on("sim_error", (data) => {
                console.log("[WS] sim_error →", data);
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

    function isSafeUrl(url) {
        if (!url) return false;
        return /^https?:\/\//i.test(url.trim());
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
        await api("/api/emotion").then((data) => {
            const badge = $("#emotion-badge");
            if (badge && data.current) badge.textContent = data.current.emoji;
        }).catch(() => {});
        connectSocket();
        loadTabData("browse");
    }

    init();

})();
