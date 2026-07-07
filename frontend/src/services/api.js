import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 30000,
});

// Retry wrapper for API calls
const withRetry = async (fn, maxRetries = 3, delayMs = 1000) => {
  let lastError;
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`[API] Attempt ${attempt}/${maxRetries}`);
      const result = await fn();
      console.log('[API] Success on attempt', attempt);
      return result;
    } catch (error) {
      lastError = error;
      console.error(`[API] Attempt ${attempt} failed:`, error.message);
      if (attempt < maxRetries) {
        const backoffDelay = delayMs * Math.pow(2, attempt - 1);
        console.log(`[API] Retrying after ${backoffDelay}ms...`);
        await new Promise(resolve => setTimeout(resolve, backoffDelay));
      }
    }
  }
  console.error('[API] All retries exhausted');
  throw lastError;
};

export const ANALYSIS_STORAGE_KEY = 'product-analysis-result';

export const saveAnalyzedProduct = (product) => {
  if (!product) return;
  try {
    localStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify(product));
  } catch (error) {
    console.warn('Unable to persist analyzed product', error);
  }
};

export const getStoredAnalyzedProduct = () => {
  try {
    const raw = localStorage.getItem(ANALYSIS_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (error) {
    return null;
  }
};

const normalizeImageUrl = (image) => {
  if (!image || typeof image !== 'string') return '';

  const value = image.trim();
  if (!value) return '';

  const withProtocol = value.startsWith('//') ? `https:${value}` : value;
  const lowered = withProtocol.toLowerCase();

  if (lowered.includes('/logo') || lowered.includes('/static') || lowered.includes('placeholder') || lowered.includes('assets')) {
    return '';
  }

  return withProtocol;
};

const getSentimentFromRating = (rating) => {
  if (rating >= 4) return 'Positive';
  if (rating >= 3) return 'Neutral';
  return 'Negative';
};

const normalizeProduct = (product) => {
  console.log('[API] normalizeProduct called with:', product);
  
  if (!product || typeof product !== 'object') {
    console.error('[API] Invalid product data:', product);
    product = {};
  }

  const reviews = Array.isArray(product.reviews) ? product.reviews : [];
  const reviewCount = reviews.length;
  console.log('[API] Review count:', reviewCount);

  const scoreSummary = reviews.reduce(
    (acc, review) => {
      const sentiment = review.sentiment || getSentimentFromRating(Number(review.review_rating ?? review.rating ?? 0));
      if (sentiment === 'Positive') acc.positive += 1;
      else if (sentiment === 'Neutral') acc.neutral += 1;
      else acc.negative += 1;
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0 }
  );

  const total = reviewCount || 1;
  const positive = Math.round((scoreSummary.positive / total) * 100);
  const neutral = Math.round((scoreSummary.neutral / total) * 100);
  const negative = Math.round((scoreSummary.negative / total) * 100);

  const sentiment =
    positive > neutral && positive > negative
      ? 'Positive'
      : negative > positive && negative > neutral
      ? 'Negative'
      : 'Neutral';

  const productName = product.product_name || product.name || product.product || 'Product';
  const productPrice = product.product_price || product.price || product.current_price || 'N/A';
  const productRating = Number(product.product_rating ?? product.rating ?? 0);
  const totalRatings = Number(product.total_ratings ?? product.totalRatings ?? 0);
  const totalReviews = Number(product.total_reviews ?? product.totalReviews ?? reviewCount);

  const normalized = {
    id: product.product || product.name || product.product_name || 'analysis-result',
    name: productName || 'Unknown Product',
    platform: (product.platform || 'FirstCry').toString().replace(/^./, (c) => c.toUpperCase()),
    price: productPrice || 'N/A',
    rating: productRating || 0,
    reviews: reviewCount,
    totalRatings: totalRatings || 0,
    totalReviews: totalReviews || 0,
    description: product.description || product.message || 'Live analysis from retailer data.',
    image: normalizeImageUrl(product.product_image || product.image || ''),
    category: product.category || 'Baby Products',
    reviewItems: reviews,
    sentiment,
    sentimentBreakdown: { positive, neutral, negative },
    topKeywords: [product.category, productName.split(' ')[0], productName.split(' ').slice(-1)[0]].filter(Boolean),
    specs: [
      `Category: ${product.category || 'Baby Products'}`,
      `Price: ${productPrice || 'N/A'}`,
      `Rating: ${productRating || 0}/5`,
      `Total Ratings: ${totalRatings || 0}`,
      `Description: ${product.description || product.message || 'Live analysis from retailer data.'}`,
    ],
    raw: product,
  };
  
  console.log('[API] Normalized product result:', normalized);
  return normalized;
};

const normalizeReview = (review, productPlatform = 'FirstCry') => {
  const rating = Number(review.review_rating ?? review.rating ?? 0);
  const sentiment = review.sentiment || getSentimentFromRating(rating);
  return {
    id: review.id || `${productPlatform}-${Math.random().toString(36).slice(2, 8)}`,
    user: review.username || review.reviewer_name || 'Customer',
    rating,
    date: review.review_date || review.date || 'Recently reviewed',
    title: review.title || 'Customer Review',
    text: review.review_text || review.comment || review.text || '',
    sentiment,
    platform: review.platform || productPlatform,
    helpful: Math.max(5, Math.round(rating * 7)),
  };
};

export const getProducts = async () => {
  const { data } = await api.get('products');
  return data.map(normalizeProduct);
};

export const getProduct = async (query) => {
  console.log('[API] getProduct called with:', query);
  const data = await analyzeProduct(query, 'firstcry');
  console.log('[API] Normalizing product data...');
  const normalized = normalizeProduct(data);
  console.log('[API] Normalized product:', normalized);
  return normalized;
};

export const analyzeProduct = async (productName, platform = 'firstcry') => {
  console.log('[API] analyzeProduct called with:', { productName, platform });
  
  return withRetry(async () => {
    try {
      console.log('[API] Making POST request to /analyze');
      const response = await api.post('analyze', {
        product: productName,
        platform,
      });

      console.log('[API] Response status:', response.status);
      console.log('[API] Response data:', response.data);

      if (response.status !== 200) {
        throw new Error(`HTTP_${response.status}`);
      }

      if (!response.data) {
        console.error('[API] Response data is null/undefined');
        throw new Error('NO_DATA');
      }

      return response.data;
    } catch (error) {
      console.error('[API] analyzeProduct error:', error);
      if (axios.isAxiosError(error)) {
        if (!error.response) {
          console.error('[API] Network error - no response');
          throw new Error('NETWORK_ERROR');
        }
        console.error('[API] HTTP error:', error.response.status, error.response.data);
        if (error.response.status !== 200) {
          throw new Error(`HTTP_${error.response.status}`);
        }
      }
      throw error;
    }
  });
};

export const searchProducts = async (query = '', platform = 'firstcry') => {
  console.log('[API] searchProducts called with:', { query, platform });
  const trimmed = query.trim();
  if (!trimmed) {
    console.log('[API] Empty query, returning empty result');
    return { products: [], message: 'Please enter a product name to analyze.' };
  }

  try {
    console.log('[API] Calling analyzeProduct...');
    const data = await analyzeProduct(trimmed, platform);
    console.log('[API] analyzeProduct returned data:', data);
    
    if (!data || Object.keys(data).length === 0) {
      console.warn('[API] analyzeProduct returned empty data');
      return { products: [], message: 'No product data received from server.' };
    }

    const normalized = normalizeProduct(data);
    console.log('[API] Normalized product:', normalized);
    
    return {
      products: [normalized],
      message: data.message || 'Analysis completed successfully.',
    };
  } catch (error) {
    console.error('[API] searchProducts error:', error);
    const message = error?.message === 'NETWORK_ERROR' 
      ? 'Network error. Please check your connection and try again.'
      : error?.message?.startsWith('HTTP_')
      ? `Server error (${error.message}). Please try again.`
      : error?.message === 'NO_DATA'
      ? 'No data received from server. Please try again.'
      : 'Unable to load products right now. Please try again.';
    console.log('[API] Returning error message:', message);
    return { products: [], message };
  }
};

export const getProductReviews = async (query) => {
  console.log('[API] getProductReviews called with:', query);
  const data = await analyzeProduct(query, 'firstcry');
  console.log('[API] analyzeProduct returned data:', data);
  console.log('[API] Reviews from data:', data.reviews);
  console.log('[API] Number of reviews:', data.reviews?.length || 0);
  
  const reviews = (data.reviews || []).map((review) => normalizeReview(review, data.platform || 'FirstCry'));
  console.log('[API] Normalized reviews:', reviews);
  return reviews;
};

export const analyzeReview = async (reviewText) => {
  const { data } = await api.post('review-analyze', { review_text: reviewText });
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('health');
  return data;
};
