import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { getProduct, getProductReviews } from '../services/api';

const sentimentConfig = {
  Positive: { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0', emoji: '😊' },
  Neutral: { bg: '#fffbeb', text: '#d97706', border: '#fde68a', emoji: '😐' },
  Negative: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca', emoji: '😞' },
};

const ReviewCard = ({ review }) => {
  const s = sentimentConfig[review.sentiment];
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-400 to-purple-400 flex items-center justify-center text-white font-bold text-sm">
            {review.user.charAt(0)}
          </div>
          <div>
            <div className="text-sm font-semibold text-gray-900">{review.user}</div>
            <div className="text-xs text-gray-400">{review.date} · {review.platform}</div>
          </div>
        </div>
        <span
          className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full"
          style={{ background: s.bg, color: s.text, border: `1px solid ${s.border}` }}
        >
          <span>{s.emoji}</span>
          {review.sentiment}
        </span>
      </div>

      {/* Stars */}
      <div className="flex gap-0.5 mb-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <svg key={i} width="14" height="14" viewBox="0 0 24 24"
            fill={i < review.rating ? '#f59e0b' : '#e5e7eb'}>
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        ))}
      </div>

      <h4 className="text-sm font-bold text-gray-900 mb-1.5">{review.title}</h4>
      <p className="text-xs text-gray-600 leading-relaxed mb-3">{review.text}</p>

      {/* Helpful */}
      <div className="flex items-center gap-2 text-xs text-gray-400 pt-3 border-t border-gray-50">
        <button className="flex items-center gap-1 hover:text-indigo-600 transition-colors">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
            <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
          </svg>
          Helpful ({review.helpful})
        </button>
        <span>·</span>
        <button className="hover:text-red-500 transition-colors">Report</button>
      </div>
    </div>
  );
};

const ReviewDisplayPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [sentimentFilter, setSentimentFilter] = useState('All');
  const [sortBy, setSortBy] = useState('recent');
  const [search, setSearch] = useState('');
  const [reviews, setReviews] = useState([]);
  const [productName, setProductName] = useState('Product');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const filters = ['All', 'Positive', 'Neutral', 'Negative'];

  useEffect(() => {
    const loadReviews = async () => {
      setLoading(true);
      setError('');
      try {
        const productData = await getProduct(decodeURIComponent(id));
        const reviewData = await getProductReviews(decodeURIComponent(id));
        setProductName(productData.name);
        setReviews(reviewData);
      } catch (err) {
        setError('Unable to load reviews right now.');
        setReviews([]);
      } finally {
        setLoading(false);
      }
    };

    loadReviews();
  }, [id]);

  const filtered = reviews
    .filter((r) => sentimentFilter === 'All' || r.sentiment === sentimentFilter)
    .filter((r) => search === '' || r.text.toLowerCase().includes(search.toLowerCase()) || r.title.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortBy === 'rating' ? b.rating - a.rating : Number(b.id.replace(/\D/g, '')) - Number(a.id.replace(/\D/g, '')));

  const counts = {
    Positive: reviews.filter((r) => r.sentiment === 'Positive').length,
    Neutral: reviews.filter((r) => r.sentiment === 'Neutral').length,
    Negative: reviews.filter((r) => r.sentiment === 'Negative').length,
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans">
      <Navbar />

      {/* Header */}
      <div className="hero-gradient py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <button
            onClick={() => navigate(`/product/${id}`)}
            className="flex items-center gap-2 text-gray-300 hover:text-white text-sm mb-4 transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
            Back to Product
          </button>
          <h1 className="text-white text-2xl font-extrabold mb-1">Customer Reviews</h1>
          <p className="text-gray-300 text-sm">{productName} · {reviews.length} reviews</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {Object.entries(counts).map(([label, count]) => {
            const s = sentimentConfig[label];
            return (
              <div key={label} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center">
                <div className="text-2xl mb-1">{s.emoji}</div>
                <div className="text-xl font-extrabold" style={{ color: s.text }}>{count}</div>
                <div className="text-xs text-gray-500">{label}</div>
              </div>
            );
          })}
        </div>

        {/* Filters Row */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            {/* Search */}
            <div className="relative flex-1 max-w-xs">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" width="14" height="14"
                viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search reviews..."
                className="w-full pl-8 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-xs focus:outline-none focus:border-indigo-300"
              />
            </div>

            {/* Sentiment Filters */}
            <div className="flex gap-2">
              {filters.map((f) => (
                <button
                  key={f}
                  onClick={() => setSentimentFilter(f)}
                  className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                    sentimentFilter === f
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-50 text-gray-600 border border-gray-200 hover:border-indigo-300'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-xs border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300 bg-gray-50"
            >
              <option value="recent">Most Recent</option>
              <option value="rating">Highest Rating</option>
            </select>
          </div>
        </div>

        {error ? <p className="text-sm text-red-500 mb-4">{error}</p> : null}
        {loading ? <p className="text-sm text-gray-500 mb-4">Loading reviews...</p> : null}

        {/* Count */}
        <p className="text-xs text-gray-500 mb-4">{filtered.length} review(s) shown</p>

        {/* Reviews Grid */}
        {filtered.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-400 text-sm">{reviews.length === 0 ? 'No reviews found' : 'No reviews match your filters.'}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {filtered.map((review) => (
              <ReviewCard key={review.id} review={review} />
            ))}
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
};

export default ReviewDisplayPage;
