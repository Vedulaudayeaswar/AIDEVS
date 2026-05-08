// API Configuration
const API_URL =
  process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://aidevs-backend.onrender.com"
    : "http://localhost:5000");

export default API_URL;
