import type { AnalysisResult } from '../types'

type RepoInfo = AnalysisResult['repo']

interface RepoHeaderProps {
  repo: RepoInfo
}

/**
 * Stage B6: repo-identity header for a done real analysis — which repo was
 * analyzed and basic scan stats. Shown above the diagram; renders nothing
 * when there is no result (callers gate on that). `is_public: false` is
 * displayed plainly, never as an error.
 */
function RepoHeader({ repo }: RepoHeaderProps) {
  return (
    <section className="repo-header" aria-label="Analyzed repository">
      <h2 className="repo-title">
        {repo.owner}/{repo.name}
      </h2>
      <p className="component-meta">
        <span className="stat-chip" title="Default branch">
          {repo.default_branch}
        </span>{' '}
        <span className="stat-chip" title={`Full commit sha: ${repo.commit_sha}`}>
          <code>{repo.commit_sha.slice(0, 7)}</code>
        </span>{' '}
        <span className="stat-chip">
          {repo.total_files_scanned} scanned
        </span>{' '}
        <span className="stat-chip">
          {repo.total_files_skipped} skipped
        </span>
        {!repo.is_public && <span className="stat-chip">private</span>}
      </p>
      {repo.is_flat_repo && (
        <p className="empty-note">Flat repository structure.</p>
      )}
    </section>
  )
}

export default RepoHeader
