import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import DonutChart from '../components/DonutChart';
import { getStoredAnalyzedProduct } from '../services/api';

const TrendLine = () => (
  <svg viewBox="0 0 300 90" className="w-full h-24">
    {[15,35,55,75].map(y=>(
      <line key={y} x1="0" y1={y} x2="300" y2={y} stroke="#f3f4f6" strokeWidth="1"/>
    ))}
    <polyline points="0,72 50,58 100,42 150,35 200,48 250,38 300,30"
      fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinejoin="round"/>
    <polyline points="0,60 50,63 100,58 150,62 200,57 250,59 300,56"
      fill="none" stroke="#f59e0b" strokeWidth="1.8" strokeLinejoin="round"/>
    <polyline points="0,80 50,76 100,82 150,78 200,72 250,75 300,77"
      fill="none" stroke="#ef4444" strokeWidth="1.8" strokeLinejoin="round"/>
    {['May 1','May 8','May 15','May 22','May 29','Jun 1'].map((l,i)=>(
      <text key={l} x={i*55+2} y="88" fontSize="7" fill="#9ca3af">{l}</text>
    ))}
  </svg>
);

const RatingBars = () => {
  const bars=[
    {r:'1★',h:12,color:'#ef4444'},{r:'2★',h:22,color:'#f97316'},
    {r:'3★',h:38,color:'#f59e0b'},{r:'4★',h:58,color:'#22c55e'},{r:'5★',h:72,color:'#16a34a'},
  ];
  return (
    <svg viewBox="0 0 110 80" className="w-full h-24">
      {bars.map((b,i)=>(
        <g key={i}>
          <rect x={i*20+5} y={72-b.h} width="14" height={b.h} rx="2" fill={b.color} opacity="0.85"/>
          <text x={i*20+12} y="79" textAnchor="middle" fontSize="6" fill="#6b7280">{b.r}</text>
        </g>
      ))}
    </svg>
  );
};

const StatCard = ({value,label,icon,color,bg}) => (
  <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
    <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{background:bg}}>
      {icon}
    </div>
    <div>
      <div className="text-2xl font-extrabold" style={{color}}>{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  </div>
);

const ReviewRow = ({user,stars,text,sentiment}) => {
  const cfg={Positive:{color:'#16a34a',bg:'#f0fdf4',emoji:'😊'},Neutral:{color:'#d97706',bg:'#fffbeb',emoji:'😐'},Negative:{color:'#dc2626',bg:'#fef2f2',emoji:'😞'}}[sentiment];
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
      <span className="text-lg">{cfg.emoji}</span>
      <div className="flex-1 min-w-0">
        <div className="flex gap-0.5 mb-0.5">
          {Array.from({length:5}).map((_,i)=>(
            <svg key={i} width="10" height="10" viewBox="0 0 24 24" fill={i<stars?'#f59e0b':'#e5e7eb'}>
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          ))}
        </div>
        <p className="text-xs text-gray-700 truncate">{text}</p>
        <p className="text-xs text-gray-400 mt-0.5">{user}</p>
      </div>
      <span className="text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0" style={{color:cfg.color,background:cfg.bg}}>{sentiment}</span>
    </div>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const [range, setRange] = useState('Last 30 Days');
  const [platformTab, setPlatformTab] = useState('All');
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const stored = getStoredAnalyzedProduct();
    if (stored) {
      setProducts([stored]);
      setError('');
      setLoading(false);
      return;
    }

    setLoading(false);
    setProducts([]);
    setError('No analyzed product yet. Search a product to populate the dashboard.');
  }, []);

  const filtered = platformTab==='All' ? products : products.filter(p=>p.platform===platformTab);
  const totalReviews = filtered.reduce((s,p)=>s+p.reviews,0);
  const avgRating = filtered.length ? (filtered.reduce((s,p)=>s+p.rating,0)/filtered.length).toFixed(1) : '0.0';
  const overallPos = filtered.length ? Math.round(filtered.reduce((s,p)=>s+p.sentimentBreakdown.positive,0)/filtered.length) : 0;
  const overallNeu = filtered.length ? Math.round(filtered.reduce((s,p)=>s+p.sentimentBreakdown.neutral,0)/filtered.length) : 0;
  const overallNeg = 100-overallPos-overallNeu;

  const recentReviews = products.flatMap((product) => (product.reviewItems || []).slice(0, 1).map((review) => ({
    user: review.username || review.user || 'Anonymous',
    stars: review.rating || 0,
    text: review.comment || review.text || 'Great feedback',
    sentiment: review.sentiment || 'Neutral',
  }))).slice(0, 5);

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar/>
      <div className="hero-gradient py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-white text-2xl font-extrabold">Dashboard Overview</h1>
            <p className="text-gray-300 text-sm mt-1">AI-Powered sentiment insights across all products</p>
          </div>
          <div className="flex items-center gap-3">
            <select value={range} onChange={e=>setRange(e.target.value)}
              className="text-xs bg-white bg-opacity-10 border border-white border-opacity-30 text-white rounded-lg px-3 py-2 focus:outline-none">
              {['Last 7 Days','Last 30 Days','Last 90 Days','All Time'].map(r=>(
                <option key={r} value={r} className="text-gray-900">{r}</option>
              ))}
            </select>
            <button onClick={()=>navigate('/search')} className="btn-gradient text-white text-xs font-semibold px-4 py-2 rounded-lg hover:opacity-90">
              + Analyze Product
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Platform Tabs */}
        <div className="flex gap-1 bg-white border border-gray-100 rounded-xl p-1 shadow-sm w-fit">
          {['All','Amazon','Flipkart'].map(tab=>(
            <button key={tab} onClick={()=>setPlatformTab(tab)}
              className={`text-xs font-semibold px-5 py-2 rounded-lg transition-colors ${platformTab===tab?'bg-indigo-600 text-white':'text-gray-600 hover:text-indigo-600'}`}>
              {tab}
            </button>
          ))}
        </div>

        {error ? <p className="text-sm text-red-500">{error}</p> : null}
        {loading ? <p className="text-sm text-gray-500">Loading dashboard data...</p> : null}

        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard value={totalReviews.toLocaleString()} label="Total Reviews" color="#6366f1" bg="#eef2ff"
            icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>}/>
          <StatCard value={filtered.length} label="Products Analyzed" color="#22c55e" bg="#f0fdf4"
            icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>}/>
          <StatCard value={avgRating+' ★'} label="Average Rating" color="#f59e0b" bg="#fffbeb"
            icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="#f59e0b"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>}/>
          <StatCard value={overallPos+'%'} label="Positive Sentiment" color="#16a34a" bg="#dcfce7"
            icon={<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M8 13s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="3"/><line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="3"/></svg>}/>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-4">Sentiment Distribution</h3>
            <div className="flex flex-col items-center gap-4">
              <DonutChart size={130} strokeWidth={20}/>
              <div className="w-full space-y-2">
                {[{l:'Positive',p:overallPos,c:'#22c55e'},{l:'Neutral',p:overallNeu,c:'#f59e0b'},{l:'Negative',p:overallNeg,c:'#ef4444'}].map(s=>(
                  <div key={s.l} className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full" style={{background:s.c}}/>
                    <span className="text-xs text-gray-600 flex-1">{s.l}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full" style={{width:`${s.p}%`,background:s.c}}/>
                    </div>
                    <span className="text-xs font-bold text-gray-800 w-8 text-right">{s.p}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-2">Sentiment Trend</h3>
            <TrendLine/>
            <div className="flex gap-4 mt-2">
              {[{c:'#22c55e',l:'Positive'},{c:'#f59e0b',l:'Neutral'},{c:'#ef4444',l:'Negative'}].map(s=>(
                <div key={s.l} className="flex items-center gap-1">
                  <span className="w-4 h-0.5 inline-block" style={{background:s.c}}/>
                  <span className="text-xs text-gray-500">{s.l}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-2">Reviews by Rating</h3>
            <RatingBars/>
            <div className="mt-2 grid grid-cols-5 gap-1 text-center">
              {['320','580','1.2K','4.8K','6.1K'].map((n,i)=>(
                <div key={i} className="text-xs font-bold text-gray-600">{n}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Products Table + Recent Reviews */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h3 className="text-sm font-bold text-gray-800">Product Performance</h3>
              <button onClick={()=>navigate('/search')} className="text-xs text-indigo-600 font-medium hover:underline">View All →</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50">
                    <th className="text-left text-xs font-semibold text-gray-500 px-5 py-3">Product</th>
                    <th className="text-left text-xs font-semibold text-gray-500 px-3 py-3">Platform</th>
                    <th className="text-left text-xs font-semibold text-gray-500 px-3 py-3">Rating</th>
                    <th className="text-left text-xs font-semibold text-gray-500 px-3 py-3">Reviews</th>
                    <th className="text-left text-xs font-semibold text-gray-500 px-3 py-3">Sentiment</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(p=>{
                    const sColor={Positive:'#16a34a',Neutral:'#d97706',Negative:'#dc2626'}[p.sentiment];
                    const sBg={Positive:'#f0fdf4',Neutral:'#fffbeb',Negative:'#fef2f2'}[p.sentiment];
                    return (
                      <tr key={p.id} className="border-t border-gray-50 hover:bg-gray-50 cursor-pointer" onClick={()=>navigate('/product-details', { state: { product: p } })}>
                        <td className="px-5 py-3">
                          <div className="text-xs font-semibold text-gray-900 max-w-[180px] truncate">{p.name}</div>
                          <div className="text-xs text-gray-400">{p.category}</div>
                        </td>
                        <td className="px-3 py-3">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${p.platform==='Amazon'?'bg-orange-50 text-orange-600':'bg-blue-50 text-blue-600'}`}>{p.platform}</span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="#f59e0b"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                            <span className="text-xs font-bold text-gray-800">{p.rating}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3 text-xs text-gray-600">{p.reviews.toLocaleString()}</td>
                        <td className="px-3 py-3">
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{color:sColor,background:sBg}}>{p.sentiment}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h3 className="text-sm font-bold text-gray-800 mb-3">Recent Reviews</h3>
            {recentReviews.map((r,i)=><ReviewRow key={i} {...r}/>)}
          </div>
        </div>

        {/* Platform Comparison */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h3 className="text-sm font-bold text-gray-800 mb-5">Platform Comparison</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {['Amazon','Flipkart'].map(plat=>{
              const pp=products.filter(p=>p.platform===plat);
              const avgR=(pp.reduce((s,p)=>s+p.rating,0)/pp.length).toFixed(1);
              const totalR=pp.reduce((s,p)=>s+p.reviews,0);
              const posP=Math.round(pp.reduce((s,p)=>s+p.sentimentBreakdown.positive,0)/pp.length);
              const color=plat==='Amazon'?'#f97316':'#3b82f6';
              const bg=plat==='Amazon'?'#fff7ed':'#eff6ff';
              return (
                <div key={plat} className="rounded-xl p-5 border" style={{background:bg,borderColor:color+'30'}}>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{background:color+'20'}}>
                      <span className="text-sm font-bold" style={{color}}>{plat[0]}</span>
                    </div>
                    <span className="text-sm font-bold text-gray-800">{plat}</span>
                    <span className="ml-auto text-xs text-gray-400">{pp.length} products</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center mb-3">
                    <div>
                      <div className="text-xl font-extrabold" style={{color}}>{pp.length}</div>
                      <div className="text-xs text-gray-500">Products</div>
                    </div>
                    <div>
                      <div className="text-xl font-extrabold" style={{color}}>{avgR}★</div>
                      <div className="text-xs text-gray-500">Avg Rating</div>
                    </div>
                    <div>
                      <div className="text-xl font-extrabold" style={{color}}>{posP}%</div>
                      <div className="text-xs text-gray-500">Positive</div>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Total Reviews</span>
                      <span className="font-bold text-gray-700">{totalR.toLocaleString()}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div className="h-1.5 rounded-full" style={{width:`${posP}%`,background:color}}/>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <Footer/>
    </div>
  );
};

export default DashboardPage;
