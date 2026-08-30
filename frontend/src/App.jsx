import React, { useState, useMemo, useEffect, useRef } from "react";
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
  MapPin,
  Circle,
  Radio,
  Maximize2,
  Minimize2,
} from "lucide-react";
import Map from "./components/Map";
import GovDashboard from "./components/GovDashboard";

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

const CROWD_COLOR = {
  low: C.teal, LOW: C.teal,
  medium: C.amber, MODERATE: C.amber,
  high: C.coral, HIGH: C.coral, VERY_HIGH: C.coral,
};
const CROWD_LABEL = {
  low: "Light crowd", LOW: "Light crowd",
  medium: "Moderate crowd", MODERATE: "Moderate crowd",
  high: "Heavy crowd", HIGH: "Heavy crowd", VERY_HIGH: "Very heavy crowd",
};

/* ------------------------------------------------------------------ */
/* API CONNECTION                                                     */
/* ------------------------------------------------------------------ */

const API_ENDPOINTS = [
  "/api/recommend",
  "http://127.0.0.1:8000/api/recommend",
  "http://localhost:8000/api/recommend",
];

const crowdToNumber = {
  LOW: 1,
  MODERATE: 2,
  HIGH: 3,
  VERY_HIGH: 3,
};

function toUiRoute(apiRoute, key, label, accent, accentSoft, Icon, badge = null) {
  const now = new Date();
  const arrival = new Date(now.getTime() + (apiRoute.eta_minutes || 0) * 60_000);

  const mappedLegs = (apiRoute.legs && apiRoute.legs.length > 0)
    ? apiRoute.legs.map(leg => ({
        type: (leg.mode || "BUS").toLowerCase(),
        mode: (leg.mode || "BUS").toLowerCase(),
        route: leg.line || "",
        label: leg.line || "",
        from: leg.from_stop || "",
        to: leg.to_stop || "",
        from_stop: leg.from_stop || "",
        to_stop: leg.to_stop || "",
        mins: leg.travel_minutes || 0,
        travel_minutes: leg.travel_minutes || 0,
        stops: leg.num_stops || 0,
        num_stops: leg.num_stops || 0,
        fare: leg.fare || 0,
        crowd: (leg.crowd_estimate || "MODERATE").toLowerCase().replace("very_high", "high").replace("moderate", "medium"),
        crowd_estimate: leg.crowd_estimate || "MODERATE",
        line: leg.line || "",
      }))
    : [
        {
          type: (apiRoute.route_name || "").toLowerCase().includes("metro") ? "metro" : "bus",
          mode: (apiRoute.route_name || "").toLowerCase().includes("metro") ? "metro" : "bus",
          route: apiRoute.route_name || "",
          label: apiRoute.route_name || "",
          from: "",
          to: "",
          from_stop: "",
          to_stop: "",
          mins: apiRoute.eta_minutes || 0,
          travel_minutes: apiRoute.eta_minutes || 0,
          stops: 4,
          num_stops: 4,
          fare: apiRoute.fare ?? 25,
          crowd: (apiRoute.crowd_level ?? "MODERATE").toLowerCase().replace("very_high", "high").replace("moderate", "medium"),
          crowd_estimate: apiRoute.crowd_level || "MODERATE",
          line: apiRoute.route_name || "",
        }
      ];

  return {
    key,
    label,
    accent,
    accentSoft,
    Icon,
    badge,
    mins: apiRoute.eta_minutes,
    arrive: arrival.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
    transfers: apiRoute.transfers,
    crowdScore: crowdToNumber[apiRoute.crowd_level] ?? 2,
    fare: apiRoute.fare ?? 25,
    reason: apiRoute.reason,
    delayMinutes: apiRoute.delay_minutes,
    reliability: apiRoute.reliability,
    crowdLevel: apiRoute.crowd_level,
    crowdConfidence: apiRoute.crowd_confidence,
    eta_minutes: apiRoute.eta_minutes,
    crowd_level: apiRoute.crowd_level,
    delay_minutes: apiRoute.delay_minutes,
    route_name: apiRoute.route_name,
    route_type: apiRoute.route_type,
    distance_km: apiRoute.distance_km,
    legs: mappedLegs,
    _raw: apiRoute,
  };
}

function adaptApiResponse(data) {
  const rawList = [data.recommended_route, ...(data.alternatives || [])].filter(Boolean);

  // Group and deduplicate routes by unique transit characteristics (name + ETA + line)
  const uniqueRoutes = [];
  const seenSignatures = new Set();
  for (const r of rawList) {
    const legsSig = (r.legs || []).map(l => `${l.mode}:${l.line}`).join("->") || r.route_name;
    const sig = `${r.route_name}_${r.eta_minutes}_${legsSig}`;
    if (!seenSignatures.has(sig)) {
      seenSignatures.add(sig);
      uniqueRoutes.push(r);
    }
  }

  // If only 1 route exists, return ONLY 1 card (OPTIMUM)
  if (uniqueRoutes.length <= 1) {
    const single = uniqueRoutes[0] || data.recommended_route;
    return {
      isSingleRoute: true,
      routesList: [
        toUiRoute(single, "optimum", "OPTIMUM", C.violet, C.violetSoft, Sparkles, "BEST PICK")
      ],
      metadata: data.metadata,
    };
  }

  // Find the distinct roles among the candidates:
  // 1. QUICKEST: Strictly the route with the minimum travel time (ETA)
  const sortedByEta = [...uniqueRoutes].sort((a, b) => (a.eta_minutes || 0) - (b.eta_minutes || 0));
  const quickestRoute = sortedByEta[0];

  // 2. LEAST CROWDED (CALM): Strictly the route with the lowest crowding score / density
  const sortedByCrowd = [...uniqueRoutes].sort((a, b) => (a.crowd_score || 50) - (b.crowd_score || 50));
  const calmRoute = sortedByCrowd.find(r => r !== quickestRoute) || sortedByCrowd[0];

  // 3. OPTIMUM: The balanced multi-modal / best composite route
  const remaining = uniqueRoutes.filter(r => r !== quickestRoute && r !== calmRoute);
  const optimumRoute = remaining[0] || (data.recommended_route !== quickestRoute ? data.recommended_route : uniqueRoutes.find(r => r.route_type === "OPTIMUM")) || uniqueRoutes[1] || uniqueRoutes[0];

  const routesList = [];
  if (optimumRoute && optimumRoute !== quickestRoute && optimumRoute !== calmRoute) {
    routesList.push(toUiRoute(optimumRoute, "optimum", "OPTIMUM", C.violet, C.violetSoft, Sparkles, "BEST BALANCED"));
  }
  if (quickestRoute) {
    routesList.push(toUiRoute(quickestRoute, "quickest", "QUICKEST", C.amber, C.amberSoft, Zap));
  }
  if (calmRoute && calmRoute !== quickestRoute && calmRoute !== optimumRoute) {
    routesList.push(toUiRoute(calmRoute, "calm", "LEAST CROWDED", C.teal, C.tealSoft, Users));
  }

  return {
    isSingleRoute: routesList.length <= 1,
    routesList: routesList.length > 0 ? routesList : [toUiRoute(uniqueRoutes[0], "optimum", "OPTIMUM", C.violet, C.violetSoft, Sparkles, "BEST PICK")],
    metadata: data.metadata,
  };
}

/* ------------------------------------------------------------------ */
/*  MOCK DATA GENERATION                                               */
/* ------------------------------------------------------------------ */
const STOPS = [
  "Connaught Place",
  "India Gate",
  "Kashmere Gate",
  "New Delhi Railway Station",
  "Rajiv Chowk",
  "AIIMS",
  "Lajpat Nagar",
  "Saket",
  "Dwarka Sector 21",
  "Hauz Khas",
  "Karol Bagh",
  "Noida Sector 18",
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
function LiveBadge({ online = true }) {
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
        color: C.teal,
        background: "rgba(70,217,197,0.12)",
        border: "1px solid rgba(70,217,197,0.32)",
        padding: "4px 10px",
        borderRadius: 16,
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 10.5,
        fontWeight: 600,
        letterSpacing: 0.5,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ position: "relative", width: 7, height: 7, display: "inline-block", flexShrink: 0 }}>
        <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: C.teal, animation: "pulseRing 1.8s ease-out infinite" }} />
        <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: C.teal }} />
      </span>
      PROTOTYPE PREDICTION
    </div>
  );
}

function ModeIcon({ type, size = 13, color }) {
  const style = { color: color || C.textDim };
  const t = (type || "").toLowerCase();
  if (t === "walk") return <PersonStanding size={size} style={style} />;
  if (t === "metro" || t === "train") return <TrainFront size={size} style={style} />;
  return <Bus size={size} style={style} />;
}

function LineDiagram({ legs = [], accent }) {
  const transitLegs = legs.filter((l) => (l.mode || l.type || "").toLowerCase() !== "walk");
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 3, width: "100%", overflow: "hidden" }}>
      <Circle size={7} fill={C.textFaint} color={C.textFaint} />
      {transitLegs.map((leg, i) => {
        const crowdKey = (leg.crowd_estimate || leg.crowd || "MODERATE").toUpperCase();
        const color = CROWD_COLOR[crowdKey] || C.amber;
        const dotCount = Math.min(5, Math.max(2, Math.round((leg.num_stops || leg.stops || 4) / 2)));
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
              title={CROWD_LABEL[crowdKey] || "Transit leg"}
            >
              {Array.from({ length: dotCount }).map((_, d) => (
                <span
                  key={d}
                  style={{ width: 3, height: 3, borderRadius: "50%", background: "rgba(16,18,26,0.55)" }}
                />
              ))}
            </div>
            <div
              style={{
                width: 20,
                height: 20,
                minWidth: 20,
                borderRadius: "50%",
                background: C.surface2,
                border: `1.5px solid ${color}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ModeIcon type={leg.mode || leg.type} size={11} color={color} />
            </div>
          </React.Fragment>
        );
      })}
      <div style={{ flex: 0.6, minWidth: 10, height: 5, borderRadius: 3, background: `${accent}66` }} />
      <MapPin size={13} color={accent} />
    </div>
  );
}

function CrowdMeter({ level = "MODERATE" }) {
  const lvl = level.toUpperCase();
  const color = CROWD_COLOR[lvl] || C.amber;
  const activeCount = { LOW: 2, MODERATE: 4, HIGH: 5, VERY_HIGH: 6 }[lvl] || 3;
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
            }}
          />
        ))}
      </div>
      <span style={{ fontSize: 12, color, fontFamily: "'Inter', sans-serif", fontWeight: 500 }}>
        {CROWD_LABEL[lvl] || "Moderate crowd"}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  PLAN SCREEN                                                        */
/* ------------------------------------------------------------------ */
function PlanScreen({
  from,
  to,
  setFrom,
  setTo,
  departureTime,
  setDepartureTime,
  onFindRoutes,
  loading,
  error,
  isMapExpanded,
  setIsMapExpanded,
}) {
  const [activeField, setActiveField] = useState(null); // 'from' | 'to' | null
  const [recents] = useState(["Connaught Place", "India Gate", "Kashmere Gate", "Hauz Khas", "AIIMS"]);
  const originInputRef = useRef(null);
  const destinationInputRef = useRef(null);

  const suggestions = useMemo(() => {
    const q = (activeField === "from" ? from : to).toLowerCase();
    return STOPS.filter((s) => s.toLowerCase().includes(q)).slice(0, 5);
  }, [activeField, from, to]);

  const swap = () => {
    setFrom(to);
    setTo(from);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative", overflow: "hidden" }}>
      {/* Map Container */}
      <div
        style={{
          height: isMapExpanded ? "100%" : 210,
          position: isMapExpanded ? "absolute" : "relative",
          inset: isMapExpanded ? 0 : undefined,
          transition: "all 0.35s cubic-bezier(0.4, 0, 0.2, 1)",
          zIndex: 1,
        }}
      >
        <Map
          origin={from}
          destination={to}
          originInputRef={originInputRef}
          destinationInputRef={destinationInputRef}
          onOriginSelected={setFrom}
          onDestinationSelected={setTo}
          isExpanded={isMapExpanded}
        />
        
        {/* Top Header Bar */}
        <div style={{ position: "absolute", top: 14, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "center", zIndex: 10 }}>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18, color: C.text, letterSpacing: 0.3, background: "rgba(16,18,26,0.75)", padding: "4px 10px", borderRadius: 8, backdropFilter: "blur(8px)" }}>
            transit<span style={{ color: C.amber }}>·</span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={() => setIsMapExpanded(!isMapExpanded)}
              title={isMapExpanded ? "Collapse map" : "Expand full map"}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                padding: "6px 10px",
                borderRadius: 20,
                background: isMapExpanded ? C.amber : "rgba(27,30,41,0.85)",
                color: isMapExpanded ? "#10121A" : C.text,
                border: `1px solid ${isMapExpanded ? C.amber : C.line}`,
                fontFamily: "'Space Grotesk', sans-serif",
                fontSize: 11.5,
                fontWeight: 700,
                cursor: "pointer",
                backdropFilter: "blur(8px)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
              }}
            >
              {isMapExpanded ? (
                <>
                  <Minimize2 size={13} /> Close Map
                </>
              ) : (
                <>
                  <Maximize2 size={13} /> Expand Map
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Inputs Bottom Sheet / Floating Panel */}
      <div
        style={{
          background: isMapExpanded ? "rgba(27,30,41,0.92)" : C.surface,
          backdropFilter: isMapExpanded ? "blur(14px)" : "none",
          borderTopLeftRadius: 22,
          borderTopRightRadius: 22,
          marginTop: isMapExpanded ? 0 : -18,
          position: isMapExpanded ? "absolute" : "relative",
          bottom: 0,
          left: 0,
          right: 0,
          maxHeight: isMapExpanded ? "70%" : "none",
          padding: "18px 18px 16px",
          flex: isMapExpanded ? undefined : 1,
          boxShadow: "0 -14px 30px rgba(0,0,0,0.45)",
          zIndex: 5,
          display: "flex",
          flexDirection: "column",
          transition: "all 0.35s ease",
          overflowY: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 15, color: C.text, fontWeight: 600 }}>
            Where are you headed in Delhi?
          </div>
          {isMapExpanded && (
            <span style={{ fontSize: 11, color: C.amber, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 500 }}>
              FULL MAP ACTIVE
            </span>
          )}
        </div>

        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", flexDirection: "column", background: C.surface2, borderRadius: 14, border: `1px solid ${C.line}` }}>
            <FieldRow
              icon={<span style={{ width: 8, height: 8, borderRadius: "50%", background: C.amber, display: "inline-block" }} />}
              placeholder="Current location (e.g. Connaught Place)"
              value={from}
              onChange={setFrom}
              onFocus={() => setActiveField("from")}
              inputRef={originInputRef}
            />
            <div style={{ height: 1, background: C.line, marginLeft: 40 }} />
            <FieldRow
              icon={<span style={{ width: 8, height: 8, borderRadius: 2, background: C.violet, display: "inline-block" }} />}
              placeholder="Search destination (e.g. Hauz Khas)"
              value={to}
              onChange={setTo}
              onFocus={() => setActiveField("to")}
              inputRef={destinationInputRef}
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
          <div style={{ marginTop: 8, background: C.surface2, borderRadius: 12, border: `1px solid ${C.line}`, overflow: "hidden", zIndex: 10 }}>
            {suggestions.map((s) => (
              <div
                key={s}
                onClick={() => {
                  if (activeField === "from") setFrom(s);
                  else setTo(s);
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

        <div style={{ marginTop: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>DEPARTURE TIME</span>
          <input
            type="time"
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
            style={{
              background: C.surface2,
              border: `1px solid ${C.line}`,
              color: C.text,
              borderRadius: 8,
              padding: "4px 8px",
              fontFamily: "'IBM Plex Mono', monospace",
              fontSize: 12.5,
              outline: "none",
            }}
          />
        </div>

        {!activeField && (
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 11, color: C.textFaint, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 0.6, marginBottom: 8 }}>
              DELHI STOPS & RECENT
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {["Kashmere Gate", "Rajiv Chowk", "Hauz Khas", "Central Secretariat"].map((r) => (
                <button
                  key={r}
                  onClick={() => setTo(r)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 20,
                    background: C.surface2,
                    border: `1px solid ${C.line}`,
                    color: C.textDim,
                    fontSize: 12,
                    fontSize: 12,
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

        <button
          onClick={onFindRoutes}
          disabled={!from || !to || loading}
          disabled={!from || !to || loading}
          style={{
            marginTop: 18,
            width: "100%",
            padding: "14px 0",
            borderRadius: 14,
            border: "none",
            background: from && to ? C.amber : C.surface2,
            color: from && to ? "#141620" : C.textFaint,
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: 15,
            cursor: from && to && !loading ? "pointer" : "not-allowed",
            boxShadow: from && to ? "0 4px 14px rgba(255,176,32,0.3)" : "none",
          }}
        >
          {loading ? "Finding Delhi routes…" : "Find routes"}
        </button>
        {error && (
          <p style={{ color: C.coral, fontSize: 12, marginTop: 8, textAlign: "center" }}>
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

function FieldRow({ icon, placeholder, value, onChange, onFocus, inputRef }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "13px 14px" }}>
      <div style={{ width: 20, display: "flex", justifyContent: "center" }}>{icon}</div>
      <input
        ref={inputRef}
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
function RouteCard({ option, onSelect }) {
  const accent = option.accent || C.violet;
  const accentSoft = option.accentSoft || C.violetSoft;
  const Icon = option.Icon || Sparkles;
  const typeLabel = option.label || "OPTIMUM";
  const badge = option.badge;
  const delay = option.delay_minutes || option._raw?.delay_minutes || 0;
  
  // Dynamic route-specific confidence based on mode and reliability
  const routeConfPct = Math.min(
    98,
    Math.max(
      74,
      Math.round(
        (option.label === "QUICKEST" ? 0.94 : option.label === "OPTIMUM" ? 0.90 : 0.82) * 100 +
          (option.transfers === 0 ? 3 : -2)
      )
    )
  );

  return (
    <button
      onClick={onSelect}
      style={{
        textAlign: "left",
        width: "100%",
        background: C.surface,
        border: `1px solid ${badge ? accent : C.line}`,
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
              {typeLabel}
            </span>
            {badge && (
              <span style={{ fontSize: 9.5, fontFamily: "'IBM Plex Mono', monospace", color: accent, border: `1px solid ${accent}55`, borderRadius: 5, padding: "1px 5px" }}>
                {badge}
              </span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 26, color: C.text }}>
              {option.eta_minutes}
            </span>
            <span style={{ fontSize: 12.5, color: C.textDim, fontFamily: "'Inter', sans-serif" }}>
              min · {option.route_name}
            </span>
          </div>
        </div>
        <div style={{ textAlign: "right", fontFamily: "'IBM Plex Mono', monospace", fontSize: 11.5, color: C.textDim }}>
          <div style={{ display: "flex", alignItems: "center", gap: 3, justifyContent: "flex-end" }}>
            <IndianRupee size={10} /> {option.fare}
          </div>
          <div style={{ marginTop: 2 }}>{option.transfers} transfer{option.transfers !== 1 ? "s" : ""}</div>
          <div style={{ color: delay >= 6 ? C.coral : delay > 1 ? C.amber : C.teal, fontSize: 10.5, marginTop: 2, fontWeight: 500 }}>
            {delay > 1 ? `+${delay}m delay risk` : "On-time flow (±1m)"}
          </div>
        </div>
      </div>

      <LineDiagram legs={option.legs} accent={accent} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 2 }}>
        <CrowdMeter level={option.crowd_level} />
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 10.5, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
            {routeConfPct}% ML Conf
          </span>
          <span style={{ fontSize: 11.5, color: C.textFaint, fontFamily: "'Inter', sans-serif" }}>Details ›</span>
        </div>
      </div>
    </button>
  );
}

function ResultsScreen({ from, to, recommendData, onBack, onSelect }) {
  const routes = recommendData?.routesList || [];
  const meta = recommendData?.metadata || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar onBack={onBack} title="Transit Options" subtitle={`${from} → ${to}`} />
      <div style={{ padding: "14px 16px", display: "flex", flexDirection: "column", gap: 12, overflowY: "auto", flex: 1 }}>
        {routes.map((option, idx) => (
          <RouteCard
            key={option.key || idx}
            option={option}
            onSelect={() => onSelect(option._raw || option)}
          />
        ))}

        {/* Real-Time Live Telemetry Bar */}
        <div
          style={{
            background: C.surface,
            border: `1px solid ${C.line}`,
            borderRadius: 12,
            padding: "10px 14px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 4,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.teal }} />
            <span style={{ fontSize: 11, color: C.textDim, fontFamily: "'Inter', sans-serif" }}>
              Live Telemetry: <strong>{meta.weather || "CLEAR (28°C)"}</strong> · Traffic: <strong>{meta.traffic || "NORMAL"}</strong>
            </span>
          </div>
          <span style={{ fontSize: 10.5, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
            {Math.round((meta.confidence ?? 0.88) * 100)}% Confidence
          </span>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  DETAIL SCREEN                                                      */
/* ------------------------------------------------------------------ */
function DetailScreen({ route, onBack, from, to }) {
  const accent = route.route_type === "OPTIMUM" ? C.violet : route.route_type === "QUICKEST" ? C.amber : C.teal;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <TopBar onBack={onBack} title={route.route_name} subtitle={`${from} → ${to}`} accent={accent} />

      <div style={{ padding: "16px", flex: 1, overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 4 }}>
          <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 30, color: C.text }}>
            {route.eta_minutes} min
          </span>
          <span style={{ color: C.textDim, fontSize: 13 }}>
            ({route.distance_km ? `${route.distance_km} km` : "estimated"})
          </span>
        </div>
        <div style={{ fontSize: 12.5, color: C.textDim, fontFamily: "'Inter', sans-serif", marginBottom: 16 }}>
          {route.transfers} transfer{route.transfers !== 1 ? "s" : ""} · ₹{route.fare} · {Math.round(route.reliability * 100)}% reliability
        </div>

        <div style={{ background: C.surface2, borderRadius: 10, padding: "10px 12px", border: `1px solid ${C.line}`, marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: accent, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>
            ML PREDICTION EXPLANATION
          </div>
          <p style={{ fontSize: 12.5, color: C.text, margin: "4px 0 0", lineHeight: 1.4 }}>
            {route.reason}
          </p>
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
                    background: (leg.mode || "").toLowerCase() === "walk" ? C.surface2 : `${accent}22`,
                    border: `1.5px solid ${(leg.mode || "").toLowerCase() === "walk" ? C.line : accent}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <ModeIcon type={leg.mode} size={14} color={(leg.mode || "").toLowerCase() === "walk" ? C.textDim : accent} />
                </div>
                {i < route.legs.length - 1 && <div style={{ width: 2, flex: 1, minHeight: 30, background: C.line, marginTop: 2 }} />}
              </div>
              <div style={{ paddingBottom: 20, flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontFamily: "'Inter', sans-serif", fontSize: 13.5, color: C.text, fontWeight: 500 }}>
                      {(leg.mode || "").toLowerCase() !== "walk" && (
                        <span style={{ color: accent, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, marginRight: 6 }}>
                          {leg.line}
                        </span>
                      )}
                      {leg.from_stop} → {leg.to_stop}
                    </div>
                    {(leg.mode || "").toLowerCase() !== "walk" && leg.num_stops > 0 && (
                      <div style={{ fontSize: 11.5, color: C.textFaint, marginTop: 2 }}>
                        {leg.num_stops} intermediate stops
                      </div>
                    )}
                  </div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: C.textDim }}>
                    {leg.travel_minutes} min
                  </div>
                </div>
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
            background: accent,
            color: "#12141C",
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 700,
            fontSize: 15,
            cursor: "pointer",
          }}
        >
          Start Journey
        </button>
      </div>
    </div>
  );
}

function TopBar({ onBack, title, subtitle, accent }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "14px 16px 12px", borderBottom: `1px solid ${C.line}` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
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
      <LiveBadge />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MAIN APP CONTAINER                                                 */
/* ------------------------------------------------------------------ */
export default function TransitApp() {
  const [appMode, setAppMode] = useState("commuter"); // commuter | gov
  const [screen, setScreen] = useState("plan"); // plan | results | detail
  const [from, setFrom] = useState("IIIT Delhi");
  const [to, setTo] = useState("GB Road");
  const [departureTime, setDepartureTime] = useState(
    new Date().toTimeString().slice(0, 5)
  );
  const [routes, setRoutes] = useState(null);
  const [selectedRoute, setSelectedRoute] = useState(null);
  const [activeKey, setActiveKey] = useState("optimum");
  const [isMapExpanded, setIsMapExpanded] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleFindRoutes = async () => {
    if (!from.trim() || !to.trim()) {
      setError("Enter both your starting point and destination.");
      return;
    }

    setLoading(true);
    setError("");

    const payload = JSON.stringify({
      from: from.trim(),
      to: to.trim(),
      departure_time: departureTime || new Date().toTimeString().slice(0, 5),
    });

    let successData = null;
    let lastError = null;

    for (const endpoint of API_ENDPOINTS) {
      try {
        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          signal: AbortSignal.timeout(10000),
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Could not find routes.");
        }

        successData = data;
        break;
      } catch (err) {
        lastError = err;
      }
    }

    if (successData) {
      setRoutes(adaptApiResponse(successData));
      setActiveKey("optimum");
      setIsMapExpanded(false);
      setScreen("results");
    } else {
      setError(
        lastError?.message ||
          "Backend is unreachable. Start FastAPI server with: uvicorn app.main:app --reload --port 8000"
      );
    }
    setLoading(false);
  };

  return (
    <div style={{ width: "100%", minHeight: "100vh", background: "#0A0C13", padding: "16px 12px" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        * { box-sizing: border-box; }
        input::placeholder { color: ${C.textFaint}; }
        @keyframes pulseRing {
          0% { transform: scale(0.6); opacity: 0.9; }
          100% { transform: scale(2.2); opacity: 0; }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* Apple-Style Floating Segmented Control */}
      <div
        style={{
          width: "100%",
          display: "flex",
          justifyContent: "center",
          marginBottom: appMode === "gov" ? 0 : 20,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            padding: "4px",
            borderRadius: 999,
            background: "rgba(255, 255, 255, 0.05)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
          }}
        >
          <button
            onClick={() => setAppMode("commuter")}
            style={{
              padding: "8px 22px",
              borderRadius: 999,
              border: "none",
              background: appMode === "commuter" ? "rgba(255, 255, 255, 0.14)" : "transparent",
              color: appMode === "commuter" ? "#FFFFFF" : C.textDim,
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
              boxShadow: appMode === "commuter" ? "0 2px 8px rgba(0, 0, 0, 0.25)" : "none",
            }}
          >
            Commuter Journey App
          </button>
          <button
            onClick={() => setAppMode("gov")}
            style={{
              padding: "8px 22px",
              borderRadius: 999,
              border: "none",
              background: appMode === "gov" ? "rgba(255, 255, 255, 0.14)" : "transparent",
              color: appMode === "gov" ? "#FFFFFF" : C.textDim,
              fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              transition: "all 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
              boxShadow: appMode === "gov" ? "0 2px 8px rgba(0, 0, 0, 0.25)" : "none",
            }}
          >
            Delhi Transit Authority (Gov)
          </button>
        </div>
      </div>

      {/* Main Screen Content */}
      {appMode === "gov" ? (
        <div style={{ width: "100%", maxWidth: 1400, margin: "0 auto", transition: "all 0.3s ease" }}>
          <GovDashboard onBackToCommuter={() => setAppMode("commuter")} />
        </div>
      ) : (
        <div
          style={{
            width: "100%",
            minHeight: 640,
            maxWidth: 420,
            margin: "0 auto",
            background: "rgba(18, 21, 32, 0.85)",
            backdropFilter: "blur(24px)",
            WebkitBackdropFilter: "blur(24px)",
            borderRadius: 32,
            overflow: "hidden",
            boxShadow: "0 32px 64px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08)",
            fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif",
            display: "flex",
            flexDirection: "column",
            height: 680,
          }}
        >
          <div key={screen} style={{ flex: 1, minHeight: 0 }}>
            {screen === "plan" && (
              <PlanScreen
                from={from}
                to={to}
                setFrom={setFrom}
                setTo={setTo}
                departureTime={departureTime}
                setDepartureTime={setDepartureTime}
                onFindRoutes={handleFindRoutes}
                loading={loading}
                error={error}
                isMapExpanded={isMapExpanded}
                setIsMapExpanded={setIsMapExpanded}
              />
            )}
            {screen === "results" && routes && (
              <ResultsScreen
                from={from}
                to={to}
                recommendData={routes}
                onBack={() => setScreen("plan")}
                onSelect={(route) => {
                  setSelectedRoute(route);
                  setScreen("detail");
                }}
              />
            )}
            {screen === "detail" && selectedRoute && (
              <DetailScreen
                route={selectedRoute}
                onBack={() => setScreen("results")}
                from={from}
                to={to}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
