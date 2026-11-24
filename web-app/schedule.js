// Festival schedules: reading files and working out who's on.
//
// The app's own format (what CSV files get turned into):
// {
//   "festival": "Example Fest",
//   "stages": [ { "name": "Main Stage", "lat": 34.05, "lon": -118.25, "radius": 150 } ],
//               // lat/lon optional; radius = how close counts as "at this stage", in meters
//   "sets": [ { "artist": "ROZ", "stage": "Main Stage",
//               "start": "2026-12-05T21:00", "end": "2026-12-05T22:30" } ]
// }
// Times are festival local time (the time on your phone when you're there).

export const DEFAULT_RADIUS = 150;   // meters

export function parseScheduleFile(text, fileName = "") {
  const trimmed = text.trim();
  const sched = trimmed.startsWith("{") ? JSON.parse(trimmed) : parseCsv(trimmed, fileName);
  return clean(sched);
}

// Make sure every schedule has the same shape, whatever it came from.
function clean(sched) {
  const out = {
    festival: String(sched.festival || "My festival"),
    stages: [],
    sets: [],
  };
  for (const st of sched.sets || []) {
    if (!st.artist || !st.start || !st.end) continue;
    const start = new Date(st.start), end = new Date(st.end);
    if (isNaN(start) || isNaN(end)) continue;
    if (end <= start) end.setDate(end.getDate() + 1);   // goes past midnight
    out.sets.push({
      artist: String(st.artist).trim(),
      stage: String(st.stage || "Main stage").trim(),
      start: toLocalString(start),
      end: toLocalString(end),
    });
  }
  const known = new Map();
  for (const s of sched.stages || []) if (s && s.name) known.set(s.name.trim(), s);
  for (const st of out.sets) if (!known.has(st.stage)) known.set(st.stage, { name: st.stage });
  out.stages = [...known.values()].map((s) => ({
    name: s.name.trim(),
    lat: typeof s.lat === "number" ? s.lat : null,
    lon: typeof s.lon === "number" ? s.lon : null,
    radius: typeof s.radius === "number" ? s.radius : DEFAULT_RADIUS,
  }));
  if (!out.sets.length) throw new Error("No sets found in that file.");
  return out;
}

function toLocalString(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

// ---------- CSV (from Google Sheets, Excel or Numbers) ----------
// Columns (any order, first row is the header):
// artist, stage, date, start, end    (optional extra: festival)

function splitCsvLine(line) {
  const cells = [];
  let cur = "", quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
      else if (ch === '"') quoted = false;
      else cur += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === "," || ch === ";" || ch === "\t") { cells.push(cur); cur = ""; }
    else cur += ch;
  }
  cells.push(cur);
  return cells.map((c) => c.trim());
}

function parseCsv(text, fileName) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  const head = splitCsvLine(lines[0]).map((h) => h.toLowerCase().replace(/[^a-z]/g, ""));
  const col = (...names) => head.findIndex((h) => names.includes(h));
  const iArtist = col("artist", "name", "act", "dj");
  const iStage = col("stage", "where");
  const iDate = col("date", "day");
  const iStart = col("start", "starttime", "from", "begin");
  const iEnd = col("end", "endtime", "to", "until", "finish");
  const iFest = col("festival", "event");
  const iLat = col("lat", "latitude");
  const iLon = col("lon", "lng", "long", "longitude");
  const iLoc = col("location", "coordinates", "coords", "gps");
  if (iArtist < 0 || iDate < 0 || iStart < 0 || iEnd < 0) {
    throw new Error("The first row needs these column names: artist, stage, date, start, end");
  }
  const sets = [];
  const stages = new Map();
  let festival = fileName.replace(/\.(csv|txt)$/i, "").replace(/[-_]+/g, " ");
  for (const line of lines.slice(1)) {
    const c = splitCsvLine(line);
    const day = parseDate(c[iDate]);
    const start = parseTime(c[iStart]), end = parseTime(c[iEnd]);
    if (!c[iArtist] || !day || !start || !end) continue;
    if (iFest >= 0 && c[iFest]) festival = c[iFest];
    const s = new Date(day[0], day[1] - 1, day[2], start[0], start[1]);
    const e = new Date(day[0], day[1] - 1, day[2], end[0], end[1]);
    const stageName = iStage >= 0 ? c[iStage] : "";
    sets.push({ artist: c[iArtist], stage: stageName, start: s, end: e });
    // Optional stage location: lat + lon columns, or one "location" column
    // pasted from Google Maps like "34.0522, -118.2437".
    let lat = iLat >= 0 ? parseFloat(c[iLat]) : NaN;
    let lon = iLon >= 0 ? parseFloat(c[iLon]) : NaN;
    if (iLoc >= 0 && c[iLoc]) {
      const m = c[iLoc].match(/(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)/);
      if (m) { lat = +m[1]; lon = +m[2]; }
    }
    if (stageName && !isNaN(lat) && !isNaN(lon) && !stages.has(stageName)) {
      stages.set(stageName, { name: stageName, lat, lon });
    }
  }
  return { festival, sets, stages: [...stages.values()] };
}

// "2026-12-05", "12/5/2026", "12/5/26"  →  [2026, 12, 5]
function parseDate(t) {
  if (!t) return null;
  let m = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) return [+m[1], +m[2], +m[3]];
  m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);
  if (m) return [m[3].length === 2 ? 2000 + +m[3] : +m[3], +m[1], +m[2]];
  return null;
}

// "21:00", "9:00 PM", "9pm", "9.30pm"  →  [21, 0]
function parseTime(t) {
  if (!t) return null;
  const m = t.toLowerCase().replace(/\s/g, "").match(/^(\d{1,2})(?:[:.](\d{2}))?(?::\d{2})?(am|pm)?$/);
  if (!m) return null;
  let h = +m[1];
  const min = +(m[2] || 0);
  if (m[3] === "pm" && h < 12) h += 12;
  if (m[3] === "am" && h === 12) h = 0;
  if (h > 23 || min > 59) return null;
  return [h, min];
}

// ---------- Who's on ----------

// Sets at one stage, as real times, sorted.
export function setsAt(sched, stageName) {
  return sched.sets
    .filter((s) => s.stage === stageName)
    .map((s) => ({ artist: s.artist, start: new Date(s.start), end: new Date(s.end) }))
    .sort((a, b) => a.start - b.start);
}

export function nowAndNext(sets, now = new Date()) {
  const current = sets.find((s) => s.start <= now && now < s.end) || null;
  const next = sets.find((s) => s.start > now) || null;
  return { current, next };
}

// A pretend festival that starts right now, to test auto mode.
export function testSchedule() {
  const now = new Date();
  const at = (min) => toLocalString(new Date(now.getTime() + min * 60000));
  return clean({
    festival: "Test run (starts now)",
    sets: [
      { artist: "ROZ", stage: "Test stage", start: at(0), end: at(2) },
      { artist: "Kandi Kid", stage: "Test stage", start: at(2), end: at(4) },
      { artist: "Bunny Bass", stage: "Test stage", start: at(5), end: at(7) },
    ],
  });
}

export function fmtTime(d) {
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

// ---------- Where am I? ----------

// Distance in meters between two GPS points.
export function distanceM(lat1, lon1, lat2, lon2) {
  const R = 6371000, rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad, dLon = (lon2 - lon1) * rad;
  const a = Math.sin(dLat / 2) ** 2 +
            Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

// The closest stage that has a saved spot. inside = within its radius.
export function nearestStage(stages, lat, lon) {
  let best = null;
  for (const st of stages) {
    if (st.lat == null || st.lon == null) continue;
    const d = distanceM(lat, lon, st.lat, st.lon);
    if (!best || d < best.distance) best = { stage: st, distance: d };
  }
  if (best) best.inside = best.distance <= (best.stage.radius || DEFAULT_RADIUS);
  return best;
}
