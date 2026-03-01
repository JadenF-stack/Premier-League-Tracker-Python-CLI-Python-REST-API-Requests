from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fpl_api import FootballDataError, get_matches, get_scorers, get_standings


# Simple aliases so users can type common shortcuts instead of exact official names.
TEAM_ALIASES = {
    "man utd": "Manchester United",
    "manchester utd": "Manchester United",
    "man united": "Manchester United",
    "united": "Manchester United",
    "mufc": "Manchester United",
    "mu": "Manchester United",
    "spurs": "Tottenham Hotspur",
    "wolves": "Wolverhampton Wanderers FC",
}


def parse_utc(utc_str: str) -> datetime:
    """Convert API utcDate like '2026-02-28T15:00:00Z' to Python datetime."""
    return datetime.fromisoformat(utc_str.replace("Z", "+00:00"))


def normalize_team_query(query: Optional[str]) -> str:
    """
    Normalise team name input:
    - If blank, default to Manchester United
    - Apply simple aliases
    """
    if not query or not query.strip():
        return "Manchester United"
    cleaned = query.strip()
    return TEAM_ALIASES.get(cleaned.lower(), cleaned)


def get_official_team_names(standings_data: Dict[str, Any]) -> List[str]:
    """
    I made this function because the API returns a big nested JSON structure
    and I only really needed the official team names.

    The standings JSON looks like:
      standings_data["standings"][0]["table"]  -> list of rows (one per team)
    and each row has:
      row["team"]["name"] -> the team's official name

    I use these official names later to:
    - match what the user types to real team names
    - avoid spelling mistakes / random nicknames not recognised by the API
    """
    # This is the actual league table list inside the JSON (1 row per team)
    table = standings_data["standings"][0]["table"]

    team_names: List[str] = []  # this will store all the team names

    # Loop through every team row and pull out the team name
    for row in table:
        name = row["team"]["name"]
        team_names.append(name)
       
        # Return the completed list of official team names
    return team_names


def resolve_team_name(user_query: Optional[str], official_names: List[str]) -> str:
    """
  I made this because the API only recognises the official team names,
    but users will type things like "man utd", "spurs", or sometimes just "united".

    This function tries to map whatever the user types to a real team name from the table.

    How it works (simple rules):
    1) Normalise the input first (strip spaces + aliases + default team if blank)
    2) Try an exact match (ignoring upper/lowercase)
    3) If that fails, try a substring match (e.g., "United" contained in "Manchester United")
    """
    # Clean the user input and apply aliases (e.g. "man utd" === "Manchester United")
    wanted = normalize_team_query(user_query)
 
    #Exact match first (safest and avoids wrong matches)
    for name in official_names:
        if name.lower() == wanted.lower():
            return name
    
    # Fallback: substring match (more flexible, but could match multiple teams)
    matches = [name for name in official_names if wanted.lower() in name.lower()]

    # If there are multiple matches, it chooses the shortest one as a simple "best guess"
    if matches:
        matches.sort(key=len)
        return matches[0] 
    
    # If matching fails here, we show an error message to the user.
    return wanted


def print_table() -> None:
    """Fetch the current league table from the API and print it in neat columns."""
    # Call the API helper (returns a nested JSON dictionary)
    data = get_standings()

    # The league table is inside standings[0]["table"] in the football-data response
    table = data["standings"][0]["table"]


    # Print a header row and a divider line so the output is readable
    print("\nPOS  TEAM                          PTS  GD  P")
    print("-" * 55)

    # Each row contains a team's league position and stats
    for row in table:
        # rjust/ljust is used to line up the columns nicely in the terminal
        pos = str(row["position"]).rjust(2)
        name = row["team"]["name"][:28].ljust(28) # trim long names so formatting stays aligned
        pts = str(row["points"]).rjust(3)
        gd = str(row["goalDifference"]).rjust(3)
        played = str(row["playedGames"]).rjust(2)
        print(f"{pos}   {name}   {pts}  {gd}  {played}")


def find_team_row(team_name: str) -> Optional[Dict[str, Any]]:
    """Look through the league table and return the row for a specific team.
    Returns None if the team isn't found."""

    data = get_standings()
    table = data["standings"][0]["table"]

    # Loop through every team row until we find the matching team name
    for row in table:
        if row["team"]["name"] == team_name:
            return row
    return None


def print_position() -> None:
    """Ask for a team, then print their league position + basic stats from the table."""
    standings = get_standings()
    official = get_official_team_names(standings)
    
    # Get the user's team input (blank defaults to Man United through normalize_team_query)
    team_query = input("\nEnter team name (press Enter for Man United): ")
    team = resolve_team_name(team_query, official)
    
    # Find that team in the standings table
    row = find_team_row(team)
    if not row:
        print(f"Couldn't find '{team_query}'. Try the exact name from the table.")
        return
    
    # Print a small summary for the team
    print(f"\n{team}")
    print("-" * 55)
    print(
        f"Position: {row['position']} | Points: {row['points']} | "
        f"Played: {row['playedGames']} | GD: {row['goalDifference']}"
    )


def print_fixtures() -> None:
    """Ask the user for a team name and how many fixtures they want,
    then print the next scheduled matches for that team."""
    # Get official names so we can match user input properly
    standings = get_standings()
    official = get_official_team_names(standings)

    team_query = input("\nEnter team name (press Enter for Man United): ")
    team = resolve_team_name(team_query, official)
    
    # Read how many fixtures to show (if not a number, default to 5)
    limit_str = input("How many fixtures? (default 5): ").strip()
    limit = int(limit_str) if limit_str.isdigit() else 5

    # Request upcoming fixtures; we grab a larger list and filter it ourselves
    scheduled = get_matches(status="SCHEDULED", limit=300).get("matches", [])

    # Keep only matches where the chosen team is either home or away    
    team_games = [
        m for m in scheduled
        if team in (m["homeTeam"]["name"], m["awayTeam"]["name"])
    ][:max(0, limit)] # cap it to the number the user asked for

    print(f"\nNEXT {len(team_games)} FIXTURES — {team}")
    print("-" * 55)

    if not team_games:
        print("No upcoming fixtures found.")
        return
    
    # Print each fixture with date/time and teams
    for m in team_games:
        dt = parse_utc(m["utcDate"]).strftime("%d %b %Y %H:%M")
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        print(f"{dt}  {home} vs {away}")


def print_scorers_menu() -> None:
    """Ask the user how many scorers to show, then print the PL top scorers list."""
    top_str = input("\nShow top how many scorers? (default 10): ").strip()
    top = int(top_str) if top_str.isdigit() else 10
    
    # Call the scorers endpoint via the API helper
    data = get_scorers(limit=top)
    scorers = data.get("scorers", [])

    print(f"\nTOP {len(scorers)} GOALSCORERS")
    print("-" * 55)

    if not scorers:
        print("No scorers data returned by the API.")
        return
    
    # Enumerate gives us ranking numbers (1,2,3)
    for i, s in enumerate(scorers, start=1):
        player = s["player"]["name"]
        team = s["team"]["name"]
        goals = s.get("goals", 0)
        print(f"{str(i).rjust(2)}. {player} ({team}) — {goals}")


def full_time_score(match: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
    """Extract the full-time score from match dictionary.Some matches can have missing score data, so we use .get to avoid KeyErrors."""
    ft = match.get("score", {}).get("fullTime", {})
    return ft.get("home"), ft.get("away")


def win_streak_from_latest_finished(team: str, finished_matches: List[Dict[str, Any]]) -> int:
    """
    Calculate current consecutive win streak:
    - Look at finished matches for the team
    - Start from the latest and count wins until first non-win
    """
    # Filter only the matches where the team played
    team_finished = [
        m for m in finished_matches
        if team in (m["homeTeam"]["name"], m["awayTeam"]["name"])
    ]

    # Make sure they are in chronological order
    team_finished.sort(key=lambda m: m["utcDate"])

    streak = 0

    # reversed() starts from the most recent match
    for m in reversed(team_finished):
        hs, a_s = full_time_score(m)

        # If score is missing, skip this match rather than crashing
        if hs is None or a_s is None:
            continue

        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]

        # A draw ends a win streak
        if hs == a_s:
            break

        # Work out if "team" won based on whether they were home or away
        if team == home:
            won = hs > a_s
        else:
            won = a_s > hs
        # If they won, streak continues. If not, streak ends.
        if won:
            streak += 1
        else:
            break

    return streak


def haircut_tracker() -> None:
    """
    United Strand haircut rule (Man United only):
    United Strand cuts his hair after Manchester United win 5 games in a row.
    """
    target = 5

    # Pull the official team name from the standings so it matches the match data exactly
    standings = get_standings()
    official = get_official_team_names(standings)
    team = resolve_team_name("Manchester United", official)  # no prompt

    # Get finished matches and calculate the current win streak
    finished = get_matches(status="FINISHED", limit=380).get("matches", [])
    streak = win_streak_from_latest_finished(team, finished)

    remaining = max(0, target - streak)

    print(f"\nUNITED STRAND HAIRCUT TRACKER — {team}")
    print("-" * 55)
    print(f"Current win streak: {streak}")
    print("Haircut happens after: 5 wins in a row")

    if remaining == 0:
        print("Rooney's giving him a haircut!")
    else:
        print(f"  {remaining} more consecutive win's needed.")


def menu() -> None:
    """Main interactive menu loop."""
    while True:
        print("\n==============================")
        print(" Premier League Tracker (CLI) ")
        print("==============================")
        print("1) View PL table")
        print("2) Team position lookup")
        print("3) Next fixtures for a team")
        print("4) Top goalscorers")
        print("5) United Stand haircut tracker")
        print("0) Exit")

        choice = input("\nChoose an option: ").strip()

        try:
            # Each option calls a function
            if choice == "1":
                print_table()
            elif choice == "2":
                print_position()
            elif choice == "3":
                print_fixtures()
            elif choice == "4":
                print_scorers_menu()
            elif choice == "5":
                haircut_tracker()
            elif choice == "0":
                print("Bye 👋")
                break
            else:
                print("Invalid option. Choose 0–5.")

        except FootballDataError as e:
            # Known API/network errors from fpl_api.py
            print(f"\nError: {e}")
            print("Tip: Check your API key and internet connection.")
        except Exception as e:
            # Safety net so the program doesn't completely crash in the terminal
            print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    menu()