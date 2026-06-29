export {
  analyzeReview,
  getProduct,
  getProductReviews,
  getProducts,
  healthCheck,
  searchProducts,
} from '../services/api';

export const ALL_PRODUCTS = [];
export const getProductById = async (id) => getProduct(id);
export const AMAZON_PRODUCTS = [];
export const FLIPKART_PRODUCTS = [];
