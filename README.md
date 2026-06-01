# Underground Track Scout

Current Version: v0.8.4 Beta

Platform Support:
✅ Windows 10 / 11

⚠ macOS support coming in a future release

## Download

The latest beta version is available in the Releases section.

Do NOT use the green "Code" button unless you want the source code.

For most users:

1. Go to Releases
2. Download the latest version
3. Extract the ZIP
4. Launch Underground Track Scout



# Underground Track Scout v0.8

DJ-focused underground music discovery prototype.

## Platform Support

Current Status: Windows Beta

✅ Windows 10 / 11 Supported

⚠ macOS Support Coming Later

⚠ Linux Support Not Tested

The current beta release is focused on Windows users.

Mac users may run the source code manually, but a native macOS build is not currently available.


## Run on Windows

```powershell
run_windows.bat
```

Or manually:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## v0.8 additions

- Submit Feedback popup for selected tracks
- Local feedback database
- Export Feedback CSV button
- Shared feedback workflow through Google Sheets Web App webhook
- Feedback Settings tab for tester name, DJ type, and webhook URL
- Feedback Summary tab
- Hover preview on result rows with track details and artwork when SoundCloud artwork is available

## Google Sheets feedback

See `GOOGLE_SHEETS_FEEDBACK_SETUP.txt`.

## Notes

Spotify remains optional. SoundCloud scanning works without Spotify configured.

## Underground Track Scout v0.8.4 Beta

New Features:
- Right-click context menu
- Double-click to open tracks
- Discovery score legend
- Grade column
- Better empty-state messages
- Status bar
- Saved search settings

Platform Support:
✅ Windows 10/11
⚠ macOS coming later

Looking for DJ beta testers and feedback.


## v0.8.3 Feedback change

Submit Feedback now opens a Google Form URL if configured in the Feedback Settings tab. If no Google Form URL is saved, it shows a Coming Soon message instead of trying to send to Google Sheets directly. Local Like/Dislike/Favorite and Export Feedback still work.


## v0.8.3 Feedback Update
- Your Google Form is preloaded: https://forms.gle/1JBeiXKLNJSWU7QN9
- Bottom button renamed to **Beta Feedback**.
- Feedback Settings tab has an **Open / Test Google Form** button.


## v0.8.3 UX update
- Feedback Settings simplified to a clean Feedback tab.
- No webhook/API fields shown to beta testers.
- Beta Feedback button opens the linked Google Form directly.

- v0.8.x
- Stability
- Feedback
- Personal Rising Artists

## RoadMap
v0.9
- BPM Detection
- Key Detection
- Right Click Menu

v1.0
- Serato Export
- Rekordbox Export
- Artist Explorer

v2.0
- User Accounts
- Cloud Sync
- Community Rising Artists
- Trending Labels
- Community Hidden Gems
