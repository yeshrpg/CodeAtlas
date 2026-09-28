import type { AnalysisResult } from '../types'

// Stage B1 test fixtures — small hand-written objects matching the real
// backend contract exactly (verified by `tsc`, since they are typed as
// AnalysisResult). Used to test Analyze state transitions without hammering
// the live API. Useful later as sample data for B2/B3 rendering work.

export const realDoneFixture: AnalysisResult = {
  analysis_id: 'test-analysis-001',
  status: 'done',
  error: null,
  created_at: '2026-09-28T10:00:00Z',
  completed_at: '2026-09-28T10:00:42Z',
  repo: {
    owner: 'octo',
    name: 'hello-world',
    default_branch: 'main',
    commit_sha: 'abc123def456',
    is_public: true,
    total_files_scanned: 3,
    total_files_skipped: 1,
    total_size_bytes: 4096,
    is_flat_repo: true,
  },
  components: [
    {
      id: 'comp-api',
      folder_path: 'api',
      files: ['api/main.py', 'api/routes.py'],
      label: {
        name: 'API Layer',
        summary: 'HTTP routes and handlers',
        source: 'heuristic',
      },
      is_other_merge: false,
    },
    {
      id: 'comp-db',
      folder_path: 'db',
      files: ['db/models.py'],
      label: { name: 'DB Layer', summary: 'Data models', source: 'llm' },
      is_other_merge: false,
    },
  ],
  edges: [
    {
      source_id: 'comp-api',
      target_id: 'comp-db',
      import_count: 2,
      evidence: ['api/routes.py imports db.models'],
    },
  ],
  unresolved: {
    imports: [
      {
        raw: 'import nonexistent',
        module: 'nonexistent',
        line: 1,
        status: 'unresolved',
        resolved_path: null,
      },
    ],
  },
  parsed_files: [
    {
      path: 'api/main.py',
      language: 'python',
      line_count: 20,
      docstring: null,
      imports: [
        {
          raw: 'from fastapi import FastAPI',
          module: 'fastapi',
          line: 1,
          status: 'external',
          resolved_path: null,
        },
      ],
      symbols: [
        {
          name: 'app',
          kind: 'variable',
          line: 3,
          docstring: null,
          route_path: null,
          route_methods: [],
        },
        {
          name: 'health',
          kind: 'route',
          line: 5,
          docstring: 'Health check',
          route_path: '/health',
          route_methods: ['GET'],
        },
      ],
      parse_error: null,
    },
  ],
  mermaid: { diagram_type: 'graph TD', source: 'graph TD\n  A-->B' },
  llm_model: null,
  llm_call_count: 0,
}

export const realFailedFixture: AnalysisResult = {
  analysis_id: 'test-analysis-002',
  status: 'failed',
  error: 'Clone failed: repository not found or not public.',
  created_at: '2026-09-28T11:00:00Z',
  completed_at: '2026-09-28T11:00:05Z',
  repo: {
    owner: 'octo',
    name: 'no-such-repo',
    default_branch: '',
    commit_sha: '',
    is_public: true,
    total_files_scanned: 0,
    total_files_skipped: 0,
    total_size_bytes: 0,
    is_flat_repo: false,
  },
  components: [],
  edges: [],
  unresolved: { imports: [] },
  parsed_files: [],
  mermaid: null,
  llm_model: null,
  llm_call_count: 0,
}

// Stage B2: a "done" analysis whose backend produced no diagram — the
// DiagramView must show its empty state, never crash.
export const realNullMermaidFixture: AnalysisResult = {
  ...realDoneFixture,
  analysis_id: 'test-analysis-003',
  repo: { ...realDoneFixture.repo },
  components: [...realDoneFixture.components],
  edges: [...realDoneFixture.edges],
  unresolved: { imports: [...realDoneFixture.unresolved.imports] },
  parsed_files: [...realDoneFixture.parsed_files],
  mermaid: null,
}

// Stage B3: richer graph for drill-down tests — 4 components (one edgeless),
// 3 edges with evidence, and parsed_files covering only some component files.
export const realB3Fixture: AnalysisResult = {
  analysis_id: 'test-analysis-b3',
  status: 'done',
  error: null,
  created_at: '2026-09-28T12:00:00Z',
  completed_at: '2026-09-28T12:01:10Z',
  repo: {
    owner: 'octo',
    name: 'shop',
    default_branch: 'main',
    commit_sha: 'deadbeefcafe',
    is_public: true,
    total_files_scanned: 6,
    total_files_skipped: 0,
    total_size_bytes: 8192,
    is_flat_repo: false,
  },
  components: [
    {
      id: 'comp-api',
      folder_path: 'api',
      files: ['api/main.py', 'api/routes.py'],
      label: { name: 'API Layer', summary: 'HTTP routes', source: 'llm' },
      is_other_merge: false,
    },
    {
      id: 'comp-auth',
      folder_path: 'auth',
      files: ['auth/login.py'],
      label: { name: 'Auth', summary: 'Login and tokens', source: 'llm' },
      is_other_merge: false,
    },
    {
      id: 'comp-db',
      folder_path: 'db',
      files: ['db/models.py'],
      label: { name: 'DB Layer', summary: 'Data models', source: 'heuristic' },
      is_other_merge: false,
    },
    {
      id: 'comp-docs',
      folder_path: 'docs',
      files: ['docs/README.md'],
      label: { name: 'Docs', summary: 'Guides', source: 'heuristic' },
      is_other_merge: true,
    },
  ],
  edges: [
    {
      source_id: 'comp-api',
      target_id: 'comp-auth',
      import_count: 3,
      evidence: ['api/routes.py:4', 'api/routes.py:9'],
    },
    {
      source_id: 'comp-api',
      target_id: 'comp-db',
      import_count: 1,
      evidence: ['api/main.py:2'],
    },
    {
      source_id: 'comp-auth',
      target_id: 'comp-db',
      import_count: 2,
      evidence: [],
    },
  ],
  unresolved: {
    imports: [
      {
        raw: 'from utils.helpers import format_date',
        module: 'utils.helpers',
        line: 6,
        status: 'unresolved',
        resolved_path: null,
      },
      {
        raw: 'import stripe',
        module: 'stripe',
        line: 2,
        status: 'unresolved',
        resolved_path: null,
      },
      {
        raw: 'from config import settings',
        module: 'config',
        line: 3,
        status: 'unresolved',
        resolved_path: null,
      },
    ],
  },
  parsed_files: [
    {
      path: 'api/routes.py',
      language: 'python',
      line_count: 30,
      docstring: 'Route handlers.',
      imports: [
        {
          raw: 'from auth.login import require_user',
          module: 'auth.login',
          line: 4,
          status: 'resolved',
          resolved_path: 'auth/login.py',
        },
      ],
      symbols: [
        {
          name: 'list_items',
          kind: 'route',
          line: 9,
          docstring: 'List all items.',
          route_path: '/items',
          route_methods: ['GET'],
        },
        {
          name: 'helper',
          kind: 'function',
          line: 20,
          docstring: null,
          route_path: null,
          route_methods: [],
        },
      ],
      parse_error: null,
    },
    {
      path: 'db/models.py',
      language: 'python',
      line_count: 15,
      docstring: null,
      imports: [],
      symbols: [
        {
          name: 'Item',
          kind: 'class',
          line: 3,
          docstring: 'An item.',
          route_path: null,
          route_methods: [],
        },
      ],
      parse_error: null,
    },
  ],
  mermaid: {
    diagram_type: 'graph TD',
    source: 'graph TD\n  API-->Auth\n  API-->DB\n  Auth-->DB',
  },
  llm_model: 'gemini-test',
  llm_call_count: 1,
}
