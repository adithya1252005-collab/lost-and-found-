
def create_notification(cursor, user_id, message):
    cursor.execute(
        """
        INSERT INTO notifications (user_id, message)
        VALUES (%s, %s)
        """,
        (user_id, message)
    )
