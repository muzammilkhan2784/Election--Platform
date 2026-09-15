"""
Production entry point.

Two ways to start this app, depending on where it's running:

    run.py      Development. Flask's built-in server, auto-reloads on file
                changes, shows the debugger. Single-threaded, not for real use.
                    python run.py

    server.py   Production. Run behind Gunicorn, which handles multiple
                requests at once via worker processes:
                    gunicorn -w 2 -b 0.0.0.0:3000 server:application

                  -w 2   2 worker processes (concurrent requests)
                  -b     address and port to bind to

`application` is the name Gunicorn looks for by default. Gunicorn is
Linux/macOS only, so on Windows use run.py locally and Gunicorn when
deploying to a server.
"""

from app import create_app

application = create_app()
