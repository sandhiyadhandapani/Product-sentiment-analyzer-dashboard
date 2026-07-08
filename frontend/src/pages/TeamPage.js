import React from 'react';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

// The five project teams, their responsibility and members. A single indigo
// accent is used across every card to match the rest of the site (kept simple,
// not multi-coloured).
const TEAMS = [
  {
    no: '01',
    role: 'Frontend Development',
    members: ['RASHIGA B', 'SANDHIYA G'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="3" width="20" height="14" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    no: '02',
    role: 'Backend API Development',
    members: ['RATISH G T', 'SANDHIYA D'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /><path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3" />
      </svg>
    ),
  },
  {
    no: '03',
    role: 'Web Scraping & Sentiment Analysis',
    members: ['SANDHIYA A', 'SAKTHI SUNDARAM K'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /><path d="M8 11h6M11 8v6" />
      </svg>
    ),
  },
  {
    no: '04',
    role: 'Database & Dashboard Development',
    members: ['RUBHA SREE S', 'JEEVAN B K '],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z" />
      </svg>
    ),
  },
  {
    no: '05',
    role: 'Integration, Testing & Deployment',
    members: ['SAMEER AHAMED S', 'RITHICK E'],
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
      </svg>
    ),
  },
];

// A circular avatar built from a member's initials (no external images needed).
const initials = (name) =>
  name
    .replace(/[^a-zA-Z ]/g, ' ')
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

const MemberRow = ({ name }) => (
  <div className="flex items-center gap-3 py-2">
    <div className="w-9 h-9 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center text-xs font-bold flex-shrink-0">
      {initials(name)}
    </div>
    <span className="text-sm font-semibold text-gray-800">{name}</span>
  </div>
);

const TeamCard = ({ team }) => (
  <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 card-hover flex flex-col">
    {/* Header */}
    <div className="flex items-center justify-between mb-4">
      <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
        {team.icon}
      </div>
      <span className="text-xs font-bold tracking-widest text-gray-400">TEAM {team.no}</span>
    </div>

    {/* Role */}
    <h3 className="text-base font-extrabold text-gray-900 mb-1">{team.role}</h3>
    <div className="w-10 h-1 rounded-full bg-indigo-600 mb-4" />

    {/* Members */}
    <div className="mt-auto pt-1 border-t border-gray-50">
      {team.members.map((name) => (
        <MemberRow key={name} name={name} />
      ))}
    </div>
  </div>
);

const TeamPage = () => {
  return (
    <div className="min-h-screen bg-white font-sans">
      <Navbar />

      {/* Hero */}
      <section className="hero-gradient py-16 text-white text-center">
        <div className="max-w-3xl mx-auto px-4">
          <h1 className="text-4xl font-extrabold mb-4">Meet Our Team</h1>
          <div className="w-12 h-1 bg-indigo-300 rounded-full mx-auto mb-5" />
          <p className="text-gray-300 text-base leading-relaxed">
            The people behind the Product Sentiment Analyzer — five focused teams that
            designed, built, and shipped every part of the platform.
          </p>
        </div>
      </section>

      {/* Stats strip */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 py-8 grid grid-cols-2 gap-6 text-center">
          <div>
            <div className="text-3xl font-extrabold text-indigo-600 mb-1">5</div>
            <div className="text-sm text-gray-500">Teams</div>
          </div>
          <div>
            <div className="text-3xl font-extrabold text-indigo-600 mb-1">10</div>
            <div className="text-sm text-gray-500">Members</div>
          </div>
        </div>
      </section>

      {/* Team grid */}
      <section className="py-14 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {TEAMS.map((team) => (
              <TeamCard key={team.no} team={team} />
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default TeamPage;
