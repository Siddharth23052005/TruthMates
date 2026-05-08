import axios from "axios"

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL
export const publicApiKey = import.meta.env.VITE_PUBLIC_API_KEY
export const adminApiKey = import.meta.env.VITE_ADMIN_API_KEY

const authHeaders = (apiKey) => (apiKey ? { "X-API-Key": apiKey } : {})

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: authHeaders(publicApiKey)
})

export const adminApiClient = axios.create({
  baseURL: apiBaseUrl,
  headers: authHeaders(adminApiKey)
})

// Social Monitor API helpers
export const socialApi = {
  getEntries: (params) => adminApiClient.get("/social/entries", { params }),
  getEntry: (id) => adminApiClient.get(`/social/entries/${id}`),
  reviewEntry: (id, data) => adminApiClient.post(`/social/entries/${id}/review`, data),
  triggerCrawl: (params) => adminApiClient.post("/social/crawl", null, { params }),
  getStats: () => adminApiClient.get("/social/stats"),
}
