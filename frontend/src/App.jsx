import React, { useState, useMemo, useRef, useEffect } from "react";
import {
  ArrowLeftRight,
  ChevronLeft,
  Search,
  Zap,
  Users,
  Sparkles,
  Bus,
  TrainFront,
  PersonStanding,
  IndianRupee,
  Clock,
  MapPin,
  Circle,
  Radio,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  DESIGN TOKENS                                                      */
/* ------------------------------------------------------------------ */
const C = {
  bg: "#10121A",
  bgSoft: "#14161F",
  surface: "#1B1E29",
  surface2: "#232734",
  line: "#2C3140",
  text: "#EEEEE6",
  textDim: "#8C93A8",
  textFaint: "#5B6175",
  amber: "#FFB020",
  amberSoft: "rgba(255,176,32,0.14)",
  teal: "#46D9C5",
  tealSoft: "rgba(70,217,197,0.14)",
  coral: "#FF6859",
  coralSoft: "rgba(255,104,89,0.14)",
  violet: "#9B8CFF",
  violetSoft: "rgba(155,140,255,0.16)",
};

const CROWD_COLOR = { low: C.teal, medium: C.amber, high: C.coral };
const CROWD_LABEL = { low: "Light crowd", medium: "Moderate crowd", high: "Heavy crowd" };

/* ------------------------------------------------------------------ */
/*  MOCK DATA GENERATION                                               */
/* ------------------------------------------------------------------ */
const STOPS = [
  "Mangaluru Central",
  "Hampankatta",
  "Pumpwell Circle",
  "Kadri Temple",
  "Kankanady",
  "Bejai",
  "State Bank",
  "Surathkal",
  "NITK Campus",
  "Panambur Beach",
  "Urwa Store",
  "Lalbagh",
];

function seededRandom(seed) {
  let s = 0;
  for (let i = 0; i < seed.length; i++) s = (s * 31 + seed.charCodeAt(i)) % 100000;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function buildRoutes(from, to) {
  const rand = seededRandom((from || "a") + (to || "b"));
  const pick = (arr) => arr[Math.floor(rand() * arr.length)];
  const busRoutes = ["44A", "12B", "6", "27C", "9"];

  const makeLegs = (count, baseMin) => {
    const legs = [];
    legs.push({
      type: "walk",
      label: `Walk to ${pick(STOPS)}`,
      mins: 3 + Math.floor(rand() * 5),
    });
    for (let i = 0; i < count; i++) {
      const crowd = pick(["low", "medium", "high"]);
      legs.push({
        type: rand() > 0.35 ? "bus" : "metro",
        route: pick(busRoutes),
        label: `${pick(STOPS)} \u2192 ${pick(STOPS)}`,
        mins: baseMin + Math.floor(rand() * 10),
        stops: 3 + Math.floor(rand() * 6),
        crowd,
      });
    }
    legs.push({
      type: "walk",
      label: `Walk to destination`,
      mins: 2 + Math.floor(rand() * 4),
    });
    return legs;
  };

  const buildOne = (kind) => {
    let legs, fare;
    if (kind === "quickest") {
      legs = makeLegs(1 + Math.floor(rand() * 2), 9);
      fare = 22 + Math.floor(rand() * 15);
    } else if (kind === "calm") {
      legs = makeLegs(2, 13);
      legs = legs.map((l) => (l.type !== "walk" ? { ...l, crowd: "low" } : l));
      fare = 20 + Math.floor(rand() * 12);
    } else {
      legs = makeLegs(2, 10);
      fare = 24 + Math.floor(rand() * 14);
    }
    const mins = legs.reduce((a, l) => a + l.mins, 0);
    const now = new Date();
    const arrive = new Date(now.getTime() + mins * 60000);
    const transitLegs = legs.filter((l) => l.type !== "walk");
    const crowdScore =
      transitLegs.reduce((a, l) => a + { low: 1, medium: 2, high: 3 }[l.crowd], 0) /
      Math.max(1, transitLegs.length);
    return {
      legs,
      mins,
      fare,
      arrive: arrive.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      transfers: transitLegs.length,
      crowdScore,
    };
  };

  return {
    quickest: { key: "quickest", label: "Quickest", accent: C.amber, accentSoft: C.amberSoft, Icon: Zap, ...buildOne("quickest") },
    calm: { key: "calm", label: "Least Crowded", accent: C.teal, accentSoft: C.tealSoft, Icon: Users, ...buildOne("calm") },
    optimum: { key: "optimum", label: "Optimum", accent: C.violet, accentSoft: C.violetSoft, Icon: Sparkles, ...buildOne("optimum") },
  };
}

/* ------------------------------------------------------------------ */
/*  SHARED BITS                                                        */
/* ------------------------------------------------------------------ */
function LiveBadge() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, letterSpacing: 0.4 }}>
      <span style={{ position: "relative", width: 7, height: 7, display: "inline-block" }}>
        <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: C.teal, animation: "pulseRing 1.8s ease-out infinite" }} />
        <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: C.teal }} />
      </span>
      LIVE MODEL
    </div>
  );
}

function ModeIcon({ type, size = 13, color }) {
  const style = { color: color || C.textDim };
  if (type === "walk") return <PersonStanding size={size} style={style} />;
  if (type === "metro") return <TrainFront size={size} style={style} />;
  return <Bus size={size} style={style} />;
}

/* Signature element: compact "transit schematic" line diagram encoding
   crowd density (segment color) and stop count (dot count) per leg. */
function LineDiagram({ legs, accent }) {
  const transitLegs = legs.filter((l) => l.type !== "walk");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 3, width: "100%", overflow: "hidden" }}>
      <Circle size={7} fill={C.textFaint} color={C.textFaint} />
      {transitLegs.map((leg, i) => {
        const color = CROWD_COLOR[leg.crowd];
        const dotCount = Math.min(5, Math.max(2, Math.round(leg.stops / 2)));
        return (
          <React.Fragment key={i}>
            <div
              style={{
                flex: 1,
                minWidth: 18,
                height: 5,
                borderRadius: 3,
                background: `linear-gradient(90deg, ${color}55, ${color})`,
                position: "relative",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-evenly",
              }}
              title={CROWD_LABEL[leg.crowd]}
            >
              {Array.from({ length: dotCount }).map((_, d) => (
                <span key={d} style={{ width: 3, height: 3, borderRadius: "50%", background: "rgba(16,18,26,0.55)" }} />
              ))}
            </div>
            <div
              style={{
                width: 18,
                height: 18,
                minWidth: 18,
                borderRadius: "50%",
                background: C.surface2,
                border: `1.5px solid ${color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ModeIcon type={leg.type} size={10} color={color} />
            </div>
          </React.Fragment>
        );
      })}
      <div style={{ flex: 0.6, minWidth: 10, height: 5, borderRadius: 3, background: `${accent}66` }} />
      <MapPin size={13} color={accent} />
    </div>
  );
}

function CrowdMeter({ level }) {
  const color = CROWD_COLOR[level];
  const activeCount = { low: 2, medium: 4, high: 6 }[level];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 14 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <span
            key={i}
            style={{
              width: 3,
              height: 4 + i * 1.6,
              borderRadius: 1,
              background: i < activeCount ? color : C.line,
              animation: i < activeCount ? `barPulse 1.6s ease-in-out ${i * 0.12}s infinite` : "none",
            }}
          />
        ))}
      </div>
      <span style={{ fontSize: 12, color, fontFamily: "'Inter', sans-serif", fontWeight: 500 }}>
        {CROWD_LABEL[level]}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  STYLISED MAP (placeholder for Google Maps API)                     */
/* ------------------------------------------------------------------ */
function MapArt({ hasDestination }) {
  return (
    <svg viewBox="0 0 400 230" width="100%" height="100%" style={{ display: "block" }}>
      <defs>
        <linearGradient id="mapBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#181B26" />
          <stop offset="100%" stopColor="#12141C" />
        </linearGradient>
      </defs>
      <rect width="400" height="230" fill="url(#mapBg)" />
      {/* coastline blob nod to a coastal city */}
      <path d="M0,190 C60,160 90,210 140,185 C190,160 210,205 260,190 L400,230 L0,230 Z" fill="#173038" opacity="0.55" />
      {/* street grid */}
      {[30, 90, 150, 210, 270, 330].map((x) => (
        <line key={"v" + x} x1={x} y1="0" x2={x - 30} y2="230" stroke={C.line} strokeWidth="1" opacity="0.5" />
      ))}
      {[20, 60, 100, 140, 180].map((y) => (
        <line key={"h" + y} x1="0" y1={y} x2="400" y2={y + 10} stroke={C.line} strokeWidth="1" opacity="0.4" />
      ))}
      {/* route path once destination chosen */}
      {hasDestination && (
        <path
          d="M110,150 C150,120 190,150 230,110 C255,88 270,95 290,70"
          fill="none"
          stroke={C.violet}
          strokeWidth="2.5"
          strokeDasharray="1 9"
          strokeLinecap="round"
          style={{ animation: "dashMove 1.4s linear infinite" }}
        />
      )}
      {/* origin pin */}
      <g transform="translate(110,150)">
        <circle r="14" fill={C.amber} opacity="0.18" style={{ animation: "pulseRing 2s ease-out infinite" }} />
        <circle r="5" fill={C.amber} stroke={C.bg} strokeWidth="2" />
      </g>
      {/* destination pin */}
      {hasDestination && (
        <g transform="translate(290,70)">
          <circle r="14" fill={C.violet} opacity="0.2" style={{ animation: "pulseRing 2s ease-out infinite" }} />
          <path d="M0,-11 C6,-11 10,-7 10,-2 C10,4 0,11 0,11 C0,11 -10,4 -10,-2 C-10,-7 -6,-11 0,-11 Z" fill={C.violet} stroke={C.bg} strokeWidth="1.5" />
        </g>
      )}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  PLAN SCREEN                                                        */
/* ------------------------------------------------------------------ */
function PlanScreen({ from, to, setFrom, setTo, onFindRoutes }) {
  const [activeField, setActiveField] = useState(null); // 'from' | 'to' | null
  const [recents] = useState(["NITK Campus", "Mangaluru Central", "Hampankatta"]);

  const suggestions = useMemo(() => {
    const q = (activeField === "from" ? from : to).toLowerCase();
    return STOPS.filter((s) => s.toLowerCase().includes(q)).slice(0, 5);
  }, [activeField, from, to]);

  const swap = () => {
    setFrom(to);
    setTo(from);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ height: 210, position: "relative" }}>
        <MapArt hasDestination={!!to} />
        <div style={{ position: "absolute", top: 14, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18, color: C.text, letterSpacing: 0.3 }}>
            transit<span style={{ color: C.amber }}>·</span>
          </div>
          <LiveBadge />
        </div>
      </div>

      <div
        style={{
          background: C.surface,
          borderTopLeftRadius: 22,
          borderTopRightRadius: 22,
          marginTop: -18,
          padding: "20px 18px 18px",
          flex: 1,
          boxShadow: "0 -14px 30px rgba(0,0,0,0.35)",
          position: "relative",
          zIndex: 2,
        }}
      >
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 15, color: C.text, marginBottom: 14, fontWeight: 600 }}>
          Where are you headed?
        </div>

        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", flexDirection: "column", background: C.surface2, borderRadius: 14, border: `1px solid ${C.line}` }}>
            <FieldRow
              icon={<span style={{ width: 8, height: 8, borderRadius: "50%", background: C.amber, display: "inline-block" }} />}
              placeholder="Current location"
              value={from}
              onChange={setFrom}
              onFocus={() => setActiveField("from")}
            />
            <div style={{ height: 1, background: C.line, marginLeft: 40 }} />
            <FieldRow
              icon={<span style={{ width: 8, height: 8, borderRadius: 2, background: C.violet, display: "inline-block" }} />}
              placeholder="Search destination"
              value={to}
              onChange={setTo}
              onFocus={() => setActiveField("to")}
            />
          </div>

          <button
            onClick={swap}
            aria-label="Swap origin and destination"
            style={{
              position: "absolute",
              right: 10,
              top: "50%",
              transform: "translateY(-50%)",
              width: 32,
              height: 32,
              borderRadius: "50%",
              background: C.bgSoft,
              border: `1px solid ${C.line}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
            }}
          >
            <ArrowLeftRight size={14} color={C.textDim} />
          </button>
        </div>

        {activeField && suggestions.length > 0 && (
          <div style={{ marginTop: 8, background: C.surface2, borderRadius: 12, border: `1px solid ${C.line}`, overflow: "hidden" }}>
            {suggestions.map((s) => (
              <div
                key={s}
                onClick={() => {
                  activeField === "from" ? setFrom(s) : setTo(s);
                  setActiveField(null);
                }}
                style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", cursor: "pointer", borderBottom: `1px solid ${C.line}`, fontFamily: "'Inter', sans-serif", fontSize: 13.5, color: C.text }}
                onMouseEnter={(e) => (e.currentTarget.style.background = C.line)}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
              >
                <Search size={13} color={C.textFaint} />
                {s}
              </div>
            ))}
          </div>
        )}

        {!activeField && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 11, color: C.textFaint, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.6, marginBottom: 8 }}>
              RECENT
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {recents.map((r) => (
                <button
                  key={r}
                  onClick={() => setTo(r)}
                  style={{
                    padding: "7px 12px",
                    borderRadius: 20,
                    background: C.surface2,
                    border: `1px solid ${C.line}`,
                    color: C.textDim,
                    fontSize: 12.5,
                    fontFamily: "'Inter', sans-serif",
                    cursor: "pointer",
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ flex: 1 }} />

        <button
          onClick={onFindRoutes}
          disabled={!from || !to}
          style={{
            marginTop: 22,
            width: "100%",
            padding: "15px 0",
            borderRadius: 14,
            border: "none",
            background: from && to ? C.amber : C.surface2,
            color: from && to ? "#141620" : C.textFaint,
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: 15,
            letterSpacing: 0.3,
            cursor: from && to ? "pointer" : "not-allowed",
            transition: "background 0.2s ease",
          }}
        >
          Find routes
        </button>
      </div>
    </div>
  );
}

function FieldRow({ icon, placeholder, value, onChange, onFocus }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 14px" }}>
      <div style={{ width: 20, display: "flex", justifyContent: "center" }}>{icon}</div>
      <input
        value={value}
        onFocus={onFocus}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          flex: 1,
          background: "transparent",
          border: "none",
          outline: "none",
          color: C.text,
          fontFamily: "'Inter', sans-serif",
          fontSize: 14,
        }}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  RESULTS SCREEN                                                     */
/* ------------------------------------------------------------------ */
function RouteCard({ route, onSelect }) {
  const { Icon, accent, accentSoft, label, mins, arrive, fare, transfers, legs, crowdScore } = route;
  const overallCrowd = crowdScore <= 1.4 ? "low" : crowdScore <= 2.2 ? "medium" : "high";
  return (
    <button
      onClick={onSelect}
      style={{
        textAlign: "left",
        width: "100%",
        background: C.surface,
        border: `1px solid ${C.line}`,
        borderRadius: 16,
        padding: "16px 16px 14px",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, background: accent }} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
            <div style={{ width: 24, height: 24, borderRadius: 8, background: accentSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <Icon size={13} color={accent} />
            </div>
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 13, color: accent, letterSpacing: 0.3 }}>
              {label.toUpperCase()}
            </span>
            {route.key === "optimum" && (
              <span style={{ fontSize: 9.5, fontFamily: "'IBM Plex Mono', monospace", color: C.textFaint, border: `1px solid ${C.line}`, borderRadius: 5, padding: "1px 5px" }}>
                ML PICK
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 26, color: C.text }}>{mins}</span>
            <span style={{ fontSize: 12.5, color: C.textDim, fontFamily: "'Inter', sans-serif" }}>min · arrive {arrive}</span>
          </div>
        </div>
        <div style={{ textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: C.textDim }}>
          <div style={{ display: "flex", alignItems: "center", gap: 3, justifyContent: "flex-end" }}>
            <IndianRupee size={10} /> {fare}
          </div>
          <div style={{ marginTop: 2 }}>{transfers} transfer{transfers !== 1 ? "s" : ""}</div>
        </div>
      </div>

      <LineDiagram legs={legs} accent={accent} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
        <CrowdMeter level={overallCrowd} />
        <span style={{ fontSize: 12, color: C.textFaint, fontFamily: "'Inter', sans-serif" }}>Details \u203a</span>
      </div>
    </button>
  );
}

function ResultsScreen({ from, to, routes, onBack, onSelect }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar onBack={onBack} title="Route options" subtitle={`${from} \u2192 ${to}`} />
      <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flex: 1 }}>
        <RouteCard route={routes.optimum} onSelect={() => onSelect("optimum")} />
        <RouteCard route={routes.quickest} onSelect={() => onSelect("quickest")} />
        <RouteCard route={routes.calm} onSelect={() => onSelect("calm")} />
        <div style={{ fontSize: 11, color: C.textFaint, fontFamily: "'Inter', sans-serif", textAlign: "center", padding: "6px 20px 4px", lineHeight: 1.5 }}>
          Crowd levels are predicted from live GTFS feeds and historical ridership \u2014 updated every few minutes.
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  DETAIL SCREEN                                                      */
/* ------------------------------------------------------------------ */
function DetailScreen({ routes, activeKey, setActiveKey, onBack, from, to }) {
  const route = routes[activeKey];
  const tabs = ["optimum", "quickest", "calm"];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar onBack={onBack} title={route.label} subtitle={`${from} \u2192 ${to}`} accent={route.accent} />

      <div style={{ display: "flex", gap: 8, padding: "12px 16px 4px" }}>
        {tabs.map((k) => {
          const r = routes[k];
          const activeTab = k === activeKey;
          return (
            <button
              key={k}
              onClick={() => setActiveKey(k)}
              style={{
                flex: 1,
                padding: "8px 4px",
                borderRadius: 10,
                border: `1px solid ${activeTab ? r.accent : C.line}`,
                background: activeTab ? r.accentSoft : "transparent",
                color: activeTab ? r.accent : C.textFaint,
                fontFamily: "'Inter', sans-serif",
                fontSize: 11.5,
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              {r.label}
            </button>
          );
        })}
      </div>

      <div style={{ padding: "16px", flex: 1, overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
          <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 30, color: C.text }}>{route.mins} min</span>
        </div>
        <div style={{ fontSize: 12.5, color: C.textDim, fontFamily: "'Inter', sans-serif", marginBottom: 22 }}>
          Arrive {route.arrive} \u00b7 {route.transfers} transfer{route.transfers !== 1 ? "s" : ""} \u00b7 \u20b9{route.fare}
        </div>

        <div style={{ position: "relative" }}>
          {route.legs.map((leg, i) => (
            <div key={i} style={{ display: "flex", gap: 14, position: "relative" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: "50%",
                    background: leg.type === "walk" ? C.surface2 : `${route.accent}22`,
                    border: `1.5px solid ${leg.type === "walk" ? C.line : route.accent}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <ModeIcon type={leg.type} size={14} color={leg.type === "walk" ? C.textDim : route.accent} />
                </div>
                {i < route.legs.length - 1 && <div style={{ width: 2, flex: 1, minHeight: 30, background: C.line, marginTop: 2 }} />}
              </div>
              <div style={{ paddingBottom: 22, flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 13.5, color: C.text, fontWeight: 500 }}>
                      {leg.type !== "walk" && (
                        <span style={{ color: route.accent, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, marginRight: 6 }}>
                          {leg.route}
                        </span>
                      )}
                      {leg.label}
                    </div>
                    {leg.type !== "walk" && (
                      <div style={{ fontSize: 11.5, color: C.textFaint, marginTop: 2, fontFamily: "'Inter', sans-serif" }}>
                        {leg.stops} stops
                      </div>
                    )}
                  </div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: C.textDim, whiteSpace: "nowrap" }}>
                    {leg.mins} min
                  </div>
                </div>
                {leg.type !== "walk" && (
                  <div style={{ marginTop: 8 }}>
                    <CrowdMeter level={leg.crowd} />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ padding: 16, borderTop: `1px solid ${C.line}`, background: C.surface }}>
        <button
          style={{
            width: "100%",
            padding: "15px 0",
            borderRadius: 14,
            border: "none",
            background: route.accent,
            color: "#12141C",
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: 15,
            cursor: "pointer",
          }}
        >
          Start trip
        </button>
      </div>
    </div>
  );
}

function TopBar({ onBack, title, subtitle, accent }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 16px 12px", borderBottom: `1px solid ${C.line}` }}>
      <button
        onClick={onBack}
        style={{ width: 32, height: 32, borderRadius: "50%", background: C.surface2, border: `1px solid ${C.line}`, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0 }}
      >
        <ChevronLeft size={16} color={C.textDim} />
      </button>
      <div>
        <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 15, color: accent || C.text }}>{title}</div>
        <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 11.5, color: C.textFaint, marginTop: 1 }}>{subtitle}</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  APP SHELL                                                          */
/* ------------------------------------------------------------------ */
export default function TransitApp() {
  const [screen, setScreen] = useState("plan"); // plan | results | detail
  const [from, setFrom] = useState("Current location");
  const [to, setTo] = useState("");
  const [routes, setRoutes] = useState(null);
  const [activeKey, setActiveKey] = useState("optimum");

  const handleFindRoutes = () => {
    setRoutes(buildRoutes(from, to));
    setScreen("results");
  };

  return (
    <div
      style={{
        width: "100%",
        minHeight: 620,
        maxWidth: 420,
        margin: "0 auto",
        background: C.bg,
        borderRadius: 24,
        overflow: "hidden",
        boxShadow: "0 30px 60px rgba(0,0,0,0.45)",
        border: `1px solid ${C.line}`,
        fontFamily: "'Inter', sans-serif",
        display: "flex",
        flexDirection: "column",
        height: 660,
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        input::placeholder { color: ${C.textFaint}; }
        @keyframes pulseRing {
          0% { transform: scale(0.6); opacity: 0.9; }
          100% { transform: scale(2.2); opacity: 0; }
        }
        @keyframes barPulse {
          0%, 100% { opacity: 0.55; }
          50% { opacity: 1; }
        }
        @keyframes dashMove {
          to { stroke-dashoffset: -20; }
        }
        @keyframes fadeSlide {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div key={screen} style={{ flex: 1, minHeight: 0, animation: "fadeSlide 0.35s ease" }}>
        {screen === "plan" && (
          <PlanScreen from={from} to={to} setFrom={setFrom} setTo={setTo} onFindRoutes={handleFindRoutes} />
        )}
        {screen === "results" && routes && (
          <ResultsScreen
            from={from}
            to={to}
            routes={routes}
            onBack={() => setScreen("plan")}
            onSelect={(key) => {
              setActiveKey(key);
              setScreen("detail");
            }}
          />
        )}
        {screen === "detail" && routes && (
          <DetailScreen
            routes={routes}
            activeKey={activeKey}
            setActiveKey={setActiveKey}
            onBack={() => setScreen("results")}
            from={from}
            to={to}
          />
        )}
      </div>
    </div>
  );
}
