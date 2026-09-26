\# CodeAtlas — Architecture



\## Pipeline

URL -> fetch zipball (GitHub API + token) -> scan -> parse (py: ast, js/ts: regex) -> resolve imports to files (with file:line evidence) -> group by folder -> ONE Gemini call (labels) -> validate or fall back -> emit Mermaid (L1 + one L2 per component) -> JSON response.



\## Grouping

Strip a single wrapper folder (src/, app/, lib/). Try folder depth 1 to 4 and take the smallest depth giving 5-25 groups. If depth 4 still gives more than 25, merge lowest-degree groups into "other". If fewer than 5 (flat repo), use the top 25 files by degree as nodes plus "other". Component id = folder path.

