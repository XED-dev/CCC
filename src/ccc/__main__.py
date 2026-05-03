"""Entry point for `python -m ccc`.

Erlaubt CLI-Aufruf via `python -m ccc <command>` als Alternative zum
`ccc`-Script-Entry-Point.
"""

from ccc.cli import main

if __name__ == "__main__":
    main()
