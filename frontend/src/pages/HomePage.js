import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import DonutChart from '../components/DonutChart';

/* ─── Mini sparkline for Sentiment Trend ─────────────────── */
const MiniTrendLine = () => (
  <svg viewBox="0 0 200 80" className="w-full h-20">
    <defs>
      <linearGradient id="gPos" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#22c55e" stopOpacity="0.3" />
        <stop offset="100%" stopColor="#22c55e" stopOpacity="0" />
      </linearGradient>
    </defs>
    {/* Grid lines */}
    {[0, 25, 50, 75].map((y) => (
      <line key={y} x1="0" y1={y} x2="200" y2={y} stroke="#e5e7eb" strokeWidth="0.5" />
    ))}
    {/* Positive line */}
    <polyline
      points="0,55 40,45 80,30 120,25 160,35 200,28"
      fill="none" stroke="#22c55e" strokeWidth="2" strokeLinejoin="round"
    />
    {/* Neutral line */}
    <polyline
      points="0,50 40,52 80,48 120,50 160,47 200,49"
      fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeLinejoin="round"
    />
    {/* Negative line */}
    <polyline
      points="0,65 40,60 80,68 120,62 160,58 200,63"
      fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinejoin="round"
    />
    {/* X-axis labels */}
    {['May 1', 'May 8', 'May 15', 'May 22', 'May 29'].map((label, i) => (
      <text key={label} x={i * 46 + 5} y="78" fontSize="6" fill="#9ca3af">{label}</text>
    ))}
  </svg>
);

/* ─── Mini bar chart for Reviews by Rating ─────────────────── */
const MiniBarChart = () => {
  const bars = [
    { rating: '1★', h: 10, color: '#ef4444' },
    { rating: '2★', h: 20, color: '#f97316' },
    { rating: '3★', h: 35, color: '#f59e0b' },
    { rating: '4★', h: 55, color: '#22c55e' },
    { rating: '5★', h: 65, color: '#16a34a' },
  ];
  return (
    <svg viewBox="0 0 100 70" className="w-full h-20">
      {bars.map((b, i) => (
        <g key={i}>
          <rect
            x={i * 18 + 5}
            y={65 - b.h}
            width="12"
            height={b.h}
            rx="2"
            fill={b.color}
            opacity="0.85"
          />
          <text x={i * 18 + 11} y="70" textAnchor="middle" fontSize="5.5" fill="#6b7280">
            {b.rating}
          </text>
        </g>
      ))}
    </svg>
  );
};

/* ─── Hero Dashboard Card ─────────────────────────────────── */
const HeroDashboardCard = () => (
  <div className="bg-white rounded-2xl shadow-2xl p-4 w-full max-w-xs">
    <div className="text-xs font-semibold text-gray-700 mb-3">Sentiment Overview</div>
    <div className="flex items-center gap-4">
      <DonutChart size={90} strokeWidth={14} />
      <div className="space-y-1.5">
        {[
          { label: 'Positive', pct: '65%', color: '#22c55e' },
          { label: 'Neutral', pct: '20%', color: '#f59e0b' },
          { label: 'Negative', pct: '15%', color: '#ef4444' },
        ].map((s) => (
          <div key={s.label} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: s.color }} />
            <span className="text-xs text-gray-600">{s.label}</span>
            <span className="text-xs font-semibold text-gray-800 ml-auto pl-2">{s.pct}</span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

/* ─── Mini bar icon for hero ───────────────────────────────── */
const HeroBarIcon = () => (
  <div className="bg-white rounded-xl shadow-xl p-3 flex items-end gap-1 animate-float">
    {[30, 50, 40, 65, 55].map((h, i) => (
      <div
        key={i}
        className="w-3 rounded-sm"
        style={{
          height: `${h}%`,
          maxHeight: '40px',
          minHeight: '8px',
          background: `hsl(${220 + i * 10}, 70%, 60%)`,
        }}
      />
    ))}
  </div>
);

/* ─── Stars Badge ───────────────────────────────────────────── */
const StarsBadge = () => (
  <div className="inline-flex items-center gap-1 stars-purple rounded-full px-3 py-1.5">
    {[1, 2, 3, 4, 5].map((i) => (
      <svg key={i} width="12" height="12" viewBox="0 0 24 24" fill="#a78bfa">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
      </svg>
    ))}
  </div>
);

/* ─── Feature Card ──────────────────────────────────────────── */
const FeatureCard = ({ icon, title, description }) => (
  <div className="bg-white border border-gray-100 rounded-xl p-6 text-center card-hover shadow-sm">
    <div className="w-14 h-14 rounded-full bg-indigo-50 flex items-center justify-center mx-auto mb-4">
      {icon}
    </div>
    <h3 className="text-sm font-bold text-gray-900 mb-2">{title}</h3>
    <p className="text-xs text-gray-500 leading-relaxed">{description}</p>
  </div>
);

/* ─── Step Card ────────────────────────────────────────────── */
const StepCard = ({ number, icon, title, description, color }) => (
  <div className="flex flex-col items-center text-center">
    <div
      className="w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-md"
      style={{ background: `${color}20`, border: `2px solid ${color}40` }}
    >
      {icon}
    </div>
    <div
      className="flex items-center justify-center w-6 h-6 rounded-full text-white text-xs font-bold mb-2"
      style={{ background: color }}
    >
      {number}
    </div>
    <h4 className="text-sm font-bold text-gray-900 mb-1">{title}</h4>
    <p className="text-xs text-gray-500 leading-relaxed max-w-[160px]">{description}</p>
  </div>
);

/* ─── Dashboard Preview ─────────────────────────────────────── */
const DashboardPreview = () => {
  const reviews = [
    { stars: 5, text: 'Great product! Excellent quality and value for money.', badge: 'Positive', color: '#22c55e', bg: '#f0fdf4' },
    { stars: 4, text: 'Product is okay, expected a bit more for the price.', badge: 'Neutral', color: '#f59e0b', bg: '#fffbeb' },
    { stars: 2, text: 'Not satisfied with the quality. Poor build quality.', badge: 'Negative', color: '#ef4444', bg: '#fef2f2' },
  ];

  const emojiMap = { Positive: '😊', Neutral: '😐', Negative: '😞' };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
          <span className="text-sm font-semibold text-gray-800">Dashboard Overview</span>
        </div>
        <div className="flex items-center gap-1 text-xs text-gray-500 border border-gray-200 rounded px-2 py-1 cursor-pointer">
          Last 30 Days
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M6 9l6 6 6-6" />
          </svg>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 divide-y lg:divide-y-0 lg:divide-x divide-gray-100">
        {/* Sentiment Distribution */}
        <div className="p-5">
          <h4 className="text-xs font-semibold text-gray-600 mb-3">Sentiment Distribution</h4>
          <div className="flex items-center gap-3">
            <DonutChart size={80} strokeWidth={12} />
            <div className="space-y-1">
              {[
                { label: 'Positive', pct: '65%', color: '#22c55e' },
                { label: 'Neutral', pct: '20%', color: '#f59e0b' },
                { label: 'Negative', pct: '15%', color: '#ef4444' },
              ].map((s) => (
                <div key={s.label} className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                  <span className="text-xs text-gray-600">{s.label}</span>
                  <span className="text-xs font-bold ml-auto pl-1">{s.pct}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sentiment Trend */}
        <div className="p-5">
          <h4 className="text-xs font-semibold text-gray-600 mb-2">Sentiment Trend</h4>
          <MiniTrendLine />
        </div>

        {/* Reviews by Rating */}
        <div className="p-5">
          <h4 className="text-xs font-semibold text-gray-600 mb-2">Reviews by Rating</h4>
          <MiniBarChart />
        </div>
      </div>

      {/* Recent Reviews */}
      <div className="border-t border-gray-100 p-5">
        <h4 className="text-xs font-semibold text-gray-600 mb-3">Recent Reviews</h4>
        <div className="space-y-3">
          {reviews.map((r, i) => (
            <div key={i} className="flex items-start gap-3 p-2 rounded-lg" style={{ background: r.bg }}>
              <span className="text-lg">{emojiMap[r.badge]}</span>
              <div className="flex-1 min-w-0">
                {/* Stars */}
                <div className="flex gap-0.5 mb-0.5">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <svg key={j} width="10" height="10" viewBox="0 0 24 24" fill={j < r.stars ? '#f59e0b' : '#e5e7eb'}>
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                    </svg>
                  ))}
                </div>
                <p className="text-xs text-gray-700 truncate">{r.text}</p>
              </div>
              <span
                className="text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0"
                style={{ color: r.color, background: `${r.color}20` }}
              >
                {r.badge}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ─── Stat Card ────────────────────────────────────────────── */
const StatCard = ({ icon, value, label }) => (
  <div className="flex flex-col items-center gap-1">
    <div className="mb-1">{icon}</div>
    <div className="text-2xl font-extrabold text-white">{value}</div>
    <div className="text-xs text-gray-300">{label}</div>
  </div>
);

/* ══════════════════════════════════════════════════════════════
   HOME PAGE
══════════════════════════════════════════════════════════════ */
const HomePage = () => {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* ── HERO ─────────────────────────────────────────────── */}
      <section className="hero-gradient text-white overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            {/* Left */}
            <div>
              <h1 className="text-4xl lg:text-5xl font-extrabold leading-tight mb-4">
                AI-Powered<br />
                Product Sentiment<br />
                <span className="text-indigo-400">Analyzer</span>
              </h1>
              <p className="text-gray-300 text-sm leading-relaxed mb-8 max-w-md">
                Search any baby or kids product on FirstCry and get AI-powered insights from customer reviews.
              </p>

              {/* Search Bar */}
              <form onSubmit={handleSearch} className="flex gap-2 mb-6">
                <div className="flex-1 relative">
                  <svg
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
                    width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                  >
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search for a product (e.g: iPhone 15, Boat Headphones...)"
                    className="w-full pl-10 pr-4 py-3 bg-white text-gray-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <button
                  type="submit"
                  className="btn-gradient text-white px-5 py-3 rounded-xl font-semibold text-sm whitespace-nowrap hover:opacity-90 transition-opacity"
                >
                  Analyze Product
                </button>
              </form>

              <div className="flex items-center gap-3">
                <div className="bg-white bg-opacity-10 rounded-xl px-4 py-2 text-sm font-semibold text-white">
                  FirstCry Reviews
                </div>
              </div>

              {/* Powered by tag */}
              <div className="flex items-center gap-1.5 mt-4">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2">
                  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                  <polyline points="17 6 23 6 23 12" />
                </svg>
                <span className="text-xs text-gray-400">Powered by Web Scraping & NLP</span>
              </div>
            </div>

            {/* Right – Floating UI */}
            <div className="relative flex flex-col items-center gap-4">
              {/* Stars badge top right */}
              <div className="absolute -top-2 right-0 z-10">
                <StarsBadge />
              </div>

              {/* Robot icon */}
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-2xl animate-float">
                <svg width="40" height="40" viewBox="0 0 64 64" fill="none">
                  <rect x="12" y="20" width="40" height="28" rx="6" fill="white" opacity="0.9" />
                  <rect x="20" y="28" width="10" height="8" rx="2" fill="#6366f1" />
                  <rect x="34" y="28" width="10" height="8" rx="2" fill="#6366f1" />
                  <rect x="26" y="38" width="12" height="3" rx="1.5" fill="#6366f1" />
                  <rect x="28" y="12" width="8" height="10" rx="4" fill="white" opacity="0.9" />
                  <circle cx="32" cy="12" r="3" fill="#6366f1" />
                  <rect x="6" y="28" width="6" height="12" rx="3" fill="white" opacity="0.7" />
                  <rect x="52" y="28" width="6" height="12" rx="3" fill="white" opacity="0.7" />
                </svg>
              </div>

              {/* Sentiment Overview Card */}
              <HeroDashboardCard />

              {/* Bar chart icon */}
              <div className="absolute bottom-0 right-0">
                <HeroBarIcon />
              </div>

              <div className="absolute bottom-10 left-0 w-12 h-12 bg-white rounded-xl shadow-lg flex items-center justify-center animate-float" style={{ animationDelay: '1s' }}>
                <svg width="28" height="28" viewBox="0 0 32 32">
                  <rect x="4" y="10" width="24" height="18" rx="2" fill="#ec4899" />
                  <path d="M11 10V8a5 5 0 0 1 10 0v2" fill="none" stroke="white" strokeWidth="2" />
                  <text x="16" y="23" textAnchor="middle" fontSize="10" fontWeight="bold" fill="white">F</text>
                </svg>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────── */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-extrabold text-gray-900 mb-2">Powerful Features</h2>
            <div className="w-12 h-1 bg-indigo-600 mx-auto rounded-full" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
            <FeatureCard
              title="Product Search"
              description="Search any product on FirstCry and fetch real customer reviews."
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" />
                </svg>
              }
            />
            <FeatureCard
              title="Sentiment Analysis"
              description="AI models analyze reviews and classify them as Positive, Neutral or Negative."
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M8 13s1.5 2 4 2 4-2 4-2" />
                  <line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="3" />
                  <line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="3" />
                </svg>
              }
            />
            <FeatureCard
              title="Interactive Dashboard"
              description="Visualize sentiment distribution, trends over time and review analytics with charts."
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
                  <line x1="18" y1="20" x2="18" y2="10" />
                  <line x1="12" y1="20" x2="12" y2="4" />
                  <line x1="6" y1="20" x2="6" y2="14" />
                </svg>
              }
            />
            <FeatureCard
              title="Real-time Insights"
              description="Live scraping and analysis provide you with the most recent customer opinions."
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              }
            />
            <FeatureCard
              title="Word Cloud Analysis"
              description="Generate word clouds from reviews to identify the most frequent keywords."
              icon={
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              }
            />
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────── */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-extrabold text-gray-900 mb-2">How It Works</h2>
            <div className="w-12 h-1 bg-indigo-600 mx-auto rounded-full" />
          </div>

          <div className="relative">
            {/* Dashed connector line */}
            <div className="hidden lg:block absolute top-8 left-[12.5%] right-[12.5%] h-0.5 border-t-2 border-dashed border-gray-300 z-0" />

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 relative z-10">
              <StepCard
                number="1"
                title="Search Product"
                description="Enter the product name you want to analyze."
                color="#6366f1"
                icon={
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                }
              />
              <StepCard
                number="2"
                title="Collect Reviews"
                description="Our system scrapes reviews from FirstCry."
                color="#22c55e"
                icon={
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                }
              />
              <StepCard
                number="3"
                title="AI Sentiment Analysis"
                description="NLP model analyzes each review and determines the sentiment."
                color="#a855f7"
                icon={
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2">
                    <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
                    <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
                  </svg>
                }
              />
              <StepCard
                number="4"
                title="Dashboard & Insights"
                description="View detailed insights with interactive charts & graphs."
                color="#f59e0b"
                icon={
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
                    <line x1="18" y1="20" x2="18" y2="10" />
                    <line x1="12" y1="20" x2="12" y2="4" />
                    <line x1="6" y1="20" x2="6" y2="14" />
                  </svg>
                }
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── DASHBOARD PREVIEW ────────────────────────────────── */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-extrabold text-gray-900 mb-2">Dashboard Preview</h2>
            <div className="w-12 h-1 bg-indigo-600 mx-auto rounded-full" />
          </div>
          <DashboardPreview />
        </div>
      </section>

      {/* ── STATS ────────────────────────────────────────────── */}
      <section className="stats-gradient py-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-6 items-center">
            <StatCard
              value="50K+"
              label="Reviews Analyzed"
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              }
            />
            <StatCard
              value="1000+"
              label="Products Analyzed"
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#34d399" strokeWidth="2">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <path d="M16 10a4 4 0 0 1-8 0" />
                </svg>
              }
            />
            <StatCard
              value="95%"
              label="Accuracy"
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2">
                  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
                  <polyline points="17 6 23 6 23 12" />
                </svg>
              }
            />
            <StatCard
              value="24/7"
              label="Real-time Analysis"
              icon={
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              }
            />

            {/* CTA */}
            <div className="col-span-2 lg:col-span-1 flex flex-col items-center lg:items-start text-center lg:text-left">
              <h3 className="text-white font-bold text-sm mb-1">Ready to Analyze Reviews?</h3>
              <p className="text-gray-400 text-xs mb-3">
                Search any product and get AI-powered sentiment insights in seconds.
              </p>
              <button
                onClick={() => navigate('/search')}
                className="btn-gradient text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center gap-2 hover:opacity-90 transition-opacity"
              >
                Start Analyzing Now
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Rating */}
            <div className="col-span-2 lg:col-span-1 flex flex-col items-center">
              <div className="flex items-center gap-1 mb-1">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="#f59e0b">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
                <span className="text-white font-extrabold text-2xl">4.3</span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="#f59e0b">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
              </div>
              <div className="text-gray-300 text-xs">Average Rating</div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default HomePage;
