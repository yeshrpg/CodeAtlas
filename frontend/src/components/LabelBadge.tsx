import type { Component } from '../types'

type LabelSource = Component['label']['source']

interface ComponentBadgesProps {
  source: LabelSource | undefined
  isOtherMerge: boolean | undefined
}

/**
 * Stage B4: per-component badges, shared by ComponentList and SidePanel.
 * "AI-labeled" (accent) vs "Heuristic" (neutral) are visually distinct;
 * "Other (merged small folders)" is informational — neutral dashed outline,
 * never error/red styling. Renders nothing for absent fields.
 */
function ComponentBadges({ source, isOtherMerge }: ComponentBadgesProps) {
  return (
    <>
      {source === 'llm' ? (
        <span className="label-badge-ai">AI-labeled</span>
      ) : source === 'heuristic' ? (
        <span className="label-badge-heuristic">Heuristic</span>
      ) : null}
      {isOtherMerge === true && (
        <span className="label-badge-merged">
          Other (merged small folders)
        </span>
      )}
    </>
  )
}

export default ComponentBadges
