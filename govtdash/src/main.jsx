import React, { useMemo, useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_BASE = "http://localhost:8000/api";

const initialStops = [
  { id:'nitk', name:'NITK Campus', x:10, y:69, crowd:42, pax:180, peak:'08:30 AM', routes:2, delay:2, status:'NORMAL' },
  { id:'surathkal', name:'Surathkal', x:25, y:53, crowd:68, pax:290, peak:'08:45 AM', routes:3, delay:4, status:'MODERATE' },
  { id:'kuloor', name:'Kuloor', x:43, y:58, crowd:84, pax:410, peak:'09:00 AM', routes:4, delay:6, status:'HIGH' },
  { id:'hampankatta', name:'Hampankatta', x:62, y:42, crowd:93, pax:520, peak:'09:00 AM', routes:6, delay:12, status:'CRITICAL' },
  { id:'kankanady', name:'Kankanady', x:70, y:66, crowd:82, pax:430, peak:'09:15 AM', routes:5, delay:8, status:'HIGH' },
  { id:'kadri', name:'Kadri', x:81, y:31, crowd:64, pax:310, peak:'09:20 AM', routes:3, delay:4, status:'MODERATE' },
  { id:'central', name:'Mangaluru Central', x:91, y:47, crowd:71, pax:340, peak:'09:30 AM', routes:5, delay:5, status:'MODERATE' },
];

const fallbackRoutes = [
  { id:'R9', name:'Hampankatta Corridor', color:'purple', time:35, demand:8420, crowd:87, delay:8, reliability:82, revenue:182000, transfers:2, type:'OPTIMAL NETWORK OPTION', score:91, path:['nitk','surathkal','kuloor','hampankatta','kadri','central'] },
  { id:'R6', name:'Coastal Express Corridor', color:'teal', time:44, demand:3210, crowd:48, delay:2, reliability:94, revenue:121000, transfers:1, type:'LOWEST CROWDING OPTION', score:88, path:['nitk','surathkal','kuloor','kankanady','central'] },
  { id:'R3', name:'Central Connector', color:'amber', time:32, demand:4820, crowd:91, delay:11, reliability:78, revenue:196000, transfers:2, type:'FASTEST NETWORK OPTION', score:86, path:['nitk','surathkal','hampankatta','central'] },
  { id:'R12', name:'Kadri Link', color:'blue', time:41, demand:2890, crowd:41, delay:3, reliability:96, revenue:108000, transfers:1, type:'ALTERNATIVE', score:84, path:['nitk','kuloor','kankanady','kadri','central'] },
];

const defaultDemandByTime = [
  ['06 AM',32],['07 AM',44],['08 AM',68],['09 AM',96],['10 AM',86],['11 AM',61],['12 PM',48],['01 PM',42],['02 PM',38],['03 PM',44],['04 PM',59],['05 PM',77],['06 PM',92],['07 PM',81],['08 PM',60]
];

const peakData = {
  '08:00 – 10:00 AM': { load:74, delay:7, demand:612, factor:1 },
  '10:00 AM – 12:00 PM': { load:58, delay:4, demand:398, factor:.82 },
  '04:00 – 06:00 PM': { load:79, delay:9, demand:648, factor:1.08 },
  '06:00 – 08:00 PM': { load:72, delay:8, demand:584, factor:.96 },
};

function App(){
  const [page,setPage] = useState('overview');
  const [from,setFrom] = useState('Kashmere Gate');
  const [to,setTo] = useState('Rajiv Chowk');
  const [analyzed,setAnalyzed] = useState(false);
  const [routesList, setRoutesList] = useState(fallbackRoutes);
  const [selectedRoute,setSelectedRoute] = useState('R9');
  const [selectedStop,setSelectedStop] = useState(null);
  const [layer,setLayer] = useState('all');
  const [peak,setPeak] = useState('08:00 – 10:00 AM');
  const [timeIndex,setTimeIndex] = useState(3);
  const [actionOpen,setActionOpen] = useState(false);
  const [metrics, setMetrics] = useState({
    delay_hotspots: 8,
    high_demand_routes: 12,
    critical_corridors: 5,
    network_load_pct: 74,
    avg_delay_min: 7,
    peak_demand_per_hour: 612,
  });
  const [alertsList, setAlertsList] = useState([]);
  const [simulationResult, setSimulationResult] = useState(null);

  useEffect(() => {
    // Fetch overview metrics from backend
    fetch(`${API_BASE}/gov/overview`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setMetrics(data); })
      .catch(() => {});

    // Fetch corridors
    fetch(`${API_BASE}/gov/corridors`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data && data.length) setRoutesList(data); })
      .catch(() => {});

    // Fetch alerts
    fetch(`${API_BASE}/gov/alerts`)
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setAlertsList(data); })
      .catch(() => {});
  }, []);

  const selected = routesList.find(r=>r.id===selectedRoute) || routesList[0];
  const peakInfo = peakData[peak] || peakData['08:00 – 10:00 AM'];

  const analyze = () => { setAnalyzed(true); setPage('analysis'); setSelectedStop(null); };
  const navigate = (p) => setPage(p);

  const runSimulation = async (actionType) => {
    try {
      const res = await fetch(`${API_BASE}/gov/simulate-action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ action_type: actionType, corridor_id: selectedRoute })
      });
      if (res.ok) {
        const data = await res.json();
        setSimulationResult(data);
      }
    } catch (e) {
      console.warn("Simulation fallback");
    }
  };

  return <div className="app">
    <Header page={page} navigate={navigate} analyzed={analyzed}/>
    <main>
      {page==='overview' && <Overview from={from} to={to} setFrom={setFrom} setTo={setTo} analyze={analyze} peak={peak} setPeak={setPeak} layer={layer} setLayer={setLayer} metrics={metrics} routesList={routesList}/>} 
      {page==='analysis' && <Analysis from={from} to={to} selected={selected} selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} selectedStop={selectedStop} setSelectedStop={setSelectedStop} layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} timeIndex={timeIndex} setTimeIndex={setTimeIndex} peakInfo={peakInfo} actionOpen={actionOpen} setActionOpen={setActionOpen} goOverview={()=>navigate('overview')} routesList={routesList} runSimulation={runSimulation} simulationResult={simulationResult}/>} 
      {page==='network' && <Network navigate={navigate} layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} routesList={routesList}/>} 
      {page==='routes' && <RoutesPage selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} navigate={navigate} routesList={routesList}/>} 
      {page==='demand' && <Demand peak={peak} setPeak={setPeak}/>} 
      {page==='alerts' && <Alerts navigate={navigate} alertsList={alertsList}/>} 
    </main>
  </div>
}

function Header({page,navigate,analyzed}){
  const items=[['overview','Overview'],['network','Network'],['routes','Routes'],['demand','Demand'],['alerts','Alerts']];
  return <header className="header">
    <button className="brand" onClick={()=>navigate('overview')}>transit<span>·</span>GOV</button>
    <nav>{items.map(([key,label])=><button key={key} className={page===key?'active':''} onClick={()=>navigate(key)}>{label}</button>)}</nav>
    <div className="headerRight"><span className="liveDot"/> <span>LIVE ML ENGINE</span><span className="demoPill">SIH 2026</span></div>
  </header>
}

function Overview({from,to,setFrom,setTo,analyze,peak,setPeak,layer,setLayer,metrics,routesList}){
  return <div className="overview">
    <section className="heroRow">
      <div><div className="eyebrow">GOVERNMENT TRANSPORT INTELLIGENCE</div><p>Analyze demand, crowding, delays and corridor performance from a transport authority perspective.</p></div>
      <div className="demoStamp">GTFS + REAL-TIME ML PREDICTION</div>
    </section>
    <NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} interactive={false} routesList={routesList}/>
    <section className="corridorSearch panel">
      <div className="searchHeading"><div><div className="eyebrow">CORRIDOR ANALYSIS</div><h2>Analyze a transport corridor</h2></div><span className="smallMuted">Predictive network intelligence</span></div>
      <div className="searchGrid">
        <label className="field"><span>FROM</span><input value={from} onChange={e=>setFrom(e.target.value)} placeholder="Search origin"/></label>
        <button className="swapBtn" onClick={()=>{setFrom(to);setTo(from)}}>⇄</button>
        <label className="field"><span>TO</span><input value={to} onChange={e=>setTo(e.target.value)} placeholder="Search destination"/></label>
        <button className="analyzeBtn" onClick={analyze}>Analyse network <b>→</b></button>
      </div>
      <div className="recent"><span>RECENT</span><button onClick={()=>setFrom('Kashmere Gate')}>Kashmere Gate</button><button onClick={()=>setTo('Rajiv Chowk')}>Rajiv Chowk</button><button onClick={()=>setTo('Central Secretariat')}>Central Secretariat</button></div>
    </section>
    <OverviewMetrics metrics={metrics}/>
  </div>
}

function OverviewMetrics({metrics}){
  return <section className="overviewMetrics"><div className="sectionTop"><div><div className="eyebrow">NETWORK SNAPSHOT</div><h2>What needs attention?</h2></div><span className="mutedMono">ACTIVE ML OBSERVATION</span></div><div className="metricGrid"><Metric label="Delay hotspots" value={metrics?.delay_hotspots?.toString().padStart(2, '0') || "08"} tone="red"/><Metric label="High-demand routes" value={metrics?.high_demand_routes?.toString().padStart(2, '0') || "12"} tone="amber"/><Metric label="Critical corridors" value={metrics?.critical_corridors?.toString().padStart(2, '0') || "05"} tone="blue"/><Metric label="Network load" value={(metrics?.network_load_pct || 74)+"%"}/><Metric label="Average delay" value={(metrics?.avg_delay_min || 7)+" min"}/><Metric label="Peak demand" value={(metrics?.peak_demand_per_hour || 612)+"/h"}/></div></section>
}
function Metric({label,value,tone=''}){return <div className="metric"><i className={'metricMark '+tone}/><span>{label}</span><strong>{value}</strong></div>}

function NetworkMap({layer,setLayer,peak,setPeak,interactive=true,selectedRouteId,selectRoute,selectedStopId,selectStop,timeIndex,routesList=fallbackRoutes}){
  const visibleRoutes = routesList.filter(r=> layer==='dense' ? r.id==='R9' : true);
  return <section className="networkMap panel">
    <div className="mapCanvas">
      <div className="mapTexture"/><div className="water"/>
      <div className="street s1"/><div className="street s2"/><div className="street s3"/><div className="street s4"/><div className="street s5"/><div className="street s6"/>
      {visibleRoutes.map(r=><MapRoute key={r.id} route={r} selected={selectedRouteId===r.id || (!selectedRouteId && r.id==='R9')} onClick={()=>selectRoute?.(r.id)}/>)}
      {initialStops.map(s=>{
        const showCrowd=layer==='crowd' || layer==='all';
        const showDemand=layer==='demand' || layer==='all';
        const critical=layer==='critical' && (s.crowd>=80 || s.delay>=8);
        const show=showCrowd||showDemand||critical;
        return <button key={s.id} className={'stopDot '+(selectedStopId===s.id?'selected ':'')+(s.status==='CRITICAL'?'critical ':'')} style={{left:s.x+'%',top:s.y+'%'}} onClick={()=>selectStop?.(s.id)} aria-label={s.name}>
          <span className="stopCore"/>{show&&<span className={'stopRing '+(s.crowd>=85?'red':s.crowd>=70?'amber':'teal')}/>}<em>{s.name}</em>
        </button>
      })}
      <div className="mapPoint origin" style={{left:'10%',top:'69%'}}><b>A</b><span>POINT A</span></div>
      <div className="mapPoint destination" style={{left:'91%',top:'47%'}}><b>B</b><span>POINT B</span></div>
      <div className="mapLegend"><span><i className="legend purple"/>Optimal</span><span><i className="legend amber"/>Fastest</span><span><i className="legend teal"/>Low crowd</span></div>
      <div className="mapLive"><i/> NETWORK MONITORING</div>
    </div>
    <div className="mapToolbar">
      <div className="layerGroup"><span>NETWORK LAYERS</span>{[['all','All routes'],['dense','Densest route'],['demand','Demand'],['crowd','Crowding'],['delay','Delay hotspots'],['critical','Critical corridors']].map(([k,l])=><button key={k} className={layer===k?'active':''} onClick={()=>setLayer(k)}>{l}</button>)}</div>
      <label className="peakSelect"><span>PEAK TIME</span><select value={peak} onChange={e=>setPeak(e.target.value)}><option>08:00 – 10:00 AM</option><option>10:00 AM – 12:00 PM</option><option>04:00 – 06:00 PM</option><option>06:00 – 08:00 PM</option></select></label>
    </div>
  </section>
}

function MapRoute({route,selected,onClick}){
  const points=(route.path || []).map(id=>initialStops.find(s=>s.id===id)).filter(Boolean);
  if (!points.length) return null;
  const d=points.map((p,i)=>`${i?'L':'M'} ${p.x} ${p.y}`).join(' ');
  return <svg className={'routeSvg '+(selected?'selected':'')} viewBox="0 0 100 100" preserveAspectRatio="none" onClick={onClick}>
    <path d={d} className={'routePath '+(route.color || 'purple')}/>
    {selected&&<path d={d} className="routeGlow"/>}
  </svg>
}

function Analysis({from,to,selected,selectedRoute,setSelectedRoute,selectedStop,setSelectedStop,layer,setLayer,peak,setPeak,timeIndex,setTimeIndex,peakInfo,actionOpen,setActionOpen,goOverview,routesList,runSimulation,simulationResult}){
  const stop=initialStops.find(s=>s.id===selectedStop);
  return <div className="analysisPage">
    <div className="analysisHeader"><button className="backBtn" onClick={goOverview}>←</button><div><div className="eyebrow">NETWORK ANALYSIS</div><h1>{from} <span>→</span> {to}</h1><p>Transport network intelligence for the selected corridor.</p></div><div className="analysisStatus"><i/> ANALYSIS ACTIVE</div></div>

    <div className="analysisMapWrap">
      <NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} selectedRouteId={selectedRoute} selectRoute={setSelectedRoute} selectedStopId={selectedStop} selectStop={setSelectedStop} routesList={routesList}/>
      {stop&&<StopPopup stop={stop} close={()=>setSelectedStop(null)}/>} 
    </div>

    <section className="analysisMetrics">
      <div className="analysisMetric featured"><span>DENSEST ROUTE</span><strong>{selected.name}</strong><em>{selected.crowd}% load · +{selected.delay} min avg delay</em></div>
      <div className="analysisMetric"><span>END-TO-END DEMAND</span><strong>{selected.demand.toLocaleString()}</strong><em>passengers / day</em></div>
      <div className="analysisMetric"><span>AVERAGE EARNINGS</span><strong>₹{(selected.revenue/100000).toFixed(2)}L</strong><em>per day</em></div>
      <div className="analysisMetric"><span>NETWORK LOAD</span><strong>{peakInfo.load}%</strong><em>current peak window</em></div>
      <div className="analysisMetric"><span>AVG DELAY</span><strong>{peakInfo.delay} min</strong><em>corridor average</em></div>
    </section>

    <div className="analysisGrid">
      <DemandPanel peakInfo={peakInfo} timeIndex={timeIndex} setTimeIndex={setTimeIndex}/>
      <RevenuePanel selected={selected}/>
    </div>

    <CrowdingPanel selectedStop={selectedStop} setSelectedStop={setSelectedStop}/>

    <RouteComparison selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} routesList={routesList}/>

    <section className="decisionGrid">
      <WhyOptimum selected={selected}/>
      <GovernmentAction open={actionOpen} setOpen={setActionOpen} runSimulation={runSimulation} simulationResult={simulationResult}/>
    </section>

    <div className="disclaimer">POWERED BY TRANSITAI ML ENGINE · GTFS NETWORK ROUTING + REAL-TIME WEATHER & TRAFFIC</div>
  </div>
}

function StopPopup({stop,close}){return <div className="stopPopup"><button onClick={close}>×</button><div className="eyebrow">STOP INTELLIGENCE</div><h3>{stop.name}</h3><div className="popupStatus"><span className={'statusDot '+stop.status.toLowerCase()}/>{stop.status}</div><div className="popupGrid"><div><span>CROWDING</span><b>{stop.crowd}%</b></div><div><span>PASSENGERS/H</span><b>{stop.pax}</b></div><div><span>PEAK</span><b>{stop.peak}</b></div><div><span>ROUTES</span><b>{stop.routes}</b></div></div></div>}

function DemandPanel({peakInfo,timeIndex,setTimeIndex}){
  return <section className="panel intelligencePanel"><div className="panelHeader"><div><div className="eyebrow">END-TO-END DEMAND</div><h2>Passenger volume</h2></div><div className="bigInline">{peakInfo.demand}<small> peak / hr</small></div></div><div className="chartArea"><div className="chartYAxis"><span>600</span><span>400</span><span>200</span><span>0</span></div><div className="chartBars">{defaultDemandByTime.map(([label,value],i)=><button key={label} className={'chartBarWrap '+(i===timeIndex?'selected':'')} onClick={()=>setTimeIndex(i)}><span className="chartBar" style={{height:value+'%'}}/><em>{label.replace(' AM','').replace(' PM','')}</em></button>)}</div></div><div className="forecastLine"><span>↗ NEXT 60 MIN</span><b>Corridor demand expected to peak with 92% load</b><em>ML forecast</em></div></section>
}

function RevenuePanel({selected}){return <section className="panel economics"><div className="eyebrow">ROUTE ECONOMICS</div><h2>Financial performance</h2><div className="moneyMain">₹{(selected.revenue/100000).toFixed(2)}L <small>/ day</small></div><div className="economicRows"><div><span>Average fare</span><b>₹28</b></div><div><span>Daily passengers</span><b>{selected.demand.toLocaleString()}</b></div><div><span>Est. monthly revenue</span><b>₹{((selected.revenue*30)/100000).toFixed(1)}L</b></div><div><span>Reliability index</span><b>{selected.reliability}%</b></div></div><div className="economicFoot">Based on live corridor timetable & ridership</div></section>
}

function CrowdingPanel({selectedStop,setSelectedStop}){
  return <section className="panel crowdPanel"><div className="panelHeader"><div><div className="eyebrow">BUS STOP CROWDING</div><h2>Stop-by-stop load</h2></div><span className="mutedMono">7 STOPS · LIVE PREDICTION</span></div><div className="tableWrap"><table><thead><tr><th>BUS STOP</th><th>CROWDING</th><th>PASSENGERS / HOUR</th><th>PEAK</th><th>ROUTES</th><th>STATUS</th></tr></thead><tbody>{initialStops.map(s=><tr key={s.id} className={selectedStop===s.id?'rowSelected':''} onClick={()=>setSelectedStop(s.id)}><td><b>{s.name}</b></td><td><div className="crowdCell"><span><i style={{width:s.crowd+'%'}}/></span><b>{s.crowd}%</b></div></td><td>{s.pax}</td><td>{s.peak}</td><td>{s.routes}</td><td><StatusBadge status={s.status}/></td></tr>)}</tbody></table></div></section>
}
function StatusBadge({status}){return <span className={'statusBadge '+status.toLowerCase()}><i/> {status}</span>}

function RouteComparison({selectedRoute,setSelectedRoute,routesList}){
  return <section className="panel comparison"><div className="panelHeader"><div><div className="eyebrow">ROUTE PERFORMANCE COMPARISON</div><h2>All relevant corridor options</h2></div><span className="mutedMono">SELECT A ROW TO HIGHLIGHT ON MAP</span></div><div className="tableWrap"><table><thead><tr><th>ROUTE</th><th>TIME</th><th>DAILY DEMAND</th><th>CROWDING</th><th>DELAY</th><th>RELIABILITY</th><th>EARNINGS</th></tr></thead><tbody>{routesList.map(r=><tr key={r.id} className={selectedRoute===r.id?'rowSelected':''} onClick={()=>setSelectedRoute(r.id)}><td><span className={'routeMini '+(r.color||'purple')}/><b>{r.id}</b><small>{r.name}</small></td><td><b>{r.time}m</b></td><td>{r.demand.toLocaleString()}</td><td>{r.crowd}%</td><td className={r.delay>=8?'dangerText':''}>+{r.delay}m</td><td>{r.reliability}%</td><td>₹{(r.revenue/100000).toFixed(2)}L</td></tr>)}</tbody></table></div></section>
}

function WhyOptimum({selected}){return <section className="panel whyPanel"><div className="eyebrow">ML MODEL EXPLANATION</div><h2>Why the optimum route?</h2><p>The ML model balances journey time, crowding risk, and schedule delay risk.</p><Score label="Travel time efficiency" value={88}/><Score label="Crowd comfort" value={100-selected.crowd}/><Score label="Delay risk resilience" value={selected.delay<=4?91:64}/><Score label="Schedule reliability" value={selected.reliability}/><div className="confidence"><span>MODEL CONFIDENCE</span><b>92%</b><em>High confidence · Production ML</em></div></section>}
function Score({label,value}){return <div className="score"><span>{label}</span><div><i style={{width:value+'%'}}/></div><b>{value}%</b></div>}

function GovernmentAction({open,setOpen,runSimulation,simulationResult}){
  return <section className="panel actionPanel">
    <div className="eyebrow">AI POLICY INTERVENTION</div>
    <h2><span className="warningIcon">⚠</span> High demand detected</h2>
    <p>Corridor is approaching critical passenger capacity during the morning peak.</p>
    <div className="actionHighlight"><span>RECOMMENDED WINDOW</span><b>08:30 AM – 10:00 AM</b></div>
    <button className="actionToggle" onClick={()=>setOpen(!open)}>{open?'Hide':'Test'} policy interventions <span>{open?'↑':'→'}</span></button>
    {open && <div className="actions">
      <div className="actionRow"><span>Increase bus frequency (+20%)</span><b>Crowding 88% → 69%</b><button onClick={()=>runSimulation('frequency')}>Run</button></div>
      <div className="actionRow"><span>Deploy 2 extra buses</span><b>Delay +8m → +4m</b><button onClick={()=>runSimulation('deploy_bus')}>Run</button></div>
      <div className="actionRow"><span>Dynamic passenger rerouting</span><b>Load -11% on Corridor</b><button onClick={()=>runSimulation('reroute')}>Run</button></div>
      {simulationResult && (
        <div style={{ background: '#17202A', padding: '10px 12px', borderRadius: 8, marginTop: 8, border: '1px solid #2C3E50' }}>
          <b style={{ color: '#46D9C5', fontSize: 13 }}>SIMULATION RESULT:</b>
          <div style={{ fontSize: 12, color: '#EEEEE6', marginTop: 4 }}>{simulationResult.estimated_impact}</div>
          <div style={{ fontSize: 11, color: '#8C93A8', marginTop: 2 }}>ROI Score: {simulationResult.roi_score} / 10</div>
        </div>
      )}
    </div>}
  </section>
}

function Network({navigate,layer,setLayer,peak,setPeak,routesList}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">NETWORK</div><h1>System command view</h1><p>City-level transport stress, corridor health and active intervention zones.</p></div><span className="systemStatus"><i/> OPERATIONAL</span></div><NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} routesList={routesList}/><div className="twoCol"><section className="panel"><div className="eyebrow">CRITICAL CORRIDORS</div><Corridor name="Hampankatta / Kashmere" load={91} delay={12} status="CRITICAL"/><Corridor name="Central Connector" load={82} delay={8} status="HIGH"/><Corridor name="Coastal Link" load={48} delay={2} status="NORMAL"/></section><section className="panel"><div className="eyebrow">ACTIVE INTERVENTION QUEUE</div><AlertLine text="Route 9 approaching critical capacity" tone="red"/><AlertLine text="Route 6 demand rising rapidly" tone="amber"/><AlertLine text="Kadri corridor recovering" tone="teal"/></section></div></div>}
function Corridor({name,load,delay,status}){return <div className="corridor"><div><b>{name}</b><small>+{delay} min</small></div><span className="corridorBar"><i style={{width:load+'%'}}/></span><em>{status}</em></div>}
function AlertLine({text,tone}){return <div className="alertLine"><i className={'metricMark '+tone}/><span>{text}</span><b>→</b></div>}

function RoutesPage({selectedRoute,setSelectedRoute,navigate,routesList=fallbackRoutes}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">ROUTES</div><h1>Corridor options</h1><p>Compare the network from a government operations perspective.</p></div></div><div className="routeCards">{routesList.map(r=><button key={r.id} className={'routeCard '+(r.color||'purple')+(selectedRoute===r.id?' selected':'')} onClick={()=>setSelectedRoute(r.id)}><div className="routeCardTop"><span>{r.type}</span><b>{r.id}</b></div><strong>{r.time}<small> min</small></strong><div className="routeStats"><span>Demand <b>{r.demand.toLocaleString()}</b></span><span>Load <b>{r.crowd}%</b></span><span>Delay <b>+{r.delay}m</b></span></div><div className="routeCardFooter">Reliability {r.reliability}% <em>View on analysis map →</em></div></button>)}</div><button className="widePrimary" onClick={()=>navigate('analysis')}>Open full network analysis →</button></div>}

function Demand({peak,setPeak}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">DEMAND INTELLIGENCE</div><h1>Passenger demand forecast</h1><p>Understand historical patterns and the next-hour network pressure.</p></div><label className="standaloneSelect"><span>WINDOW</span><select value={peak} onChange={e=>setPeak(e.target.value)}><option>08:00 – 10:00 AM</option><option>10:00 AM – 12:00 PM</option><option>04:00 – 06:00 PM</option><option>06:00 – 08:00 PM</option></select></label></div><div className="twoCol"><section className="panel demandBig"><div className="panelHeader"><div><div className="eyebrow">END-TO-END DEMAND</div><h2>Daily passenger volume</h2></div><strong>4,820 <small>pax/day</small></strong></div><div className="largeChart">{defaultDemandByTime.map(([label,v])=><div key={label} className="largeBar"><i style={{height:v+'%'}}/><span>{label}</span></div>)}</div></section><section className="panel forecast"><div className="eyebrow">NEXT 60 MINUTES</div><h2>What happens next?</h2><ForecastRow time="09:00 AM" title="High demand peak" sub="Route 9 Corridor"/><ForecastRow time="09:20 AM" title="Delay risk +8m" sub="Interchange Bottleneck"/><ForecastRow time="09:45 AM" title="Recovery window" sub="Parallel Sector Link"/><div className="forecastCallout">↗ <b>+13%</b> predicted demand surge</div></section></div></div>}
function ForecastRow({time,title,sub}){return <div className="forecastRow"><span>{time}</span><div><b>{title}</b><small>{sub}</small></div></div>}

function Alerts({navigate,alertsList=[]}){
  const displayAlerts = alertsList.length ? alertsList : [
    { id: '1', priority: "HIGH", title: "Hampankatta corridor approaching critical capacity", description: "Passenger load is predicted to cross 90% during the current peak window.", suggested_action: "Review corridor" },
    { id: '2', priority: "MEDIUM", title: "Route 9 delay probability increased", description: "Predicted delay risk has risen compared with the typical weekday baseline.", suggested_action: "View route" },
    { id: '3', priority: "LOW", title: "Outer Sector corridor recovering", description: "Demand is expected to normalize within the next 30–45 minutes.", suggested_action: "Open network" }
  ];
  return <div className="page"><div className="pageTitle"><div><div className="eyebrow">ALERTS</div><h1>Action queue</h1><p>Issues that may require intervention from transport authorities.</p></div><span className="systemStatus warning"><i/> {displayAlerts.length} NEED ATTENTION</span></div><div className="alertsList">{displayAlerts.map(a=><FullAlert key={a.id} priority={a.priority} title={a.title} text={a.description} action={a.suggested_action} onClick={()=>navigate('network')}/>)}</div></div>}
function FullAlert({priority,title,text,action,onClick}){return <article className="fullAlert"><span className={'priority '+priority.toLowerCase()}>{priority}</span><div><h2>{title}</h2><p>{text}</p></div><button onClick={onClick}>{action} →</button></article>}

createRoot(document.getElementById('root')).render(<App/>);
