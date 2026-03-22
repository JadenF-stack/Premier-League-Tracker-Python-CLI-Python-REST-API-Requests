from __future__ import annotations

from datetime import datetime

from fpl_api import FootballDataError, get_matches, get_scorers, get_standings


# Simple aliases so users can type common shortcuts instead of exact official names
TEAM_ALIASES = {
    "united": "Manchester United",
    "mufc": "Manchester United",
    "spurs": "Tottenham Hotspur",
    "wolves": "Wolverhampton Wanderers FC",
}


def parse_utc(utc_str):
    """Convert API date like '2026-02-28T15:00:00Z' to a Python datetime."""
    return datetime.fromisoformat(utc_str.replace("Z", "+00:00"))


def normalize_team_query(query):
    """
    Clean up the user's team input:
    - If blank, default to Manchester United
    """
    if not query or not query.strip():
        return "Manchester United"
    cleaned = query.strip()
    return TEAM_ALIASES.get(cleaned.lower(), cleaned)


def get_official_team_names(standings_data):
    """
    Pull out just the team names from the standings JSON.
    The standings JSON looks like:
      standings_data["standings"][0]["table"] -> list of rows (one per team)
    Each row has:
      row["team"]["name"] -> the team's official name
    """
    table = standings_data["standings"][0]["table"]

    team_names = []

    for row in table:
        name = row["team"]["name"]
        team_names.append(name)

    return team_names


def resolve_team_name(user_query, official_names):
    """
    Map what the user types to a real official team name.
    1) Clean the input and apply aliases
    2) Try an exact match first
    3) Fall back to a substring match if no exact match found
    """
    wanted = normalize_team_query(user_query)

    # Exact match first
    for name in official_names:
        if name.lower() == wanted.lower():
            return name

    # Substring match fallback
    matches = [name for name in official_names if wanted.lower() in name.lower()]

    # Pick the shortest match as best guess
    if matches:
        matches.sort(key=len)
        return matches[0]

    return wanted


def print_table():
    """Fetch and print the current Premier League table."""
    data = get_standings()
    table = data["standings"][0]["table"]

    print("\nPOS  TEAM                          PTS  GD  P")
    print("-" * 55)

    for row in table:
        pos = str(row["position"]).rjust(2)
        name = row["team"]["name"][:28].ljust(28)
        pts = str(row["points"]).rjust(3)
        gd = str(row["goalDifference"]).rjust(3)
        played = str(row["playedGames"]).rjust(2)
        print(f"{pos}   {name}   {pts}  {gd}  {played}")


def find_team_row(team_name):
    """Find and return a specific team's row from the league table."""
    data = get_standings()
    table = data["standings"][0]["table"]

    for row in table:
        if row["team"]["name"] == team_name:
            return row
    return None


def print_position():
    """Ask for a team name and print their current league position and stats."""
    standings = get_standings()
    official = get_official_team_names(standings)

    team_query = input("\nEnter team name (press Enter for Man United): ")
    team = resolve_team_name(team_query, official)

    row = find_team_row(team)
    if not row:
        print(f"Couldn't find '{team_query}'. Try the exact name from the table.")
        return

    print(f"\n{team}")
    print("-" * 55)
    print(
        f"Position: {row['position']} | Points: {row['points']} | "
        f"Played: {row['playedGames']} | GD: {row['goalDifference']}"
    )


def print_fixtures():
    """Ask for a team and how many fixtures, then print their upcoming matches."""
    standings = get_standings()
    official = get_official_team_names(standings)

    team_query = input("\nEnter team name (press Enter for Man United): ")
    team = resolve_team_name(team_query, official)

    limit_str = input("How many fixtures? (default 5): ").strip()
    limit = int(limit_str) if limit_str.isdigit() else 5

    # Grab a large batch of scheduled matches and filter for the team
    scheduled = get_matches(status="SCHEDULED", limit=300).get("matches", [])

    team_games = [
        m for m in scheduled
        if team in (m["homeTeam"]["name"], m["awayTeam"]["name"])
    ][:max(0, limit)]

    print(f"\nNEXT {len(team_games)} FIXTURES — {team}")
    print("-" * 55)

    if not team_games:
        print("No upcoming fixtures found.")
        return

    for m in team_games:
        dt = parse_utc(m["utcDate"]).strftime("%d %b %Y %H:%M")
        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]
        print(f"{dt}  {home} vs {away}")


def print_scorers_menu():
    """Ask how many scorers to show, then print the top PL goalscorers."""
    top_str = input("\nShow top how many scorers? (default 10): ").strip()
    top = int(top_str) if top_str.isdigit() else 10

    data = get_scorers(limit=top)
    scorers = data.get("scorers", [])

    print(f"\nTOP {len(scorers)} GOALSCORERS")
    print("-" * 55)

    if not scorers:
        print("No scorers data returned by the API.")
        return

    for i, s in enumerate(scorers, start=1):
        player = s["player"]["name"]
        team = s["team"]["name"]
        goals = s.get("goals", 0)
        print(f"{str(i).rjust(2)}. {player} ({team}) — {goals}")


def full_time_score(match):
    """Extract the full time home and away score from a match."""
    ft = match.get("score", {}).get("fullTime", {})
    return ft.get("home"), ft.get("away")


def win_streak_from_latest_finished(team, finished_matches):
    """
    Calculate the current consecutive win streak for a team:
    - Filter to only matches the team played
    - Start from the most recent match and count wins backwards
    - Stop counting when we hit a draw or loss
    """
    # Only keep matches where this team played
    team_finished = [
        m for m in finished_matches
        if team in (m["homeTeam"]["name"], m["awayTeam"]["name"])
    ]

    # Sort oldest to newest
    team_finished.sort(key=lambda m: m["utcDate"])

    streak = 0

    # Work backwards from most recent match
    for m in reversed(team_finished):
        hs, a_s = full_time_score(m)

        # Skip matches with missing score data
        if hs is None or a_s is None:
            continue

        home = m["homeTeam"]["name"]
        away = m["awayTeam"]["name"]

        # A draw ends the streak
        if hs == a_s:
            break

        # Check if the team won depending on whether they were home or away
        if team == home:
            won = hs > a_s
        else:
            won = a_s > hs

        if won:
            streak += 1
        else:
            break

    return streak


def haircut_tracker():
    """
    United Strand haircut tracker:
    United Strand cuts his hair after Manchester United win 5 games in a row.
    """
    target = 5

    standings = get_standings()
    official = get_official_team_names(standings)
    team = resolve_team_name("Manchester United", official)

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
        print(f"  {remaining} more consecutive wins needed.")


def menu():
    """Main interactive menu loop."""
    while True:
        print("\n==============================")
        print(" Premier League Tracker (CLI) ")
        print("==============================")
        print("1) View PL table")
        print("2) Team position lookup")
        print("3) Next fixtures for a team")
        print("4) Top goalscorers")
        print("5) United Strand haircut tracker")
        print("0) Exit")

        choice = input("\nChoose an option: ").strip()

        try:
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
            print(f"\nError: {e}")
            print("Tip: Check your API key and internet connection.")
        except Exception as e:
            print(f"\nUnexpected error: {e}")


if __name__ == "__main__":
    menu()
