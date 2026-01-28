import sqlite3


def get_event_outcomes(event_title, character_name):
    """
    Queries the umamusume_events.db for a given event title, checking for both
    character-specific and "Common" events.

    Args:
        event_title (str): The cleaned title of the event to look up.
        character_name (str): The name of the character currently being trained.

    Returns:
        A list of tuples containing the option number and outcome description,
        or None if the event is not found or an error occurs.
    """
    results = None
    con = None
    try:
        # Connect to the database file in the same directory
        con = sqlite3.connect("umamusume_events.db")
        cur = con.cursor()

        # This query looks for an event matching the specific character OR a "Common" event
        query = """
            SELECT "option_number", "outcome_description" 
            FROM events 
            WHERE ("character_name" = ? OR "character_name" = 'Common') 
              AND "event_title" = ?
            ORDER BY "option_number"
        """

        cur.execute(query, (character_name, event_title))
        results = cur.fetchall()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        # In case of an error, results will remain None, which is the intended failure state
    finally:
        if con:
            con.close()

    # Return the results, which will be a list of rows or an empty list if not found.
    # The calling function can check if the result is empty.
    return results