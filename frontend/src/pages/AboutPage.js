import React from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const TeamCard = ({ name, role, emoji }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 text-center card-hover">
    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center mx-auto mb-4 text-3xl">
      {emoji}
    </div>
    <h3 className="text-sm font-bold text-gray-900 mb-1">{name}</h3>
    <p className="text-xs text-indigo-600 font-medium">{role}</p>
  </div>
);

const StatBadge = ({ value, label }) => (
  <div className="text-center">
    <div className="text-3xl font-extrabold text-indigo-600 mb-1">{value}</div>
    <div className="text-sm text-gray-500">{label}</div>
  </div>
);

const AboutPage = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* Hero */}
      <section className="hero-gradient py-16 text-white text-center">
        <div className="max-w-3xl mx-auto px-4">
          <div className="w-16 h-16 bg-white bg-opacity-20 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h1 className="text-4xl font-extrabold mb-4">About Product Sentiment Analyzer</h1>
          <p className="text-gray-300 text-base leading-relaxed">
            We help consumers and businesses make smarter decisions by turning thousands
            of raw customer reviews into clear, actionable AI-powered sentiment insights.
          </p>
        </div>
      </section>

      {/* Mission */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-2xl font-extrabold text-gray-900 mb-4">Our Mission</h2>
              <div className="w-10 h-1 bg-indigo-600 rounded-full mb-5" />
              <p className="text-gray-600 text-sm leading-relaxed mb-4">
                Product Sentiment Analyzer was built to bridge the gap between raw customer
                feedback and meaningful product intelligence. With thousands of reviews
                published daily on FirstCry, it's impossible to read them all.
              </p>
              <p className="text-gray-600 text-sm leading-relaxed mb-4">
                Our AI-powered NLP engine scrapes, processes, and classifies reviews in
                real time — giving you instant clarity on what customers love, dislike,
                and feel neutral about any product.
              </p>
              <p className="text-gray-600 text-sm leading-relaxed">
                Whether you're a student, researcher, or business analyst, our platform
                delivers professional-grade sentiment insights in seconds.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              {[
                { icon: '🎯', title: 'Accurate', desc: '95%+ sentiment classification accuracy using advanced NLP models.' },
                { icon: '⚡', title: 'Real-time', desc: 'Live web scraping from FirstCry product pages.' },
                { icon: '📊', title: 'Visual', desc: 'Interactive charts, trend graphs, and word cloud analysis.' },
                { icon: '🔒', title: 'Reliable', desc: 'Robust scraping pipeline with fallback data mechanisms.' },
              ].map((item) => (
                <div key={item.title} className="bg-gray-50 rounded-xl p-4">
                  <div className="text-2xl mb-2">{item.icon}</div>
                  <h4 className="text-sm font-bold text-gray-900 mb-1">{item.title}</h4>
                  <p className="text-xs text-gray-500 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-12 bg-indigo-50">
        <div className="max-w-4xl mx-auto px-4 grid grid-cols-2 md:grid-cols-4 gap-8">
          <StatBadge value="50K+" label="Reviews Analyzed" />
          <StatBadge value="1000+" label="Products Tracked" />
          <StatBadge value="95%" label="Accuracy Rate" />
          <StatBadge value="24/7" label="Real-time Scraping" />
        </div>
      </section>

      {/* Tech Stack */}
      <section className="py-16 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-2">Technology Stack</h2>
          <div className="w-10 h-1 bg-indigo-600 rounded-full mx-auto mb-10" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: 'React.js', desc: 'Frontend UI', color: '#61dafb', bg: '#e8f9fd' },
              { name: 'Flask', desc: 'Backend API', color: '#000000', bg: '#f5f5f5' },
              { name: 'MongoDB', desc: 'Database', color: '#47a248', bg: '#edf7ed' },
              { name: 'Selenium', desc: 'Web Scraping', color: '#43b02a', bg: '#edf9eb' },
              { name: 'Tailwind CSS', desc: 'Styling', color: '#06b6d4', bg: '#ecfeff' },
              { name: 'NLTK / spaCy', desc: 'NLP Engine', color: '#7c3aed', bg: '#f5f3ff' },
              { name: 'Recharts', desc: 'Data Viz', color: '#e84d8a', bg: '#fff0f7' },
              { name: 'Axios', desc: 'API Calls', color: '#5a29e4', bg: '#f0edff' },
            ].map((t) => (
              <div key={t.name} className="rounded-xl p-4 border border-gray-100 shadow-sm" style={{ background: t.bg }}>
                <div className="text-sm font-bold mb-1" style={{ color: t.color }}>{t.name}</div>
                <div className="text-xs text-gray-500">{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="py-16 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-2">Meet the Team</h2>
          <div className="w-10 h-1 bg-indigo-600 rounded-full mx-auto mb-10" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <TeamCard name="Member 1" role="Frontend Developer" emoji="👨‍💻" />
            <TeamCard name="Member 2" role="Frontend Developer" emoji="👩‍💻" />
            <TeamCard name="Member 3" role="Backend Developer" emoji="👨‍🔧" />
            <TeamCard name="Member 4" role="ML / NLP Engineer" emoji="👩‍🔬" />
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default AboutPage;
