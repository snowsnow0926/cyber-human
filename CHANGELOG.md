# CHANGELOG / 更新日志

## v0.7 — Night Build (2026-05-16)

### 🆕 New Features

- **Weather Awareness**: Real Wuxi weather via wttr.in API, affects mood (+30% on sunny days)
- **Holiday Recognition**: Auto-detect holidays, weekends, seasons, and birthdays
- **Dialogue Memory**: Remembers past conversations with users
- **AI Self-Training**: Auto-review short-term memories, promote important ones
- **Profile Page**: Personal homepage with stats, mood, personality tags
- **Search System**: Full-text search across thoughts, diary, browse, and knowledge
- **Phone UI Refresh**: Notification feed style, cleaner layout, date display

### 🔧 Improvements

- **Knowledge Extraction**: Enhanced AI-based detection with curiosity patterns
- **Data Source Caching**: 5-minute cache to reduce redundant requests
- **Cron Schedule**: Added runs at 6:00, 12:00, 18:00 (was only 8:00, 20:00)
- **Health Monitor**: Auto-restart web UI if it crashes (checked every 5 min)
- **Playwright Enhanced**: Weibo, Douban, Netease now use browser automation as primary
- **Diary Grouping**: Entries grouped by date for easier navigation
- **Timeline Date Nav**: Browse past days with date picker
- **Dark Mode Toggle**: Switch between light/dark themes
- **Emotion Display**: Mood emoji shown on timeline and phone views
- **Code Refactoring**: Unified error handling, duplicate code cleanup

### 🐛 Fixed

- Douyin API: Added missing Referer header
- Zhihu API: Replaced blocked endpoint with Playwright explore page scraper
- Token Stats: Proper recording of AI token usage
- Control Panel: Fixed /api/ URL paths for nginx reverse proxy
- Database Migration: Added missing daily_schedule, dialogue_memory tables
- Web.py Rollback: Restored accidentally deleted control panel and knowledge tabs

### 📚 Documentation

- Complete bilingual README (English + Chinese)
- Full test checklist
- Architecture overview with data flow diagram
- API documentation
