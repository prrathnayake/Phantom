@echo off
REM Phantom Docker Management CLI
REM Usage: phantom <command> [args]
REM Run as: python phantom start

python "%~dp0phantom" %*

if "%COMMAND%"=="status" (
    echo.
    echo [PHANTOM CONTAINERS]
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    goto :end
)

if "%COMMAND%"=="start" (
    echo.
    echo [STARTING CONTAINERS]
    docker compose -f docker-compose.yml up -d
    echo Containers started.
    goto :end
)

if "%COMMAND%"=="stop" (
    echo.
    echo [STOPPING CONTAINERS]
    docker compose -f docker-compose.yml stop
    echo Containers stopped.
    goto :end
)

if "%COMMAND%"=="restart" (
    set SERVICE=%2
    if "!SERVICE!"=="" (
        echo.
        echo [RESTARTING ALL CONTAINERS]
        docker compose -f docker-compose.yml restart
    ) else (
        echo.
        echo [RESTARTING: !SERVICE!]
        docker restart phantom-!SERVICE!
    )
    goto :end
)

if "%COMMAND%"=="logs" (
    set SERVICE=%2
    if "!SERVICE!"=="" set SERVICE=agent
    set LINES=%3
    if "!LINES!"=="" set LINES=50
    echo.
    echo [LOGS: !SERVICE!]
    docker logs --tail !LINES! phantom-!SERVICE!
    goto :end
)

if "%COMMAND%"=="logs-follow" (
    set SERVICE=%2
    if "!SERVICE!"=="" set SERVICE=agent
    echo.
    echo [FOLLOWING LOGS: !SERVICE!]
    docker logs -f --tail 50 phantom-!SERVICE!
    goto :end
)

if "%COMMAND%"=="ps" (
    docker compose -f docker-compose.yml ps
    goto :end
)

if "%COMMAND%"=="build" (
    echo.
    echo [BUILDING CONTAINERS]
    docker compose -f docker-compose.yml build --no-cache
    echo Build complete.
    goto :end
)

if "%COMMAND%"=="clean" (
    echo.
    echo [CLEANING]
    docker compose -f docker-compose.yml down -v
    echo Cleaned.
    goto :end
)

if "%COMMAND%"=="exec" (
    set SERVICE=%2
    set CMD=%3
    if "!SERVICE!"=="" (
        echo Usage: phantom-cli exec ^<service^> ^<command^>
        goto :end
    )
    if "!CMD!"=="" (
        echo Usage: phantom-cli exec ^<service^> ^<command^>
        goto :end
    )
    shift
    shift
    :collect_args
    set ARG=%~2
    if "!ARG!"=="" goto run_exec
    set CMD=!CMD! !ARG!
    shift
    goto collect_args
    :run_exec
    docker exec -it phantom-!SERVICE! sh -c "!CMD!"
    goto :end
)

if "%COMMAND%"=="help" goto help

echo Unknown command: %COMMAND%
echo.
:help
echo Phantom Docker Management CLI
echo.
echo Commands:
echo   status             - Show container status
echo   start               - Start all containers
echo   stop                - Stop all containers
echo   restart [service]  - Restart all or specific service
echo   logs [service]      - Show logs (default: agent)
echo   logs-follow        - Follow logs in real-time
echo   ps                 - Show running services
echo   build              - Rebuild containers
echo   clean              - Remove containers and volumes
echo   exec service cmd    - Execute command in container
echo   help               - Show this help

:end
endlocal