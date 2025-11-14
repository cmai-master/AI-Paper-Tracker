import axios from 'axios'
import type { Paper } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Papers
  getPapers: async (): Promise<Paper[]> => {
    const response = await client.get('/papers/')
    return response.data
  },

  getPaper: async (id: number): Promise<Paper> => {
    const response = await client.get(`/papers/${id}`)
    return response.data
  },

  getPaperStats: async () => {
    const response = await client.get('/papers/stats/count')
    return response.data
  },

  // Add more API methods as needed
}
