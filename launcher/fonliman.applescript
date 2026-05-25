-- fonliman launcher
--
-- One-shot launcher compiled into /Applications/fonliman.app via osacompile.
-- Steps:
--   1. Ensure Docker Desktop is running (start it if not, wait up to 60 s).
--   2. `docker compose up -d` in the project directory — no-ops if the
--      container is already running.
--   3. Poll /api/health until it responds (so the browser doesn't open on
--      a blank tab while Python is still booting).
--   4. Open http://localhost:8765 in the default browser.
--
-- If any step takes too long, a dialog explains what happened.

on run
    set projectPath to "PROJECT_PATH_PLACEHOLDER"
    set dockerBin to "PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

    -- Step 1: is Docker daemon reachable?
    set dockerReady to false
    try
        do shell script dockerBin & " && docker info > /dev/null 2>&1"
        set dockerReady to true
    on error
        -- Docker Desktop is probably not running. Boot it.
        try
            tell application "Docker" to activate
        on error
            display dialog "Docker Desktop bulunamadı. Önce Docker Desktop'ı yükleyip bir kez aç." buttons {"Tamam"} default button 1 with icon stop
            return
        end try

        -- Wait up to 90 seconds for the daemon to come up.
        repeat 90 times
            delay 1
            try
                do shell script dockerBin & " && docker info > /dev/null 2>&1"
                set dockerReady to true
                exit repeat
            end try
        end repeat
    end try

    if not dockerReady then
        display dialog "Docker Desktop 90 saniye içinde hazır olmadı. Manuel olarak açıp tekrar dene." buttons {"Tamam"} default button 1 with icon stop
        return
    end if

    -- Step 2: bring the container up (idempotent — already-running == no-op).
    try
        do shell script dockerBin & " && cd " & quoted form of projectPath & " && docker compose up -d"
    on error errMsg
        display dialog "Container başlatılamadı:" & return & errMsg buttons {"Tamam"} default button 1 with icon stop
        return
    end try

    -- Step 3: wait for the API to answer. Backend startup needs ~2-3 s, plus
    -- catch-up sync in background (which doesn't block the health endpoint).
    set apiReady to false
    repeat 30 times
        try
            do shell script "curl -fsS http://localhost:8765/api/health > /dev/null"
            set apiReady to true
            exit repeat
        on error
            delay 0.5
        end try
    end repeat

    if not apiReady then
        display dialog "fonliman API 15 saniyede cevap vermedi. `docker logs fonliman` ile loglara bak." buttons {"Tamam"} default button 1 with icon caution
        return
    end if

    -- Step 4: open in default browser.
    do shell script "open http://localhost:8765"
end run
