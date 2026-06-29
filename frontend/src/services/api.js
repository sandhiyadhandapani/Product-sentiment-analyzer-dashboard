import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
});

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
      if (review.rating >= 4) acc.positive += 1;
      else if (review.rating >= 3) acc.neutral += 1;
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

  const keywords = [product.category, product.name.split(' ')[0], product.name.split(' ').slice(-1)[0]]
    .filter(Boolean)
    .map((item) => item.toString());

  return {
    ...product,
    platform: product.platform || 'Amazon',
    sentiment,
    reviews: reviewCount,
    reviewItems: reviews,
    sentimentBreakdown: { positive, neutral, negative },
    topKeywords: keywords,
    specs: [
      `Category: ${product.category}`,
      `Price: ${product.price}`,
      `Rating: ${product.rating}/5`,
      `Description: ${product.description}`,
    ],
  };
};

const normalizeReview = (review, productPlatform = 'Amazon') => ({
  id: review.id,
  user: review.username,
  rating: review.rating,
  date: 'Recently reviewed',
  title: 'Customer Review',
  text: review.comment,
  sentiment: getSentimentFromRating(review.rating),
  platform: productPlatform,
  helpful: Math.max(5, Math.round(review.rating * 7)),
});

export const getProducts = async () => {
  const { data } = await api.get('/products');
  return data.map(normalizeProduct);
};

export const getProduct = async (productId) => {
  const { data } = await api.get(`/products/${productId}`);
  return normalizeProduct(data);
};

export const searchProducts = async (query = '') => {
  const trimmed = query.trim();
  if (!trimmed) return getProducts();

  const { data } = await api.get('/search', { params: { query: trimmed } });
  return data.map(normalizeProduct);
};

export const getProductReviews = async (productId) => {
  const { data } = await api.get(`/products/${productId}/reviews`);
  return (data.reviews || []).map((review) => normalizeReview(review, data.platform || 'Amazon'));
};

export const analyzeReview = async (reviewText) => {
  const { data } = await api.post('/analyze', { review_text: reviewText });
  return data;
};

export const healthCheck = async () => {
  const { data } = await api.get('/health');
  return data;
};
