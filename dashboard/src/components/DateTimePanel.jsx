import { useEffect, useMemo, useState } from "react";
import { CalendarDays, Clock3, Globe2, MapPin } from "lucide-react";
import Card from "./Card";

const LOCATION_PRESETS = [
  { label: "Kuala Lumpur, Malaysia", timeZone: "Asia/Kuala_Lumpur" },
  { label: "Singapore", timeZone: "Asia/Singapore" },
  { label: "Tokyo, Japan", timeZone: "Asia/Tokyo" },
  { label: "Seoul, South Korea", timeZone: "Asia/Seoul" },
  { label: "London, United Kingdom", timeZone: "Europe/London" },
  { label: "New York, United States", timeZone: "America/New_York" },
  { label: "San Francisco, United States", timeZone: "America/Los_Angeles" },
  { label: "Sydney, Australia", timeZone: "Australia/Sydney" },
  { label: "UTC", timeZone: "UTC" }
];

function getBrowserTimeZone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kuala_Lumpur";
}

function getSupportedTimeZones() {
  if (typeof Intl.supportedValuesOf === "function") {
    try {
      return Intl.supportedValuesOf("timeZone");
    } catch {
      return [];
    }
  }
  return [];
}

function formatLocationFromTimeZone(timeZone) {
  const preset = LOCATION_PRESETS.find((item) => item.timeZone === timeZone);
  if (preset) return preset.label;
  return timeZone.replace(/_/g, " ").replace("/", " / ");
}

function formatUtcOffset(date, timeZone) {
  try {
    const parts = new Intl.DateTimeFormat("en-GB", {
      timeZone,
      timeZoneName: "shortOffset",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    }).formatToParts(date);
    return parts.find((part) => part.type === "timeZoneName")?.value ?? timeZone;
  } catch {
    return timeZone;
  }
}

function safeFormat(date, options, fallback = "—") {
  try {
    return new Intl.DateTimeFormat("en-GB", options).format(date);
  } catch {
    return fallback;
  }
}

export default function DateTimePanel() {
  const browserTimeZone = useMemo(getBrowserTimeZone, []);
  const allTimeZones = useMemo(getSupportedTimeZones, []);
  const [now, setNow] = useState(() => new Date());
  const [timeZone, setTimeZone] = useState(() => {
    return window.localStorage.getItem("juno-dashboard-timezone") || browserTimeZone;
  });
  const [locationLabel, setLocationLabel] = useState(() => {
    return window.localStorage.getItem("juno-dashboard-location") || formatLocationFromTimeZone(browserTimeZone);
  });

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("juno-dashboard-timezone", timeZone);
    window.localStorage.setItem("juno-dashboard-location", locationLabel);
  }, [timeZone, locationLabel]);

  function handleLocationChange(event) {
    const selected = LOCATION_PRESETS.find((item) => item.timeZone === event.target.value);
    if (!selected) return;
    setTimeZone(selected.timeZone);
    setLocationLabel(selected.label);
  }

  function handleTimeZoneChange(event) {
    const selectedTimeZone = event.target.value;
    setTimeZone(selectedTimeZone);
    setLocationLabel(formatLocationFromTimeZone(selectedTimeZone));
  }

  function useDeviceTimeZone() {
    setTimeZone(browserTimeZone);
    setLocationLabel(formatLocationFromTimeZone(browserTimeZone));
  }

  const currentTime = safeFormat(now, {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  });
  const currentDate = safeFormat(now, {
    timeZone,
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric"
  });
  const utcOffset = formatUtcOffset(now, timeZone);
  const presetValue = LOCATION_PRESETS.some((item) => item.timeZone === timeZone) ? timeZone : "custom";

  return (
    <Card title="Current System Date & Time" className="h-full">
      <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr] lg:items-center">
        <div className="rounded-[1.75rem] border border-white/20 bg-slate-950/55 p-5 shadow-inner">
          <div className="flex flex-wrap items-center gap-2 text-sm text-slate-300/80">
            <MapPin className="h-4 w-4 text-cyan-200" />
            <span>{locationLabel}</span>
            <span className="rounded-full border border-white/15 bg-white/[0.08] px-2 py-0.5 text-xs text-slate-200">
              {timeZone} · {utcOffset}
            </span>
          </div>

          <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="section-kicker text-xs font-semibold">Live clock</p>
              <p className="mt-2 text-5xl font-black tabular-nums text-white sm:text-6xl">
                {currentTime}
              </p>
            </div>
            <div className="min-w-52 rounded-2xl border border-white/15 bg-white/[0.08] p-4">
              <div className="flex items-center gap-2 text-sm text-slate-300/80">
                <CalendarDays className="h-4 w-4 text-fuchsia-200" />
                <span>Date</span>
              </div>
              <p className="mt-1 text-lg font-semibold text-white">{currentDate}</p>
            </div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm font-medium text-slate-200">
            Select location
            <select
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2 text-sm"
              value={presetValue}
              onChange={handleLocationChange}
            >
              {LOCATION_PRESETS.map((item) => (
                <option key={item.label} value={item.timeZone}>
                  {item.label}
                </option>
              ))}
              {!LOCATION_PRESETS.some((item) => item.timeZone === timeZone) && (
                <option value="custom">Custom timezone</option>
              )}
            </select>
          </label>

          <label className="text-sm font-medium text-slate-200">
            Select timezone
            <select
              className="input-glass mt-1 w-full rounded-2xl px-3 py-2 text-sm"
              value={timeZone}
              onChange={handleTimeZoneChange}
            >
              {[timeZone, ...LOCATION_PRESETS.map((item) => item.timeZone), ...allTimeZones]
                .filter(Boolean)
                .filter((item, index, arr) => arr.indexOf(item) === index)
                .map((zone) => (
                  <option key={zone} value={zone}>
                    {zone.replace(/_/g, " ")}
                  </option>
                ))}
            </select>
          </label>

          <button
            type="button"
            onClick={useDeviceTimeZone}
            className="btn-secondary inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-semibold md:col-span-2"
          >
            <Globe2 className="h-4 w-4" />
            Use device timezone ({browserTimeZone})
          </button>

          <div className="soft-panel rounded-2xl p-4 text-sm leading-6 text-slate-300/80 md:col-span-2">
            <div className="flex items-center gap-2 font-medium text-white">
              <Clock3 className="h-4 w-4 text-cyan-200" />
              Dashboard clock
            </div>
            <p className="mt-1">
              This clock is based on the device system time and is displayed using the selected timezone or location.
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
