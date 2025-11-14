import { useState } from 'react'

export default function SearchPage() {
  const [query, setQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement search
    console.log('Searching for:', query)
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Search Papers</h1>

      <div className="bg-white shadow rounded-lg p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label
              htmlFor="search"
              className="block text-sm font-medium text-gray-700"
            >
              Search Query
            </label>
            <input
              type="text"
              id="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              placeholder="Enter keywords, topics, or authors..."
            />
          </div>
          <button
            type="submit"
            className="inline-flex justify-center rounded-md border border-transparent bg-primary-600 py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            Search
          </button>
        </form>

        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Results</h2>
          <p className="text-gray-500">Enter a search query to see results</p>
        </div>
      </div>
    </div>
  )
}
