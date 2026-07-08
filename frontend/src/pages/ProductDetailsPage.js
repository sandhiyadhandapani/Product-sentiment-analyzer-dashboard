import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import DonutChart from '../components/DonutChart';
import { getProduct, getStoredAnalyzedProduct } from '../services/api';

const MiniTrendLine = () => (
  <svg viewBox="0 0 300 100" className="w-full h-24">
    {[20,40,60,80].map(y=><line key={y} x1="0" y1={y} x2="300" y2={y} stroke="#f3f4f6" strokeWidth="1"/>)}
    <polyline points="0,75 60,60 120,40 180,35 240,50 300,38" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinejoin="round"/>
    <polyline points="0,65 60,68 120,62 180,65 240,60 300,64" fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinejoin="round"/>
    <polyline points="0,82 60,78 120,85 180,80 240,75 300,80" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinejoin="round"/>
    {['May 1','May 8','May 15','May 22','May 29','Jun 1'].map((l,i)=>(
      <text key={l} x={i*56+2} y="98" fontSize="7" fill="#9ca3af">{l}</text>
    ))}
  </svg>
);

const ProductDetailsPage = () => {
  const location = useLocation();
  const params = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    const loadProduct = async () => {
      console.log('[ProductDetailsPage] Loading product...');
      console.log('[ProductDetailsPage] Location state:', location.state);
      console.log('[ProductDetailsPage] Params:', params);
      
      const stateProduct = location.state?.product;
      if (stateProduct) {
        console.log('[ProductDetailsPage] Using product from location state:', stateProduct);
        setProduct(stateProduct);
        setLoading(false);
        return;
      }

      const storedProduct = getStoredAnalyzedProduct();
      if (storedProduct) {
        console.log('[ProductDetailsPage] Using product from storage:', storedProduct);
        setProduct(storedProduct);
        setLoading(false);
        return;
      }

      // Decode defensively so a name with a literal '%' can't crash the page.
      let query = params.id || null;
      if (params.id) {
        try {
          query = decodeURIComponent(params.id);
        } catch (decodeError) {
          console.warn('[ProductDetailsPage] params.id is not valid percent-encoding, using raw value:', params.id);
          query = params.id;
        }
      }
      if (!query) {
        console.error('[ProductDetailsPage] No product query found');
        setError('No product selected.');
        setProduct(null);
        setLoading(false);
        return;
      }

      console.log('[ProductDetailsPage] Fetching product from API with query:', query);
      setLoading(true);
      setError('');
      try {
        const productData = await getProduct(query);
        console.log('[ProductDetailsPage] Product data received:', productData);
        setProduct(productData);
      } catch (err) {
        console.error('[ProductDetailsPage] Error loading product:', err);
        setError('Unable to load product details right now. Please try again.');
        setProduct(null);
      } finally {
        console.log('[ProductDetailsPage] Product loading completed');
        setLoading(false);
      }
    };

    loadProduct();
  }, [location.state, params.id]);

  if (loading) return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar/>
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 mb-2">Loading product details...</p>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
        </div>
      </div>
      <Footer/>
    </div>
  );

  if (!product) return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar/>
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 mb-4">{error || 'Product not found.'}</p>
          <button onClick={()=>navigate('/search')} className="btn-gradient text-white px-5 py-2 rounded-xl text-sm">Back to Search</button>
        </div>
      </div>
      <Footer/>
    </div>
  );

  // Safe access helpers
  const rawProduct = product?.raw || product || {};
  const safeName = rawProduct.product_name || rawProduct.name || rawProduct.product || product?.name || 'Unknown Product';
  // Issue 1: Product Details must display the Original Price (MRP) that the
  // backend/database already provides in `original_price`, not the current
  // selling price. Format the numeric MRP as ₹ (Indian grouping); fall back to
  // the current price only when the product genuinely has no separate MRP.
  // Product Details shows a single price: the Current (selling) price that the
  // backend/database saves in `current_price` — the actual price the user pays.
  // Keep the paise (652.86 -> ₹652.86). Fall back to the MRP only when the
  // product genuinely has no separate selling price.
  const currentPriceValue = rawProduct.current_price ?? product?.raw?.current_price ?? null;
  const originalPriceValue = rawProduct.original_price ?? product?.raw?.original_price ?? null;
  const formatRupees = (value) => {
    const num = Number(value);
    return value !== null && value !== undefined && value !== '' && !Number.isNaN(num) && num > 0
      ? `₹${num.toLocaleString('en-IN')}`
      : null;
  };
  const safePrice = formatRupees(currentPriceValue) || formatRupees(originalPriceValue) || rawProduct.product_price || rawProduct.price || product?.price || 'N/A';
  console.log('[UI] Product Details price → current:', currentPriceValue, '| original:', originalPriceValue, '| displayed:', safePrice);
  const safeRating = Number(rawProduct.product_rating ?? rawProduct.rating ?? product?.rating ?? 0);
  const safeReviews = Number(rawProduct.total_reviews ?? rawProduct.totalReviews ?? rawProduct.reviews ?? product?.reviews ?? 0);
  const safeTotalRatings = Number(rawProduct.total_ratings ?? rawProduct.totalRatings ?? product?.totalRatings ?? 0);
  const safeDescription = rawProduct.description || rawProduct.message || product?.description || 'No description available.';
  const safeImage = rawProduct.product_image || rawProduct.image || product?.image || '';
  const safePlatform = rawProduct.platform || product?.platform || 'FirstCry';
  const safeCategory = rawProduct.category || product?.category || 'Baby Products';
  const safeSentiment = rawProduct.sentiment || product?.sentiment || 'Neutral';
  const safeSentimentBreakdown = rawProduct.sentimentBreakdown || product?.sentimentBreakdown || { positive: 0, neutral: 0, negative: 0 };
  const safeTopKeywords = rawProduct.topKeywords || product?.topKeywords || [];
  const safeSpecs = rawProduct.specs || product?.specs || [];
  const safeReviewItems = rawProduct.reviewItems || product?.reviewItems || [];

  // Export a neat, single-page report (product photo + name, price, ratings and
  // sentiment breakdown). Opens a self-contained printable page and triggers the
  // browser's print dialog, from which the user can view it on one page or
  // "Save as PDF" to download. No external libraries required.
  const handleExport = () => {
    const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
    ));
    const pos = Number(safeSentimentBreakdown.positive) || 0;
    const neu = Number(safeSentimentBreakdown.neutral) || 0;
    const neg = Number(safeSentimentBreakdown.negative) || 0;
    const totalR = Number(safeReviews) || 0;
    const countOf = (pct) => Math.round((totalR * pct) / 100);
    const stars = '★★★★★☆☆☆☆☆'.slice(5 - Math.round(safeRating), 10 - Math.round(safeRating));
    const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

    // Shorten the long SEO-style title to a clean product name for the report:
    // drop a leading "Buy" and cut at the first marketing separator.
    const cleanName = (raw) => {
      let n = String(raw || '').trim().replace(/^buy\s+/i, '');
      n = n.split(/,|\swith\s|\s[–—-]\s|\|| online/i)[0].trim();
      if (n.length > 70) n = n.slice(0, 67).trim() + '…';
      return n || 'Product';
    };
    const reportName = cleanName(safeName);

    // Inline SVG donut chart for the sentiment split (no external libraries).
    const C = 2 * Math.PI * 70;
    let acc = 0;
    const donutSeg = (pct, color) => {
      const dash = (Math.max(Number(pct) || 0, 0) / 100) * C;
      const seg = `<circle cx="100" cy="100" r="70" fill="none" stroke="${color}" stroke-width="26" stroke-dasharray="${dash.toFixed(2)} ${(C - dash).toFixed(2)}" stroke-dashoffset="${(-acc).toFixed(2)}"/>`;
      acc += dash;
      return seg;
    };
    const donutSVG = `<svg width="180" height="180" viewBox="0 0 200 200">
      <g transform="rotate(-90 100 100)">
        <circle cx="100" cy="100" r="70" fill="none" stroke="#f1f1f4" stroke-width="26"/>
        ${donutSeg(pos, '#22c55e')}${donutSeg(neu, '#f59e0b')}${donutSeg(neg, '#ef4444')}
      </g>
      <text x="100" y="94" text-anchor="middle" font-size="30" font-weight="800" fill="#22c55e">${pos}%</text>
      <text x="100" y="116" text-anchor="middle" font-size="13" fill="#6b7280">Positive</text>
    </svg>`;

    const bar = (label, pct, count, color) => `
      <div class="row">
        <div class="row-head"><span class="dot" style="background:${color}"></span>${label}</div>
        <div class="track"><div class="fill" style="width:${Math.min(pct, 100)}%;background:${color}"></div></div>
        <div class="row-val"><b>${pct}%</b><span>${count} reviews</span></div>
      </div>`;

    const html = `<!doctype html><html><head><meta charset="utf-8"/>
      <title>${esc(safeName)} — Report</title>
      <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:'Segoe UI',Arial,sans-serif;color:#1f2937;padding:32px;background:#fff}
        .sheet{max-width:760px;margin:0 auto}
        .top{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #6366f1;padding-bottom:12px;margin-bottom:20px}
        .brand{font-size:18px;font-weight:800;color:#4f46e5}
        .brand small{display:block;font-weight:500;color:#6b7280;font-size:11px}
        .date{font-size:12px;color:#6b7280}
        .hero{display:flex;gap:20px;align-items:center;margin-bottom:24px}
        .photo{width:140px;height:140px;border-radius:14px;object-fit:contain;background:#f4f4f8;border:1px solid #eee;flex-shrink:0}
        .ph-fallback{display:flex;align-items:center;justify-content:center;font-size:34px;color:#c7c9d9}
        .title{font-size:20px;font-weight:800;line-height:1.3;margin-bottom:6px}
        .tag{display:inline-block;background:#fdf2f8;color:#db2777;font-size:11px;font-weight:600;padding:2px 8px;border-radius:6px;margin-right:6px}
        .price{font-size:22px;font-weight:800;color:#4f46e5;margin-top:8px}
        .cards{display:flex;gap:12px;margin-bottom:24px}
        .card{flex:1;border:1px solid #eee;border-radius:12px;padding:14px;text-align:center}
        .card .n{font-size:20px;font-weight:800}
        .card .l{font-size:11px;color:#6b7280;margin-top:2px}
        .stars{color:#f59e0b;font-size:16px;letter-spacing:2px}
        h2{font-size:14px;font-weight:700;margin-bottom:12px;color:#374151}
        .row{display:flex;align-items:center;gap:12px;margin-bottom:10px}
        .row-head{width:90px;font-size:13px;font-weight:600;display:flex;align-items:center;gap:6px}
        .dot{width:9px;height:9px;border-radius:50%;display:inline-block}
        .track{flex:1;height:10px;background:#f1f1f4;border-radius:6px;overflow:hidden}
        .fill{height:100%}
        .row-val{width:110px;text-align:right;font-size:12px;color:#6b7280}
        .row-val b{color:#111;margin-right:6px}
        .senti{display:flex;align-items:center;gap:28px;margin-bottom:18px}
        .donut{flex-shrink:0}
        .bars{flex:1}
        .verdict{background:#f5f3ff;border:1px solid #ddd6fe;border-radius:10px;padding:12px 16px;font-size:13px;color:#4338ca}
        .foot{margin-top:28px;border-top:1px solid #eee;padding-top:12px;font-size:11px;color:#9ca3af;text-align:center}
        @media print{body{padding:0}.sheet{max-width:100%}}
      </style></head><body>
      <div class="sheet">
        <div class="top">
          <div class="brand">Product Sentiment Analyzer<small>Sentiment Report</small></div>
          <div class="date">Generated: ${esc(today)}</div>
        </div>
        <div class="hero">
          ${safeImage
            ? `<img class="photo" src="${esc(safeImage)}" alt="product"/>`
            : `<div class="photo ph-fallback">📦</div>`}
          <div>
            <div class="title">${esc(reportName)}</div>
            <span class="tag">${esc(safePlatform)}</span>
            <span class="tag">${esc(safeCategory)}</span>
            <div class="price">${esc(safePrice)}</div>
          </div>
        </div>
        <div class="cards">
          <div class="card"><div class="n">${safeRating}</div><div class="stars">${stars}</div><div class="l">Average Rating</div></div>
          <div class="card"><div class="n">${totalR.toLocaleString('en-IN')}</div><div class="l">Total Reviews</div></div>
          <div class="card"><div class="n">${safeTotalRatings.toLocaleString('en-IN')}</div><div class="l">Total Ratings</div></div>
          <div class="card"><div class="n" style="color:#22c55e">${pos}%</div><div class="l">Positive Rate</div></div>
        </div>
        <h2>Sentiment Analysis</h2>
        <div class="senti">
          <div class="donut">${donutSVG}</div>
          <div class="bars">
            ${bar('Positive', pos, countOf(pos), '#22c55e')}
            ${bar('Neutral', neu, countOf(neu), '#f59e0b')}
            ${bar('Negative', neg, countOf(neg), '#ef4444')}
          </div>
        </div>
        <div class="verdict">Overall Sentiment: <b>${esc(safeSentiment)}</b> — ${pos}% of ${totalR.toLocaleString('en-IN')} analysed reviews are positive.</div>
        <div class="foot">Product Sentiment Analyzer • This report reflects analysis at the time of generation.</div>
      </div>
      <script>window.onload=function(){setTimeout(function(){window.print();},300);};<\/script>
      </body></html>`;

    const w = window.open('', '_blank');
    if (!w) {
      alert('Please allow pop-ups to export the report.');
      return;
    }
    w.document.open();
    w.document.write(html);
    w.document.close();
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar/>
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center gap-2 text-xs text-gray-500">
          <button onClick={()=>navigate('/')} className="hover:text-indigo-600">Home</button>
          <span>/</span>
          <button onClick={()=>navigate('/search')} className="hover:text-indigo-600">Search</button>
          <span>/</span>
          <span className="text-gray-900 font-medium">{safeName}</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Product Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <div className="flex flex-col lg:flex-row gap-6">
            <div className="w-full lg:w-48 h-48 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl flex items-center justify-center flex-shrink-0 overflow-hidden">
              {product.image ? (
                <img src={product.image} alt={product.name} className="w-full h-full object-contain" />
              ) : (
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="1.5">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
                  <line x1="3" y1="6" x2="21" y2="6"/>
                  <path d="M16 10a4 4 0 0 1-8 0"/>
                </svg>
              )}
            </div>
            <div className="flex-1">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h1 className="text-xl font-extrabold text-gray-900">{safeName}</h1>
                  <span className="text-xs font-medium px-2 py-0.5 rounded mt-1 inline-block bg-pink-50 text-pink-600">{safePlatform}</span>
                </div>
                <span className="text-xl font-bold text-indigo-600">{safePrice}</span>
              </div>
              <div className="flex items-center gap-1.5 mb-3">
                {Array.from({length:5}).map((_,i)=>(
                  <svg key={i} width="16" height="16" viewBox="0 0 24 24" fill={i<Math.floor(safeRating)?'#f59e0b':'#e5e7eb'}>
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                ))}
                <span className="text-sm font-bold text-gray-800">{safeRating}</span>
                <span className="text-sm text-gray-500">({safeReviews.toLocaleString()} reviews)</span>
              </div>
              <p className="text-sm text-gray-600 mb-4">{safeDescription}</p>
              {safeReviews === 0 ? <p className="text-sm text-amber-600 mb-4">No reviews found</p> : null}
              <div className="flex gap-3">
                <button onClick={()=>navigate(`/reviews/${encodeURIComponent(safeName)}`, { state: { product } })} className="btn-gradient text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:opacity-90">
                  View All Reviews
                </button>
                <button onClick={handleExport} className="border border-indigo-200 text-indigo-600 text-sm font-semibold px-5 py-2.5 rounded-xl hover:bg-indigo-50">
                  Export Report
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white border border-gray-100 rounded-xl p-1 shadow-sm mb-6 w-fit">
          {['overview','sentiment','keywords','specs'].map(tab=>(
            <button key={tab} onClick={()=>setActiveTab(tab)}
              className={`text-xs font-semibold px-4 py-2 rounded-lg capitalize transition-colors ${activeTab===tab?'bg-indigo-600 text-white':'text-gray-600 hover:text-indigo-600'}`}>
              {tab}
            </button>
          ))}
        </div>

        {activeTab==='overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-sm font-bold text-gray-800 mb-4">Sentiment Distribution</h3>
              <div className="flex flex-col items-center gap-4">
                <DonutChart size={120} strokeWidth={18} segments={[
                  { value: safeSentimentBreakdown.positive, color: '#22c55e' },
                  { value: safeSentimentBreakdown.neutral, color: '#f59e0b' },
                  { value: safeSentimentBreakdown.negative, color: '#ef4444' },
                ]} />
                <div className="w-full space-y-2">
                  {[{label:'Positive',p:safeSentimentBreakdown.positive,c:'#22c55e'},{label:'Neutral',p:safeSentimentBreakdown.neutral,c:'#f59e0b'},{label:'Negative',p:safeSentimentBreakdown.negative,c:'#ef4444'}].map(s=>(
                    <div key={s.label} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full" style={{background:s.c}}/>
                      <span className="text-xs text-gray-600 flex-1">{s.label}</span>
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
              <h3 className="text-sm font-bold text-gray-800 mb-4">Sentiment Trend</h3>
              <MiniTrendLine/>
              <div className="flex gap-4 mt-2">
                {[{c:'#22c55e',l:'Positive'},{c:'#f59e0b',l:'Neutral'},{c:'#ef4444',l:'Negative'}].map(s=>(
                  <div key={s.l} className="flex items-center gap-1">
                    <span className="w-3 h-0.5 inline-block" style={{background:s.c}}/>
                    <span className="text-xs text-gray-500">{s.l}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-sm font-bold text-gray-800 mb-4">Quick Stats</h3>
              <div className="space-y-3">
                {[
                  {label:'Total Reviews',value:safeReviews.toLocaleString(),icon:'💬'},
                  {label:'Average Rating',value:`${safeRating} / 5`,icon:'⭐'},
                  {label:'Positive Rate',value:`${safeSentimentBreakdown.positive}%`,icon:'✅'},
                  {label:'Platform',value:safePlatform,icon:'🛒'},
                  {label:'Category',value:safeCategory,icon:'📦'},
                ].map(stat=>(
                  <div key={stat.label} className="flex items-center justify-between py-2 border-b border-gray-50">
                    <div className="flex items-center gap-2">
                      <span>{stat.icon}</span>
                      <span className="text-xs text-gray-600">{stat.label}</span>
                    </div>
                    <span className="text-xs font-bold text-gray-900">{stat.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab==='sentiment' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-6">Detailed Sentiment Analysis</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {label:'Positive Reviews',count:Math.floor(safeReviews*safeSentimentBreakdown.positive/100),color:'#22c55e',bg:'#f0fdf4',icon:'😊'},
                {label:'Neutral Reviews',count:Math.floor(safeReviews*safeSentimentBreakdown.neutral/100),color:'#f59e0b',bg:'#fffbeb',icon:'😐'},
                {label:'Negative Reviews',count:Math.floor(safeReviews*safeSentimentBreakdown.negative/100),color:'#ef4444',bg:'#fef2f2',icon:'😞'},
              ].map(s=>(
                <div key={s.label} className="rounded-xl p-5 text-center" style={{background:s.bg}}>
                  <div className="text-3xl mb-2">{s.icon}</div>
                  <div className="text-2xl font-extrabold" style={{color:s.color}}>{s.count.toLocaleString()}</div>
                  <div className="text-xs text-gray-600 mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab==='keywords' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-6">Top Keywords from Reviews</h3>
            <div className="flex flex-wrap gap-3">
              {safeTopKeywords.length > 0 ? safeTopKeywords.map((kw,i)=>{
                const sizes=['text-2xl','text-xl','text-lg','text-base','text-sm'];
                const colors=['text-indigo-600','text-purple-600','text-blue-600','text-green-600','text-orange-500'];
                return (
                  <span key={kw} className={`${sizes[i%sizes.length]} ${colors[i%colors.length]} font-bold px-3 py-1 rounded-lg bg-gray-50 hover:bg-indigo-50 cursor-default`}>
                    {kw}
                  </span>
                );
              }) : <span className="text-gray-500 text-sm">No keywords available</span>}
            </div>
          </div>
        )}

        {activeTab==='specs' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 mb-4">Product Specifications</h3>
            <div className="space-y-2">
              {safeSpecs.length > 0 ? safeSpecs.map((spec,i)=>{
                const [key,val]=spec.split(': ');
                return (
                  <div key={i} className="flex items-start gap-4 py-3 border-b border-gray-50">
                    <span className="text-xs font-semibold text-gray-500 w-32 flex-shrink-0">{key}</span>
                    <span className="text-xs text-gray-800">{val}</span>
                  </div>
                );
              }) : <span className="text-gray-500 text-sm">No specifications available</span>}
            </div>
          </div>
        )}
      </div>
      <Footer/>
    </div>
  );
};

export default ProductDetailsPage;
