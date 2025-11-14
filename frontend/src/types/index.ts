export interface Paper {
  id: number
  arxiv_id: string
  title: string
  abstract: string
  authors: string[]
  categories: string[]
  published_date: string
  updated_date?: string
  doi?: string
  semantic_scholar_id?: string
  citation_count: number
  influential_citation_count: number
  is_processed: boolean
  created_at: string
  updated_at: string
}

export interface User {
  id: number
  email: string
  username: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  last_login?: string
}
