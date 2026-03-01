# Premier League Tracker (Python CLI)

A terminal-based Python app that fetches live Premier League data (table, fixtures, scorers) from a football API and prints it in a clean format.

## Features
- View current league table (position, points, goal difference)
- Display upcoming fixtures
- Show top scorers
- Menu-driven CLI interface
- API error handling (timeouts/failed requests)

## Tech Stack
Python, Requests, REST API

## Run Locally
1. Install dependencies:
   pip install requests
2. Add your API key (see fpl_api.py or use an environment variable if you’ve set that up)
3. Run:
   python main.py

## Future Improvements
- Move API key to environment variables
- Add unit tests for key functions
- Improve input validation and formatting
