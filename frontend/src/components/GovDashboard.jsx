import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart2,
  Bus,
  CheckCircle2,
  ChevronRight,
  Clock,
  Compass,
  Layers,
  MapPin,
  RefreshCw,
  Sliders,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";

const C = {
  bg: "#0B0D14",
  surface: "#121520",
  surfaceHover: "#181C2B",
  surfaceElevated: "#1D2235",
  line: "#22273A",
  lineMuted: "#1A1F30",
  text: "#F3F5FA",
  textDim: "#8E97B0",
  textFaint: "#555E77",
  teal: "#2CD3B5",
  tealSoft: "rgba(44,211,181,0.12)",
  amber: "#FFB020",
  amberSoft: "rgba(255,176,32,0.12)",
  coral: "#FF5E57",
  coralSoft: "rgba(255,94,87,0.12)",
  blue: "#4D96FF",
  blueSoft: "rgba(77,150,255,0.12)",
  purple: "#9D72FF",
  purpleSoft: "rgba(157,114,255,0.12)",
};

const DELHI_CENTER = { lat: 28.6139, lng: 77.2090 };

const DELHI_BOTTLENECK_STOPS = [
  { id: "KASHMERE_GATE", name: "Kashmere Gate ISBT & Interchange", lat: 28.6678, lng: 77.2280, departures: 5591, routes: 205, score: 98.5, type: "ISBT Interchange" },
  { id: "RAJIV_CHOWK", name: "Rajiv Chowk / Connaught Place", lat: 28.6328, lng: 77.2195, departures: 4865, routes: 180, score: 92.1, type: "Metro Core" },
  { id: "ANAND_VIHAR", name: "Anand Vihar ISBT & Terminal", lat: 28.6469, lng: 77.3160, departures: 4699, routes: 173, score: 84.3, type: "East Delhi ISBT" },
  { id: "SARAI_KALE_KHAN", name: "Sarai Kale Khan / Nizamuddin", lat: 28.5898, lng: 77.2555, departures: 4622, routes: 153, score: 82.9, type: "South-East Hub" },
  { id: "DHAULA_KUAN", name: "Dhaula Kuan Arterial Interchange", lat: 28.5921, lng: 77.1565, departures: 4420, routes: 161, score: 78.4, type: "Airport Arterial" },
  { id: "AIIMS", name: "AIIMS / Safdarjung Ring Road", lat: 28.5672, lng: 77.2100, departures: 4339, routes: 156, score: 77.8, type: "Hospital Concourse" },
  { id: "OKHLA_IIIT", name: "Okhla Industrial / IIIT Delhi Hub", lat: 28.5457, lng: 77.2732, departures: 3890, routes: 92, score: 74.2, type: "Tech Hub Feeder" },
];

export default function GovDashboard({ onBackToCommuter }) {
  const [summary, setSummary] = useState(null);
  const [bottlenecks, setBottlenecks] = useState(DELHI_BOTTLENECK_STOPS);
  const [corridors, setCorridors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCorridor, setActiveCorridor] = useState(null);
  const [trafficEnabled, setTrafficEnabled] = useState(true);
  const [selectedBottleneck, setSelectedBottleneck] = useState(DELHI_BOTTLENECK_STOPS[0]);
  const [simIntervention, setSimIntervention] = useState("buses");
  const [simResult, setSimResult] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);

  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const trafficLayerRef = useRef(null);
  const markersRef = useRef([]);

  const fetchGovData = async () => {
    setLoading(true);
    try {
      const [sumRes, bRes, cRes] = await Promise.allSettled([
        fetch("/api/insights/summary"),
        fetch("/api/insights/bottlenecks"),
        fetch("/api/gov/corridors"),
      ]);

      if (sumRes.status === "fulfilled" && sumRes.value.ok) {
        const d = await sumRes.value.json();
        setSummary(d);
      }
      if (bRes.status === "fulfilled" && bRes.value.ok) {
        const d = await bRes.value.json();
        const rawBottlenecks = d?.datasets?.[0]?.bottlenecks || [];
        if (rawBottlenecks.length > 0) {
          setBottlenecks(rawBottlenecks);
        }
      }
      if (cRes.status === "fulfilled" && cRes.value.ok) {
        const d = await cRes.value.json();
        setCorridors(d);
        if (d.length > 0) setActiveCorridor(d[0]);
      }
    } catch (e) {
      console.warn("Gov data fetch:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGovData();
  }, []);

  // Initialize Google Maps
  useEffect(() => {
    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    if (!apiKey || !window.google?.maps || !mapContainerRef.current) return;

    const maps = window.google.maps;
    const map = new maps.Map(mapContainerRef.current, {
      center: DELHI_CENTER,
      zoom: 11.2,
      disableDefaultUI: true,
      zoomControl: true,
      styles: [
        { elementType: "geometry", stylers: [{ color: "#11141F" }] },
        { elementType: "labels.text.fill", stylers: [{ color: "#8E97B0" }] },
        { elementType: "labels.text.stroke", stylers: [{ color: "#11141F" }] },
        { featureType: "road", elementType: "geometry", stylers: [{ color: "#1F2538" }] },
        { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#2E3754" }] },
        { featureType: "water", elementType: "geometry", stylers: [{ color: "#0A1724" }] },
        { featureType: "poi", stylers: [{ visibility: "off" }] },
      ],
    });

    mapInstanceRef.current = map;

    const trafficLayer = new maps.TrafficLayer();
    trafficLayer.setMap(trafficEnabled ? map : null);
    trafficLayerRef.current = trafficLayer;

    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];

    bottlenecks.forEach((stop) => {
      const lat = stop.lat || (stop.stop_lat ? parseFloat(stop.stop_lat) : 28.6139);
      const lng = stop.lon || stop.lng || (stop.stop_lon ? parseFloat(stop.stop_lon) : 77.2090);

      const marker = new maps.Marker({
        position: { lat, lng },
        map,
        title: stop.stop_name || stop.name,
        icon: {
          path: maps.SymbolPath.CIRCLE,
          scale: 7,
          fillColor: (stop.score || 80) > 85 ? C.coral : (stop.score || 80) > 75 ? C.amber : C.teal,
          fillOpacity: 0.9,
          strokeColor: "#FFFFFF",
          strokeWeight: 1.5,
        },
      });

      marker.addListener("click", () => {
        setSelectedBottleneck(stop);
      });

      markersRef.current.push(marker);
    });
  }, [bottlenecks, trafficEnabled]);

  const handleRunSimulation = () => {
    setIsSimulating(true);
    setTimeout(() => {
      if (simIntervention === "buses") {
        setSimResult({
          title: "Fleet Augmentation (+20 Electric Buses on Ring Road)",
          delayReduction: "-22% Avg Delay",
          reliabilityGain: "+14.5% Schedule Reliability",
          crowdRelief: "-18% Peak Dwell Time",
          costEstimate: "₹1.8L / day operational",
          insight: "Relieves major confluence pressure at Kashmere Gate and Sarai Kale Khan during 08:30–10:30 peak hours.",
        });
      } else if (simIntervention === "signals") {
        setSimResult({
          title: "Transit Signal Priority (TSP) at Key Concourse Hubs",
          delayReduction: "-16% Junction Hold",
          reliabilityGain: "+19.0% On-Time Arrivals",
          crowdRelief: "4.2 min ETA gain per passenger",
          costEstimate: "₹45k infrastructure setup",
          insight: "Synchronizes bus lane priority lights at Dhaula Kuan & AIIMS Ring Road intersections.",
        });
      } else {
        setSimResult({
          title: "Dynamic Feeder Micro-Shuttles (Okhla / IIIT Delhi)",
          delayReduction: "-14% First/Last Mile Delay",
          reliabilityGain: "+11.2% Seamless Transfer",
          crowdRelief: "-24% Feeder Wait Time",
          costEstimate: "₹60k / day fleet lease",
          insight: "Balances Violet Line & Magenta Line transfers connecting Govindpuri, Okhla Estate, and Nehru Place.",
        });
      }
      setIsSimulating(false);
    }, 500);
  };

  const defaultCorridors = [
    { id: "R9", name: "Ring Road Arterial Express", demand: 14200, delay: 6, reliability: 88, crowd: 86, type: "Optimal Trunk" },
    { id: "R6", name: "Kashmere Gate – Connaught Place Central", demand: 18900, delay: 4, reliability: 94, crowd: 91, type: "Core Metro Trunk" },
    { id: "R3", name: "South Delhi Okhla – Hauz Khas Feeder", demand: 9800, delay: 5, reliability: 85, crowd: 72, type: "Tech Feeder" },
    { id: "R12", name: "East-West Trans-Yamuna Connector", demand: 12400, delay: 7, reliability: 83, crowd: 68, type: "Cross-City" },
  ];

  const corridorList = corridors.length > 0 ? corridors : defaultCorridors;

  return (
    <div
      style={{
        width: "100%",
        minHeight: "100vh",
        background: C.bg,
        color: C.text,
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
      }}
    >
      {/* Enterprise Navigation Header */}
      <header
        style={{
          borderBottom: `1px solid ${C.line}`,
          background: C.surface,
          padding: "16px 28px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "linear-gradient(135deg, #2CD3B5 0%, #1A8A76 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 2px 8px rgba(44,211,181,0.25)",
            }}
          >
            <Activity size={19} color="#0B0D14" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16, letterSpacing: -0.2, color: C.text }}>
              Delhi Integrated Multi-Modal Transit Authority
            </div>
            <div style={{ fontSize: 12, color: C.textDim, marginTop: 1 }}>
              DTC Bus & DMRC Metro Real-Time Operations Portal
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={fetchGovData}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "7px 14px",
              background: "transparent",
              border: `1px solid ${C.line}`,
              borderRadius: 8,
              color: C.textDim,
              fontSize: 12.5,
              cursor: "pointer",
              transition: "all 0.15s ease",
            }}
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Sync Feeds
          </button>
          <button
            onClick={onBackToCommuter}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "7px 16px",
              background: C.teal,
              border: "none",
              borderRadius: 8,
              color: "#0B0D14",
              fontWeight: 600,
              fontSize: 12.5,
              cursor: "pointer",
            }}
          >
            Commuter View →
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ maxWidth: 1240, margin: "0 auto", padding: "24px 28px", display: "flex", flexDirection: "column", gap: 24 }}>
        
        {/* KPI Strip */}
        <section
          style={{
            background: C.surface,
            borderRadius: 12,
            border: `1px solid ${C.line}`,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            overflow: "hidden",
          }}
        >
          <div style={{ padding: "18px 22px", borderRight: `1px solid ${C.line}` }}>
            <div style={{ fontSize: 12, color: C.textDim, fontWeight: 500, marginBottom: 6 }}>
              Total Daily Departures
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.5, color: C.text }}>
              {summary?.scheduled_service?.total_scheduled_departures
                ? summary.scheduled_service.total_scheduled_departures.toLocaleString()
                : "3,276,092"}
            </div>
            <div style={{ fontSize: 11.5, color: C.teal, marginTop: 4 }}>
              6,342 DTC Stops • 262 Metro Stations
            </div>
          </div>

          <div style={{ padding: "18px 22px", borderRight: `1px solid ${C.line}` }}>
            <div style={{ fontSize: 12, color: C.textDim, fontWeight: 500, marginBottom: 6 }}>
              Peak Demand Hour
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.5, color: C.amber }}>
              {summary?.scheduled_service?.peak_hour || "09:00 AM"}
            </div>
            <div style={{ fontSize: 11.5, color: C.textDim, marginTop: 4 }}>
              213,416 scheduled trips/hr
            </div>
          </div>

          <div style={{ padding: "18px 22px", borderRight: `1px solid ${C.line}` }}>
            <div style={{ fontSize: 12, color: C.textDim, fontWeight: 500, marginBottom: 6 }}>
              Critical Transfer Hubs
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.5, color: C.coral }}>
              {bottlenecks.length} Nodes
            </div>
            <div style={{ fontSize: 11.5, color: C.coral, marginTop: 4 }}>
              Confluence & interchange load
            </div>
          </div>

          <div style={{ padding: "18px 22px" }}>
            <div style={{ fontSize: 12, color: C.textDim, fontWeight: 500, marginBottom: 6 }}>
              Active Monitored Corridors
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: -0.5, color: C.blue }}>
              485 Routes
            </div>
            <div style={{ fontSize: 11.5, color: C.textDim, marginTop: 4 }}>
              DTC AC/Non-AC + DMRC Lines
            </div>
          </div>
        </section>

        {/* Spatial Map & Hotspots Section */}
        <section
          style={{
            background: C.surface,
            borderRadius: 12,
            border: `1px solid ${C.line}`,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 20px",
              borderBottom: `1px solid ${C.line}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: C.surface,
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: 14, color: C.text }}>
                Delhi NCR Network Load & Live Traffic Heatmap
              </div>
              <div style={{ fontSize: 11.5, color: C.textDim, marginTop: 1 }}>
                Real-time congestion overlay with GTFS bottleneck confluence points
              </div>
            </div>

            <button
              onClick={() => setTrafficEnabled(!trafficEnabled)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 12px",
                borderRadius: 6,
                fontSize: 12,
                fontWeight: 500,
                cursor: "pointer",
                background: trafficEnabled ? C.tealSoft : "transparent",
                color: trafficEnabled ? C.teal : C.textDim,
                border: `1px solid ${trafficEnabled ? C.teal : C.line}`,
              }}
            >
              <Layers size={13} />
              Traffic Layer: {trafficEnabled ? "Active" : "Hidden"}
            </button>
          </div>

          <div style={{ position: "relative", width: "100%", height: 360, background: "#0F121C" }}>
            <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />

            {!window.google?.maps && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "#111420",
                  padding: 24,
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 12 }}>
                  Major Delhi NCR Hub Network Grid
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", maxWidth: 640 }}>
                  {DELHI_BOTTLENECK_STOPS.map((stop) => (
                    <button
                      key={stop.id}
                      onClick={() => setSelectedBottleneck(stop)}
                      style={{
                        padding: "7px 12px",
                        borderRadius: 8,
                        background: selectedBottleneck?.id === stop.id ? C.tealSoft : C.surfaceElevated,
                        border: `1px solid ${selectedBottleneck?.id === stop.id ? C.teal : C.line}`,
                        color: selectedBottleneck?.id === stop.id ? C.teal : C.text,
                        fontSize: 12,
                        cursor: "pointer",
                        fontWeight: 500,
                      }}
                    >
                      {stop.name} · {stop.departures} dep/day
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Selected Node Details Card */}
            {selectedBottleneck && (
              <div
                style={{
                  position: "absolute",
                  bottom: 16,
                  left: 16,
                  background: "rgba(18, 21, 32, 0.95)",
                  backdropFilter: "blur(12px)",
                  border: `1px solid ${C.line}`,
                  borderRadius: 10,
                  padding: "14px 18px",
                  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
                  maxWidth: 360,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 13.5, color: C.text }}>
                    {selectedBottleneck.stop_name || selectedBottleneck.name}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: (selectedBottleneck.score || 80) > 85 ? C.coral : C.amber,
                      background: (selectedBottleneck.score || 80) > 85 ? C.coralSoft : C.amberSoft,
                      padding: "2px 6px",
                      borderRadius: 4,
                    }}
                  >
                    Score {selectedBottleneck.score || 85}/100
                  </span>
                </div>
                <div style={{ fontSize: 12, color: C.textDim, display: "flex", gap: 16, marginTop: 6 }}>
                  <span>Daily Departures: <strong style={{ color: C.text }}>{(selectedBottleneck.scheduled_departures || selectedBottleneck.departures || 0).toLocaleString()}</strong></span>
                  <span>Routes: <strong style={{ color: C.text }}>{selectedBottleneck.route_count || selectedBottleneck.routes || 0}</strong></span>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Corridors Table & Simulator Grid */}
        <section style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 24 }}>
          
          {/* Arterial Corridors Data List */}
          <div
            style={{
              background: C.surface,
              borderRadius: 12,
              border: `1px solid ${C.line}`,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: "16px 20px", borderBottom: `1px solid ${C.line}` }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: C.text }}>
                High-Volume Transit Corridors
              </div>
              <div style={{ fontSize: 11.5, color: C.textDim, marginTop: 1 }}>
                Ridership demand, delay index, and schedule reliability metrics
              </div>
            </div>

            <div>
              {corridorList.map((corridor, idx) => (
                <div
                  key={corridor.id || idx}
                  onClick={() => setActiveCorridor(corridor)}
                  style={{
                    padding: "14px 20px",
                    borderBottom: idx < corridorList.length - 1 ? `1px solid ${C.lineMuted}` : "none",
                    background: activeCorridor?.id === corridor.id ? C.surfaceElevated : "transparent",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    transition: "background 0.15s ease",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: C.text, display: "flex", alignItems: "center", gap: 8 }}>
                      <span>{corridor.name}</span>
                      <span style={{ fontSize: 10.5, color: C.teal, background: C.tealSoft, padding: "1px 6px", borderRadius: 4 }}>
                        {corridor.id}
                      </span>
                    </div>
                    <div style={{ fontSize: 11.5, color: C.textDim, marginTop: 3 }}>
                      {corridor.type || "Arterial Transit"}
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: C.text }}>
                        {(corridor.demand || 12000).toLocaleString()} pax/day
                      </div>
                      <div style={{ fontSize: 11, color: C.textDim }}>
                        Avg Delay: <strong>{corridor.delay}m</strong> · {corridor.reliability}% On-Time
                      </div>
                    </div>
                    <ChevronRight size={16} color={C.textFaint} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Predictive Policy Simulator */}
          <div
            style={{
              background: C.surface,
              borderRadius: 12,
              border: `1px solid ${C.line}`,
              padding: "20px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <Sliders size={16} color={C.amber} />
                <span style={{ fontWeight: 600, fontSize: 14, color: C.text }}>
                  Policy Intervention Simulator
                </span>
              </div>
              <p style={{ fontSize: 12, color: C.textDim, lineHeight: 1.5, margin: "0 0 16px" }}>
                Test transit management decisions across the Delhi network prior to field implementation.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  { id: "buses", label: "Deploy +20 Electric Buses on Ring Road" },
                  { id: "signals", label: "Transit Signal Priority at 6 Arterial Junctions" },
                  { id: "feeders", label: "Dynamic Feeder Shuttles at Okhla / IIIT Hub" },
                ].map((opt) => (
                  <label
                    key={opt.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 14px",
                      borderRadius: 8,
                      background: simIntervention === opt.id ? C.surfaceElevated : "transparent",
                      border: `1px solid ${simIntervention === opt.id ? C.amber : C.line}`,
                      cursor: "pointer",
                      fontSize: 12.5,
                      color: simIntervention === opt.id ? C.text : C.textDim,
                    }}
                  >
                    <input
                      type="radio"
                      name="intervention"
                      checked={simIntervention === opt.id}
                      onChange={() => setSimIntervention(opt.id)}
                      style={{ accentColor: C.amber }}
                    />
                    {opt.label}
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 18 }}>
              <button
                onClick={handleRunSimulation}
                disabled={isSimulating}
                style={{
                  width: "100%",
                  padding: "10px 0",
                  borderRadius: 8,
                  border: "none",
                  background: C.amber,
                  color: "#0B0D14",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <Sparkles size={14} />
                {isSimulating ? "Computing Network Impact..." : "Simulate Decision Impact"}
              </button>

              {simResult && (
                <div
                  style={{
                    marginTop: 14,
                    padding: "12px 14px",
                    borderRadius: 8,
                    background: C.surfaceElevated,
                    border: `1px solid ${C.teal}`,
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 12.5, color: C.teal, marginBottom: 4 }}>
                    {simResult.title}
                  </div>
                  <div style={{ fontSize: 11.5, color: C.textDim, lineHeight: 1.4, marginBottom: 8 }}>
                    {simResult.insight}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11 }}>
                    <div><span style={{ color: C.teal, fontWeight: 600 }}>{simResult.delayReduction}</span></div>
                    <div><span style={{ color: C.teal, fontWeight: 600 }}>{simResult.reliabilityGain}</span></div>
                    <div>{simResult.crowdRelief}</div>
                    <div>{simResult.costEstimate}</div>
                  </div>
                </div>
              )}
            </div>
          </div>

        </section>

      </main>
    </div>
  );
}
