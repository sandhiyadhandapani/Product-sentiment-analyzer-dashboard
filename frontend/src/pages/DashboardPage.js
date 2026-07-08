import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import DonutChart from '../components/DonutChart';
import { fetchDashboard, fetchProducts, hasAnalyzedInSession } from '../services/api';

const TrendLine = ({ data }) => (
  <svg viewBox="0 0 300 90" className="w-full h-24">
    {[15,35,55,75].map((y) => (
      <line key={y} x1="0" y1={y} x2="300" y2={y} stroke="#f3f4f6" strokeWidth="1" />
    ))}
    {data.length > 0 ? (
      <>
        <polyline points={data.map((point, index) => `${index * 60},${80 - point.value * 0.6}`).join(' ')} fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinejoin="round" />
      </>
    ) : (
      <polyline points="0,72 50,58 100,42 150,35 200,48 250,38 300,30" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinejoin="round" />
    )}
    {['May 1','May 8','May 15','May 22','May 29','Jun 1'].map((label, index) => (
      <text key={label} x={index * 55 + 2} y="88" fontSize="7" fill="#9ca3af">{label}</text>
    ))}
  </svg>
);

const RatingBars = ({ distribution = {} }) => {
  const bars = [
    { label: '1★', value: distribution['1_star'] || 0, color: '#ef4444' },
    { label: '2★', value: distribution['2_star'] || 0, color: '#f97316' },
    { label: '3★', value: distribution['3_star'] || 0, color: '#f59e0b' },
    { label: '4★', value: distribution['4_star'] || 0, color: '#22c55e' },
    { label: '5★', value: distribution['5_star'] || 0, color: '#16a34a' },
  ];
  const max = Math.max(...bars.map((bar) => bar.value), 1);

  return (
    <svg viewBox="0 0 110 80" className="w-full h-24">
      {bars.map((bar, index) => {
        const height = (bar.value / max) * 60 + 8;
        return (
          <g key={bar.label}>
            <rect x={index * 20 + 5} y={72 - height} width="14" height={height} rx="2" fill={bar.color} opacity="0.85" />
            <text x={index * 20 + 12} y="79" textAnchor="middle" fontSize="6" fill="#6b7280">{bar.label}</text>
          </g>
        );
      })}
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

const ReviewRow = ({ user, stars, date, text, sentiment }) => {
  const cfg = { Positive: { color: '#16a34a', bg: '#f0fdf4', emoji: '😊' }, Neutral: { color: '#d97706', bg: '#fffbeb', emoji: '😐' }, Negative: { color: '#dc2626', bg: '#fef2f2', emoji: '😞' } }[sentiment] || { color: '#6b7280', bg: '#f3f4f6', emoji: '💬' };
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
        <p className="text-xs text-gray-400 mt-0.5">{user}{date ? ` · ${date}` : ''}</p>
      </div>
      <span className="text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0" style={{color:cfg.color,background:cfg.bg}}>{sentiment}</span>
    </div>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const [range, setRange] = useState('Last 30 Days');
  const [products, setProducts] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  // Show data only after an analysis in THIS session. A full page refresh resets
  // this (module flag reloads), so the dashboard returns to its empty state
  // instead of showing the last persisted product.
  const [analyzed, setAnalyzed] = useState(hasAnalyzedInSession());
  const [loading, setLoading] = useState(hasAnalyzedInSession());
  const [error, setError] = useState('');

  useEffect(() => {
    // Nothing analyzed this session (e.g. fresh load / after refresh) -> keep the
    // empty state; do not pull the last persisted product from the backend.
    if (!hasAnalyzedInSession()) {
      setLoading(false);
      return;
    }
    const loadData = async () => {
      try {
        setLoading(true);
        const [productList, dashboardData] = await Promise.all([
          fetchProducts(),
          fetchDashboard(),
        ]);
        setProducts(productList);
        setDashboard(dashboardData);
        setError('');
      } catch (err) {
        setProducts([]);
        setDashboard(null);
        setError('Unable to load dashboard data yet. Make sure the backend is running and MongoDB is reachable.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  // Refresh dashboard when a new analysis completes elsewhere in the app
  useEffect(() => {
    const handler = async () => {
      try {
        setAnalyzed(true);
        setLoading(true);
        const [productList, dashboardData] = await Promise.all([fetchProducts(), fetchDashboard()]);
        setProducts(productList);
        setDashboard(dashboardData);
        setError('');
      } catch (err) {
        // keep previous state but surface an error
        setError('Unable to refresh dashboard after analysis.');
      } finally {
        setLoading(false);
      }
    };
    window.addEventListener('productAnalyzed', handler);
    return () => window.removeEventListener('productAnalyzed', handler);
  }, []);

  const overallPos = dashboard?.positive_percentage || 0;
  const overallNeu = dashboard?.neutral_percentage || 0;
  const overallNeg = dashboard?.negative_percentage || 0;
  const dominantSentiment =
    overallPos >= overallNeu && overallPos >= overallNeg
      ? 'Positive'
      : overallNeg >= overallNeu
      ? 'Negative'
      : 'Neutral';

  // Dashboard shows ONLY the latest analyzed product (Issues 5 & 6). `products`
  // is sorted by updated_at desc, so index 0 is the latest; its authoritative
  // rating/reviews/sentiment come from the latest dashboard payload.
  const latestProduct = products[0] || (dashboard?.product_name ? {
    id: dashboard.product_name,
    name: dashboard.product_name,
    platform: dashboard.platform || 'FirstCry',
    category: 'Product',
  } : null);
  const filtered = latestProduct
    ? [{
        ...latestProduct,
        rating: Number(dashboard?.average_rating ?? latestProduct.rating ?? 0),
        totalReviews: Number(dashboard?.total_reviews ?? latestProduct.totalReviews ?? 0),
        sentiment: dominantSentiment,
      }]
    : [];

  const totalReviews = dashboard?.total_reviews || filtered.reduce((sum, product) => sum + Number(product.totalReviews || product.reviews || 0), 0);
  const avgRating = dashboard?.average_rating ? dashboard.average_rating.toFixed(1) : (filtered.length ? (filtered.reduce((sum, product) => sum + Number(product.rating || 0), 0) / filtered.length).toFixed(1) : '0.0');
  const recentReviews = (dashboard?.recent_reviews || []).map((review) => ({
    user: review.reviewer_name || review.username || 'Anonymous',
    stars: review.rating || 0,
    date: review.review_date || review.date || '',
    text: review.review_text || review.comment || 'Great feedback',
    sentiment: review.sentiment || 'Neutral',
  })).slice(0, 5);

  // Empty state: nothing analyzed in this session (fresh load / after refresh).
  if (!analyzed) {
    return (
      <div className="min-h-screen bg-gray-50 font-sans">
        <Navbar/>
        <div className="hero-gradient py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-white text-2xl font-extrabold">Dashboard Overview</h1>
              <p className="text-gray-300 text-sm mt-1">AI-Powered sentiment insights across all products</p>
            </div>
            <button onClick={()=>navigate('/search')} className="btn-gradient text-white text-xs font-semibold px-4 py-2 rounded-lg hover:opacity-90">
              + Analyze Product
            </button>
          </div>
        </div>
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-lg font-bold text-gray-800 mb-2">No analysis yet</h2>
            <p className="text-sm text-gray-500 mb-6">
              Analyze a product to see its sentiment insights here. These results are for the
              current session only and clear when you refresh the page.
            </p>
            <button onClick={()=>navigate('/search')} className="btn-gradient text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:opacity-90">
              + Analyze a Product
            </button>
          </div>
        </div>
        <Footer/>
      </div>
    );
  }

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
              <DonutChart size={130} strokeWidth={20} segments={[
                { value: overallPos, color: '#22c55e' },
                { value: overallNeu, color: '#f59e0b' },
                { value: overallNeg, color: '#ef4444' },
              ]} />
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
            <TrendLine data={[{ value: overallPos }, { value: overallNeu }, { value: overallNeg }]} />
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
            <RatingBars distribution={dashboard?.rating_distribution || {}} />
            <div className="mt-2 grid grid-cols-5 gap-1 text-center">
              {['1★','2★','3★','4★','5★'].map((label, index) => (
                <div key={label} className="text-xs font-bold text-gray-600">{dashboard?.rating_distribution?.[`${index + 1}_star`] || 0}</div>
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
                    const sColor={Positive:'#16a34a',Neutral:'#d97706',Negative:'#dc2626'}[p.sentiment || 'Neutral'];
                    const sBg={Positive:'#f0fdf4',Neutral:'#fffbeb',Negative:'#fef2f2'}[p.sentiment || 'Neutral'];
                    return (
                      <tr key={p.id} className="border-t border-gray-50 hover:bg-gray-50 cursor-pointer" onClick={()=>navigate('/product-details', { state: { product: p } })}>
                        <td className="px-5 py-3">
                          <div className="text-xs font-semibold text-gray-900 max-w-[180px] truncate">{p.name || p.product_name}</div>
                          <div className="text-xs text-gray-400">{p.category || 'Product'}</div>
                        </td>
                        <td className="px-3 py-3">
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-pink-50 text-pink-600">{p.platform || 'FirstCry'}</span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex items-center gap-1">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="#f59e0b"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                            <span className="text-xs font-bold text-gray-800">{p.rating || 0}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3 text-xs text-gray-600">{Number(p.totalReviews || p.reviews || 0).toLocaleString()}</td>
                        <td className="px-3 py-3">
                          <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{color:sColor,background:sBg}}>{p.sentiment || 'Neutral'}</span>
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

        {/* Source Summary */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h3 className="text-sm font-bold text-gray-800 mb-5">Source Summary</h3>
          <div className="grid grid-cols-1 md:grid-cols-1 gap-6">
            {(() => {
              // Populated from the persisted backend Source Summary of the
              // latest analyzed product (Issue 5) - no hardcoded/placeholder values.
              const ss = dashboard?.source_summary || {};
              const color = '#ec4899';
              const bg = '#fdf2f8';
              const website = ss.website || 'FirstCry';
              const productName = ss.product_name || dashboard?.product_name || '—';
              const totalR = Number(ss.total_reviews ?? dashboard?.total_reviews ?? 0);
              const avgR = Number(ss.average_rating ?? dashboard?.average_rating ?? 0).toFixed(1);
              const posC = Number(ss.positive_reviews ?? dashboard?.positive_count ?? 0);
              const neuC = Number(ss.neutral_reviews ?? dashboard?.neutral_count ?? 0);
              const negC = Number(ss.negative_reviews ?? dashboard?.negative_count ?? 0);
              // Total Reviews shows the website total, but the sentiment counts are
              // over the analyzed sample - so Positive% must divide by the analyzed
              // count, not the (much larger) site total.
              const analyzedR = Number(ss.analyzed_reviews ?? dashboard?.analyzed_reviews ?? (posC + neuC + negC)) || 0;
              const posP = analyzedR ? Math.round((posC / analyzedR) * 100) : 0;
              const scrapeTime = ss.scraping_time_seconds != null ? `${ss.scraping_time_seconds}s` : '—';
              const analysisTime = ss.analysis_completed_at ? new Date(ss.analysis_completed_at).toLocaleString() : '—';
              return (
                <div className="rounded-xl p-5 border" style={{background:bg,borderColor:color+'30'}}>
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{background:color+'20'}}>
                      <span className="text-sm font-bold" style={{color}}>{website[0]}</span>
                    </div>
                    <span className="text-sm font-bold text-gray-800">{website}</span>
                    <span className="ml-auto text-xs text-gray-400 truncate max-w-[220px]">{productName}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center mb-3">
                    <div>
                      <div className="text-xl font-extrabold" style={{color}}>{totalR.toLocaleString()}</div>
                      <div className="text-xs text-gray-500">Total Reviews</div>
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
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs text-gray-500"><span>Positive Reviews</span><span className="font-bold text-gray-700">{posC.toLocaleString()}</span></div>
                    <div className="flex justify-between text-xs text-gray-500"><span>Neutral Reviews</span><span className="font-bold text-gray-700">{neuC.toLocaleString()}</span></div>
                    <div className="flex justify-between text-xs text-gray-500"><span>Negative Reviews</span><span className="font-bold text-gray-700">{negC.toLocaleString()}</span></div>
                    <div className="flex justify-between text-xs text-gray-500"><span>Scraping Time</span><span className="font-bold text-gray-700">{scrapeTime}</span></div>
                    <div className="flex justify-between text-xs text-gray-500"><span>Analysis Time</span><span className="font-bold text-gray-700">{analysisTime}</span></div>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      </div>
      <Footer/>
    </div>
  );
};

export default DashboardPage;
