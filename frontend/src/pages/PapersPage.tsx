import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import type { Paper } from '../types'

export default function PapersPage() {
  const { data: papers, isLoading } = useQuery({
    queryKey: ['papers'],
    queryFn: () => api.getPapers(),
  })

  if (isLoading) {
    return <div>Loading...</div>
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Papers</h1>

      <div className="space-y-4">
        {papers && papers.length > 0 ? (
          papers.map((paper: Paper) => (
            <div key={paper.id} className="bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {paper.title}
                  </h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {paper.authors.join(', ')}
                  </p>
                  <p className="text-sm text-gray-700 mt-2">
                    {paper.abstract.substring(0, 300)}...
                  </p>
                  <div className="flex items-center gap-4 mt-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                      {paper.arxiv_id}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(paper.published_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="bg-white shadow rounded-lg p-6">
            <p className="text-gray-500">No papers found</p>
          </div>
        )}
      </div>
    </div>
  )
}
