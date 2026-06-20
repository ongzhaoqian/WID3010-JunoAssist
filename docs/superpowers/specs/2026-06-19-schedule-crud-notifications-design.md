# Schedule Module — Full CRUD, Persistence, Notifications

**Date:** 2026-06-19
**Owner:** Vanness (per `docs/action_plan.md` — "Vanness — Schedule")
**Status:** Approved

## Context

The action plan requires the schedule module to:
- support full CRUD (create, read, update, delete), including an update path the current implementation lacks
- persist across backend restarts
- proactively notify the user 30 minutes before, and at, the scheduled time
- avoid any SQLite locking issues

Read-aloud on explicit request ("what is my schedule today?") already works via `Intent.CHECK_SCHEDULE` in `response_generator.py` — out of scope to change. There is no voice-driven schedule creation requirement; all creation is via the dashboard frontend (confirmed against current code, matches existing behavior).

## Current State (verified against code)

- `backend/src/calendar_module/calendar_service.py` — `CalendarService` has `add_schedule_item`, `get_today_schedule`, `get_upcoming_deadlines`, `delete_schedule_item`. No update method.
- `backend/src/api/app.py` — `GET /api/schedule/today`, `POST /api/schedule`, `DELETE /api/schedule/{item_id}` exist. No `PUT`.
- `app.py`'s `_refresh_runtime_database()` calls `calendar_service.reset_runtime_data()` on every app construction and on `startup_event`, which deletes all rows from `schedule_items` (and `reminders`). This contradicts persistence requirement for schedule.
- No notification loop exists. The codebase's established pattern for periodic background work is `asyncio.create_task(...)` registered in `startup_event`, e.g. `_timer_loop`, `_emotion_monitor_loop` (checked every N seconds via `asyncio.sleep`).
- Connections are already short-lived (`with self._connect() as conn:` per call) — good baseline for avoiding long-held locks, but WAL mode is not enabled.
- `dashboard/src/lib/api.js` has `getJson`, `postJson`, `deleteJson`. No `putJson`.
- `dashboard/src/components/SchedulePanel.jsx` has add + remove only.
- Existing test `backend/tests/test_dashboard_productivity_api.py::test_database_refresh_on_start_clears_runtime_tables` asserts schedule items are cleared on restart — this assertion will be inverted by this change.

## Design

### 1. `CalendarService` changes

- New columns on `schedule_items` via migration (`_migrate_schedule_columns`): `notified_30 INTEGER DEFAULT 0`, `notified_due INTEGER DEFAULT 0`.
- `_connect()` sets `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` on every new connection, so concurrent short transactions (API requests vs. the notification loop) queue briefly instead of raising `database is locked`.
- New method `update_schedule_item(item_id, *, title=None, date=None, time=None, type=None, priority=None, user_id=None) -> dict | None`: partial update (only provided fields change), scoped by `user_id`, returns the updated row as a dict (same shape as `add_schedule_item`) or `None` if the row doesn't exist or isn't owned by `user_id`.
- New method `get_items_needing_notification(now: datetime) -> list[dict]`: scans **all users'** `schedule_items` (not scoped to the active user — notifications must fire regardless of which dashboard session is currently active) and returns items that have a parseable `date`+`time` and are due for either the 30-minute or due-now notification, using the tolerance-window rule below.
- New method `mark_notified(item_id: int, stage: str) -> None` where `stage` is `"30"` or `"due"`; sets the corresponding column to `1`.
- `reset_runtime_data()`: stop deleting from `schedule_items`. Leave `reminders` deletion as-is (owned by a different action-plan item, out of scope here).

### 2. Notification trigger semantics (tolerance window)

The notification loop ticks every 15 seconds. For an item with combined datetime `due`:
- **30-minute stage**: fires once when `now` falls in `[due - 30min - 15s, due - 30min]` and `notified_30 = 0`. Marks `notified_30 = 1` after firing.
- **Due stage**: fires once when `now` falls in `[due - 15s, due]` (i.e., a few seconds before or at the exact instant) and `notified_due = 0`. Marks `notified_due = 1` after firing.
- Items with unparseable/missing `date` or `time` are skipped (never notified).
- Each stage fires **at most once** per item, persisted via the flag columns — survives process restarts and multiple loop ticks within the same window.

### 3. `app.py` changes

- `PUT /api/schedule/{item_id}` — body re-uses `ScheduleItemRequest` fields as optional (new `ScheduleItemUpdateRequest` model in `core/models.py` with all fields optional). Calls `update_schedule_item`; 404 if `None` returned.
- `_schedule_notification_loop()` registered in `startup_event` alongside `_timer_loop`/`_emotion_monitor_loop`. Each tick: call `calendar_service.get_items_needing_notification(datetime.now())`; for each item speak via `tts.speak(phrase_bank.say(...))` and call `calendar_service.mark_notified(...)`.
- `PhraseBank` additions: `schedule_reminder_30` → "Upcoming: {title} in 30 minutes.", `schedule_reminder_due` → "{title} starts now."

### 4. Frontend changes

- `dashboard/src/lib/api.js`: add `putJson(path, data)`, mirroring `postJson` but with `method: "PUT"`.
- `dashboard/src/components/SchedulePanel.jsx`: add an "Edit" button per schedule item. Clicking it populates the existing add-form fields with that item's values and switches the submit button to "Save changes" (calls `putJson` instead of `postJson`) plus a "Cancel" button to exit edit mode. No new component needed — reuse the existing form.

### 5. Testing (`backend/tests/test_schedule_module.py`, new file)

- CRUD: create → read (today) → update (partial fields) → delete; verify ownership (user A's token can't update/delete user B's item — expect 404).
- Persistence: create two `create_app()` instances pointed at the same `tmp_path` db file (same pattern as existing `test_database_refresh_on_start_clears_runtime_tables`); item added via instance 1 is visible via instance 2's `/api/schedule/today`.
- Update existing test `test_database_refresh_on_start_clears_runtime_tables` in `test_dashboard_productivity_api.py`: change assertion so schedule items **persist** across a fresh `create_app()` call instead of being cleared (rename if needed to reflect new behavior).
- Notifications: directly exercise `CalendarService.get_items_needing_notification` / `mark_notified` with a fabricated item whose due time is ~30 minutes out, then due now; assert each stage fires exactly once and not again on a repeated call within the same window.
- Concurrency: spawn multiple threads performing concurrent `add_schedule_item`/`get_today_schedule`/`update_schedule_item` calls against one db file; assert no `sqlite3.OperationalError` is raised.

## Out of scope

- Reminder persistence/notifications (separate action-plan item, owned by Anas).
- Voice-driven schedule creation (not required; current voice path only reads/check existing schedule).
- Changing the read-aloud ("what is my schedule today?") flow.
