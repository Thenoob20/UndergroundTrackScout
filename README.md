# Underground Track Scout v0.8

DJ-focused underground music discovery prototype.

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
