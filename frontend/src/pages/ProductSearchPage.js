import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { ALL_PRODUCTS } from '../data/products';

const sentimentColors = {
  Positive: { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' },
  Neutral:  { bg: '#fffbeb', text: '#d97706', border: '#fde68a' },
  Negative: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
};

const ProductCard = ({ product, onClick }) => {
  const s = sentimentColors[product.sentiment];
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-all cursor-pointer card-hover" onClick={() => onClick(product.id)}>
      <div className="w-full h-32 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-lg flex items-center justify-center mb-4">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="1.5">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 0 1-8 0"/>
        </svg>
      </div>
      <h3 className="text-sm font-bold text-gray-900 mb-1 truncate">{product.name}</h3>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${product.platform==='Amazon'?'bg-orange-50 text-orange-600':'bg-blue-50 text-blue-600'}`}>{product.platform}</span>
        <span className="text-sm font-bold text-indigo-600">{product.price}</span>
      </div>
      <div className="flex items-center gap-1 mb-3">
        {Array.from({length:5}).map((_,i)=>(
          <svg key={i} width="12" height="12" viewBox="0 0 24 24" fill={i<Math.floor(product.rating)?'#f59e0b':'#e5e7eb'}>
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
        ))}
        <span className="text-xs text-gray-500 ml-1">{product.rating} ({product.reviews.toLocaleString()})</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full" style={{background:s.bg,color:s.text,border:`1px solid ${s.border}`}}>{product.sentiment}</span>
        <span className="text-xs text-indigo-600 font-medium">View Details →</span>
      </div>
    </div>
  );
};

const ProductSearchPage = () => {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState(ALL_PRODUCTS);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('All');
  const [platform, setPlatform] = useState('All');
  const navigate = useNavigate();

  const doSearch = (q) => {
    setLoading(true);
    setTimeout(() => {
      setResults(q ? ALL_PRODUCTS.filter(p => p.name.toLowerCase().includes(q.toLowerCase()) || p.category.toLowerCase().includes(q.toLowerCase())) : ALL_PRODUCTS);
      setLoading(false);
    }, 400);
  };

  useEffect(() => { doSearch(query); }, []);

  const handleSearch = (e) => { e.preventDefault(); doSearch(query); };

  const filtered = results.filter(p => {
    const ms = filter === 'All' || p.sentiment === filter;
    const mp = platform === 'All' || p.platform === platform;
    return ms && mp;
  });

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar/>
      <div className="hero-gradient py-10">
        <div className="max-w-3xl mx-auto px-4">
          <h1 className="text-white text-2xl font-extrabold text-center mb-6">Search Products</h1>
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 relative">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input type="text" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search for a product (e.g: iPhone 15, Boat Headphones...)"
                className="w-full pl-10 pr-4 py-3 bg-white text-gray-800 rounded-xl text-sm focus:outline-none"/>
            </div>
            <button type="submit" className="btn-gradient text-white px-5 py-3 rounded-xl font-semibold text-sm">Analyze Product</button>
          </form>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-600">Platform:</span>
            {['All','Amazon','Flipkart'].map(p=>(
              <button key={p} onClick={()=>setPlatform(p)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${platform===p?'bg-indigo-600 text-white':'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300'}`}>
                {p}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-gray-600">Sentiment:</span>
            {['All','Positive','Neutral','Negative'].map(s=>(
              <button key={s} onClick={()=>setFilter(s)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${filter===s?'bg-indigo-600 text-white':'bg-white text-gray-600 border border-gray-200 hover:border-indigo-300'}`}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <p className="text-sm text-gray-500 mb-4">{loading?'Searching...':`${filtered.length} product(s) found`}{query&&` for "${query}"`}</p>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {Array.from({length:8}).map((_,i)=>(
              <div key={i} className="bg-white rounded-xl p-5 shadow-sm animate-pulse">
                <div className="h-32 bg-gray-100 rounded-lg mb-4"/>
                <div className="h-4 bg-gray-100 rounded mb-2"/>
                <div className="h-3 bg-gray-100 rounded w-2/3"/>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500 font-medium">No products found. Try a different search.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {filtered.map(p=>(
              <ProductCard key={p.id} product={p} onClick={id=>navigate(`/product/${id}`)}/>
            ))}
          </div>
        )}
      </div>
      <Footer/>
    </div>
  );
};

export default ProductSearchPage;
