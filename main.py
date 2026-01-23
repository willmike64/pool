import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import pyrebase
import random
import requests
from datetime import datetime, timedelta
import pytz

# --------------- Firebase Setup -----------------
firebaseConfig = {
    "apiKey": st.secrets["FIREBASE_API_KEY"],
    "authDomain": st.secrets["FIREBASE_AUTH_DOMAIN"],
    "projectId": st.secrets["FIREBASE_PROJECT_ID"],
    "storageBucket": st.secrets["FIREBASE_STORAGE_BUCKET"],
    "messagingSenderId": st.secrets["FIREBASE_MESSAGING_SENDER_ID"],
    "appId": st.secrets["FIREBASE_APP_ID"],
    "databaseURL": st.secrets["FIREBASE_DATABASE_URL"]
}

# Initialize Firebase Auth (pyrebase)
firebase = pyrebase.initialize_app(firebaseConfig)
auth = firebase.auth()

# Firebase Admin SDK (Firestore)
cred = credentials.Certificate(dict(st.secrets["firebase_credentials"]))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --------------- User Login -----------------

def login_user():
    st.title("🏈 Super Bowl Squares - Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login / Register"):
        if not email or not password:
            st.error("Please enter both email and password")
            return
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.session_state.user = user
            st.session_state.email = email
            st.success(f"Welcome back, {email}!")
            st.rerun()
        except Exception as e:
            try:
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state.user = user
                st.session_state.email = email
                st.success(f"Account created! Welcome, {email}!")
                st.rerun()
            except Exception as e2:
                st.error(f"Error: {str(e2)}")
                st.info("Make sure Email/Password authentication is enabled in Firebase Console")

# --------------- Avatar / Icons -----------------

AVATARS = [
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🦆",
    "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🐛", "🦋",
    "🐌", "🐞", "🐜", "🦟", "🦗", "🕷", "🦂", "🐢", "🐍", "🦎",
    "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀", "🐡", "🐠", "🐟",
    "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆", "🦓", "🦍", "🦧",
    "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🦬", "🐃", "🐂",
    "🐄", "🐎", "🐖", "🐏", "🐑", "🦙", "🐐", "🦌", "🐕", "🐩",
    "🦮", "🐈", "🐓", "🦃", "🦚", "🦜", "🦢", "🦩", "🕊", "🐇",
    "🦝", "🦨", "🦡", "🦦", "🦥", "🐁", "🐀", "🐿", "🦔", "⭐"
]

def get_user_avatar(email):
    # Use hash to get consistent index for each email
    email_hash = hash(email)
    return AVATARS[email_hash % len(AVATARS)]

# --------------- Grid UI -----------------

@st.cache_data(ttl=2)
def get_all_squares():
    grid_ref = db.collection("squares")
    docs = grid_ref.stream()
    squares = {doc.id: doc.to_dict() for doc in docs}
    return squares

def get_game_config():
    config_ref = db.collection("config").document("game")
    config = config_ref.get()
    if config.exists:
        return config.to_dict()
    else:
        default_config = {
            "top_team": "NFC Team",
            "side_team": "AFC Team",
            "top_numbers": list(range(10)),
            "side_numbers": list(range(10)),
            "numbers_randomized": False
        }
        config_ref.set(default_config)
        return default_config

def draw_grid():
    st.title("🏈 Super Bowl Squares Grid")
    config = get_game_config()
    squares = get_all_squares()
    email = st.session_state.get("email")
    is_admin = email == "mwill1003@gmail.com"
    
    st.info("ℹ️ Numbers will be randomized just before game time to ensure fairness")
    
    if is_admin:
        top_team = st.text_input("Top Team (NFC)", value=config.get("top_team", "NFC Team"), key="top_team_input")
        side_team = st.text_input("Side Team (AFC)", value=config.get("side_team", "AFC Team"), key="side_team_input")
        
        if st.button("Update Teams"):
            db.collection("config").document("game").update({
                "top_team": top_team,
                "side_team": side_team
            })
            st.success("Teams updated!")
            st.rerun()
        
        if st.button("Reset Numbers to 0-9"):
            db.collection("config").document("game").update({
                "top_numbers": list(range(10)),
                "side_numbers": list(range(10)),
                "numbers_randomized": False
            })
            st.success("Numbers reset to 0-9!")
            st.rerun()
        
        if st.button("🎲 Randomize Numbers (Game Time Only!)"):
            nums = list(range(10))
            random.shuffle(nums)
            top_nums = nums.copy()
            random.shuffle(nums)
            side_nums = nums
            db.collection("config").document("game").update({
                "top_numbers": top_nums,
                "side_numbers": side_nums,
                "numbers_randomized": True
            })
            st.success("✅ Numbers randomized!")
            st.rerun()
    
    top_numbers = config.get("top_numbers", list(range(10)))
    side_numbers = config.get("side_numbers", list(range(10)))
    numbers_randomized = config.get("numbers_randomized", False)
    
    if not numbers_randomized:
        st.warning("⚠️ Numbers are currently 0-9 in order. They will be randomized before kickoff.")
    
    st.markdown(f"### {config.get('top_team', 'NFC Team')} →")
    header_cols = st.columns([1] + [1]*10)
    header_cols[0].write("")
    for j, num in enumerate(top_numbers):
        header_cols[j+1].markdown(f"**{num}**")
    
    for i in range(10):
        cols_container = st.columns([1] + [1]*10)
        cols_container[0].markdown(f"**{side_numbers[i]}**")
        for j in range(10):
            square_id = f"{i}-{j}"
            if square_id in squares:
                data = squares[square_id]
                avatar = data.get("avatar", "❌")
                claimed_by = data.get("claimed_by")
                paid = data.get("paid", False)
                
                if claimed_by == email and not paid:
                    if cols_container[j+1].button(avatar, key=square_id):
                        unclaim_square(square_id)
                else:
                    cols_container[j+1].button(avatar, key=square_id, disabled=True)
            else:
                if cols_container[j+1].button("⬜", key=square_id):
                    claim_square(square_id)
    
    st.markdown(f"### ↑ {config.get('side_team', 'AFC Team')}")

# --------------- Claim Logic -----------------

def claim_square(square_id):
    email = st.session_state.get("email")
    avatar = get_user_avatar(email)
    square_ref = db.collection("squares").document(square_id)
    if square_ref.get().exists:
        st.warning("Already claimed!")
        return
    square_ref.set({
        "claimed_by": email,
        "avatar": avatar,
        "timestamp": firestore.SERVER_TIMESTAMP
    })
    get_all_squares.clear()
    st.rerun()

def unclaim_square(square_id):
    if "confirm_unclaim" not in st.session_state:
        st.session_state.confirm_unclaim = square_id
        st.warning(f"Click again to confirm removing square {square_id}")
        return
    
    if st.session_state.confirm_unclaim == square_id:
        db.collection("squares").document(square_id).delete()
        get_all_squares.clear()
        st.session_state.confirm_unclaim = None
        st.success(f"Square {square_id} removed!")
        st.rerun()
    else:
        st.session_state.confirm_unclaim = square_id
        st.warning(f"Click again to confirm removing square {square_id}")

# --------------- Main App -----------------

def main():
    if "user" not in st.session_state:
        login_user()
        return
    st.sidebar.write(f"👤 {st.session_state.email}")
    show_odds_ticker()
    draw_grid()
    show_user_stats()

def show_odds_ticker():
    st.markdown("### 🎰 Current Super Bowl Odds")
    
    # Calculate time until Super Bowl LIX - Feb 9, 2025, 6:30 PM ET
    eastern = pytz.timezone('US/Eastern')
    game_time = eastern.localize(datetime(2025, 2, 9, 18, 30))
    now = datetime.now(pytz.UTC)
    time_diff = game_time - now
    
    if time_diff.total_seconds() > 0:
        days = time_diff.days
        hours = time_diff.seconds // 3600
        countdown = f"⏰ {days} days, {hours} hours until kickoff"
    else:
        countdown = "🏈 GAME TIME!"
    
    odds_data = fetch_superbowl_odds()
    
    if odds_data:
        odds_text = countdown + " • " + " • ".join(odds_data) + " • "
    else:
        odds_text = countdown + " • Super Bowl LIX • Feb 9, 2025 • Caesars Superdome, New Orleans • "
    
    st.markdown(
        f"""
        <style>
        @keyframes scroll {{
            0% {{ transform: translateX(100%); }}
            100% {{ transform: translateX(-100%); }}
        }}
        .ticker {{
            background-color: #1e1e1e;
            color: #ffd700;
            padding: 10px;
            overflow: hidden;
            white-space: nowrap;
            border-radius: 5px;
        }}
        .ticker-content {{
            display: inline-block;
            animation: scroll 40s linear infinite;
        }}
        </style>
        <div class="ticker">
            <div class="ticker-content">{odds_text * 3}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

@st.cache_data(ttl=3600)
def fetch_superbowl_odds():
    try:
        api_key = st.secrets["ODDS_API_KEY"]
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl_super_bowl_winner/odds/"
        params = {
            "apiKey": api_key,
            "regions": "us",
            "markets": "outrights",
            "oddsFormat": "american"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data or not isinstance(data, list) or len(data) == 0:
            return None
        
        event = data[0]
        bookmakers = event.get("bookmakers", [])
        
        if not bookmakers:
            return None
        
        team_odds = {}
        for bookmaker in bookmakers:
            markets = bookmaker.get("markets", [])
            for market in markets:
                if market.get("key") == "outrights":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        team = outcome.get("name")
                        price = outcome.get("price")
                        if team and price:
                            if team not in team_odds:
                                team_odds[team] = []
                            team_odds[team].append(price)
        
        avg_odds = {}
        for team, prices in team_odds.items():
            avg_odds[team] = sum(prices) / len(prices)
        
        sorted_teams = sorted(avg_odds.items(), key=lambda x: x[1])
        
        odds_list = []
        for team, odds in sorted_teams[:10]:
            odds_str = f"{team} {int(odds):+d}"
            odds_list.append(odds_str)
        
        return odds_list
        
    except Exception as e:
        return None

# --------------- User Stats -----------------

def show_user_stats():
    email = st.session_state.get("email")
    is_admin = email == "mwill1003@gmail.com"
    squares = db.collection("squares").where(filter=FieldFilter("claimed_by", "==", email)).stream()
    claimed = [s.id for s in squares]
    
    st.sidebar.markdown("### 💰 Payment")
    amount = len(claimed) * 10
    if amount > 0:
        venmo_url = f"https://venmo.com/u/michael-williams-200?txn=pay&amount={amount}&note=Football%20Pool%20-%20{len(claimed)}%20squares"
        st.sidebar.markdown(f"[Pay ${amount} via Venmo]({venmo_url})")
    else:
        st.sidebar.write("Claim squares to pay")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Your Squares")
    
    if claimed:
        config = get_game_config()
        top_numbers = config.get("top_numbers", list(range(10)))
        side_numbers = config.get("side_numbers", list(range(10)))
        
        square_labels = []
        for square_id in claimed:
            row, col = map(int, square_id.split("-"))
            top_num = top_numbers[col]
            side_num = side_numbers[row]
            square_labels.append(f"{top_num}-{side_num}")
        
        st.sidebar.write(", ".join(square_labels))
    else:
        st.sidebar.write("None yet")
    
    st.sidebar.write(f"💸 Total: ${amount}")
    
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ✅ Mark as Paid")
        all_squares = get_all_squares()
        players_payment = {}
        for square_id, data in all_squares.items():
            player_email = data.get("claimed_by")
            paid = data.get("paid", False)
            if player_email not in players_payment:
                players_payment[player_email] = {"count": 0, "paid": paid}
            players_payment[player_email]["count"] += 1
        
        for player_email, info in sorted(players_payment.items()):
            name = player_email.split("@")[0]
            amount = info["count"] * 10
            paid = info.get("paid", False)
            if st.sidebar.checkbox(f"{name} - ${amount}", value=paid, key=f"paid_{player_email}"):
                mark_player_paid(player_email, True)
            else:
                mark_player_paid(player_email, False)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Players Legend")
    
    all_squares = get_all_squares()
    players = {}
    for square_id, data in all_squares.items():
        player_email = data.get("claimed_by")
        avatar = data.get("avatar")
        if player_email not in players:
            players[player_email] = {"avatar": avatar, "count": 0}
        players[player_email]["count"] += 1
    
    for player_email, info in sorted(players.items(), key=lambda x: x[1]["count"], reverse=True):
        name = player_email.split("@")[0]
        if player_email == email:
            st.sidebar.markdown(f"**{info['avatar']} {name} (You)** - {info['count']} squares")
        else:
            st.sidebar.write(f"{info['avatar']} {name} - {info['count']} squares")

def mark_player_paid(player_email, paid_status):
    squares_ref = db.collection("squares").where(filter=FieldFilter("claimed_by", "==", player_email))
    for doc in squares_ref.stream():
        doc.reference.update({"paid": paid_status})
    get_all_squares.clear()

# --------------- Run -----------------
if __name__ == "__main__":
    main()