from notifications import create_notification
from matching import calculate_match_score
from flask import Flask, render_template, request, redirect, url_for, session,flash
from database import get_db_connection

app = Flask(__name__)

# Used for Flask sessions
app.secret_key = "lost_found_secret_key"


@app.route("/")
def home():
    return redirect(url_for("login"))


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
            """,
            (name, email, phone, password)
        )

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id, name, email,role
            FROM users
            WHERE email = %s AND password = %s
            """,
            (email, password)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session.clear()
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["role"] = user[3]

            print("Logged-in user:", user[2])
            print("Database role:", user[3])
            print("Session role:", session.get("role"))

            return redirect(url_for("dashboard"))

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        name=session["name"]
    )
# ---------------- REPORT LOST ITEM ----------------

@app.route("/lost-item", methods=["GET", "POST"])
def lost_item():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        item_name = request.form["item_name"]
        category = request.form["category"]
        description = request.form["description"]
        color = request.form["color"]
        lost_date = request.form["lost_date"]
        lost_location = request.form["lost_location"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO lost_items
            (user_id, item_name, category, description, color, lost_date, lost_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                item_name,
                category,
                description,
                color,
                lost_date,
                lost_location
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash("Thank you for reporting the lost item! Your report has been successfully submitted.")
        return redirect(url_for("dashboard"))

    return render_template("lost_item.html")

# ---------------- REPORT FOUND ITEM ----------------

@app.route("/found-item", methods=["GET", "POST"])
def found_item():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        item_name = request.form["item_name"]
        category = request.form["category"]
        description = request.form["description"]
        color = request.form["color"]
        found_date = request.form["found_date"]
        found_location = request.form["found_location"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO found_items
            (user_id, item_name, category, description, color, found_date, found_location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                item_name,
                category,
                description,
                color,
                found_date,
                found_location
            )
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash("Thank you for reporting the item! Your report has been successfully submitted.")
        return redirect(url_for("dashboard"))

    return render_template("found_item.html")
# ---------------- FIND ITEMS ----------------

@app.route("/find-items")
def find_items():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all lost items
    cursor.execute("""
        SELECT lost_id, item_name, category, description,
               color, lost_date, lost_location
        FROM lost_items
        ORDER BY lost_id DESC
    """)

    lost_items = cursor.fetchall()

    # Get all found items
    cursor.execute("""
        SELECT found_id, item_name, category, description,
               color, found_date, found_location
        FROM found_items
        ORDER BY found_id DESC
    """)

    found_items = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "find_items.html",
        lost_items=lost_items,
        found_items=found_items
    )

# ---------------- MANUAL CLAIM ----------------

@app.route("/claim/<int:found_id>", methods=["POST"])
def claim_item(found_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    verification_details = request.form.get(
        "verification_details", ""
    ).strip()

    if not verification_details:
        flash("Please provide details to verify your ownership.")
        return redirect(url_for("find_items"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check whether the found item exists
        cursor.execute(
            "SELECT user_id FROM found_items WHERE found_id = %s",
            (found_id,)
        )
        item = cursor.fetchone()

        if item is None:
            flash("Item not found.")
            return redirect(url_for("find_items"))

        # Do not allow users to claim items they reported
        if item[0] == user_id:
            flash("You cannot claim your own found item.")
            return redirect(url_for("find_items"))

        # Check for an existing pending or approved claim
        cursor.execute(
            """
            SELECT claim_id
            FROM claims
            WHERE found_id = %s
              AND user_id = %s
              AND claim_status IN ('pending', 'approved')
            """,
            (found_id, user_id)
        )

        if cursor.fetchone():
            flash("You have already claimed this item.")
            return redirect(url_for("find_items"))

        # Insert the claim into PostgreSQL
        cursor.execute(
            """
            INSERT INTO claims
                (found_id, user_id, verification_details)
            VALUES (%s, %s, %s)
            """,
            (found_id, user_id, verification_details)
        )

        conn.commit()
        flash("Your claim has been submitted successfully!")

    except Exception:
        conn.rollback()
        app.logger.exception("Error submitting claim")
        flash("Unable to submit the claim. Please try again.")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("find_items"))
# ---------------- ADMIN CLAIM MANAGEMENT ----------------

@app.route("/admin/claims")
def admin_claims():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied. Administrators only.")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            c.claim_id,
            f.item_name,
            u.name,
            c.claim_date,
            c.claim_status,
            c.verification_details
        FROM claims c
        JOIN found_items f ON c.found_id = f.found_id
        JOIN users u ON c.user_id = u.user_id
        ORDER BY c.claim_date DESC, c.claim_id DESC
    """)

    claims = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_claims.html", claims=claims)


# ---------------- REVIEW CLAIM ----------------

@app.route("/admin/claims/<int:claim_id>/review", methods=["POST"])
def review_claim(claim_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        flash("Access denied. Administrators only.")
        return redirect(url_for("dashboard"))

    decision = request.form.get("decision")

    if decision not in ("approved", "rejected"):
        flash("Invalid claim decision.")
        return redirect(url_for("admin_claims"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            UPDATE claims
            SET claim_status = %s
            WHERE claim_id = %s
              AND claim_status = 'pending'
            RETURNING claim_id
            """,
            (decision, claim_id)
        )

        updated_claim = cursor.fetchone()

        if updated_claim:
            conn.commit()
            flash(f"Claim #{claim_id} has been {decision}.")
        else:
            conn.rollback()
            flash("Claim not found or it has already been reviewed.")

    except Exception:
        conn.rollback()
        app.logger.exception("Failed to review claim")
        flash("Unable to update the claim.")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("admin_claims"))

# ---------------- AUTOMATIC MATCHING ----------------

@app.route("/matches")
def view_matches():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT lost_id, item_name, category,
                   description, color, lost_location
            FROM lost_items
        """)
        lost_rows = cursor.fetchall()

        cursor.execute("""
            SELECT found_id, item_name, category,
                   description, color, found_location
            FROM found_items
        """)
        found_rows = cursor.fetchall()

        # Compare every lost item with every found item
        for lost in lost_rows:
            for found in found_rows:

                lost_item = {
                    "item_name": lost[1],
                    "category": lost[2],
                    "description": lost[3],
                    "color": lost[4],
                    "location": lost[5]
                }

                found_item = {
                    "item_name": found[1],
                    "category": found[2],
                    "description": found[3],
                    "color": found[4],
                    "location": found[5]
                }

                score = calculate_match_score(
                    lost_item, found_item
                )

                # Save promising matches (score >= 40)
                if score >= 40:
                    cursor.execute("""
                        INSERT INTO matches
                            (lost_id, found_id, match_score, match_status)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        lost[0], found[0], score, "pending"
                    ))

        conn.commit()

        cursor.execute("""
            SELECT
                m.lost_id,
                l.item_name,
                m.found_id,
                f.item_name,
                m.match_score,
                m.match_status
            FROM matches m
            JOIN lost_items l ON l.lost_id = m.lost_id
            JOIN found_items f ON f.found_id = m.found_id
            ORDER BY m.match_score DESC
        """)

        matches = cursor.fetchall()

    except Exception:
        conn.rollback()
        app.logger.exception("Matching failed")
        flash("Unable to calculate matches. Check the Flask terminal.")
        matches = []

    finally:
        cursor.close()
        conn.close()

    return render_template("matches.html", matches=matches)

# ---------------- USER NOTIFICATIONS ----------------

@app.route("/notifications")
def user_notifications():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT notification_id, message, created_at, is_read
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (session["user_id"],)
    )

    notifications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications
    )

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)