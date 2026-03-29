Original prompt: Create a standalone Tetris game using Python and embed into a HTML front end as a web app.

- Replaced the event-store prototype architecture with a standalone Python simulation plan.
- Implemented the standalone backend and canvas frontend with in-memory sessions and automation hooks (`render_game_to_text`, `advanceTime`).
- Smoke check passed: `py_compile` and `from web.tetris_api import app` both succeed.
- Browser automation passed with the provided Playwright client after starting the local server on port 8001; screenshots confirmed board rendering, movement, gravity, rotation, and hard drop with next-piece spawn.
- Added a real stdio MCP server that exposes the Tetris controls as tools and drives the running web app over HTTP.
- Added pytest coverage for both the FastAPI surface and the MCP control layer.
- Validation passed: `python -m pytest -q` now succeeds with 2 tests.
- TODO: no major blockers found; if iterating further, add richer features such as ghost pieces, hold, sound, persistent high scores, or an HTTP-mounted MCP transport.
