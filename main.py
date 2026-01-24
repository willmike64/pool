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
    # Original animals
    "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
    "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🐤", "🦆",
    "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🐛", "🦋",
    "🐌", "🐞", "🐜", "🦟", "🦗", "🕷", "🦂", "🐢", "🐍", "🦎",
    "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀", "🐡", "🐠", "🐟",
    "🐬", "🐳", "🐋", "🦈", "🐊", "🐅", "🐆", "🦓", "🦍", "🦧",
    "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🦬", "🐃", "🐂",
    "🐄", "🐎", "🐖", "🐏", "🐑", "🦙", "🐐", "🦌", "🐕", "🐩",
    "🦮", "🐈", "🐓", "🦃", "🦚", "🦜", "🦢", "🦩", "🕊", "🐇",
    "🦝", "🦨", "🦡", "🦦", "🦥", "🐁", "🐀", "🐿", "🦔", 
    # Sports & Activities
    "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
    "🏓", "🏸", "🥅", "⛳", "🏏", "🥊", "🥋", "🥌", "🎯", "🪀",
    # Food & Drinks
    "🍔", "🍕", "🌭", "🌮", "🌯", "🥙", "🧀", "🍗", "🍖", "🥩",
    "🍟", "🥓", "🍿", "🧈", "🍦", "🍧", "🍨", "🍩", "🍪", "🎂",
    # Objects & Symbols  
    "⭐", "🌟", "✨", "💥", "🔥", "⚡", "🌈", "💎", "💍", "🏆",
    "🥇", "🥈", "🥉", "🎯", "🎲", "🎰", "🎭", "🎨", "🎸", "🎺",
    # Faces & Emotions
    "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "😍", "🥰",
    "😘", "😎", "🤓", "🤩", "🥳", "😎", "🤡", "🤠", "🤯", "😱"
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
            "numbers_randomized": False,
            "winners": {"Q1": None, "Q2": None, "Q3": None, "Final": None}
        }
        config_ref.set(default_config)
        return default_config

def draw_grid():
    st.title("🏈 Super Bowl Squares Grid")
    config = get_game_config()
    squares = get_all_squares()
    email = st.session_state.get("email")
    is_admin = email == "mwill1003@gmail.com"
    
    # Add custom CSS for square styling
    st.markdown("""
        <style>
        /* Paid square styling - green border */
        div[data-testid="stButton"] button[kind="secondary"].paid-square {
            border: 3px solid #00ff00 !important;
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.5) !important;
        }
        
        /* Claimed square hover effect */
        div[data-testid="stButton"] button[kind="secondary"]:hover {
            transform: scale(1.05);
            transition: transform 0.2s ease;
        }
        
        /* Unclaimed square styling */
        div[data-testid="stButton"] button[kind="secondary"]:not(:disabled) {
            background-color: #f0f0f0;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        </style>
    """, unsafe_allow_html=True)
    
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
        
        # Winner Assignment
        st.markdown("---")
        st.markdown("### 🏆 Assign Quarter Winners")
        winners = config.get("winners", {"Q1": None, "Q2": None, "Q3": None, "Final": None})
        
        col1, col2 = st.columns(2)
        with col1:
            q1_nfc = st.number_input("Q1 - NFC Score (last digit)", 0, 9, value=winners.get("Q1", {}).get("nfc", 0) if winners.get("Q1") else 0, key="q1_nfc")
            q1_afc = st.number_input("Q1 - AFC Score (last digit)", 0, 9, value=winners.get("Q1", {}).get("afc", 0) if winners.get("Q1") else 0, key="q1_afc")
            if st.button("Set Q1 Winner"):
                set_quarter_winner("Q1", q1_nfc, q1_afc, top_numbers, side_numbers)
        
        with col2:
            q2_nfc = st.number_input("Q2 - NFC Score (last digit)", 0, 9, value=winners.get("Q2", {}).get("nfc", 0) if winners.get("Q2") else 0, key="q2_nfc")
            q2_afc = st.number_input("Q2 - AFC Score (last digit)", 0, 9, value=winners.get("Q2", {}).get("afc", 0) if winners.get("Q2") else 0, key="q2_afc")
            if st.button("Set Q2 Winner"):
                set_quarter_winner("Q2", q2_nfc, q2_afc, top_numbers, side_numbers)
        
        col3, col4 = st.columns(2)
        with col3:
            q3_nfc = st.number_input("Q3 - NFC Score (last digit)", 0, 9, value=winners.get("Q3", {}).get("nfc", 0) if winners.get("Q3") else 0, key="q3_nfc")
            q3_afc = st.number_input("Q3 - AFC Score (last digit)", 0, 9, value=winners.get("Q3", {}).get("afc", 0) if winners.get("Q3") else 0, key="q3_afc")
            if st.button("Set Q3 Winner"):
                set_quarter_winner("Q3", q3_nfc, q3_afc, top_numbers, side_numbers)
        
        with col4:
            final_nfc = st.number_input("Final - NFC Score (last digit)", 0, 9, value=winners.get("Final", {}).get("nfc", 0) if winners.get("Final") else 0, key="final_nfc")
            final_afc = st.number_input("Final - AFC Score (last digit)", 0, 9, value=winners.get("Final", {}).get("afc", 0) if winners.get("Final") else 0, key="final_afc")
            if st.button("Set Final Winner"):
                set_quarter_winner("Final", final_nfc, final_afc, top_numbers, side_numbers)
    
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
                
                # Add visual indicator for paid squares
                if paid:
                    button_label = f"✅ {avatar}"  # Checkmark + avatar for paid
                else:
                    button_label = avatar
                
                if claimed_by == email and not paid:
                    if cols_container[j+1].button(button_label, key=square_id):
                        unclaim_square(square_id)
                else:
                    cols_container[j+1].button(button_label, key=square_id, disabled=True)
            else:
                if cols_container[j+1].button("⬜", key=square_id):
                    claim_square(square_id)
    
    st.markdown(f"### ↑ {config.get('side_team', 'AFC Team')}")
    
    # Display Payouts
    st.markdown("---")
    st.markdown("### 💰 Prize Payouts")
    payout_cols = st.columns(4)
    payouts = [("Q1", "$100"), ("Q2", "$150"), ("Q3", "$250"), ("Final", "$500")]
    for idx, (quarter, amount) in enumerate(payouts):
        with payout_cols[idx]:
            st.markdown(f"**{quarter}**")
            st.markdown(f"<h2 style='text-align: center; color: #00ff00;'>{amount}</h2>", unsafe_allow_html=True)
    
    # Display Winners
    winners = config.get("winners", {})
    if any(winners.values()):
        st.markdown("---")
        st.markdown("### 🏆 Quarter Winners")
        winner_cols = st.columns(4)
        for idx, (quarter, data) in enumerate([("Q1", winners.get("Q1")), ("Q2", winners.get("Q2")), ("Q3", winners.get("Q3")), ("Final", winners.get("Final"))]):
            with winner_cols[idx]:
                if data:
                    st.markdown(f"**{quarter}**")
                    st.markdown(f"{data.get('winner_avatar', '❓')} {data.get('winner_email', 'Unclaimed').split('@')[0]}")
                    st.markdown(f"Score: {data.get('nfc', 0)}-{data.get('afc', 0)}")
                else:
                    st.markdown(f"**{quarter}**")
                    st.markdown("Not set")

# --------------- Claim Logic -----------------

def claim_square(square_id):
    email = st.session_state.get("email")
    
    # Check if user already has squares and reuse their avatar
    all_squares = get_all_squares()
    existing_avatar = None
    for sid, data in all_squares.items():
        if data.get("claimed_by") == email:
            existing_avatar = data.get("avatar")
            break
    
    # Use existing avatar or generate new one
    avatar = existing_avatar if existing_avatar else get_user_avatar(email)
    
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

def set_quarter_winner(quarter, nfc_score, afc_score, top_numbers, side_numbers):
    # Find the winning square based on scores
    try:
        nfc_col = top_numbers.index(nfc_score)
        afc_row = side_numbers.index(afc_score)
        winning_square_id = f"{afc_row}-{nfc_col}"
        
        # Get the square data
        all_squares = get_all_squares()
        if winning_square_id in all_squares:
            winner_data = all_squares[winning_square_id]
            winner_email = winner_data.get("claimed_by", "Unclaimed")
            winner_avatar = winner_data.get("avatar", "❓")
        else:
            winner_email = "Unclaimed"
            winner_avatar = "❓"
        
        # Update config with winner info
        config_ref = db.collection("config").document("game")
        config = config_ref.get().to_dict()
        winners = config.get("winners", {})
        winners[quarter] = {
            "nfc": nfc_score,
            "afc": afc_score,
            "square_id": winning_square_id,
            "winner_email": winner_email,
            "winner_avatar": winner_avatar
        }
        config_ref.update({"winners": winners})
        
        st.success(f"{quarter} Winner: {winner_avatar} {winner_email.split('@')[0]} (Square {nfc_score}-{afc_score})")
        st.rerun()
    except ValueError:
        st.error("Invalid score - number not found in grid!")

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
    
    # Calculate time until Super Bowl LX - Feb 8, 2026, 6:30 PM ET
    eastern = pytz.timezone('US/Eastern')
    game_time = eastern.localize(datetime(2026, 2, 8, 18, 30))
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
        odds_text = countdown + " • Super Bowl LX • Feb 8, 2026 • Caesars Superdome, New Orleans • "
    
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
    
    # Avatar Picker - only if user has claimed squares
    if claimed:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎨 Change Your Avatar")
        
        # Get all squares to find taken avatars
        all_squares = get_all_squares()
        
        # Find avatars used by OTHER players
        taken_avatars = set()
        current_user_avatar = None
        for square_id, data in all_squares.items():
            avatar = data.get("avatar")
            claimed_by = data.get("claimed_by")
            if claimed_by == email:
                current_user_avatar = avatar
            elif claimed_by != email:
                taken_avatars.add(avatar)
        
        # Available avatars = all avatars minus ones taken by others
        available_avatars = [a for a in AVATARS if a not in taken_avatars]
        
        # Find current avatar index
        try:
            current_index = available_avatars.index(current_user_avatar)
        except ValueError:
            current_index = 0
        
        selected_avatar = st.sidebar.selectbox(
            "Pick your icon:",
            available_avatars,
            index=current_index,
            key="avatar_picker"
        )
        
        if selected_avatar != current_user_avatar:
            if st.sidebar.button("Update Avatar"):
                # Update all user's squares with new avatar
                for square_id in claimed:
                    db.collection("squares").document(square_id).update({"avatar": selected_avatar})
                get_all_squares.clear()
                st.sidebar.success(f"Avatar changed to {selected_avatar}!")
                st.rerun()
    
    st.sidebar.markdown("---")
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
    
    # Mini Game - 2048 Football
    st.sidebar.markdown("---")
    if st.sidebar.button("🎮 Play 2048 Football!"):
        st.session_state.show_2048 = not st.session_state.get("show_2048", False)
    
    if st.session_state.get("show_2048", False):
        play_2048_football()
    
    # Mini Game - Memory Match
    st.sidebar.markdown("---")
    if st.sidebar.button("🧠 Play Memory Match!"):
        st.session_state.show_memory = not st.session_state.get("show_memory", False)
    
    if st.session_state.get("show_memory", False):
        play_memory_match()
    
    # Mini Game - Catch the Football
    st.sidebar.markdown("---")
    if st.sidebar.button("⚡ Catch the Football!"):
        st.session_state.show_catch = not st.session_state.get("show_catch", False)
    
    if st.session_state.get("show_catch", False):
        play_catch_football()

def mark_player_paid(player_email, paid_status):
    squares_ref = db.collection("squares").where(filter=FieldFilter("claimed_by", "==", player_email))
    for doc in squares_ref.stream():
        doc.reference.update({"paid": paid_status})
    get_all_squares.clear()

# --------------- 2048 Football Game -----------------

def play_2048_football():
    st.sidebar.markdown("### 🏈 2048 Football")
    
    # Instructions
    with st.sidebar.expander("📖 How to Play"):
        st.write("""
        **Goal:** Reach the 🏁 (2048) tile!
        
        **How it works:**
        - **ALL tiles slide together** in the arrow direction
        - When two matching tiles collide, they merge!
        
        **Example:**
        ```
        Before ⬅️:  [⬜][🏈][🏈][⬜]
        After  ⬅️:  [🎯][⬜][⬜][⬜]
        ```
        The two 🏈 slid left and merged into 🎯!
        
        **Controls:**
        - ⬅️ = Slide all tiles left
        - ➡️ = Slide all tiles right
        - ⬆️ = Slide all tiles up
        - ⬇️ = Slide all tiles down
        
        **Progression:**
        🏈(2) → 🎯(4) → 🏆(8) → 🥇(16) → 🔥(32) → ⚡(64) → 💥(128) → ⭐(256) → 🌟(512) → 💫(1024) → 🏁(2048)
        """)
    
    # Initialize game state
    if "game_2048" not in st.session_state:
        st.session_state.game_2048 = [[0]*4 for _ in range(4)]
        st.session_state.score_2048 = 0
        add_new_tile()
        add_new_tile()
    
    # Football emojis for tiles
    tile_emojis = {
        0: "⬜",
        2: "🏈",
        4: "🎯",
        8: "🏆",
        16: "🥇",
        32: "🔥",
        64: "⚡",
        128: "💥",
        256: "⭐",
        512: "🌟",
        1024: "💫",
        2048: "🏁"
    }
    
    st.sidebar.write(f"Score: {st.session_state.score_2048}")
    
    # Display grid
    for row in st.session_state.game_2048:
        cols = st.sidebar.columns(4)
        for idx, val in enumerate(row):
            emoji = tile_emojis.get(val, "🏁")
            cols[idx].markdown(f"<div style='text-align: center; font-size: 30px;'>{emoji}</div>", unsafe_allow_html=True)
    
    # Controls
    st.sidebar.write("**Controls:**")
    col1, col2, col3 = st.sidebar.columns([1, 1, 1])
    with col2:
        if st.button("⬆️", key="up_2048", use_container_width=True):
            move_up()
    
    col4, col5, col6 = st.sidebar.columns([1, 1, 1])
    with col4:
        if st.button("⬅️", key="left_2048", use_container_width=True):
            move_left()
    with col5:
        if st.button("⬇️", key="down_2048", use_container_width=True):
            move_down()
    with col6:
        if st.button("➡️", key="right_2048", use_container_width=True):
            move_right()
    
    if st.sidebar.button("New Game"):
        st.session_state.game_2048 = [[0]*4 for _ in range(4)]
        st.session_state.score_2048 = 0
        add_new_tile()
        add_new_tile()
        st.rerun()

def add_new_tile():
    empty_cells = [(i, j) for i in range(4) for j in range(4) if st.session_state.game_2048[i][j] == 0]
    if empty_cells:
        i, j = random.choice(empty_cells)
        st.session_state.game_2048[i][j] = 2 if random.random() < 0.9 else 4

def move_left():
    moved = False
    for i in range(4):
        row = [x for x in st.session_state.game_2048[i] if x != 0]
        new_row = []
        skip = False
        for j in range(len(row)):
            if skip:
                skip = False
                continue
            if j + 1 < len(row) and row[j] == row[j+1]:
                new_row.append(row[j] * 2)
                st.session_state.score_2048 += row[j] * 2
                skip = True
                moved = True
            else:
                new_row.append(row[j])
        new_row += [0] * (4 - len(new_row))
        if new_row != st.session_state.game_2048[i]:
            moved = True
        st.session_state.game_2048[i] = new_row
    if moved:
        add_new_tile()
        st.rerun()

def move_right():
    for i in range(4):
        st.session_state.game_2048[i] = st.session_state.game_2048[i][::-1]
    move_left()
    for i in range(4):
        st.session_state.game_2048[i] = st.session_state.game_2048[i][::-1]

def move_up():
    st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]
    move_left()
    st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]

def move_down():
    st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]
    move_right()
    st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]

# --------------- Memory Match Game -----------------

def play_memory_match():
    st.sidebar.markdown("### 🧠 Memory Match")
    
    # Instructions
    with st.sidebar.expander("📖 How to Play"):
        st.write("""
        **Goal:** Match all pairs of football emojis!
        
        **Rules:**
        - Click cards to flip them over
        - Find matching pairs
        - Match all pairs to win!
        - Try to do it in as few moves as possible
        """)
    
    # Initialize game
    if "memory_cards" not in st.session_state:
        emojis = ["🏈", "🏆", "🥇", "🔥", "⚡", "⭐", "🎯", "🏁"]
        cards = emojis * 2  # 2 of each
        random.shuffle(cards)
        st.session_state.memory_cards = cards
        st.session_state.memory_flipped = [False] * 16
        st.session_state.memory_matched = [False] * 16
        st.session_state.memory_first = None
        st.session_state.memory_moves = 0
    
    st.sidebar.write(f"Moves: {st.session_state.memory_moves}")
    matched_count = sum(st.session_state.memory_matched)
    st.sidebar.write(f"Matched: {matched_count // 2} / 8")
    
    # Display grid (4x4)
    for row in range(4):
        cols = st.sidebar.columns(4)
        for col in range(4):
            idx = row * 4 + col
            
            if st.session_state.memory_matched[idx]:
                # Matched - show emoji
                cols[col].markdown(f"<div style='text-align: center; font-size: 25px;'>{st.session_state.memory_cards[idx]}</div>", unsafe_allow_html=True)
            elif st.session_state.memory_flipped[idx]:
                # Flipped - show emoji
                cols[col].markdown(f"<div style='text-align: center; font-size: 25px;'>{st.session_state.memory_cards[idx]}</div>", unsafe_allow_html=True)
            else:
                # Hidden - show button
                if cols[col].button("🎴", key=f"mem_{idx}"):
                    flip_card(idx)
    
    # Check win
    if all(st.session_state.memory_matched):
        st.sidebar.success(f"🎉 You won in {st.session_state.memory_moves} moves!")
    
    if st.sidebar.button("New Game", key="new_memory"):
        del st.session_state.memory_cards
        del st.session_state.memory_flipped
        del st.session_state.memory_matched
        del st.session_state.memory_first
        del st.session_state.memory_moves
        st.rerun()

def flip_card(idx):
    # Can't flip if already matched or already flipped
    if st.session_state.memory_matched[idx] or st.session_state.memory_flipped[idx]:
        return
    
    # Flip the card
    st.session_state.memory_flipped[idx] = True
    
    if st.session_state.memory_first is None:
        # First card flipped
        st.session_state.memory_first = idx
    else:
        # Second card flipped
        st.session_state.memory_moves += 1
        first_idx = st.session_state.memory_first
        
        if st.session_state.memory_cards[first_idx] == st.session_state.memory_cards[idx]:
            # Match!
            st.session_state.memory_matched[first_idx] = True
            st.session_state.memory_matched[idx] = True
        else:
            # No match - flip back after showing
            import time
            time.sleep(0.5)
            st.session_state.memory_flipped[first_idx] = False
            st.session_state.memory_flipped[idx] = False
        
        st.session_state.memory_first = None
    
    st.rerun()

# --------------- Catch the Football Game -----------------

def play_catch_football():
    st.sidebar.markdown("### ⚡ Catch the Football")
    
    # Instructions
    with st.sidebar.expander("📖 How to Play"):
        st.write("""
        **Goal:** Test your reaction time!
        
        **Rules:**
        - Click START to begin
        - Wait for the 🏈 to appear
        - Click it as FAST as you can!
        - Your time is recorded in milliseconds
        - Compete for the best time!
        """)
    
    # Initialize game
    if "catch_state" not in st.session_state:
        st.session_state.catch_state = "ready"  # ready, waiting, show, caught
        st.session_state.catch_start_time = None
        st.session_state.catch_show_time = None
        st.session_state.catch_best_time = None
    
    if st.session_state.catch_state == "ready":
        if st.sidebar.button("🚀 START", key="catch_start", use_container_width=True):
            st.session_state.catch_state = "waiting"
            st.session_state.catch_start_time = datetime.now()
            # Random delay between 1-4 seconds
            delay = random.uniform(1, 4)
            st.session_state.catch_show_time = st.session_state.catch_start_time + timedelta(seconds=delay)
            st.rerun()
        
        if st.session_state.catch_best_time:
            st.sidebar.success(f"🏆 Best: {st.session_state.catch_best_time}ms")
    
    elif st.session_state.catch_state == "waiting":
        now = datetime.now()
        if now >= st.session_state.catch_show_time:
            st.session_state.catch_state = "show"
            st.session_state.catch_show_time = now
            st.rerun()
        else:
            st.sidebar.warning("⏳ Wait for it...")
            # Auto-refresh to check if it's time
            import time
            time.sleep(0.1)
            st.rerun()
    
    elif st.session_state.catch_state == "show":
        st.sidebar.markdown("<div style='text-align: center; font-size: 80px;'>🏈</div>", unsafe_allow_html=True)
        if st.sidebar.button("🏈 CATCH IT!", key="catch_it", use_container_width=True):
            catch_time = datetime.now()
            reaction_ms = int((catch_time - st.session_state.catch_show_time).total_seconds() * 1000)
            
            # Update best time
            if st.session_state.catch_best_time is None or reaction_ms < st.session_state.catch_best_time:
                st.session_state.catch_best_time = reaction_ms
            
            # Save to leaderboard
            email = st.session_state.get("email")
            save_catch_score(email, reaction_ms)
            
            st.session_state.catch_state = "caught"
            st.session_state.catch_last_time = reaction_ms
            st.rerun()
    
    elif st.session_state.catch_state == "caught":
        st.sidebar.success(f"⚡ {st.session_state.catch_last_time}ms")
        if st.session_state.catch_best_time:
            st.sidebar.info(f"🏆 Your Best: {st.session_state.catch_best_time}ms")
        
        if st.sidebar.button("🔄 Try Again", key="catch_again"):
            st.session_state.catch_state = "ready"
            st.rerun()
    
    # Show leaderboard
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏆 Top 5 Fastest")
    show_catch_leaderboard()

def save_catch_score(email, reaction_ms):
    try:
        # Save to Firestore
        score_ref = db.collection("catch_scores").document(email)
        current = score_ref.get()
        
        if current.exists:
            current_best = current.to_dict().get("best_time", 999999)
            if reaction_ms < current_best:
                score_ref.update({"best_time": reaction_ms, "timestamp": firestore.SERVER_TIMESTAMP})
        else:
            score_ref.set({"email": email, "best_time": reaction_ms, "timestamp": firestore.SERVER_TIMESTAMP})
    except:
        pass  # Fail silently if Firestore error

def show_catch_leaderboard():
    try:
        scores = db.collection("catch_scores").order_by("best_time").limit(5).stream()
        for idx, doc in enumerate(scores, 1):
            data = doc.to_dict()
            name = data.get("email", "Unknown").split("@")[0]
            time_ms = data.get("best_time", 0)
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][idx-1]
            st.sidebar.write(f"{medal} {name}: {time_ms}ms")
    except:
        st.sidebar.write("No scores yet!")

# --------------- Run -----------------
if __name__ == "__main__":
    main()