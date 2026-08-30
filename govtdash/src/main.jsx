import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const stops = [
  { id:'nitk', name:'NITK Campus', x:10, y:69, crowd:42, pax:180, peak:'08:30 AM', routes:2, delay:2, status:'NORMAL' },
  { id:'surathkal', name:'Surathkal', x:25, y:53, crowd:68, pax:290, peak:'08:45 AM', routes:3, delay:4, status:'MODERATE' },
  { id:'kuloor', name:'Kuloor', x:43, y:58, crowd:84, pax:410, peak:'09:00 AM', routes:4, delay:6, status:'HIGH' },
  { id:'hampankatta', name:'Hampankatta', x:62, y:42, crowd:93, pax:520, peak:'09:00 AM', routes:6, delay:12, status:'CRITICAL' },
  { id:'kankanady', name:'Kankanady', x:70, y:66, crowd:82, pax:430, peak:'09:15 AM', routes:5, delay:8, status:'HIGH' },
  { id:'kadri', name:'Kadri', x:81, y:31, crowd:64, pax:310, peak:'09:20 AM', routes:3, delay:4, status:'MODERATE' },
  { id:'central', name:'Mangaluru Central', x:91, y:47, crowd:71, pax:340, peak:'09:30 AM', routes:5, delay:5, status:'MODERATE' },
];

const routes = [
  { id:'R9', name:'Hampankatta Corridor', color:'purple', time:35, demand:8420, crowd:87, delay:8, reliability:82, revenue:182000, transfers:2, type:'OPTIMAL NETWORK OPTION', score:91, path:['nitk','surathkal','kuloor','hampankatta','kadri','central'] },
  { id:'R6', name:'Coastal Express Corridor', color:'teal', time:44, demand:3210, crowd:48, delay:2, reliability:94, revenue:121000, transfers:1, type:'LOWEST CROWDING OPTION', score:88, path:['nitk','surathkal','kuloor','kankanady','central'] },
  { id:'R3', name:'Central Connector', color:'amber', time:32, demand:4820, crowd:91, delay:11, reliability:78, revenue:196000, transfers:2, type:'FASTEST NETWORK OPTION', score:86, path:['nitk','surathkal','hampankatta','central'] },
  { id:'R12', name:'Kadri Link', color:'blue', time:41, demand:2890, crowd:41, delay:3, reliability:96, revenue:108000, transfers:1, type:'ALTERNATIVE', score:84, path:['nitk','kuloor','kankanady','kadri','central'] },
];

const demandByTime = [
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
  const [from,setFrom] = useState('NITK Campus');
  const [to,setTo] = useState('Mangaluru Central');
  const [analyzed,setAnalyzed] = useState(false);
  const [selectedRoute,setSelectedRoute] = useState('R9');
  const [selectedStop,setSelectedStop] = useState(null);
  const [layer,setLayer] = useState('all');
  const [peak,setPeak] = useState('08:00 – 10:00 AM');
  const [timeIndex,setTimeIndex] = useState(3);
  const [actionOpen,setActionOpen] = useState(false);

  const selected = routes.find(r=>r.id===selectedRoute) || routes[0];
  const peakInfo = peakData[peak];

  const analyze = () => { setAnalyzed(true); setPage('analysis'); setSelectedStop(null); };
  const navigate = (p) => setPage(p);

  return <div className="app">
    <Header page={page} navigate={navigate} analyzed={analyzed}/>
    <main>
      {page==='overview' && <Overview from={from} to={to} setFrom={setFrom} setTo={setTo} analyze={analyze} peak={peak} setPeak={setPeak} layer={layer} setLayer={setLayer}/>} 
      {page==='analysis' && <Analysis from={from} to={to} selected={selected} selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} selectedStop={selectedStop} setSelectedStop={setSelectedStop} layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} timeIndex={timeIndex} setTimeIndex={setTimeIndex} peakInfo={peakInfo} actionOpen={actionOpen} setActionOpen={setActionOpen} goOverview={()=>navigate('overview')}/>} 
      {page==='network' && <Network navigate={navigate} layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak}/>} 
      {page==='routes' && <RoutesPage selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} navigate={navigate}/>} 
      {page==='demand' && <Demand peak={peak} setPeak={setPeak}/>} 
      {page==='alerts' && <Alerts navigate={navigate}/>} 
    </main>
  </div>
}

function Header({page,navigate,analyzed}){
  const items=[['overview','Overview'],['network','Network'],['routes','Routes'],['demand','Demand'],['alerts','Alerts']];
  return <header className="header">
    <button className="brand" onClick={()=>navigate('overview')}>transit<span>·</span></button>
    <nav>{items.map(([key,label])=><button key={key} className={page===key?'active':''} onClick={()=>navigate(key)}>{label}</button>)}</nav>
    <div className="headerRight"><span className="liveDot"/> <span>LIVE MODEL</span><span className="demoPill">DEMO</span></div>
  </header>
}

function Overview({from,to,setFrom,setTo,analyze,peak,setPeak,layer,setLayer}){
  return <div className="overview">
    <section className="heroRow">
      <div><div className="eyebrow">GOVERNMENT TRANSPORT INTELLIGENCE</div><p>Analyze demand, crowding, delays and corridor performance from a transport authority perspective.</p></div>
      <div className="demoStamp">DEMO MODE · SIMULATED DATA</div>
    </section>
    <NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} interactive={false}/>
    <section className="corridorSearch panel">
      <div className="searchHeading"><div><div className="eyebrow">CORRIDOR ANALYSIS</div><h2>Analyze a transport corridor</h2></div><span className="smallMuted">Predictive network intelligence</span></div>
      <div className="searchGrid">
        <label className="field"><span>FROM</span><input value={from} onChange={e=>setFrom(e.target.value)} placeholder="Search origin"/></label>
        <button className="swapBtn" onClick={()=>{setFrom(to);setTo(from)}}>⇄</button>
        <label className="field"><span>TO</span><input value={to} onChange={e=>setTo(e.target.value)} placeholder="Search destination"/></label>
        <button className="analyzeBtn" onClick={analyze}>Analyse network <b>→</b></button>
      </div>
      <div className="recent"><span>RECENT</span><button onClick={()=>setFrom('NITK Campus')}>NITK Campus</button><button onClick={()=>setTo('Mangaluru Central')}>Mangaluru Central</button><button onClick={()=>setTo('Hampankatta')}>Hampankatta</button></div>
    </section>
    <OverviewMetrics/>
  </div>
}

function OverviewMetrics(){
  return <section className="overviewMetrics"><div className="sectionTop"><div><div className="eyebrow">NETWORK SNAPSHOT</div><h2>What needs attention?</h2></div><span className="mutedMono">CURRENT SIMULATION</span></div><div className="metricGrid"><Metric label="Delay hotspots" value="08" tone="red"/><Metric label="High-demand routes" value="12" tone="amber"/><Metric label="Critical corridors" value="05" tone="blue"/><Metric label="Network load" value="74%"/><Metric label="Average delay" value="07 min"/><Metric label="Peak demand" value="612/h"/></div></section>
}
function Metric({label,value,tone=''}){return <div className="metric"><i className={'metricMark '+tone}/><span>{label}</span><strong>{value}</strong></div>}

function NetworkMap({layer,setLayer,peak,setPeak,interactive=true,selectedRouteId,selectRoute,selectedStopId,selectStop,timeIndex}){
  const visibleRoutes = routes.filter(r=> layer==='dense' ? r.id==='R9' : true);
  return <section className="networkMap panel">
    <div className="mapCanvas">
      <div className="mapTexture"/><div className="water"/>
      <div className="street s1"/><div className="street s2"/><div className="street s3"/><div className="street s4"/><div className="street s5"/><div className="street s6"/>
      {visibleRoutes.map(r=><MapRoute key={r.id} route={r} selected={selectedRouteId===r.id || (!selectedRouteId && r.id==='R9')} onClick={()=>selectRoute?.(r.id)}/>)}
      {stops.map(s=>{
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
      <div className="mapZoom"><button>+</button><button>−</button><button>⌖</button></div>
    </div>
    <div className="mapToolbar">
      <div className="layerGroup"><span>NETWORK LAYERS</span>{[['all','All routes'],['dense','Densest route'],['demand','Demand'],['crowd','Crowding'],['delay','Delay hotspots'],['critical','Critical corridors']].map(([k,l])=><button key={k} className={layer===k?'active':''} onClick={()=>setLayer(k)}>{l}</button>)}</div>
      <label className="peakSelect"><span>PEAK TIME</span><select value={peak} onChange={e=>setPeak(e.target.value)}><option>08:00 – 10:00 AM</option><option>10:00 AM – 12:00 PM</option><option>04:00 – 06:00 PM</option><option>06:00 – 08:00 PM</option></select></label>
    </div>
  </section>
}

function MapRoute({route,selected,onClick}){
  const points=route.path.map(id=>stops.find(s=>s.id===id));
  const d=points.map((p,i)=>`${i?'L':'M'} ${p.x} ${p.y}`).join(' ');
  return <svg className={'routeSvg '+(selected?'selected':'')} viewBox="0 0 100 100" preserveAspectRatio="none" onClick={onClick}>
    <path d={d} className={'routePath '+route.color}/>
    {selected&&<path d={d} className="routeGlow"/>}
  </svg>
}

function Analysis({from,to,selected,selectedRoute,setSelectedRoute,selectedStop,setSelectedStop,layer,setLayer,peak,setPeak,timeIndex,setTimeIndex,peakInfo,actionOpen,setActionOpen,goOverview}){
  const stop=stops.find(s=>s.id===selectedStop);
  const timeLabel=demandByTime[timeIndex]?.[0] || '09 AM';
  return <div className="analysisPage">
    <div className="analysisHeader"><button className="backBtn" onClick={goOverview}>←</button><div><div className="eyebrow">NETWORK ANALYSIS</div><h1>{from} <span>→</span> {to}</h1><p>Transport network intelligence for the selected corridor.</p></div><div className="analysisStatus"><i/> ANALYSIS ACTIVE</div></div>

    <div className="analysisMapWrap">
      <NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak} selectedRouteId={selectedRoute} selectRoute={setSelectedRoute} selectedStopId={selectedStop} selectStop={setSelectedStop}/>
      {stop&&<StopPopup stop={stop} close={()=>setSelectedStop(null)}/>} 
    </div>

    <section className="analysisMetrics">
      <div className="analysisMetric featured"><span>DENSEST ROUTE</span><strong>Route 9</strong><em>91% load · +8 min avg delay</em></div>
      <div className="analysisMetric"><span>END-TO-END DEMAND</span><strong>4,820</strong><em>passengers / day</em></div>
      <div className="analysisMetric"><span>AVERAGE EARNINGS</span><strong>₹1.82L</strong><em>per day</em></div>
      <div className="analysisMetric"><span>NETWORK LOAD</span><strong>{peakInfo.load}%</strong><em>current peak window</em></div>
      <div className="analysisMetric"><span>AVG DELAY</span><strong>{peakInfo.delay} min</strong><em>corridor average</em></div>
    </section>

    <div className="analysisGrid">
      <DemandPanel peakInfo={peakInfo} timeIndex={timeIndex} setTimeIndex={setTimeIndex}/>
      <RevenuePanel selected={selected}/>
    </div>

    <CrowdingPanel selectedStop={selectedStop} setSelectedStop={setSelectedStop}/>

    <RouteComparison selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute}/>

    <section className="decisionGrid">
      <WhyOptimum selected={selected}/>
      <GovernmentAction open={actionOpen} setOpen={setActionOpen}/>
    </section>

    <div className="disclaimer">DEMO MODE · SIMULATED TRANSPORT DATA · Replace with GTFS, traffic feeds and ML outputs when backend is connected.</div>
  </div>
}

function StopPopup({stop,close}){return <div className="stopPopup"><button onClick={close}>×</button><div className="eyebrow">STOP INTELLIGENCE</div><h3>{stop.name}</h3><div className="popupStatus"><span className={'statusDot '+stop.status.toLowerCase()}/>{stop.status}</div><div className="popupGrid"><div><span>CROWDING</span><b>{stop.crowd}%</b></div><div><span>PASSENGERS/H</span><b>{stop.pax}</b></div><div><span>PEAK</span><b>{stop.peak}</b></div><div><span>ROUTES</span><b>{stop.routes}</b></div></div></div>}

function DemandPanel({peakInfo,timeIndex,setTimeIndex}){
  return <section className="panel intelligencePanel"><div className="panelHeader"><div><div className="eyebrow">END-TO-END DEMAND</div><h2>Passenger volume</h2></div><div className="bigInline">{peakInfo.demand}<small> peak / hr</small></div></div><div className="chartArea"><div className="chartYAxis"><span>600</span><span>400</span><span>200</span><span>0</span></div><div className="chartBars">{demandByTime.map(([label,value],i)=><button key={label} className={'chartBarWrap '+(i===timeIndex?'selected':'')} onClick={()=>setTimeIndex(i)}><span className="chartBar" style={{height:value+'%'}}/><em>{label.replace(' AM','').replace(' PM','')}</em></button>)}</div></div><div className="forecastLine"><span>↗ NEXT 60 MIN</span><b>Route 9 demand expected to rise by 13%</b><em>simulated prediction</em></div></section>
}

function RevenuePanel({selected}){return <section className="panel economics"><div className="eyebrow">ROUTE ECONOMICS</div><h2>Financial performance</h2><div className="moneyMain">₹1.82L <small>/ day</small></div><div className="economicRows"><div><span>Average fare</span><b>₹28</b></div><div><span>Daily passengers</span><b>8,420</b></div><div><span>Est. monthly revenue</span><b>₹54.6L</b></div><div><span>Revenue / passenger</span><b>₹28</b></div></div><div className="economicFoot">Based on selected corridor · simulated values</div></section>
}

function CrowdingPanel({selectedStop,setSelectedStop}){
  return <section className="panel crowdPanel"><div className="panelHeader"><div><div className="eyebrow">BUS STOP CROWDING</div><h2>Stop-by-stop load</h2></div><span className="mutedMono">7 STOPS · LIVE SIMULATION</span></div><div className="tableWrap"><table><thead><tr><th>BUS STOP</th><th>CROWDING</th><th>PASSENGERS / HOUR</th><th>PEAK</th><th>ROUTES</th><th>STATUS</th></tr></thead><tbody>{stops.map(s=><tr key={s.id} className={selectedStop===s.id?'rowSelected':''} onClick={()=>setSelectedStop(s.id)}><td><b>{s.name}</b></td><td><div className="crowdCell"><span><i style={{width:s.crowd+'%'}}/></span><b>{s.crowd}%</b></div></td><td>{s.pax}</td><td>{s.peak}</td><td>{s.routes}</td><td><StatusBadge status={s.status}/></td></tr>)}</tbody></table></div></section>
}
function StatusBadge({status}){return <span className={'statusBadge '+status.toLowerCase()}><i/> {status}</span>}

function RouteComparison({selectedRoute,setSelectedRoute}){
  return <section className="panel comparison"><div className="panelHeader"><div><div className="eyebrow">ROUTE PERFORMANCE COMPARISON</div><h2>All relevant corridor options</h2></div><span className="mutedMono">SELECT A ROW TO HIGHLIGHT ON MAP</span></div><div className="tableWrap"><table><thead><tr><th>ROUTE</th><th>TIME</th><th>DAILY DEMAND</th><th>CROWDING</th><th>DELAY</th><th>RELIABILITY</th><th>EARNINGS</th></tr></thead><tbody>{routes.map(r=><tr key={r.id} className={selectedRoute===r.id?'rowSelected':''} onClick={()=>setSelectedRoute(r.id)}><td><span className={'routeMini '+r.color}/><b>{r.id}</b><small>{r.name}</small></td><td><b>{r.time}m</b></td><td>{r.demand.toLocaleString()}</td><td>{r.crowd}%</td><td className={r.delay>=8?'dangerText':''}>+{r.delay}m</td><td>{r.reliability}%</td><td>₹{(r.revenue/100000).toFixed(2)}L</td></tr>)}</tbody></table></div></section>
}

function WhyOptimum({selected}){return <section className="panel whyPanel"><div className="eyebrow">MODEL EXPLANATION</div><h2>Why the optimum route?</h2><p>The model balances multiple network conditions instead of optimizing travel time alone.</p><Score label="Travel time" value={88}/><Score label="Crowding" value={100-selected.crowd}/><Score label="Delay risk" value={selected.delay<=4?91:64}/><Score label="Reliability" value={selected.reliability}/><div className="confidence"><span>MODEL CONFIDENCE</span><b>91%</b><em>High confidence · simulated</em></div></section>}
function Score({label,value}){return <div className="score"><span>{label}</span><div><i style={{width:value+'%'}}/></div><b>{value}%</b></div>}

function GovernmentAction({open,setOpen}){return <section className="panel actionPanel"><div className="eyebrow">AI NETWORK INSIGHT</div><h2><span className="warningIcon">⚠</span> High demand detected</h2><p>Hampankatta corridor is approaching critical passenger capacity during the morning peak.</p><div className="actionHighlight"><span>RECOMMENDED WINDOW</span><b>08:30 AM – 10:00 AM</b></div><button className="actionToggle" onClick={()=>setOpen(!open)}>{open?'Hide':'View'} suggested government actions <span>{open?'↑':'→'}</span></button>{open&&<div className="actions"><Action label="Increase bus frequency" impact="Crowding 91% → 72%"/><Action label="Deploy additional bus" impact="Delay +8m → +5m"/><Action label="Redirect demand to Route 6" impact="Load -11% on Route 9"/><Action label="Monitor corridor" impact="Trigger early warning"/></div>}<div className="aiLabel">AI RECOMMENDATION · SIMULATED</div></section>}
function Action({label,impact}){return <div className="actionRow"><span>{label}</span><b>{impact}</b><button>+</button></div>}

function Network({navigate,layer,setLayer,peak,setPeak}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">NETWORK</div><h1>System command view</h1><p>City-level transport stress, corridor health and active intervention zones.</p></div><span className="systemStatus"><i/> OPERATIONAL</span></div><NetworkMap layer={layer} setLayer={setLayer} peak={peak} setPeak={setPeak}/><div className="twoCol"><section className="panel"><div className="eyebrow">CRITICAL CORRIDORS</div><Corridor name="Hampankatta" load={91} delay={12} status="CRITICAL"/><Corridor name="Kankanady" load={82} delay={8} status="HIGH"/><Corridor name="Kadri" load={64} delay={4} status="NORMAL"/></section><section className="panel"><div className="eyebrow">ACTIVE INTERVENTION QUEUE</div><AlertLine text="Route 9 approaching critical capacity" tone="red"/><AlertLine text="Route 6 demand rising rapidly" tone="amber"/><AlertLine text="Kadri corridor recovering" tone="teal"/></section></div></div>}
function Corridor({name,load,delay,status}){return <div className="corridor"><div><b>{name}</b><small>+{delay} min</small></div><span className="corridorBar"><i style={{width:load+'%'}}/></span><em>{status}</em></div>}
function AlertLine({text,tone}){return <div className="alertLine"><i className={'metricMark '+tone}/><span>{text}</span><b>→</b></div>}

function RoutesPage({selectedRoute,setSelectedRoute,navigate}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">ROUTES</div><h1>Corridor options</h1><p>Compare the network from a government operations perspective.</p></div></div><div className="routeCards">{routes.map(r=><button key={r.id} className={'routeCard '+r.color+(selectedRoute===r.id?' selected':'')} onClick={()=>setSelectedRoute(r.id)}><div className="routeCardTop"><span>{r.type}</span><b>{r.id}</b></div><strong>{r.time}<small> min</small></strong><div className="routeStats"><span>Demand <b>{r.demand.toLocaleString()}</b></span><span>Load <b>{r.crowd}%</b></span><span>Delay <b>+{r.delay}m</b></span></div><div className="routeCardFooter">Reliability {r.reliability}% <em>View on analysis map →</em></div></button>)}</div><button className="widePrimary" onClick={()=>navigate('analysis')}>Open full network analysis →</button></div>}

function Demand({peak,setPeak}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">DEMAND INTELLIGENCE</div><h1>Passenger demand forecast</h1><p>Understand historical patterns and the next-hour network pressure.</p></div><label className="standaloneSelect"><span>WINDOW</span><select value={peak} onChange={e=>setPeak(e.target.value)}><option>08:00 – 10:00 AM</option><option>10:00 AM – 12:00 PM</option><option>04:00 – 06:00 PM</option><option>06:00 – 08:00 PM</option></select></label></div><div className="twoCol"><section className="panel demandBig"><div className="panelHeader"><div><div className="eyebrow">END-TO-END DEMAND</div><h2>Daily passenger volume</h2></div><strong>4,820 <small>pax/day</small></strong></div><div className="largeChart">{demandByTime.map(([label,v])=><div key={label} className="largeBar"><i style={{height:v+'%'}}/><span>{label}</span></div>)}</div></section><section className="panel forecast"><div className="eyebrow">NEXT 60 MINUTES</div><h2>What happens next?</h2><ForecastRow time="09:00 AM" title="High demand" sub="Route 9"/><ForecastRow time="09:20 AM" title="Delay risk ↑" sub="Hampankatta"/><ForecastRow time="09:45 AM" title="Recovery" sub="Kadri"/><div className="forecastCallout">↗ <b>+13%</b> predicted demand on Route 9</div></section></div></div>}
function ForecastRow({time,title,sub}){return <div className="forecastRow"><span>{time}</span><div><b>{title}</b><small>{sub}</small></div></div>}

function Alerts({navigate}){return <div className="page"><div className="pageTitle"><div><div className="eyebrow">ALERTS</div><h1>Action queue</h1><p>Issues that may require intervention from transport authorities.</p></div><span className="systemStatus warning"><i/> 3 NEED ATTENTION</span></div><div className="alertsList"><FullAlert priority="HIGH" title="Hampankatta corridor approaching critical capacity" text="Passenger load is predicted to cross 90% during the current peak window." action="Review corridor" onClick={()=>navigate('network')}/><FullAlert priority="MEDIUM" title="Route 9 delay probability increased" text="Predicted delay risk has risen compared with the typical weekday baseline." action="View route" onClick={()=>navigate('routes')}/><FullAlert priority="LOW" title="Kadri corridor recovering" text="Demand is expected to normalize within the next 30–45 minutes." action="Open network" onClick={()=>navigate('network')}/></div></div>}
function FullAlert({priority,title,text,action,onClick}){return <article className="fullAlert"><span className={'priority '+priority.toLowerCase()}>{priority}</span><div><h2>{title}</h2><p>{text}</p></div><button onClick={onClick}>{action} →</button></article>}

createRoot(document.getElementById('root')).render(<App/>);
