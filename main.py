from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session.get('is_admin'):  # Check for admin status
        return render_template('admin_dashboard.html')
    else:
        flash("Unauthorized access!")
        return redirect(url_for('login'))

@app.route('/admin/information')
def admin_information():
    if 'username' in session and session['username'] == 'Admin':
        conn = get_db_connection()
        users = conn.execute('SELECT id, username FROM user').fetchall()
        conn.close()
        return render_template('information.html', users=users)
    else:
        flash("Unauthorized access!")
        return redirect(url_for('main'))

@app.route('/admin/leaderboard')
def admin_leaderboard():
    if 'username' in session and session['username'] == 'Admin':
        conn = get_db_connection()
        scores = conn.execute('SELECT id, username, score, test_type FROM leaderboard').fetchall()
        conn.close()
        return render_template('leaderboard_admin.html', scores=scores)
    else:
        flash("Unauthorized access!")
        return redirect(url_for('main'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'username' in session and session['username'] == 'Admin':
        conn = get_db_connection()
        try:
            # Delete the user's scores from the leaderboard
            conn.execute('DELETE FROM leaderboard WHERE username = (SELECT username FROM user WHERE id = ?)', (user_id,))
            # Delete the user profile
            conn.execute('DELETE FROM user WHERE id = ?', (user_id,))
            conn.commit()
            flash("User and their scores deleted successfully.")
        except Exception as e:
            flash("An error occurred while deleting the user.")
        finally:
            conn.close()
        
        return redirect(url_for('admin_information'))
    else:
        flash("Unauthorized access!")
        return redirect(url_for('main'))

@app.route('/admin/delete_score/<int:score_id>', methods=['POST'])
def delete_score(score_id):
    if 'username' in session and session['username'] == 'Admin':
        conn = get_db_connection()
        try:
            conn.execute('DELETE FROM leaderboard WHERE id = ?', (score_id,))
            conn.commit()
            flash("Score deleted successfully.")
        except Exception as e:
            flash("An error occurred while deleting the score.")
        finally:
            conn.close()
        
        return redirect(url_for('admin_leaderboard'))
    else:
        flash("Unauthorized access!")
        return redirect(url_for('main'))

def check_and_create_tables():
    try:
        conn = sqlite3.connect('WA2.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                scores_20 INTEGER NOT NULL DEFAULT 0,
                scores_30 INTEGER NOT NULL DEFAULT 0,
                scores_40 INTEGER NOT NULL DEFAULT 0,
                scores_50 INTEGER NOT NULL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_type TEXT NOT NULL,
                username TEXT NOT NULL,
                score INTEGER NOT NULL,
                FOREIGN KEY(username) REFERENCES user(username)
            )
        ''')
        conn.commit()
    finally:
        if conn:
            conn.close()

@app.before_first_request
def initialize():
    check_and_create_tables()


def get_db_connection():
        conn = sqlite3.connect('WA2.db')  # Connect to your SQLite database
        conn.row_factory = sqlite3.Row  # This allows dictionary-like access to rows
        return conn

    
@app.route('/', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = None
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
            if user is None:
                error_message = 'User not registered'
            elif user['password'] != password:
                error_message = 'Password or username Incorrect'
            else:
                session['username'] = username
                session['is_admin'] = user['is_admin']  # Store admin status in session

                # Redirect to admin dashboard if the user is an admin
                if user['is_admin']:
                    return redirect(url_for('admin_dashboard'))

                return redirect(url_for('main'))
        except Exception as e:
            error_message = 'Internal server error. Please try again later.'
        finally:
            if conn:
                conn.close()

    return render_template('login.html', error_message=error_message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username and password:
            conn = get_db_connection()
            try:
                user_exists = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
                if not user_exists:
                    # Determine if the user is an admin
                    is_admin = 1 if username == 'Admin' else 0
                    conn.execute('INSERT INTO user (username, password, is_admin) VALUES (?, ?, ?)', (username, password, is_admin))
                    conn.commit()  # Commit the transaction
                    flash('Registration successful!', 'success')
                    return redirect(url_for('login'))
                else:
                    return render_template('register.html', error_message='Username already taken!')
            except Exception as e:
                return render_template('register.html', error_message='Internal server error. Please try again later.')
            finally:
                conn.close()
        else:
            return render_template('register.html', error_message='Please fill in all fields.')

    return render_template('register.html')

def update_high_scores(username, test_type, new_score):
    try:
        conn = sqlite3.connect('WA2.db')
        cursor = conn.cursor()

        scores_key_map = {
            "20:00": "scores_20",
            "30:00": "scores_30",
            "40:00": "scores_40",
            "50:00": "scores_50"
        }

        scores_key = scores_key_map.get(test_type)

        if not scores_key:
            raise ValueError(f"Unknown test_type: {test_type}")
        
        cursor.execute(f'SELECT {scores_key} FROM user WHERE username = ?', (username,))
        current_scores_json = cursor.fetchone()[0]
        
        current_scores = json.loads(current_scores_json) if current_scores_json else []
        current_scores.append(new_score)
        current_scores = sorted(current_scores, reverse=True)[:10]

        scores_json = json.dumps(current_scores)
        cursor.execute(f'UPDATE user SET {scores_key} = ? WHERE username = ?', (scores_json, username))
        
        # Also update the leaderboard table
        cursor.execute('INSERT INTO leaderboard (test_type, username, score) VALUES (?, ?, ?)', (test_type, username, new_score))

        conn.commit()
    finally:
        if conn:
            conn.close()

@app.route('/profile')
def profile():
    username = session.get('username')
    
    if not username:
        return "User not logged in", 401  # Handle case where user is not logged in

    conn = get_db_connection()
    
    # Initialize a dictionary to hold top scores
    top_scores = {
        '20': [],
        '30': [],
        '40': [],
        '50': []
    }

    # Fetch top 5 scores for each test duration from the `user` table
    for test_duration in ['20', '30', '40', '50']:
        scores_key = f'scores_{test_duration}'
        cursor = conn.execute(f"SELECT {scores_key} FROM user WHERE username = ?", (username,))
        result = cursor.fetchone()

        if result:
            scores_list = json.loads(result[0]) if result[0] else []
            top_scores[test_duration] = sorted(scores_list, reverse=True)[:5]

    conn.close()
    
    return render_template('profile.html', top_scores=top_scores, username=username)

@app.route('/<test_type>_leaderboard')
def leaderboard(test_type):
    formatted_test_type = f'{test_type}:00'
    template_name = f'{test_type}_leaderboard.html'
    conn = None
    users = []
    ranked_users = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, score FROM leaderboard WHERE test_type = ? ORDER BY score DESC LIMIT 50', (formatted_test_type,))
        users = cursor.fetchall()

        rank = 1
        for user in users:
            ranked_users.append({
                'rank': rank,
                'username': user[0],
                'score': user[1]
            })
            rank += 1
    finally:
        if conn:
            conn.close()

    return render_template(template_name, users=ranked_users)

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/leaderboard')
def leaderboard_main():
    return render_template('leaderboard.html')

@app.route('/20')
def twenty_minutes():
    return render_template('20.html')

@app.route('/30')
def thirty_minutes():
    return render_template('30.html')

@app.route('/40')
def fourty_minutes():
    return render_template('40.html')

@app.route('/50')
def fifty_minutes():
    return render_template('50.html')

@app.route('/test_finished')
def test_finished():
    username = session.get('username')
    score = request.args.get('score', type=int)
    test_type = request.args.get('testType')

    if username and score is not None and test_type:
        print(f"Calling update_high_scores for user: {username}, test type: {test_type}, score: {score}")
        update_high_scores(username, test_type, score)
        # Pass parameters to the template
        return render_template('test_finished.html', score=score, test_type=test_type)
    else:
        print(f"Missing username, score, or testType: username={username}, score={score}, testType={test_type}")
        # Handle missing parameters, maybe render an error page or redirect
        return render_template('error.html', message="Missing username, score, or test type.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
