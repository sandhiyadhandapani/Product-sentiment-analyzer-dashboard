import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import DashboardPage from './pages/DashboardPage';
import AboutPage from './pages/AboutPage';
import FeaturesPage from './pages/FeaturesPage';
import HowItWorksPage from './pages/HowItWorksPage';
import TeamPage from './pages/TeamPage';
import ProductSearchPage from './pages/ProductSearchPage';
import ProductDetailsPage from './pages/ProductDetailsPage';
import ReviewDisplayPage from './pages/ReviewDisplayPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/how-it-works" element={<HowItWorksPage />} />
        <Route path="/team" element={<TeamPage />} />
        <Route path="/contact" element={<TeamPage />} />
        <Route path="/search" element={<ProductSearchPage />} />
        <Route path="/product-details" element={<ProductDetailsPage />} />
        <Route path="/details" element={<ProductDetailsPage />} />
        <Route path="/product/:id" element={<ProductDetailsPage />} />
        <Route path="/reviews/:id" element={<ReviewDisplayPage />} />
      </Routes>
    </Router>
  );
}

export default App;
