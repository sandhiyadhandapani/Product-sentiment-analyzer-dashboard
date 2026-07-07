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

      const query = params.id ? decodeURIComponent(params.id) : null;
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
  const safeName = product?.name || 'Unknown Product';
  const safePrice = product?.price || 'N/A';
  const safeRating = product?.rating || 0;
  const safeReviews = product?.reviews || 0;
  const safeTotalRatings = product?.totalRatings || 0;
  const safeDescription = product?.description || 'No description available.';
  const safeImage = product?.image || '';
  const safePlatform = product?.platform || 'FirstCry';
  const safeCategory = product?.category || 'Baby Products';
  const safeSentiment = product?.sentiment || 'Neutral';
  const safeSentimentBreakdown = product?.sentimentBreakdown || { positive: 0, neutral: 0, negative: 0 };
  const safeTopKeywords = product?.topKeywords || [];
  const safeSpecs = product?.specs || [];
  const safeReviewItems = product?.reviewItems || [];

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
                <button onClick={()=>navigate(`/reviews/${encodeURIComponent(safeName)}`)} className="btn-gradient text-white text-sm font-semibold px-5 py-2.5 rounded-xl hover:opacity-90">
                  View All Reviews
                </button>
                <button className="border border-indigo-200 text-indigo-600 text-sm font-semibold px-5 py-2.5 rounded-xl hover:bg-indigo-50">
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
