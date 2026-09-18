"""
Claude Code hooks: `run.py session` (SessionStart) and `run.py watch`
(UserPromptSubmit). Runs the package that ships inside the plugin, so it
works without `pip install`. Its only network call is a throttled
`git fetch` of the main branch; it sends nothing anywhere else.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trazabilidad.cli import main  # noqa: E402

command = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("session", "watch") else "session"
sys.exit(main([command]))
