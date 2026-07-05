import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 20000,
});

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
  const reviews = Array.isArray(product.reviews) ? product.reviews : [];
  const reviewCount = reviews.length;

  const scoreSummary = reviews.reduce(
    (acc, review) => {
      const rating = Number(review.review_rating ?? review.rating ?? 0);
      if (rating >= 4) acc.positive += 1;
      else if (rating >= 3) acc.neutral += 1;
      else acc.negative += 1;
      return acc;
    },
    { positive: 0, neutral: 0, negative: 0 }
  );

  const total = reviewCount || 1;
  const positive = Math.round((scoreSummary.positive / total) * 100);
  const neutral = Math.round((scoreSummary.neutral / total) * 100);
  const negative = 100 - positive - neutral;

  const sentiment =
    positive > neutral && positive > negative
      ? 'Positive'
      : negative > positive && negative > neutral
      ? 'Negative'
      : 'Neutral';

  const productName = product.product_name || product.name || product.product || 'Product';
  const productPrice = product.product_price || product.price || 'N/A';
  const productRating = Number(product.product_rating ?? product.rating ?? 0);

  return {
    id: product.product || product.name || product.product_name || 'analysis-result',
    name: productName,
    platform: (product.platform || 'FirstCry').toString().replace(/^./, (c) => c.toUpperCase()),
    price: productPrice,
    rating: productRating,
    reviews: reviewCount,
    description: product.message || 'Live analysis from retailer data.',
    image: normalizeImageUrl(product.product_image || product.image || ''),
    category: product.category || 'Electronics',
    totalRatings: product.total_ratings || product.totalRatings || 0,
    reviewItems: reviews,
    sentiment,
    sentimentBreakdown: { positive, neutral, negative },
    topKeywords: [product.category, productName.split(' ')[0], productName.split(' ').slice(-1)[0]].filter(Boolean),
    specs: [
      `Category: ${product.category || 'Electronics'}`,
      `Price: ${productPrice}`,
      `Rating: ${productRating}/5`,
      `Description: ${product.message || 'Live analysis from retailer data.'}`,
    ],
    raw: product,
  };
};

const normalizeReview = (review, productPlatform = 'FirstCry') => {
  const rating = Number(review.review_rating ?? review.rating ?? 0);
  return {
    id: review.id || `${productPlatform}-${Math.random().toString(36).slice(2, 8)}`,
    user: 'Customer',
    rating,
    date: 'Recently reviewed',
    title: 'Customer Review',
    text: review.review_text || review.comment || '',
    sentiment: getSentimentFromRating(rating),
    platform: productPlatform,
    helpful: Math.max(5, Math.round(rating * 7)),
  };
};

export const getProducts = async () => {
  const { data } = await api.get('/products');
  return data.map(normalizeProduct);
};

export const getProduct = async (query) => {
  const data = await analyzeProduct(query, 'firstcry');
  return normalizeProduct(data);
};

export const analyzeProduct = async (productName, platform = 'firstcry') => {
  try {
    const response = await axios.post('http://127.0.0.1:8001/analyze', {
      product: productName,
      platform,
    });

    if (response.status !== 200) {
      throw new Error(`HTTP_${response.status}`);
    }

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        throw new Error('NETWORK_ERROR');
      }
      if (error.response.status !== 200) {
        throw new Error(`HTTP_${error.response.status}`);
      }
    }
    throw error;
  }
};

export const searchProducts = async (query = '', platform = 'firstcry') => {
  const trimmed = query.trim();
  if (!trimmed) return { products: [], message: 'Please enter a product name to analyze.' };

  try {
    const data = await analyzeProduct(trimmed, platform);
    return {
      products: [normalizeProduct(data)],
      message: data.message || 'Analysis completed successfully.',
    };
  } catch (error) {
    const message = error?.message === 'NETWORK_ERROR' || error?.message?.startsWith('HTTP_')
      ? 'Unable to load products right now.'
      : 'Unable to load products right now.';
    return { products: [], message };
  }
};

export const getProductReviews = async (query) => {
  const data = await analyzeProduct(query, 'firstcry');
  return (data.reviews || []).map((review) => normalizeReview(review, data.platform || 'FirstCry'));
};

export const analyzeReview = async (reviewText) => {
  const { data } = await api.post('/analyze', { review_text: reviewText });
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};
