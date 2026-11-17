# DriveLan

Simple, secure, and controlled folder sharing on the local area network (LAN), without the cloud
and without relying on native Windows file sharing (SMB). A desktop application for **Windows and
Linux**, licensed under the **GPLv3**.

> This project is under construction. The complete specification is available in `docs/FSD.md`
> (behavior) and `docs/DESIGN.md` (visual design). Progress is tracked in `docs/PLANO.md` and
> `docs/STATUS.md`.

## How It Works

Each computer runs two processes:

- `drivelan-service`: a system service with no user interface. It hosts the folders, stores the
  data (SQLite), communicates over the network (HTTP/WebSocket over TLS), and enforces the
  business rules.
- `drivelan`: a windowed application with a system tray icon, one instance per user session
  (PySide6).

## Development Environment

Requirements: Fedora (reference platform) or Windows, Git, and [uv](https://docs.astral.sh/uv/).
uv installs Python 3.12, which is required by the project.

```bash
uv sync                      # creates the .venv with Python 3.12 and the dependencies pinned in uv.lock
uv run ruff check .          # linting
uv run ruff format --check . # formatting
uv run mypy                  # type checking
uv run pytest                # tests
```

Running in development mode (available starting with Phases 5 and 6 of the plan):

```bash
uv run drivelan-service --console --dados .dev/servico-a
uv run drivelan --servico-local <socket-path>
```

## License

GPLv3 (see the `LICENSE` file). The Inter and JetBrains Mono fonts in `recursos/fontes/` are
distributed under the SIL Open Font License 1.1 (see the `OFL.txt` file in each folder).
