# MEDIA DOWNLOADER PRO — NEXUS V5 (Development)

**✦ 𝑴𝒂𝒅𝒆 𝒃𝒚 𝑨𝑩𝑫𝑼𝑳𝑳𝑨𝑯 ✦**

This is a separate development build. Keep production V4 on `main` unchanged.

## Run
- Python 3.10+
- `pip install -r requirements.txt`
- Set `BOT_TOKEN` as an environment variable (never put the token in source code).
- Optional: `OWNER_ID`, `NEXUS_DATA_DIR`, `NEXUS_DOWNLOAD_DIR`, `MAX_UPLOAD_BYTES`, `MAX_PLAYLIST_ITEMS`.
- `python bot.py`

## Included
- Modular structure and SQLite usage statistics
- Public/private access control and owner commands
- Link-first inspection flow, video quality choices and MP3 extraction
- Playlist item picker with visible checkmarks
- Per-job temporary folders and limited concurrent downloads
- Support forwarding with a stable owner-reply anchor
- Branded messages

## Limits / deployment
Supported sites depend on yt-dlp extractors and each site's own restrictions. Private, login-gated, DRM-protected and restricted media are not bypassed. Spotify protected audio is not directly downloaded. The 49 MB upload threshold is conservative. Use a separate test bot token for V5; do not replace the V4 worker until end-to-end tests pass. Persist the `data/` directory on the host if you want the SQLite database and access settings to survive restarts.
