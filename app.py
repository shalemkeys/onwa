from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3, os, hashlib, random, string, math
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'onwa-secret-2025'
DB = 'onwa.db'

UK_COORDS = {
    'London': (51.5074, -0.1278),
    'Birmingham': (52.5086, -1.8756),
    'Manchester': (53.4808, -2.2426),
    'Bristol': (51.4545, -2.5879),
    'Edinburgh': (55.9533, -3.1883),
}

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(DB):
        return
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'member',
            bio TEXT DEFAULT '',
            location TEXT DEFAULT '',
            points INTEGER DEFAULT 0,
            books_passed INTEGER DEFAULT 0,
            books_read INTEGER DEFAULT 0,
            date_joined DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            description TEXT,
            cover_color TEXT DEFAULT '#4A90D9',
            passport_code TEXT UNIQUE,
            current_holder_id INTEGER,
            status TEXT DEFAULT 'circulating',
            total_miles REAL DEFAULT 0,
            total_readers INTEGER DEFAULT 0,
            added_by INTEGER,
            date_added DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS passport_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            location TEXT,
            note TEXT,
            miles_travelled REAL DEFAULT 0,
            date_received DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            position INTEGER,
            status TEXT DEFAULT 'waiting',
            date_queued DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL,
            type TEXT,
            description TEXT,
            status TEXT DEFAULT 'completed',
            date DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            book_id INTEGER,
            message TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            read INTEGER DEFAULT 0,
            book_id INTEGER,
            date DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reading_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT DEFAULT 'want',
            date_started DATETIME,
            date_finished DATETIME,
            date_added DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    pw = lambda p: hashlib.md5(p.encode()).hexdigest()

    users = [
        ('Admin Dave','admin@onwa.com', pw('admin123'),'admin','Founder of Onwa. Passionate about keeping books moving.','London',500,12,18),
        ('Shalem Raj','shalem@onwa.com', pw('password'),'member','Software developer and avid reader. Love sci-fi and history.','Birmingham',220,8,14),
        ('Alice Brown','alice@onwa.com', pw('password'),'member','Primary school teacher. Mostly fiction and self-help.','Manchester',185,6,11),
        ('James Carter','james@onwa.com', pw('password'),'member','Retired. Got more time for books now than ever.','Bristol',140,5,9),
        ('Priya Nair','priya@onwa.com', pw('password'),'member','UX designer. I judge books by their covers — and their insides.','Edinburgh',95,3,6),
    ]
    for u in users:
        c.execute("INSERT INTO users (name,email,password,role,bio,location,points,books_passed,books_read) VALUES (?,?,?,?,?,?,?,?,?)", u)

    books = [
        ('The Alchemist','Paulo Coelho','Fiction','A timeless story about following your dreams and listening to your heart. Santiago, an Andalusian shepherd, travels from Spain to Egypt in search of treasure.','#c0783c','ONWA-0001',2,3),
        ('Atomic Habits','James Clear','Self-Help','Tiny changes, remarkable results. A practical guide to building good habits and breaking bad ones through small, consistent actions.','#2d6a4f','ONWA-0002',3,2),
        ('1984','George Orwell','Dystopian','A harrowing portrait of a totalitarian society where Big Brother watches your every move. Chilling, brilliant and more relevant than ever.','#6b2d2d','ONWA-0003',4,2),
        ('Sapiens','Yuval Noah Harari','History','A sweeping narrative of human history from the Stone Age to the twenty-first century. Thought-provoking and impossible to put down.','#4a4e8c','ONWA-0004',5,1),
        ('The Great Gatsby','F. Scott Fitzgerald','Classic','A brilliant study of wealth, class and the American Dream set in the roaring twenties. One of the great American novels.','#1a6b8a','ONWA-0005',2,1),
        ('Educated','Tara Westover','Biography','A memoir about a woman who grows up in a survivalist family in rural Idaho and goes on to earn a PhD from Cambridge. Extraordinary.','#7b5e3a','ONWA-0006',3,1),
        ('Thinking, Fast and Slow','Daniel Kahneman','Psychology','Nobel laureate Kahneman reveals the two systems that drive the way we think — fast, intuitive thinking and slow, deliberate thinking.','#3d6b5e','ONWA-0007',4,1),
    ]
    for b in books:
        c.execute("INSERT INTO books (title,author,genre,description,cover_color,passport_code,current_holder_id,total_readers,added_by) VALUES (?,?,?,?,?,?,?,?,1)", b)

    entries = [
        (1,1,'London, UK','Added this to the Onwa community. A book that changed my life — hope it does the same for others.',0,'2024-10-01'),
        (1,3,'Manchester, UK','Read in one weekend. The message hit differently at this point in my life. Passing on with love.',180,'2024-10-18'),
        (1,2,'Birmingham, UK','This came to me at exactly the right time. Incredible.',92,'2024-11-03'),
        (2,1,'London, UK','Added this one — James Clear changed how I think about building routines.',0,'2024-10-05'),
        (2,4,'Bristol, UK','Already implementing the 2-minute rule. Brilliant practical book.',125,'2024-10-22'),
        (3,2,'Birmingham, UK','Added to Onwa. Orwell was writing about today.',0,'2024-09-14'),
        (3,5,'Edinburgh, UK','Read this in a week. Terrifying and beautiful.',340,'2024-10-01'),
        (4,4,'Bristol, UK','Added to the community. Harari is a genius.',0,'2024-09-20'),
        (5,3,'Manchester, UK','A classic everyone should read at least once.',0,'2024-11-10'),
        (6,5,'Edinburgh, UK','Tara Westover is a force of nature. Wept at this.',0,'2024-10-30'),
        (7,2,'Birmingham, UK','Dense but rewarding. Changed how I think.',0,'2024-11-01'),
    ]
    for e in entries:
        c.execute("INSERT INTO passport_entries (book_id,user_id,location,note,miles_travelled,date_received) VALUES (?,?,?,?,?,?)", e)

    c.execute("UPDATE books SET total_miles=272, total_readers=3 WHERE id=1")
    c.execute("UPDATE books SET total_miles=125, total_readers=2 WHERE id=2")
    c.execute("UPDATE books SET total_miles=340, total_readers=2 WHERE id=3")

    queue_data = [(1,4,1),(1,5,2),(2,2,1),(3,3,1)]
    for q in queue_data:
        c.execute("INSERT INTO queue (book_id,user_id,position) VALUES (?,?,?)", q)

    payments = [
        (2,4.99,'membership','Monthly membership — November 2024','2024-11-01'),
        (3,4.99,'membership','Monthly membership — November 2024','2024-11-01'),
        (4,4.99,'membership','Monthly membership — November 2024','2024-11-02'),
        (5,4.99,'membership','Monthly membership — November 2024','2024-11-03'),
        (2,4.99,'membership','Monthly membership — December 2024','2024-12-01'),
        (3,4.99,'membership','Monthly membership — December 2024','2024-12-01'),
    ]
    for p in payments:
        c.execute("INSERT INTO payments (user_id,amount,type,description,date) VALUES (?,?,?,?,?)", p)

    activity_data = [
        (2,'passed',1,'Shalem passed The Alchemist on to James in Bristol'),
        (3,'joined',None,'Alice joined the Onwa community'),
        (4,'queued',1,'James joined the queue for The Alchemist'),
        (5,'read',3,'Priya finished reading 1984'),
        (1,'added',6,'Dave added Educated to the community'),
        (3,'passed',2,'Alice passed Atomic Habits on to James'),
        (2,'read',7,'Shalem finished reading Thinking, Fast and Slow'),
    ]
    for a in activity_data:
        c.execute("INSERT INTO activity (user_id,type,book_id,message) VALUES (?,?,?,?)", a)

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return redirect('/dashboard' if 'user_id' in session else '/login')

@app.route('/login', methods=['GET','POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')
    error = None
    if request.method == 'POST':
        email = request.form['email']
        pw = hashlib.md5(request.form['password'].encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,pw)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            return redirect('/dashboard')
        error = 'Incorrect email or password.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        loc = request.form.get('location','')
        pw = hashlib.md5(request.form['password'].encode()).hexdigest()
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name,email,password,location) VALUES (?,?,?,?)",(name,email,pw,loc))
            conn.commit()
            conn.close()
            return redirect('/login')
        except:
            error = 'That email is already registered.'
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    uid = session['user_id']
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    recent_books = conn.execute("SELECT * FROM books ORDER BY date_added DESC LIMIT 5").fetchall()
    my_queue = conn.execute("SELECT q.*,b.title,b.passport_code,b.cover_color FROM queue q JOIN books b ON b.id=q.book_id WHERE q.user_id=? AND q.status='waiting'", (uid,)).fetchall()
    feed = conn.execute("SELECT a.*,u.name as uname,u.location,b.title as btitle FROM activity a JOIN users u ON u.id=a.user_id LEFT JOIN books b ON b.id=a.book_id ORDER BY a.date DESC LIMIT 8").fetchall()
    stats = {
        'books': conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        'members': conn.execute("SELECT COUNT(*) FROM users WHERE role='member'").fetchone()[0],
        'journeys': conn.execute("SELECT COUNT(*) FROM passport_entries").fetchone()[0],
        'miles': conn.execute("SELECT COALESCE(SUM(miles_travelled),0) FROM passport_entries").fetchone()[0],
    }
    conn.close()
    return render_template('dashboard.html', user=user, recent_books=recent_books, my_queue=my_queue, feed=feed, stats=stats)

@app.route('/library')
def library():
    if 'user_id' not in session:
        return redirect('/login')
    q = request.args.get('q','')
    genre = request.args.get('genre','')
    conn = get_db()
    sql = "SELECT b.*,u.name as holder_name FROM books b LEFT JOIN users u ON u.id=b.current_holder_id WHERE 1=1"
    params = []
    if q:
        sql += " AND (b.title LIKE ? OR b.author LIKE ?)"
        params += [f'%{q}%', f'%{q}%']
    if genre:
        sql += " AND b.genre=?"
        params.append(genre)
    sql += " ORDER BY b.date_added DESC"
    books = conn.execute(sql, params).fetchall()
    genres = conn.execute("SELECT DISTINCT genre FROM books ORDER BY genre").fetchall()
    conn.close()
    return render_template('library.html', books=books, genres=genres, q=q, genre=genre)

@app.route('/api/search')
def api_search():
    if 'user_id' not in session:
        return jsonify([])
    q = request.args.get('q','').strip()
    if not q or len(q) < 2:
        return jsonify([])
    conn = get_db()
    books = conn.execute("SELECT b.id, b.title, b.author, b.cover_color, b.passport_code, u.name as holder_name FROM books b LEFT JOIN users u ON u.id=b.current_holder_id WHERE b.title LIKE ? OR b.author LIKE ? LIMIT 8", (f'%{q}%', f'%{q}%')).fetchall()
    conn.close()
    return jsonify([dict(b) for b in books])

@app.route('/passport/<code>')
def passport(code):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    book = conn.execute("SELECT b.*,u.name as holder_name FROM books b LEFT JOIN users u ON u.id=b.current_holder_id WHERE b.passport_code=?", (code,)).fetchone()
    if not book:
        return "Not found", 404
    entries = conn.execute("SELECT p.*,u.name as reader_name,u.location as uloc FROM passport_entries p JOIN users u ON u.id=p.user_id WHERE p.book_id=? ORDER BY p.date_received ASC", (book['id'],)).fetchall()
    queue = conn.execute("SELECT q.*,u.name as member_name,u.location as uloc FROM queue q JOIN users u ON u.id=q.user_id WHERE q.book_id=? AND q.status='waiting' ORDER BY q.position", (book['id'],)).fetchall()
    total_miles = sum(e['miles_travelled'] for e in entries)
    in_queue = conn.execute("SELECT id FROM queue WHERE book_id=? AND user_id=? AND status='waiting'", (book['id'], session['user_id'])).fetchone()
    reading = conn.execute("SELECT status FROM reading_log WHERE user_id=? AND book_id=?", (session['user_id'], book['id'])).fetchone()
    conn.close()
    return render_template('passport.html', book=book, entries=entries, queue=queue, total_miles=total_miles, in_queue=in_queue, reading=reading)

@app.route('/passport/<code>/pass-on', methods=['POST'])
def pass_on_book(code):
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401
    data = request.get_json()
    conn = get_db()
    book = conn.execute("SELECT * FROM books WHERE passport_code=?", (code,)).fetchone()
    if not book or book['current_holder_id'] != session['user_id']:
        return jsonify({'error':'Not authorized'}), 403
    
    new_holder_id = data.get('user_id')
    location = data.get('location','')
    note = data.get('note','')
    miles = float(data.get('miles', 0))
    
    conn.execute("INSERT INTO passport_entries (book_id,user_id,location,note,miles_travelled) VALUES (?,?,?,?,?)", (book['id'], new_holder_id, location, note, miles))
    conn.execute("UPDATE books SET current_holder_id=?, total_miles=total_miles+?, total_readers=total_readers+1 WHERE id=?", (new_holder_id, miles, book['id']))
    conn.execute("UPDATE users SET points=points+50, books_passed=books_passed+1 WHERE id=?", (session['user_id'],))
    conn.execute("INSERT INTO activity (user_id,type,book_id,message) VALUES (?,?,?,?)", (session['user_id'], 'passed', book['id'], f"{session['user_name']} passed {book['title']} to a new reader"))
    
    next_in_queue = conn.execute("SELECT user_id FROM queue WHERE book_id=? AND status='waiting' ORDER BY position LIMIT 1", (book['id'],)).fetchone()
    if next_in_queue:
        conn.execute("INSERT INTO notifications (user_id,message,book_id) VALUES (?,?,?)", (next_in_queue['user_id'], f"Your queued book {book['title']} is ready for pickup!", book['id']))
    
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/profile/<int:uid>')
def profile(uid):
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    if not user:
        return "User not found", 404
    passed = conn.execute("SELECT p.*,b.title,b.cover_color,b.passport_code FROM passport_entries p JOIN books b ON b.id=p.book_id WHERE p.user_id=? ORDER BY p.date_received DESC", (uid,)).fetchall()
    activity = conn.execute("SELECT a.*,b.title as btitle FROM activity a LEFT JOIN books b ON b.id=a.book_id WHERE a.user_id=? ORDER BY a.date DESC LIMIT 10", (uid,)).fetchall()
    conn.close()
    return render_template('profile.html', user=user, passed=passed, activity=activity)

@app.route('/queue/join/<int:book_id>', methods=['POST'])
def join_queue(book_id):
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401
    uid = session['user_id']
    conn = get_db()
    existing = conn.execute("SELECT id FROM queue WHERE book_id=? AND user_id=? AND status='waiting'", (book_id,uid)).fetchone()
    if not existing:
        pos = (conn.execute("SELECT MAX(position) FROM queue WHERE book_id=?", (book_id,)).fetchone()[0] or 0) + 1
        conn.execute("INSERT INTO queue (book_id,user_id,position) VALUES (?,?,?)", (book_id,uid,pos))
        book = conn.execute("SELECT title FROM books WHERE id=?", (book_id,)).fetchone()
        conn.execute("INSERT INTO activity (user_id,type,book_id,message) VALUES (?,?,?,?)", (uid,'queued',book_id,f"{session['user_name']} joined the queue for {book['title']}"))
        conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/reading-log')
def reading_log():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    uid = session['user_id']
    entries = conn.execute("SELECT rl.*, b.title, b.author, b.cover_color, b.passport_code FROM reading_log rl JOIN books b ON b.id=rl.book_id WHERE rl.user_id=? ORDER BY rl.date_added DESC", (uid,)).fetchall()
    stats = {
        'reading': conn.execute("SELECT COUNT(*) FROM reading_log WHERE user_id=? AND status='reading'", (uid,)).fetchone()[0],
        'finished': conn.execute("SELECT COUNT(*) FROM reading_log WHERE user_id=? AND status='finished'", (uid,)).fetchone()[0],
        'want': conn.execute("SELECT COUNT(*) FROM reading_log WHERE user_id=? AND status='want'", (uid,)).fetchone()[0],
    }
    conn.close()
    return render_template('reading_log.html', entries=entries, stats=stats)

@app.route('/reading-log/update/<int:book_id>', methods=['POST'])
def update_reading_log(book_id):
    if 'user_id' not in session:
        return jsonify({'error':'Not logged in'}), 401
    status = request.get_json().get('status')
    uid = session['user_id']
    conn = get_db()
    existing = conn.execute("SELECT id FROM reading_log WHERE user_id=? AND book_id=?", (uid, book_id)).fetchone()
    if existing:
        conn.execute("UPDATE reading_log SET status=? WHERE user_id=? AND book_id=?", (status, uid, book_id))
    else:
        conn.execute("INSERT INTO reading_log (user_id, book_id, status) VALUES (?,?,?)", (uid, book_id, status))
    if status == 'finished':
        conn.execute("UPDATE users SET books_read=books_read+1 WHERE id=?", (uid,))
        conn.execute("INSERT INTO activity (user_id,type,book_id,message) VALUES (?,?,?,?)", (uid,'read',book_id,f"{session['user_name']} finished reading a book"))
    conn.commit()
    conn.close()
    return jsonify({'success':True})

@app.route('/map')
def map_view():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    books = conn.execute("SELECT b.*, u.location FROM books b LEFT JOIN users u ON u.id=b.current_holder_id WHERE u.location IS NOT NULL").fetchall()
    conn.close()
    locations = []
    for book in books:
        loc = book['location'].split(',')[0].strip()
        if loc in UK_COORDS:
            lat, lng = UK_COORDS[loc]
            locations.append({'title': book['title'], 'lat': lat, 'lng': lng, 'code': book['passport_code'], 'holder': book['location']})
    return render_template('map.html', locations=locations)

@app.route('/impact')
def impact():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    total_miles = conn.execute("SELECT COALESCE(SUM(miles_travelled),0) FROM passport_entries").fetchone()[0]
    total_journeys = conn.execute("SELECT COUNT(*) FROM passport_entries").fetchone()[0]
    co2_saved = total_books * 0.5
    top_books = conn.execute("SELECT b.title, b.total_miles, b.total_readers FROM books b ORDER BY b.total_miles DESC LIMIT 3").fetchall()
    conn.close()
    return render_template('impact.html', total_books=total_books, total_miles=total_miles, total_journeys=total_journeys, co2_saved=co2_saved, top_books=top_books)

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect('/login')
    conn = get_db()
    uid = session['user_id']
    notifs = conn.execute("SELECT n.*, b.title FROM notifications n LEFT JOIN books b ON b.id=n.book_id WHERE n.user_id=? ORDER BY n.date DESC", (uid,)).fetchall()
    unread = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0", (uid,)).fetchone()[0]
    conn.execute("UPDATE notifications SET read=1 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return render_template('notifications.html', notifs=notifs, unread=unread)

@app.route('/api/notifications/unread')
def api_unread():
    if 'user_id' not in session:
        return jsonify({'count':0})
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0", (session['user_id'],)).fetchone()[0]
    conn.close()
    return jsonify({'count':count})

@app.route('/admin')
def admin():
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY date_joined DESC").fetchall()
    books = conn.execute("SELECT b.*,u.name as holder_name FROM books b LEFT JOIN users u ON u.id=b.current_holder_id").fetchall()
    payments = conn.execute("SELECT p.*,u.name as uname FROM payments p JOIN users u ON u.id=p.user_id ORDER BY p.date DESC").fetchall()
    stats = {
        'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'books': conn.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        'journeys': conn.execute("SELECT COUNT(*) FROM passport_entries").fetchone()[0],
        'revenue': conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='completed'").fetchone()[0],
        'miles': conn.execute("SELECT COALESCE(SUM(miles_travelled),0) FROM passport_entries").fetchone()[0],
        'queue': conn.execute("SELECT COUNT(*) FROM queue WHERE status='waiting'").fetchone()[0],
    }
    genre_data = conn.execute("SELECT genre, COUNT(*) as cnt FROM books GROUP BY genre").fetchall()
    conn.close()
    return render_template('admin.html', users=users, books=books, payments=payments, stats=stats, genre_data=genre_data)

@app.route('/admin/add_book', methods=['POST'])
def add_book():
    if session.get('user_role') != 'admin':
        return redirect('/')
    data = request.form
    colors = ['#c0783c','#2d6a4f','#6b2d2d','#4a4e8c','#1a6b8a','#7b5e3a','#3d6b5e','#5c4a7a']
    code = 'ONWA-' + ''.join(random.choices(string.digits, k=4))
    conn = get_db()
    conn.execute("INSERT INTO books (title,author,genre,description,cover_color,passport_code,added_by) VALUES (?,?,?,?,?,?,?)", (data['title'],data['author'],data['genre'],data['description'],random.choice(colors), code, session['user_id']))
    conn.execute("INSERT INTO activity (user_id,type,message) VALUES (?,?,?)", (session['user_id'],'added',f"A new book was added to the Onwa library: {data['title']}"))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if session.get('user_role') != 'admin':
        return redirect('/')
    conn = get_db()
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

if __name__ == '__main__':
    init_db()
    print("\n  Onwa is running → http://localhost:5000")
    print("  Admin:  admin@onwa.com  /  admin123")
    print("  Member: shalem@onwa.com /  password\n")
    app.run(debug=True, port=5000)
