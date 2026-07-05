import React from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const Step = ({ number, icon, title, description, details, color, bg }) => (
  <div className="flex gap-6">
    {/* Left – number + line */}
    <div className="flex flex-col items-center">
      <div className="w-12 h-12 rounded-full flex items-center justify-center text-white font-extrabold text-lg flex-shrink-0 shadow-lg" style={{ background: color }}>
        {number}
      </div>
      <div className="w-0.5 flex-1 mt-3" style={{ background: color + '40' }} />
    </div>
    {/* Right – content */}
    <div className="pb-12 flex-1">
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: bg }}>
            {icon}
          </div>
          <h3 className="text-base font-extrabold text-gray-900">{title}</h3>
        </div>
        <p className="text-sm text-gray-500 leading-relaxed mb-4">{description}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {details.map((d) => (
            <div key={d} className="flex items-start gap-2 text-xs text-gray-600">
              <span className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: bg }}>
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
              </span>
              {d}
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const HowItWorksPage = () => {
  const navigate = useNavigate();

  const steps = [
    {
      number: '1',
      title: 'Search for a Product',
      description: 'Enter the name of any product you want to analyze in the search bar. Our system focuses on FirstCry product pages for review analysis.',
      details: ['Type any product name or keyword','Use the FirstCry source flow','System auto-completes popular searches','No account or login required'],
      color: '#6366f1', bg: '#eef2ff',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>,
    },
    {
      number: '2',
      title: 'Collect Reviews via Web Scraping',
      description: 'Once you hit "Analyze Product", our Selenium-powered scraper navigates to the product listing page and extracts the most recent customer reviews in real time.',
      details: ['Selenium WebDriver automates browser interaction','Scrapes up to 100 reviews per product','Extracts star rating, review text, date, and user','Handles pagination automatically'],
      color: '#22c55e', bg: '#f0fdf4',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>,
    },
    {
      number: '3',
      title: 'AI Sentiment Analysis',
      description: 'Each collected review is passed through our NLP pipeline. A BERT-based classification model determines whether the review is Positive, Neutral, or Negative.',
      details: ['Pre-trained BERT sentiment model','Handles Hinglish (Hindi + English) text','Confidence score per classification','Phrase-level keyword extraction'],
      color: '#a855f7', bg: '#f5f3ff',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a855f7" strokeWidth="2"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96-.46 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z"/><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z"/></svg>,
    },
    {
      number: '4',
      title: 'Dashboard & Visual Insights',
      description: 'Results are displayed in a rich, interactive dashboard. Explore sentiment distribution, rating histograms, trend lines, word clouds, and individual review cards.',
      details: ['Sentiment donut chart (Positive / Neutral / Negative)','Time-series trend line over review dates','Rating distribution bar chart','Word cloud of top keywords'],
      color: '#f59e0b', bg: '#fffbeb',
      icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
    },
  ];

  const faqs = [
    { q: 'How accurate is the sentiment analysis?', a: 'Our NLP model achieves 95%+ accuracy on standard English reviews and around 88% on mixed Hinglish content.' },
    { q: 'How many reviews are scraped per search?', a: 'By default the scraper collects up to 100 of the most recent reviews. This can be configured in the backend settings.' },
    { q: 'Does it work for any product?', a: 'Yes — any product listed on FirstCry with customer reviews can be analyzed.' },
    { q: 'How long does a search take?', a: 'A typical search takes 15–30 seconds for scraping + 5–10 seconds for NLP processing.' },
    { q: 'Can I export the results?', a: 'Yes. You can export the full review dataset and sentiment breakdown as a CSV file from the dashboard.' },
    { q: 'Is the data live or cached?', a: 'Data is scraped live on every search, so you always get the most recent customer opinions.' },
  ];

  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* Hero */}
      <section className="hero-gradient py-16 text-white text-center">
        <div className="max-w-3xl mx-auto px-4">
          <h1 className="text-4xl font-extrabold mb-4">How It Works</h1>
          <div className="w-12 h-1 bg-indigo-300 rounded-full mx-auto mb-5" />
          <p className="text-gray-300 text-base leading-relaxed">
            From a simple product search to a full AI-powered sentiment dashboard — here's exactly how our system works under the hood.
          </p>
        </div>
      </section>

      {/* Steps */}
      <section className="py-16">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          {steps.map((step) => (
            <Step key={step.number} {...step} />
          ))}
        </div>
      </section>

      {/* Architecture */}
      <section className="py-12 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl font-extrabold text-gray-900 text-center mb-2">System Architecture</h2>
          <div className="w-10 h-1 bg-indigo-600 rounded-full mx-auto mb-8" />
          <div className="flex flex-col md:flex-row items-center justify-center gap-3">
            {[
              { label: 'React Frontend', sub: 'Tailwind + Axios', color: '#6366f1', bg: '#eef2ff' },
              { label: '→', sub: '', color: '#9ca3af', bg: 'transparent' },
              { label: 'Flask API', sub: 'REST Endpoints', color: '#000', bg: '#f5f5f5' },
              { label: '→', sub: '', color: '#9ca3af', bg: 'transparent' },
              { label: 'Selenium Scraper', sub: 'FirstCry', color: '#22c55e', bg: '#f0fdf4' },
              { label: '→', sub: '', color: '#9ca3af', bg: 'transparent' },
              { label: 'NLP Model', sub: 'BERT Classifier', color: '#a855f7', bg: '#f5f3ff' },
              { label: '→', sub: '', color: '#9ca3af', bg: 'transparent' },
              { label: 'MongoDB', sub: 'Data Storage', color: '#47a248', bg: '#edf7ed' },
            ].map((item, i) => (
              item.label === '→'
                ? <div key={i} className="text-gray-400 text-xl font-bold hidden md:block">→</div>
                : (
                  <div key={item.label} className="rounded-xl p-4 text-center min-w-[110px]" style={{ background: item.bg }}>
                    <div className="text-xs font-bold" style={{ color: item.color }}>{item.label}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{item.sub}</div>
                  </div>
                )
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 bg-white">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-xl font-extrabold text-gray-900 text-center mb-2">Frequently Asked Questions</h2>
          <div className="w-10 h-1 bg-indigo-600 rounded-full mx-auto mb-8" />
          <div className="space-y-4">
            {faqs.map((faq) => (
              <div key={faq.q} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <h4 className="text-sm font-bold text-gray-900 mb-2">❓ {faq.q}</h4>
                <p className="text-xs text-gray-500 leading-relaxed">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14 stats-gradient text-center">
        <div className="max-w-xl mx-auto px-4">
          <h2 className="text-white text-2xl font-extrabold mb-3">See it in action</h2>
          <p className="text-gray-300 text-sm mb-6">Try analyzing any product right now — no sign-up required.</p>
          <button
            onClick={() => navigate('/search')}
            className="btn-gradient text-white font-bold px-8 py-3 rounded-xl hover:opacity-90 transition-opacity"
          >
            Analyze a Product →
          </button>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default HowItWorksPage;
