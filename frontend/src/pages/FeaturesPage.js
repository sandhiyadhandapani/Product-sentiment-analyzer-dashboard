import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const FeatureBlock = ({ icon, title, description, bullets, color, bg, reverse }) => (
  <div className={`flex flex-col ${reverse ? 'md:flex-row-reverse' : 'md:flex-row'} gap-10 items-center`}>
    <div className="flex-1">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5" style={{ background: bg }}>
        {icon}
      </div>
      <h3 className="text-xl font-extrabold text-gray-900 mb-3">{title}</h3>
      <p className="text-sm text-gray-500 leading-relaxed mb-4">{description}</p>
      <ul className="space-y-2">
        {bullets.map((b) => (
          <li key={b} className="flex items-center gap-2 text-sm text-gray-700">
            <span className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: bg }}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            {b}
          </li>
        ))}
      </ul>
    </div>
    <div className="flex-1 w-full">
      <div className="rounded-2xl p-8 flex items-center justify-center" style={{ background: bg, minHeight: 220 }}>
        <div className="opacity-80">{icon}</div>
      </div>
    </div>
  </div>
);

const FeaturesPage = () => {
  const navigate = useNavigate();
  const features = [
    {
      title: 'Product Search',
      description: 'Instantly search any product from Amazon or Flipkart. Our scraper fetches the most recent and relevant customer reviews directly from the product listing page.',
      bullets: ['Search by product name or keyword', 'Supports Amazon & Flipkart simultaneously', 'Auto-fetches top 100 reviews per product', 'Filter results by platform, rating, or category'],
      color: '#6366f1',
      bg: '#eef2ff',
      icon: <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" /></svg>,
    },
    {
      title: 'AI Sentiment Analysis',
      description: 'Our NLP pipeline uses state-of-the-art machine learning models to classify every review as Positive, Neutral, or Negative with over 95% accuracy.',
      bullets: ['BERT-based sentiment classification', 'Handles Hindi-English (Hinglish) reviews', 'Phrase-level sentiment extraction', 'Confidence score per review'],
      color: '#22c55e',
      bg: '#f0fdf4',
      icon: <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M8 13s1.5 2 4 2 4-2 4-2" /><line x1="9" y1="9" x2="9.01" y2="9" strokeWidth="3" /><line x1="15" y1="9" x2="15.01" y2="9" strokeWidth="3" /></svg>,
    },
    {
      title: 'Interactive Dashboard',
      description: 'Visualise sentiment data with beautiful, interactive charts. Track how sentiment changes over time and compare distributions across ratings.',
      bullets: ['Donut chart for sentiment distribution', 'Time-series trend line chart', 'Rating histogram bar chart', 'One-click CSV export'],
      color: '#6366f1',
      bg: '#eef2ff',
      icon: <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" /><path d="M3 9h18M9 21V9" /></svg>,
    },
    {
      title: 'Word Cloud Analysis',
      description: 'Automatically extract the most frequent and impactful keywords from reviews. Instantly identify what customers are talking about most.',
      bullets: ['Top 50 keyword extraction', 'Weighted by frequency and sentiment', 'Click keyword to filter reviews', 'Export word cloud as image'],
      color: '#f59e0b',
      bg: '#fffbeb',
      icon: <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>,
    },
    {
      title: 'Real-time Insights',
      description: 'Get live data every time you search. Our Selenium-powered scraper pulls fresh reviews on demand, ensuring you always see the most current customer opinions.',
      bullets: ['Live scraping on every search', 'No stale cached data', 'Timestamps on every review', 'Detects new review trends instantly'],
      color: '#ef4444',
      bg: '#fef2f2',
      icon: <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>,
    },
  ];

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* Hero */}
      <section className="hero-gradient py-16 text-white text-center">
        <div className="max-w-3xl mx-auto px-4">
          <h1 className="text-4xl font-extrabold mb-4">Powerful Features</h1>
          <div className="w-12 h-1 bg-indigo-300 rounded-full mx-auto mb-5" />
          <p className="text-gray-300 text-base leading-relaxed">
            Everything you need to understand customer sentiment at scale — from live scraping to AI classification to beautiful visualisations.
          </p>
        </div>
      </section>

      {/* Feature Blocks */}
      <section className="py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-20">
          {features.map((f, i) => (
            <FeatureBlock key={f.title} {...f} reverse={i % 2 !== 0} />
          ))}
        </div>
      </section>

      {/* Quick Feature Grid */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl font-extrabold text-gray-900 text-center mb-8">More Capabilities</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              '📱 Mobile Responsive UI',
              '📥 CSV Export',
              '🔍 Review Search & Filter',
              '📈 Trend Analysis',
              '🌐 Multi-platform Support',
              '⚡ Fast Load Times',
              '🔒 Secure API Calls',
              '🎨 Beautiful Charts',
              '📊 Platform Comparison',
            ].map((item) => (
              <div key={item} className="bg-white rounded-xl border border-gray-100 shadow-sm px-4 py-3 text-sm font-medium text-gray-700 flex items-center gap-2">
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14 stats-gradient text-center">
        <div className="max-w-xl mx-auto px-4">
          <h2 className="text-white text-2xl font-extrabold mb-3">Ready to try it out?</h2>
          <p className="text-gray-300 text-sm mb-6">Search any product and get instant AI-powered sentiment insights.</p>
          <button
            onClick={() => navigate('/search')}
            className="btn-gradient text-white font-bold px-8 py-3 rounded-xl hover:opacity-90 transition-opacity"
          >
            Start Analyzing Now →
          </button>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default FeaturesPage;
