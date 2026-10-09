@echo off
rem Runs the whole ChickenKiller on this machine.
rem
rem   run-app.cmd          rebuild the Docker images, start Postgres and the web app in Docker,
rem                        update the database and content, then run the API here (Ctrl+C stops it)
rem   run-app.cmd stop     stop the Docker containers
rem
rem The API runs on this machine, not in Docker, because grading written answers runs the
rem Claude Code CLI signed in here (docs/adr/0006). Settings come from .env.local (see .env.example).
rem Open http://localhost:3000 once the API says "Application startup complete".

setlocal EnableExtensions
cd /d "%~dp0"

if /i "%~1"=="stop" goto :stop
if not "%~1"=="" if /i not "%~1"=="start" (
  echo Usage: run-app.cmd [start^|stop]
  exit /b 2
)

rem --- Settings --------------------------------------------------------------------------------
if not exist ".env.local" (
  echo .env.local is missing. Copy .env.example to .env.local and fill in the Clerk keys.
  exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env.local") do set "%%A=%%B"
if not defined API_PORT set "API_PORT=8000"
for %%V in (NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY CLERK_SECRET_KEY CLERK_ISSUER ADMIN_EMAILS) do (
  if not defined %%V (
    echo %%V is not set in .env.local.
    exit /b 1
  )
)
set "DATABASE_URL=postgresql+psycopg://learning:learning@localhost:5433/learning"
set "CLERK_AUTHORIZED_PARTIES=http://localhost:3000"

rem --- Checks ----------------------------------------------------------------------------------
where docker >nul 2>&1 || (echo Docker is not installed. & exit /b 1)
docker info >nul 2>&1 || (echo Docker Desktop is not running. Start it and try again. & exit /b 1)
where uv >nul 2>&1 || (echo uv is not installed: https://docs.astral.sh/uv/ & exit /b 1)
where claude >nul 2>&1 || echo WARNING: Claude Code isn't on PATH, so written answers can't be graded.
netstat -ano | findstr /r /c:":%API_PORT% .*LISTENING" >nul && (
  echo Port %API_PORT% is already in use, probably by an API that's still running.
  echo Stop it, or set API_PORT to another port in .env.local.
  exit /b 1
)

rem --- Docker: rebuild and start ------------------------------------------------------------
echo.
echo [1/4] Rebuilding the Docker images...
docker compose pull db || goto :failed
docker compose build --pull web || goto :failed

echo.
echo [2/4] Starting Postgres and the web app...
docker compose up -d --wait --force-recreate db web || goto :failed

rem --- API: dependencies, database, content -------------------------------------------------
echo.
echo [3/4] Updating the API, the database and the content...
pushd api
uv sync --locked || goto :failed_api
uv run alembic upgrade head || goto :failed_api
uv run content-import ../content || goto :failed_api

echo.
echo [4/4] Starting the API on http://localhost:%API_PORT% (Ctrl+C stops it).
echo       The app is at http://localhost:3000
echo       "run-app.cmd stop" stops the Docker containers.
echo.
uv run uvicorn app.main:app --host 127.0.0.1 --port %API_PORT%
popd
exit /b 0

:stop
docker compose stop web db
exit /b %errorlevel%

:failed_api
popd
:failed
echo.
echo Something failed; see the messages above.
exit /b 1
