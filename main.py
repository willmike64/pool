import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import pyrebase
import random
import requests
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import string
import csv

st.set_page_config(
    page_title="Super Bowl Squares",
    page_icon="🏈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* Compact grid buttons */
.compact-grid .stButton > button {
  width: 28px !important;
  height: 28px !important;
  min-width: 28px !important;
  padding: 0 !important;
  font-size: 0.7rem !important;
  margin: 1px !important;
}

/* Mobile layout */
@media (max-width: 768px) {
  body:not(.compact-mode) .stButton > button {
    width: 100%;
    font-size: 1.05rem;
    padding: 0.75rem;
  }

  .block-container {
    padding: 1rem !important;
    max-width: 100vw !important;
  }

  .stColumn {
    width: 100% !important;
    flex: 1 1 100% !important;
  }

  .compact-grid .stColumn {
    width: auto !important;
    flex: 0 0 auto !important;
  }
  
  section.main > div {
    max-width: 100% !important;
  }
}
</style>
""", unsafe_allow_html=True)


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
        
        if st.button("Reset Numbers to 0-9"):
            db.collection("config").document("game").update({
                "top_numbers": list(range(10)),
                "side_numbers": list(range(10)),
                "numbers_randomized": False
            })
            st.success("Numbers reset to 0-9!")
        
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
    
    # Compact mode toggle
    if "compact_grid" not in st.session_state:
        st.session_state.compact_grid = False
    
    if st.button("🔍 Switch to Compact View" if not st.session_state.compact_grid else "🔎 Switch to Normal View"):
        st.session_state.compact_grid = not st.session_state.compact_grid
        st.rerun()
    
    # Open compact-grid wrapper
    if st.session_state.compact_grid:
        st.markdown('<div class="compact-grid">', unsafe_allow_html=True)
        st.markdown('<script>document.body.classList.add("compact-mode");</script>', unsafe_allow_html=True)
    
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
    
    # Close compact-grid wrapper
    if st.session_state.compact_grid:
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display Payouts
    st.markdown("---")
    st.markdown("### 💰 Prize Payouts")
    
    # Calculate total pot from paid squares
    all_squares = get_all_squares()
    paid_count = sum(1 for data in all_squares.values() if data.get("paid", False))
    total_pot = paid_count * 10
    
    # Calculate payouts based on percentages
    q1_payout = int(total_pot * 0.10)
    q2_payout = int(total_pot * 0.15)
    q3_payout = int(total_pot * 0.25)
    final_payout = int(total_pot * 0.50)
    
    st.info(f"🎫 {paid_count} paid squares = ${total_pot} total pot")
    
    payout_cols = st.columns(4)
    payouts = [("Q1", q1_payout, "10%"), ("Q2", q2_payout, "15%"), ("Q3", q3_payout, "25%"), ("Final", final_payout, "50%")]
    for idx, (quarter, amount, pct) in enumerate(payouts):
        with payout_cols[idx]:
            st.markdown(f"**{quarter}** ({pct})")
            st.markdown(f"<h2 style='text-align: center; color: #00ff00;'>${amount}</h2>", unsafe_allow_html=True)
    
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
    except ValueError:
        st.error("Invalid score - number not found in grid!")

# --------------- Games Page -----------------

def show_games_page():
    st.title("🎮 Football Games")
    
    game = st.radio("Select a game:", ["Catch the Football", "Field Goal Kicker", "Line Battle"], horizontal=True)
    st.markdown("---")
    
    if game == "Catch the Football":
        play_catch_football_main()
    elif game == "Field Goal Kicker":
        play_field_goal_kicker_main()
    else:
        play_line_battle_main()

def play_catch_football_main():
    st.markdown("### ⚡ Catch the Football")
    
    with st.expander("📖 How to Play"):
        st.write("""
        **Goal:** Test your reaction time!
        
        **Rules:**
        - Click START to begin
        - Wait for the 🏈 to appear
        - Click it as FAST as you can!
        - Your time is recorded in milliseconds
        - Compete for the best time!
        """)
    
    if "catch_state" not in st.session_state:
        st.session_state.catch_state = "ready"
        st.session_state.catch_start_time = None
        st.session_state.catch_show_time = None
        st.session_state.catch_best_time = None
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.session_state.catch_state == "ready":
            if st.button("🚀 START", key="catch_start", use_container_width=True):
                st.session_state.catch_state = "waiting"
                st.session_state.catch_start_time = datetime.now()
                delay = random.uniform(1, 4)
                st.session_state.catch_show_time = st.session_state.catch_start_time + timedelta(seconds=delay)
                st.rerun()
            
            if st.session_state.catch_best_time:
                st.success(f"🏆 Your Best: {st.session_state.catch_best_time}ms")
        
        elif st.session_state.catch_state == "waiting":
            now = datetime.now()
            if now >= st.session_state.catch_show_time:
                st.session_state.catch_state = "show"
                st.session_state.catch_show_time = now
                st.rerun()
            else:
                st.warning("⏳ Wait for it...")
        
        elif st.session_state.catch_state == "show":
            st.markdown("<div style='text-align: center; font-size: 120px;'>🏈</div>", unsafe_allow_html=True)
            if st.button("🏈 CATCH IT!", key="catch_it", use_container_width=True):
                catch_time = datetime.now()
                reaction_ms = int((catch_time - st.session_state.catch_show_time).total_seconds() * 1000)
                
                if st.session_state.catch_best_time is None or reaction_ms < st.session_state.catch_best_time:
                    st.session_state.catch_best_time = reaction_ms
                
                email = st.session_state.get("email")
                save_catch_score(email, reaction_ms)
                
                st.session_state.catch_state = "caught"
                st.session_state.catch_last_time = reaction_ms
                st.rerun()
        
        elif st.session_state.catch_state == "caught":
            st.success(f"⚡ {st.session_state.catch_last_time}ms")
            if st.session_state.catch_best_time:
                st.info(f"🏆 Your Best: {st.session_state.catch_best_time}ms")
            
            if st.button("🔄 Try Again", key="catch_again"):
                st.session_state.catch_state = "ready"
                st.rerun()
    
    with col2:
        st.markdown("### 🏆 Top 5 Fastest")
        show_catch_leaderboard()

def save_catch_score(email, reaction_ms):
    try:
        score_ref = db.collection("catch_scores").document(email)
        current = score_ref.get()
        
        if current.exists:
            current_best = current.to_dict().get("best_time", 999999)
            if reaction_ms < current_best:
                score_ref.update({"best_time": reaction_ms, "timestamp": firestore.SERVER_TIMESTAMP})
        else:
            score_ref.set({"email": email, "best_time": reaction_ms, "timestamp": firestore.SERVER_TIMESTAMP})
    except:
        pass

def show_catch_leaderboard():
    try:
        scores = db.collection("catch_scores").order_by("best_time").limit(5).stream()
        for idx, doc in enumerate(scores, 1):
            data = doc.to_dict()
            name = data.get("email", "Unknown").split("@")[0]
            time_ms = data.get("best_time", 0)
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][idx-1]
            st.write(f"{medal} {name}: {time_ms}ms")
    except:
        st.write("No scores yet!")

def save_kicker_score(email, score, made, attempts):
    try:
        score_ref = db.collection("kicker_scores").document(email)
        current = score_ref.get()
        
        if current.exists:
            current_best = current.to_dict().get("high_score", 0)
            if score > current_best:
                score_ref.update({"high_score": score, "made": made, "attempts": attempts, "timestamp": firestore.SERVER_TIMESTAMP})
        else:
            score_ref.set({"email": email, "high_score": score, "made": made, "attempts": attempts, "timestamp": firestore.SERVER_TIMESTAMP})
    except:
        pass

def show_kicker_leaderboard():
    try:
        scores = db.collection("kicker_scores").order_by("high_score", direction=firestore.Query.DESCENDING).limit(5).stream()
        for idx, doc in enumerate(scores, 1):
            data = doc.to_dict()
            name = data.get("email", "Unknown").split("@")[0]
            high_score = data.get("high_score", 0)
            made = data.get("made", 0)
            attempts = data.get("attempts", 0)
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][idx-1]
            st.write(f"{medal} {name}: {high_score} pts")
            st.caption(f"{made}/{attempts} made")
    except:
        st.write("No scores yet!")

# --------------- Line Battle Game -----------------

# NFL Team helmets - Super Bowl matchup!
NFL_TEAMS = {
    "Seahawks": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/sea.png&h=100&w=100",
    "Patriots": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nfl/500/ne.png&h=100&w=100"
}

def play_line_battle_main():
    st.markdown("### 🏈 Line Battle")
    
    # Team selection at start
    if "battle_user_team" not in st.session_state:
        st.markdown("### Pick Your Team!")
        col1, col2 = st.columns(2)
        with col1:
            st.image(NFL_TEAMS['Seahawks'], width=150)
            if st.button("🦅 Seattle Seahawks", key="team_seahawks", use_container_width=True):
                st.session_state.battle_user_team = "Seahawks"
                st.session_state.battle_cpu_team = "Patriots"
                st.rerun()
        with col2:
            st.image(NFL_TEAMS['Patriots'], width=150)
            if st.button("🔴 New England Patriots", key="team_patriots", use_container_width=True):
                st.session_state.battle_user_team = "Patriots"
                st.session_state.battle_cpu_team = "Seahawks"
                st.rerun()
        return
    
    user_team = st.session_state.battle_user_team
    cpu_team = st.session_state.battle_cpu_team
    user_helmet = NFL_TEAMS[user_team]
    cpu_helmet = NFL_TEAMS[cpu_team]
    
    with st.expander("📖 How to Play"):
        st.write("**Goal:** Score touchdowns by winning line battles! Click SNAP to start. Team with highest dice total wins. 6 vs 1 = +5 bonus yards. Reach 30+ yards = TD (7 pts). First to 21 wins!")
    
    # Initialize game
    if "battle_score_user" not in st.session_state:
        st.session_state.battle_score_user = 0
        st.session_state.battle_score_cpu = 0
        st.session_state.battle_yards = 0
        st.session_state.battle_rolls_user = None
        st.session_state.battle_rolls_cpu = None
        st.session_state.battle_down = 1
        st.session_state.battle_yards_to_go = 10
        st.session_state.battle_possession = "user"
        st.session_state.battle_drive_start = 0
        st.session_state.battle_fg_mode = False
        st.session_state.battle_fg_distance = 0
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Show team helmets with possession indicator
        helmet_html = f"""
        <div style='display: flex; justify-content: space-around; align-items: center; margin: 20px 0; padding: 15px; background: linear-gradient(90deg, #1e1e1e 0%, #2d2d2d 50%, #1e1e1e 100%); border-radius: 10px;'>
            <div style='text-align: center; {'opacity: 1; transform: scale(1.1);' if st.session_state.battle_possession == 'user' else 'opacity: 0.4;'} transition: all 0.3s;'>
                <img src='{user_helmet}' width='80' style='filter: {'drop-shadow(0 0 15px #00ff00)' if st.session_state.battle_possession == 'user' else 'none'};'/>
                <div style='color: #00ff00; font-weight: bold; margin-top: 10px;'>{user_team}</div>
                <div style='font-size: 24px; color: #00ff00;'>{st.session_state.battle_score_user}</div>
            </div>
            <div style='font-size: 40px; color: #ffd700;'>🏆 VS 🏆</div>
            <div style='text-align: center; {'opacity: 1; transform: scale(1.1);' if st.session_state.battle_possession == 'cpu' else 'opacity: 0.4;'} transition: all 0.3s;'>
                <img src='{cpu_helmet}' width='80' style='filter: {'drop-shadow(0 0 15px #ff0000)' if st.session_state.battle_possession == 'cpu' else 'none'};'/>
                <div style='color: #ff0000; font-weight: bold; margin-top: 10px;'>{cpu_team}</div>
                <div style='font-size: 24px; color: #ff0000;'>{st.session_state.battle_score_cpu}</div>
            </div>
        </div>
        """
        st.markdown(helmet_html, unsafe_allow_html=True)
        
        # Compact status
        st.markdown(f"**{'🟢 YOUR BALL' if st.session_state.battle_possession == 'user' else '🔴 CPU BALL'}** | Down {st.session_state.battle_down}, {st.session_state.battle_yards_to_go} to go | Field: {50 + st.session_state.battle_yards} yd")
        
        yards = st.session_state.battle_yards
        
        # Check for touchdown
        if st.session_state.battle_possession == "user" and yards >= 30:
            st.success("🎉 TOUCHDOWN! You scored 7 points!")
            st.session_state.battle_score_user += 7
            st.session_state.battle_yards = 0
            st.session_state.battle_down = 1
            st.session_state.battle_yards_to_go = 10
            st.session_state.battle_possession = "cpu"
            st.session_state.battle_drive_start = 0
            st.session_state.battle_rolls_user = None
            st.session_state.battle_rolls_cpu = None
            st.balloons()
        elif st.session_state.battle_possession == "cpu" and yards <= -30:
            st.error("😱 CPU TOUCHDOWN! They scored 7 points!")
            st.session_state.battle_score_cpu += 7
            st.session_state.battle_yards = 0
            st.session_state.battle_down = 1
            st.session_state.battle_yards_to_go = 10
            st.session_state.battle_possession = "user"
            st.session_state.battle_drive_start = 0
            st.session_state.battle_rolls_user = None
            st.session_state.battle_rolls_cpu = None
        
        # Animated field visualization
        yards = st.session_state.battle_yards
        
        # Convert yards to proper field position (0-50 scale)
        if yards > 0:
            # Moving towards opponent's endzone
            if yards <= 50:
                field_position = 50 - yards
                field_desc = f"Own {field_position}"
            else:
                field_position = yards - 50
                field_desc = f"Opp {field_position}"
        else:
            # Negative yards (opponent has ball or pushed back)
            if yards >= -50:
                field_position = 50 + yards
                field_desc = f"Own {field_position}"
            else:
                field_position = abs(yards) - 50
                field_desc = f"Opp {field_position}"
        
        st.markdown(f"**Field Position: {field_desc} yard line**")
        
        # Calculate ball position for animation (0-100%)
        field_pos = max(0, min(100, 50 + yards))
        
        field_html = f"""
        <style>
        .field {{
            background: linear-gradient(90deg, #2d5016 0%, #3d6b1f 50%, #2d5016 100%);
            height: 100px;
            position: relative;
            border: 3px solid white;
            margin: 20px 0;
        }}
        .ball {{
            position: absolute;
            left: {field_pos}%;
            top: 50%;
            transform: translate(-50%, -50%);
            font-size: 40px;
            animation: bounce 1s infinite;
        }}
        @keyframes bounce {{
            0%, 100% {{ transform: translate(-50%, -50%); }}
            50% {{ transform: translate(-50%, -60%); }}
        }}
        .endzone-left {{
            position: absolute;
            left: 0;
            top: 0;
            width: 10%;
            height: 100%;
            background: rgba(255, 0, 0, 0.3);
        }}
        .endzone-right {{
            position: absolute;
            right: 0;
            top: 0;
            width: 10%;
            height: 100%;
            background: rgba(0, 255, 0, 0.3);
        }}
        </style>
        <div class='field'>
            <div class='endzone-left'></div>
            <div class='endzone-right'></div>
            <div class='ball'>🏈</div>
        </div>
        """
        st.markdown(field_html, unsafe_allow_html=True)
        
        # Check win condition
        if st.session_state.battle_score_user >= 21:
            st.success(f"🏆 {user_team.upper()} WIN THE GAME!")
            if st.button("Play Again", key="battle_reset_win"):
                del st.session_state.battle_user_team
                del st.session_state.battle_cpu_team
                st.session_state.battle_score_user = 0
                st.session_state.battle_score_cpu = 0
                st.session_state.battle_yards = 0
                st.session_state.battle_rolls_user = None
                st.session_state.battle_rolls_cpu = None
                st.session_state.battle_down = 1
                st.session_state.battle_yards_to_go = 10
                st.session_state.battle_possession = "user"
                st.session_state.battle_drive_start = 0
                st.rerun()
            return
        elif st.session_state.battle_score_cpu >= 21:
            st.error(f"😔 {cpu_team.upper()} WIN THE GAME!")
            if st.button("Play Again", key="battle_reset_lose"):
                del st.session_state.battle_user_team
                del st.session_state.battle_cpu_team
                st.session_state.battle_score_user = 0
                st.session_state.battle_score_cpu = 0
                st.session_state.battle_yards = 0
                st.session_state.battle_rolls_user = None
                st.session_state.battle_rolls_cpu = None
                st.session_state.battle_down = 1
                st.session_state.battle_yards_to_go = 10
                st.session_state.battle_possession = "user"
                st.session_state.battle_drive_start = 0
                st.rerun()
            return
        
        # Line of scrimmage - HEAD TO HEAD DICE ANIMATION
        if st.session_state.battle_rolls_user:
            user_total = sum(st.session_state.battle_rolls_user)
            cpu_total = sum(st.session_state.battle_rolls_cpu)
            
            # Show totals and result in one line
            bonus_count = sum(1 for i in range(11) if st.session_state.battle_rolls_user[i] == 6 and st.session_state.battle_rolls_cpu[i] == 1) - sum(1 for i in range(11) if st.session_state.battle_rolls_user[i] == 1 and st.session_state.battle_rolls_cpu[i] == 6)
            yards_diff = abs(user_total - cpu_total)
            
            # 1) Show overall result first
            if user_total > cpu_total:
                total_yards = yards_diff + (bonus_count * 5 if bonus_count > 0 else 0)
                result = f"✅ {user_team.upper()} WIN! +{total_yards} yards"
                if bonus_count > 0:
                    result += f" (⭐ +{bonus_count * 5} bonus)"
            elif user_total < cpu_total:
                total_yards = yards_diff + (abs(bonus_count) * 5 if bonus_count < 0 else 0)
                result = f"❌ {cpu_team.upper()} WIN! -{total_yards} yards"
                if bonus_count < 0:
                    result += f" (💥 {abs(bonus_count) * 5} penalty)"
            else:
                result = "🤝 TIE! No change"
            
            # 2) Show prediction result if available
            if "battle_prediction_result" in st.session_state and st.session_state.battle_prediction_result:
                pred_result = st.session_state.battle_prediction_result
                if pred_result["correct"]:
                    result += f" | ⭐ PREDICTION CORRECT! 2X MULTIPLIER!"
                    # Apply multiplier to yards
                    if user_total > cpu_total:
                        total_yards *= 2
                    elif user_total < cpu_total:
                        total_yards *= 2
                else:
                    winning = pred_result['winning_sections']
                    if winning:
                        winning_str = ", ".join([s.upper() for s in winning])
                        result += f" | 🔶 Wrong pick: {winning_str} won"
                    else:
                        result += f" | 🔶 Wrong pick: NO sections won"
            
            # Show result with helmet images
            result_html = f"""
            <div style='display: flex; align-items: center; justify-content: center; gap: 15px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px;'>
                <img src='{user_helmet}' width='40'/>
                <span style='font-weight: bold; color: #00ff00;'>{user_team}: {user_total}</span>
                <span style='font-size: 24px;'>⚔️</span>
                <span style='font-weight: bold; color: #ff0000;'>{cpu_team}: {cpu_total}</span>
                <img src='{cpu_helmet}' width='40'/>
            </div>
            """
            st.markdown(result_html, unsafe_allow_html=True)
            st.info(result)
            
            # HEAD TO HEAD DICE ANIMATION
            dice_html = "<style>"
            for i in range(11):
                user_roll = st.session_state.battle_rolls_user[i]
                cpu_roll = st.session_state.battle_rolls_cpu[i]
                is_user_domination = (user_roll == 6 and cpu_roll == 1)
                is_cpu_domination = (cpu_roll == 6 and user_roll == 1)
                
                user_color = "gold" if is_user_domination else "red" if is_cpu_domination else "#00ff00"
                cpu_color = "gold" if is_cpu_domination else "red" if is_user_domination else "#ff0000"
                
                dice_html += f"""
                @keyframes slideUser{i} {{
                    0% {{ transform: translateX(-200px) rotateY(0deg); opacity: 0; }}
                    50% {{ transform: translateX(0) rotateY(720deg); opacity: 1; }}
                    100% {{ transform: translateX(0) rotateY(720deg); opacity: 1; }}
                }}
                @keyframes slideCpu{i} {{
                    0% {{ transform: translateX(200px) rotateY(0deg); opacity: 0; }}
                    50% {{ transform: translateX(0) rotateY(-720deg); opacity: 1; }}
                    100% {{ transform: translateX(0) rotateY(-720deg); opacity: 1; }}
                }}
                .dice-user{i} {{
                    animation: slideUser{i} 0.8s ease-out;
                    color: {user_color};
                    font-size: 28px;
                    font-weight: bold;
                    text-shadow: 0 0 10px rgba(0,255,0,0.5);
                }}
                .dice-cpu{i} {{
                    animation: slideCpu{i} 0.8s ease-out;
                    color: {cpu_color};
                    font-size: 28px;
                    font-weight: bold;
                    text-shadow: 0 0 10px rgba(255,0,0,0.5);
                }}
                """
            
            dice_html += "</style><div style='margin: 20px 0;'>"
            dice_html += "<div style='display: flex; justify-content: space-around; margin-bottom: 10px;'>"
            for i in range(11):
                user_roll = st.session_state.battle_rolls_user[i]
                is_domination = (user_roll == 6 and st.session_state.battle_rolls_cpu[i] == 1)
                bonus = "⭐" if is_domination else ""
                dice_html += f"<div class='dice-user{i}'>🎲{user_roll}{bonus}</div>"
            dice_html += "</div>"
            
            dice_html += "<div style='text-align: center; font-size: 40px; margin: 10px 0;'>⚔️ VS ⚔️</div>"
            
            dice_html += "<div style='display: flex; justify-content: space-around; margin-top: 10px;'>"
            for i in range(11):
                cpu_roll = st.session_state.battle_rolls_cpu[i]
                is_domination = (cpu_roll == 6 and st.session_state.battle_rolls_user[i] == 1)
                bonus = "⭐" if is_domination else ""
                dice_html += f"<div class='dice-cpu{i}'>🎲{cpu_roll}{bonus}</div>"
            dice_html += "</div></div>"
            
            st.markdown(dice_html, unsafe_allow_html=True)
        
        # SNAP button and 4th down options - compact
        st.markdown("---")
        
        # Initialize line prediction if not set
        if "battle_line_prediction" not in st.session_state:
            st.session_state.battle_line_prediction = None
        
        # Show line section picker FIRST if no choice made
        if st.session_state.battle_line_prediction is None:
            st.info("🎯 Pick which section of the line will win! (2x multiplier if correct)")
            col_l, col_m, col_r = st.columns(3)
            with col_l:
                if st.button("⬅️ LEFT (0-3)", key="pick_left", use_container_width=True):
                    st.session_state.battle_line_prediction = "left"
                    st.rerun()
            with col_m:
                if st.button("⬆️ MIDDLE (4-7)", key="pick_middle", use_container_width=True):
                    st.session_state.battle_line_prediction = "middle"
                    st.rerun()
            with col_r:
                if st.button("➡️ RIGHT (8-10)", key="pick_right", use_container_width=True):
                    st.session_state.battle_line_prediction = "right"
                    st.rerun()
            return  # Don't show SNAP button until choice is made
        
        # Show choice and SNAP button
        prediction_display = {
            "left": "⬅️ LEFT (0-3)",
            "middle": "⬆️ MIDDLE (4-7)",
            "right": "➡️ RIGHT (8-10)"
        }
        st.info(f"🎯 Your Pick: {prediction_display[st.session_state.battle_line_prediction]}")
        
        # Check for field goal option on 4th down
        if st.session_state.battle_down == 4:
            fg_distance = 30 - st.session_state.battle_yards + 17  # Add 17 for endzone + holder
            if st.session_state.battle_possession == "user" and 20 <= fg_distance <= 55:
                st.warning(f"🎯 4th Down - Field Goal Range! ({fg_distance} yards)")
                col_fg1, col_fg2, col_fg3 = st.columns(3)
                with col_fg1:
                    if st.button("🦵 ATTEMPT FIELD GOAL", key="fg_attempt", use_container_width=True):
                        st.session_state.battle_fg_mode = True
                        st.session_state.battle_fg_distance = fg_distance
                        st.rerun()
                with col_fg2:
                    if st.button("🥾 PUNT", key="punt_attempt", use_container_width=True):
                        # Punt 30-50 yards (push ball back towards own endzone)
                        punt_distance = random.randint(30, 50)
                        st.session_state.battle_yards += punt_distance
                        st.session_state.battle_possession = "cpu"
                        st.session_state.battle_down = 1
                        st.session_state.battle_yards_to_go = 10
                        st.success(f"🥾 Punted {punt_distance} yards!")
                        st.rerun()
                with col_fg3:
                    if st.button("🏈 GO FOR IT!", key="go_for_it", use_container_width=True):
                        pass  # Continue to normal snap
            elif st.session_state.battle_possession == "user":
                # Out of FG range, offer punt or go for it
                st.warning("🎯 4th Down - Out of FG Range")
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    if st.button("🥾 PUNT", key="punt_attempt2", use_container_width=True):
                        # Punt 30-50 yards (push ball back towards own endzone)
                        punt_distance = random.randint(30, 50)
                        st.session_state.battle_yards += punt_distance
                        st.session_state.battle_possession = "cpu"
                        st.session_state.battle_down = 1
                        st.session_state.battle_yards_to_go = 10
                        st.success(f"🥾 Punted {punt_distance} yards!")
                        st.rerun()
                with col_p2:
                    if st.button("🏈 GO FOR IT!", key="go_for_it2", use_container_width=True):
                        pass  # Continue to normal snap
            elif st.session_state.battle_possession == "cpu" and 20 <= fg_distance <= 55:
                # CPU decides: 70% FG, 30% punt
                cpu_decision = random.random()
                if cpu_decision < 0.7:
                    st.info(f"🔴 CPU is attempting a {fg_distance} yard field goal!")
                    st.write("**Try to block it!** Roll higher to block:")
                    if st.button("🚫 ATTEMPT BLOCK!", key="block_attempt", use_container_width=True):
                        user_block = random.randint(1, 20)
                        cpu_kick = random.randint(1, 20)
                        
                        st.write(f"🟢 Your block roll: {user_block}")
                        st.write(f"🔴 CPU kick roll: {cpu_kick}")
                        
                        if user_block > cpu_kick:
                            st.success("✅ BLOCKED! Turnover on downs!")
                            st.session_state.battle_possession = "user"
                            st.session_state.battle_down = 1
                            st.session_state.battle_yards_to_go = 10
                        else:
                            # Calculate FG success based on distance
                            fg_chance = max(50, 100 - (fg_distance - 20))
                            if random.randint(1, 100) <= fg_chance:
                                st.error("❌ GOOD! CPU scores 3 points!")
                                st.session_state.battle_score_cpu += 3
                                st.session_state.battle_possession = "user"
                                st.session_state.battle_yards = 0
                            else:
                                st.success("✅ MISS! Turnover on downs!")
                                st.session_state.battle_possession = "user"
                            st.session_state.battle_down = 1
                            st.session_state.battle_yards_to_go = 10
                        st.rerun()
                    return
                else:
                    st.info("🔴 CPU is punting!")
                    punt_distance = random.randint(30, 50)
                    st.session_state.battle_yards += punt_distance
                    st.session_state.battle_possession = "user"
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.write(f"🥾 CPU punted {punt_distance} yards")
                    if st.button("Continue", key="punt_continue"):
                        st.rerun()
                    return
            elif st.session_state.battle_possession == "cpu":
                # CPU out of FG range, always punts
                st.info("🔴 CPU is punting!")
                punt_distance = random.randint(30, 50)
                st.session_state.battle_yards += punt_distance
                st.session_state.battle_possession = "user"
                st.session_state.battle_down = 1
                st.session_state.battle_yards_to_go = 10
                st.write(f"🥾 CPU punted {punt_distance} yards")
                if st.button("Continue", key="punt_continue2"):
                    st.rerun()
                return
        
        # Field goal mode
        if st.session_state.battle_fg_mode:
            # Check if already kicked
            if "battle_fg_kicked" not in st.session_state:
                st.session_state.battle_fg_kicked = False
            
            if st.session_state.battle_fg_kicked:
                # Already kicked, just show continue button
                if st.button("Continue", key="fg_continue", use_container_width=True):
                    st.session_state.battle_possession = "cpu"
                    st.session_state.battle_yards = 0
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.session_state.battle_fg_mode = False
                    st.session_state.battle_fg_kicked = False
                    st.rerun()
                return
            
            st.markdown("### 🦵 Field Goal Attempt")
            distance = st.session_state.battle_fg_distance
            wind = random.randint(-15, 15)
            
            st.write(f"📏 Distance: {distance} yards")
            wind_dir = "⬅️ Left" if wind < 0 else "➡️ Right" if wind > 0 else "None"
            st.write(f"💨 Wind: {abs(wind)} mph {wind_dir}")
            
            angle = st.slider("Angle ⬅️➡️", -30, 30, 0, key="fg_angle")
            power = st.slider("Power 💪", 0, 100, 50, key="fg_power")
            
            if st.button("🦵 KICK!", key="fg_kick", use_container_width=True):
                # Wind affects angle
                effective_angle = angle + wind
                
                # Simple FG calculation
                min_power = 40 + (distance - 20) * 0.5
                max_power = 70 + (distance - 20) * 0.3
                
                angle_good = -10 <= effective_angle <= 10
                power_good = min_power <= power <= max_power
                
                if angle_good and power_good:
                    st.balloons()
                    st.success("✅ FIELD GOAL IS GOOD! You score 3 points!")
                    st.session_state.battle_score_user += 3
                elif not angle_good:
                    if effective_angle < -10:
                        st.error(f"❌ NO GOOD! Wide left! Wind pushed it {abs(wind)} mph")
                    else:
                        st.error(f"❌ NO GOOD! Wide right! Wind pushed it {abs(wind)} mph")
                else:
                    st.error("❌ NO GOOD! Wrong power - too weak or too strong")
                
                st.session_state.battle_fg_kicked = True
                st.rerun()
            
            if st.button("Cancel", key="fg_cancel"):
                st.session_state.battle_fg_mode = False
                st.rerun()
            return
        
        if st.button("🏈 SNAP THE BALL!", key="snap_button", use_container_width=True):
            # Roll all dice
            user_rolls = [random.randint(1, 6) for _ in range(11)]
            cpu_rolls = [random.randint(1, 6) for _ in range(11)]
            
            st.session_state.battle_rolls_user = user_rolls
            st.session_state.battle_rolls_cpu = cpu_rolls
            
            user_total = sum(user_rolls)
            cpu_total = sum(cpu_rolls)
            
            # Calculate which section won (just needs to win, not dominate)
            left_user = sum(user_rolls[0:4])
            left_cpu = sum(cpu_rolls[0:4])
            middle_user = sum(user_rolls[4:8])
            middle_cpu = sum(cpu_rolls[4:8])
            right_user = sum(user_rolls[8:11])
            right_cpu = sum(cpu_rolls[8:11])
            
            # Check if predicted section won
            prediction_correct = False
            if st.session_state.battle_line_prediction == "left" and left_user > left_cpu:
                prediction_correct = True
            elif st.session_state.battle_line_prediction == "middle" and middle_user > middle_cpu:
                prediction_correct = True
            elif st.session_state.battle_line_prediction == "right" and right_user > right_cpu:
                prediction_correct = True
            
            multiplier = 2 if prediction_correct else 1
            
            # Store prediction result for display
            winning_sections = []
            if left_user > left_cpu:
                winning_sections.append("left")
            if middle_user > middle_cpu:
                winning_sections.append("middle")
            if right_user > right_cpu:
                winning_sections.append("right")
            
            st.session_state.battle_prediction_result = {
                "predicted": st.session_state.battle_line_prediction,
                "winning_sections": winning_sections,
                "correct": prediction_correct,
                "multiplier": multiplier
            }
            
            # Reset prediction for next play
            st.session_state.battle_line_prediction = None
            
            # Calculate yardage based on difference (with multiplier if prediction correct)
            multiplier = st.session_state.battle_prediction_result.get("multiplier", 1) if "battle_prediction_result" in st.session_state else 1
            yards_diff = abs(user_total - cpu_total) * multiplier
            
            # Check for 1 vs 6 matchups (bonus 5 yards each)
            bonus_yards = 0
            for i in range(11):
                if user_rolls[i] == 6 and cpu_rolls[i] == 1:
                    bonus_yards += 5
                elif user_rolls[i] == 1 and cpu_rolls[i] == 6:
                    bonus_yards -= 5
            
            # Determine yards gained based on possession
            if st.session_state.battle_possession == "user":
                if user_total > cpu_total:
                    yards_gained = yards_diff + (bonus_yards if bonus_yards > 0 else 0)
                    st.session_state.battle_yards += yards_gained
                    st.session_state.battle_yards_to_go -= yards_gained
                elif user_total < cpu_total:
                    yards_lost = yards_diff + (abs(bonus_yards) if bonus_yards < 0 else 0)
                    st.session_state.battle_yards -= yards_lost
                    st.session_state.battle_yards_to_go += yards_lost
                
                # Check for first down
                if st.session_state.battle_yards_to_go <= 0:
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.session_state.battle_drive_start = st.session_state.battle_yards
                else:
                    st.session_state.battle_down += 1
                
                # Check for turnover on downs
                if st.session_state.battle_down > 4:
                    st.session_state.battle_possession = "cpu"
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.session_state.battle_drive_start = st.session_state.battle_yards
            else:
                # CPU possession
                if cpu_total > user_total:
                    yards_gained = yards_diff + (abs(bonus_yards) if bonus_yards < 0 else 0)
                    st.session_state.battle_yards -= yards_gained
                    st.session_state.battle_yards_to_go -= yards_gained
                elif cpu_total < user_total:
                    yards_lost = yards_diff + (bonus_yards if bonus_yards > 0 else 0)
                    st.session_state.battle_yards += yards_lost
                    st.session_state.battle_yards_to_go += yards_lost
                
                # Check for first down
                if st.session_state.battle_yards_to_go <= 0:
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.session_state.battle_drive_start = st.session_state.battle_yards
                else:
                    st.session_state.battle_down += 1
                
                # Check for turnover on downs
                if st.session_state.battle_down > 4:
                    st.session_state.battle_possession = "user"
                    st.session_state.battle_down = 1
                    st.session_state.battle_yards_to_go = 10
                    st.session_state.battle_drive_start = st.session_state.battle_yards
            
            st.rerun()
    
    with col2:
        st.markdown("**📊 Stats**")
        st.write(f"Down: {st.session_state.battle_down}")
        st.write(f"To Go: {st.session_state.battle_yards_to_go}")
        st.write(f"Drive: {st.session_state.battle_yards} yds")
        if st.button("🔄 Reset", key="battle_reset", use_container_width=True):
            del st.session_state.battle_user_team
            del st.session_state.battle_cpu_team
            st.session_state.battle_score_user = 0
            st.session_state.battle_score_cpu = 0
            st.session_state.battle_yards = 0
            st.session_state.battle_rolls_user = None
            st.session_state.battle_rolls_cpu = None
            st.session_state.battle_down = 1
            st.session_state.battle_yards_to_go = 10
            st.session_state.battle_possession = "user"
            st.session_state.battle_drive_start = 0
            st.rerun()

def play_field_goal_kicker_main():
    st.markdown("### 🏈 Field Goal Kicker")
    
    with st.expander("📖 How to Play"):
        st.write("""
        **Goal:** Kick field goals through the uprights!
        
        **Rules:**
        - Each kick has random distance (25-55 yards)
        - Wind affects your kick left/right
        - Adjust angle to compensate for wind
        - Longer kicks need more power
        - Score more points for longer kicks:
          - 25-39 yards = 3 points
          - 40-49 yards = 4 points
          - 50+ yards = 5 points
        """)
    
    if "kicker_score" not in st.session_state:
        st.session_state.kicker_score = 0
        st.session_state.kicker_attempts = 0
        st.session_state.kicker_made = 0
        st.session_state.kicker_wind = random.randint(-20, 20)
        st.session_state.kicker_distance = random.choice([25, 30, 35, 40, 45, 50, 55])
        st.session_state.kicker_elevation = random.randint(-5, 5)
        st.session_state.kicker_grass = random.choice(["Dry", "Wet", "Muddy"])
        st.session_state.kicker_pressure = random.randint(1, 10)
    
    # Check if game over
    if st.session_state.kicker_attempts >= 3:
        st.warning("⏱️ Game Over! 3 attempts used.")
        st.info(f"Final Score: {st.session_state.kicker_score} points")
        if st.button("Play Again", key="play_again_kicker", use_container_width=True):
            st.session_state.kicker_score = 0
            st.session_state.kicker_attempts = 0
            st.session_state.kicker_made = 0
            st.session_state.kicker_wind = random.randint(-20, 20)
            st.session_state.kicker_distance = random.choice([25, 30, 35, 40, 45, 50, 55])
            st.session_state.kicker_elevation = random.randint(-5, 5)
            st.session_state.kicker_grass = random.choice(["Dry", "Wet", "Muddy"])
            st.session_state.kicker_pressure = random.randint(1, 10)
            st.rerun()
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"🎯 Score: {st.session_state.kicker_score}")
        st.write(f"✅ Made: {st.session_state.kicker_made}/{st.session_state.kicker_attempts}")
        st.write(f"🎯 Attempts Left: {3 - st.session_state.kicker_attempts}")
        
        st.markdown("---")
        st.markdown("**Kick Conditions:**")
        st.write(f"📏 Distance: {st.session_state.kicker_distance} yards")
        
        wind_dir = "⬅️ Left" if st.session_state.kicker_wind < 0 else "➡️ Right"
        wind_strength = abs(st.session_state.kicker_wind)
        st.write(f"💨 Wind: {wind_strength} mph {wind_dir}")
        
        elev_dir = "Uphill" if st.session_state.kicker_elevation > 0 else "Downhill" if st.session_state.kicker_elevation < 0 else "Flat"
        st.write(f"⛰️ Elevation: {elev_dir} ({st.session_state.kicker_elevation})")
        
        grass_emoji = {"Dry": "🌾", "Wet": "💧", "Muddy": "🪨"}[st.session_state.kicker_grass]
        st.write(f"{grass_emoji} Field: {st.session_state.kicker_grass}")
        
        st.write(f"👀 Pressure: {st.session_state.kicker_pressure}/10")
        
        angle = st.slider("Angle ⬅️➡️", -45, 45, 0, key="kick_angle")
        power = st.slider("Power 💪", 0, 100, 50, key="kick_power")
        
        goal_visual = ""
        if -15 <= angle <= 15:
            goal_visual = "🟫 🎯 🟫"
        elif angle < -15:
            goal_visual = "🏈 🟫 🟫"
        else:
            goal_visual = "🟫 🟫 🏈"
        
        st.markdown(f"<div style='text-align: center; font-size: 40px;'>{goal_visual}</div>", unsafe_allow_html=True)
        
        # Show kick animation if just kicked
        if "show_kick_animation" in st.session_state and st.session_state.show_kick_animation:
            st.markdown("""
                <style>
                @keyframes kick {
                    0% { transform: translateY(0) scale(1); opacity: 1; }
                    50% { transform: translateY(-150px) scale(0.5); opacity: 0.8; }
                    100% { transform: translateY(-300px) scale(0.3); opacity: 0; }
                }
                .football-kick {
                    font-size: 60px;
                    animation: kick 1.5s ease-out;
                    text-align: center;
                }
                </style>
                <div class='football-kick'>🏈</div>
            """, unsafe_allow_html=True)
            st.session_state.show_kick_animation = False
        
        if st.button("🦵 KICK!", key="kick_button", use_container_width=True):
            st.session_state.show_kick_animation = True
            wind = st.session_state.kicker_wind
            distance = st.session_state.kicker_distance
            elevation = st.session_state.kicker_elevation
            grass = st.session_state.kicker_grass
            pressure = st.session_state.kicker_pressure
            
            # Calculate effective angle with all factors
            effective_angle = angle + wind + (elevation * 2)
            
            # Grass affects power needed
            grass_modifier = {"Dry": 0, "Wet": 5, "Muddy": 10}[grass]
            
            # Pressure affects accuracy (random jitter)
            pressure_jitter = random.randint(-pressure, pressure)
            effective_angle += pressure_jitter
            
            # Distance affects required power
            min_power = 30 + (distance - 25) * 0.8 + grass_modifier
            max_power = 70 + (distance - 25) * 0.6 + grass_modifier
            
            # Tighter accuracy window
            angle_good = -10 <= effective_angle <= 10
            power_good = min_power <= power <= max_power
            
            st.session_state.kicker_attempts += 1
            
            if angle_good and power_good:
                if distance >= 50:
                    points = 5
                elif distance >= 40:
                    points = 4
                else:
                    points = 3
                st.session_state.kicker_score += points
                st.session_state.kicker_made += 1
                
                # Save high score
                email = st.session_state.get("email")
                save_kicker_score(email, st.session_state.kicker_score, st.session_state.kicker_made, st.session_state.kicker_attempts)
                
                st.balloons()
                st.markdown("""
                    <style>
                    @keyframes flyacross {
                        0% { left: -50%; }
                        100% { left: 150%; }
                    }
                    .its-good {
                        position: fixed;
                        top: 30%;
                        left: -50%;
                        font-size: 80px;
                        font-weight: bold;
                        color: #00ff00;
                        text-shadow: 3px 3px 6px rgba(0,0,0,0.8);
                        animation: flyacross 2s ease-in-out forwards;
                        z-index: 9999;
                        pointer-events: none;
                        white-space: nowrap;
                    }
                    </style>
                    <div class='its-good'>IT'S GOOD! 🏈</div>
                """, unsafe_allow_html=True)
                st.success(f"✅ GOOD from {distance} yards! +{points} points")
            elif angle_good:
                if power < min_power:
                    st.error(f"❌ Too weak! Needed {int(min_power)}+ power")
                else:
                    st.error("❌ Too strong! Sailed over")
            else:
                if effective_angle < -10:
                    st.error(f"❌ Wide left!")
                else:
                    st.error(f"❌ Wide right!")
            
            # New conditions for next kick
            st.session_state.kicker_wind = random.randint(-20, 20)
            st.session_state.kicker_distance = random.choice([25, 30, 35, 40, 45, 50, 55])
            st.session_state.kicker_elevation = random.randint(-5, 5)
            st.session_state.kicker_grass = random.choice(["Dry", "Wet", "Muddy"])
            st.session_state.kicker_pressure = random.randint(1, 10)
            st.rerun()
    
    with col2:
        st.markdown("### 🏆 Top 5 Kickers")
        show_kicker_leaderboard()
        st.markdown("---")

# --------------- Main App -----------------

def main():
    if "user" not in st.session_state:
        login_user()
        return
    
    # Mobile-first tab navigation
    email = st.session_state.get("email")
    is_admin = email == "mwill1003@gmail.com"
    
    # Create tabs based on user role
    if is_admin:
        tabs = st.tabs(["🏈 Squares", "🎮 Games", "📧 Outreach", "⚙️ Account"])
    else:
        tabs = st.tabs(["🏈 Squares", "🎮 Games", "⚙️ Account"])
    
    # Squares tab
    with tabs[0]:
        show_odds_ticker()
        draw_grid()
    
    # Games tab
    with tabs[1]:
        show_games_page()
    
    # Outreach tab (admin only)
    if is_admin:
        with tabs[2]:
            show_outreach_page()
        # Account tab for admin
        with tabs[3]:
            show_user_stats()
    else:
        # Account tab for regular users
        with tabs[2]:
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
        odds_text = countdown + " • Super Bowl LX • Feb 8, 2026 • Levi's Stadium, Santa Clara, CA • "
    
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
        st.sidebar.markdown("### 📧 Invite Player")
        invite_email = st.sidebar.text_input("Email address", key="invite_email")
        if st.sidebar.button("Send Invite", key="send_invite"):
            if invite_email:
                send_invite_email(invite_email)
            else:
                st.sidebar.error("Enter an email")
        
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
        
        # Payment reminder button
        unpaid_players = [email for email, info in players_payment.items() if not info.get("paid", False)]
        if unpaid_players:
            st.sidebar.markdown("---")
            if st.sidebar.button(f"💸 Send Payment Reminder ({len(unpaid_players)})", use_container_width=True):
                send_payment_reminders(unpaid_players, players_payment)
    
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

def send_invite_email(email):
    try:
        # Generate temporary password
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        
        # Create user in Firebase with temp password
        try:
            auth.create_user_with_email_and_password(email, temp_password)
        except:
            # User might already exist, reset password instead
            auth.send_password_reset_email(email)
            st.sidebar.success(f"Password reset sent to {email}")
            return
        
        # Send email with credentials
        smtp_config = st.secrets["smtp"]
        
        msg = MIMEMultipart()
        msg['From'] = smtp_config["user"]
        msg['To'] = email
        msg['Subject'] = "🏈 You're Invited to Super Bowl Squares!"
        
        body = f"""Hi there!

You've been invited to join our Super Bowl Squares pool!

Login at: https://footballpool.streamlit.app

Your temporary credentials:
Email: {email}
Password: {temp_password}

Please login and claim your squares. Each square is $10.

Good luck!
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)
        server.quit()
        
        st.sidebar.success(f"✅ Invite sent to {email}")
    except Exception as e:
        st.sidebar.error(f"Error: {str(e)}")

def send_payment_reminders(unpaid_emails, players_payment):
    """Send payment reminder emails to unpaid players"""
    smtp_config = st.secrets["smtp"]
    
    sent_count = 0
    failed = []
    
    for player_email in unpaid_emails:
        try:
            square_count = players_payment[player_email]["count"]
            amount = square_count * 10
            name = player_email.split("@")[0]
            
            venmo_url = f"https://venmo.com/u/michael-williams-200?txn=pay&amount={amount}&note=Football%20Pool%20-%20{square_count}%20squares"
            
            msg = MIMEMultipart()
            msg['From'] = smtp_config["user"]
            msg['To'] = player_email
            msg['Subject'] = "🏈 Payment Reminder: Super Bowl Squares Pool"
            
            body = f"""Hey {name}!

Just a friendly reminder that you have {square_count} square{'s' if square_count > 1 else ''} claimed in our Super Bowl Squares pool.

Total due: ${amount}

Pay now via Venmo:
{venmo_url}

Or search: @michael-williams-200
Note: "Football Pool - {square_count} squares"

Thanks!
- Michael
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
            server.quit()
            
            sent_count += 1
            
        except Exception as e:
            failed.append((player_email, str(e)))
    
    if sent_count > 0:
        st.sidebar.success(f"✅ Sent {sent_count} payment reminders")
    if failed:
        st.sidebar.error(f"❌ Failed to send {len(failed)} reminders")
# --------------- Email Outreach Page -----------------

def show_outreach_page():
    st.title("📧 Email Outreach")
    
    # Email content
    subject = "🏈 BREAKING: Seahawks Fans Get First Pick at Super Bowl Squares! (Just Kidding... Or Am I?) 🦅"
    body = """Hey there, 12s (and other assorted football enthusiasts)!

Remember Super Bowl XLIX? Yeah, me neither. I've blocked it out. Therapy is expensive.

But here's the good news: Super Bowl LX is coming February 8, 2026, and THIS time we're not leaving it up to fate, questionable play-calling, or Malcolm Butler's reflexes. We're leaving it up to MATH and RANDOM NUMBERS! 🎲

Introducing: The Super Bowl Squares Pool That Will Definitely Not Break Your Heart Like That One Play Did!

🎮 Join here: https://futbolislife.streamlit.app

💰 THE DEAL:
• $10 per square (cheaper than therapy, more fun than yelling at your TV)
• Pick your squares NOW before your cousin Gary takes all the good ones
• Numbers randomized before kickoff (totally fair, unlike certain referees)
• Win cold hard cash for each quarter!

💵 PRIZE BREAKDOWN:
• Q1: 10% of pot (early bird gets the worm)
• Q2: 15% of pot (halftime snack money)
• Q3: 25% of pot (now we're talking)
• Final: 50% of pot (BIG MONEY, NO WHAMMIES)

🏆 LAST YEAR'S WINNERS:
Luke Rubik, Derek Slusarski, Donny Slotty, and Kyle Ralph all took home cash! Will YOU be next?

🦅 SEAHAWKS FAN BONUS:
If you're still bitter about 2015, this is your chance for redemption. Or at least some cash to ease the pain. Plus, you can play our mini-games while pretending you're calling better plays than... well, you know.

🎯 MINI-GAMES INCLUDED:
• Catch the Football (faster reflexes than you-know-who)
• Field Goal Kicker (because sometimes you SHOULD kick it)
• Line Battle (dice-based football - no heartbreak guaranteed!)

💳 PAYMENT:
Venmo: @michael-williams-200
(Please include "Not Still Mad About 2015" in the memo)

Claim your squares before they're gone! And remember: in Super Bowl Squares, EVERYONE has a chance to win. Unlike certain goal-line situations we shall not speak of.

Go Hawks! (And also go other teams, I guess) 🏈

P.S. - Yes, I'm a diehard fair-weather Seahawks fan. I only show up when they're winning... or when there's money involved. 💰

- Michael
"""
    
    # Preview section
    st.markdown("### 👀 Email Preview")
    with st.expander("📨 Click to view email content", expanded=True):
        st.markdown(f"**Subject:** {subject}")
        st.markdown("---")
        st.text(body)
    
    st.markdown("---")
    
    # Load contacts from CSV
    try:
        with open('outreach.csv', 'r') as file:
            reader = csv.DictReader(file)
            contacts = list(reader)
        
        st.markdown(f"### 📊 Recipients ({len(contacts)} contacts)")
        
        # Show contacts in a nice format
        with st.expander("📄 View all recipients"):
            for contact in contacts:
                st.write(f"• {contact['Name']} ({contact['Email']})")
        
        st.markdown("---")
        
        # Send emails section
        st.markdown("### 🚀 Send Emails")
        st.warning("⚠️ This will send the email to ALL contacts in the list!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📧 SEND TO ALL", type="primary", use_container_width=True):
                send_bulk_emails(contacts, subject, body)
        
        with col2:
            if st.button("🧪 Test Send (to yourself)", use_container_width=True):
                test_contact = [{"Name": "Test", "Email": st.session_state.email}]
                send_bulk_emails(test_contact, subject, body)
    
    except FileNotFoundError:
        st.error("❌ outreach.csv file not found!")
    except Exception as e:
        st.error(f"❌ Error loading contacts: {str(e)}")

def send_bulk_emails(contacts, subject, body):
    """Send emails to a list of contacts"""
    smtp_config = st.secrets["smtp"]
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    sent_count = 0
    failed = []
    
    for idx, contact in enumerate(contacts):
        name = contact['Name']
        email = contact['Email']
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = smtp_config["user"]
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_config["server"], smtp_config["port"])
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
            server.quit()
            
            sent_count += 1
            status_text.text(f"✅ Sent to {name} ({email})")
            
        except Exception as e:
            failed.append((name, email, str(e)))
            status_text.text(f"❌ Failed: {name} ({email})")
        
        # Update progress
        progress_bar.progress((idx + 1) / len(contacts))
    
    # Summary
    st.success(f"✅ Successfully sent: {sent_count}/{len(contacts)}")
    
    if failed:
        st.error(f"❌ Failed: {len(failed)}")
        with st.expander("View failed emails"):
            for name, email, error in failed:
                st.write(f"• {name} ({email}): {error}")

# --------------- 2048 Football Game (COMMENTED OUT) -----------------

# def play_2048_football():
#     st.sidebar.markdown("### 🏈 2048 Football")
#     
#     # Instructions
#     with st.sidebar.expander("📖 How to Play"):
#         st.write("""
#         **Goal:** Reach the 🏁 (2048) tile!
#         
#         **How it works:**
#         - **ALL tiles slide together** in the arrow direction
#         - When two matching tiles collide, they merge!
#         
#         **Example:**
#         ```
#         Before ⬅️:  [⬜][🏈][🏈][⬜]
#         After  ⬅️:  [🎯][⬜][⬜][⬜]
#         ```
#         The two 🏈 slid left and merged into 🎯!
#         
#         **Controls:**
#         - ⬅️ = Slide all tiles left
#         - ➡️ = Slide all tiles right
#         - ⬆️ = Slide all tiles up
#         - ⬇️ = Slide all tiles down
#         
#         **Progression:**
#         🏈(2) → 🎯(4) → 🏆(8) → 🥇(16) → 🔥(32) → ⚡(64) → 💥(128) → ⭐(256) → 🌟(512) → 💫(1024) → 🏁(2048)
#         """)
#     
#     # Initialize game state
#     if "game_2048" not in st.session_state:
#         st.session_state.game_2048 = [[0]*4 for _ in range(4)]
#         st.session_state.score_2048 = 0
#         add_new_tile()
#         add_new_tile()
#     
#     # Football emojis for tiles
#     tile_emojis = {
#         0: "⬜",
#         2: "🏈",
#         4: "🎯",
#         8: "🏆",
#         16: "🥇",
#         32: "🔥",
#         64: "⚡",
#         128: "💥",
#         256: "⭐",
#         512: "🌟",
#         1024: "💫",
#         2048: "🏁"
#     }
#     
#     st.sidebar.write(f"Score: {st.session_state.score_2048}")
#     
#     # Display grid
#     for row in st.session_state.game_2048:
#         cols = st.sidebar.columns(4)
#         for idx, val in enumerate(row):
#             emoji = tile_emojis.get(val, "🏁")
#             cols[idx].markdown(f"<div style='text-align: center; font-size: 30px;'>{emoji}</div>", unsafe_allow_html=True)
#     
#     # Controls
#     st.sidebar.write("**Controls:**")
#     col1, col2, col3 = st.sidebar.columns([1, 1, 1])
#     with col2:
#         if st.button("⬆️", key="up_2048", use_container_width=True):
#             move_up()
#     
#     col4, col5, col6 = st.sidebar.columns([1, 1, 1])
#     with col4:
#         if st.button("⬅️", key="left_2048", use_container_width=True):
#             move_left()
#     with col5:
#         if st.button("⬇️", key="down_2048", use_container_width=True):
#             move_down()
#     with col6:
#         if st.button("➡️", key="right_2048", use_container_width=True):
#             move_right()
#     
#     if st.sidebar.button("New Game"):
#         st.session_state.game_2048 = [[0]*4 for _ in range(4)]
#         st.session_state.score_2048 = 0
#         add_new_tile()
#         add_new_tile()
#         st.rerun()

# def add_new_tile():
#     empty_cells = [(i, j) for i in range(4) for j in range(4) if st.session_state.game_2048[i][j] == 0]
#     if empty_cells:
#         i, j = random.choice(empty_cells)
#         st.session_state.game_2048[i][j] = 2 if random.random() < 0.9 else 4

# def move_left():
#     moved = False
#     for i in range(4):
#         row = [x for x in st.session_state.game_2048[i] if x != 0]
#         new_row = []
#         skip = False
#         for j in range(len(row)):
#             if skip:
#                 skip = False
#                 continue
#             if j + 1 < len(row) and row[j] == row[j+1]:
#                 new_row.append(row[j] * 2)
#                 st.session_state.score_2048 += row[j] * 2
#                 skip = True
#                 moved = True
#             else:
#                 new_row.append(row[j])
#         new_row += [0] * (4 - len(new_row))
#         if new_row != st.session_state.game_2048[i]:
#             moved = True
#         st.session_state.game_2048[i] = new_row
#     if moved:
#         add_new_tile()
#         st.rerun()

# def move_right():
#     for i in range(4):
#         st.session_state.game_2048[i] = st.session_state.game_2048[i][::-1]
#     move_left()
#     for i in range(4):
#         st.session_state.game_2048[i] = st.session_state.game_2048[i][::-1]

# def move_up():
#     st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]
#     move_left()
#     st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]

# def move_down():
#     st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]
#     move_right()
#     st.session_state.game_2048 = [list(x) for x in zip(*st.session_state.game_2048)]

# --------------- Memory Match Game (COMMENTED OUT) -----------------

# def play_memory_match():
#     st.sidebar.markdown("### 🧠 Memory Match")
#     
#     # Instructions
#     with st.sidebar.expander("📖 How to Play"):
#         st.write("""
#         **Goal:** Match all pairs of football emojis!
#         
#         **Rules:**
#         - Click cards to flip them over
#         - Find matching pairs
#         - Match all pairs to win!
#         - Try to do it in as few moves as possible
#         """)
#     
#     # Initialize game
#     if "memory_cards" not in st.session_state:
#         emojis = ["🏈", "🏆", "🥇", "🔥", "⚡", "⭐", "🎯", "🏁"]
#         cards = emojis * 2  # 2 of each
#         random.shuffle(cards)
#         st.session_state.memory_cards = cards
#         st.session_state.memory_flipped = [False] * 16
#         st.session_state.memory_matched = [False] * 16
#         st.session_state.memory_first = None
#         st.session_state.memory_moves = 0
#     
#     st.sidebar.write(f"Moves: {st.session_state.memory_moves}")
#     matched_count = sum(st.session_state.memory_matched)
#     st.sidebar.write(f"Matched: {matched_count // 2} / 8")
#     
#     # Display grid (4x4)
#     for row in range(4):
#         cols = st.sidebar.columns(4)
#         for col in range(4):
#             idx = row * 4 + col
#             
#             if st.session_state.memory_matched[idx]:
#                 # Matched - show emoji
#                 cols[col].markdown(f"<div style='text-align: center; font-size: 25px;'>{st.session_state.memory_cards[idx]}</div>", unsafe_allow_html=True)
#             elif st.session_state.memory_flipped[idx]:
#                 # Flipped - show emoji
#                 cols[col].markdown(f"<div style='text-align: center; font-size: 25px;'>{st.session_state.memory_cards[idx]}</div>", unsafe_allow_html=True)
#             else:
#                 # Hidden - show button
#                 if cols[col].button("🎴", key=f"mem_{idx}"):
#                     flip_card(idx)
#     
#     # Check win
#     if all(st.session_state.memory_matched):
#         st.sidebar.success(f"🎉 You won in {st.session_state.memory_moves} moves!")
#     
#     if st.sidebar.button("New Game", key="new_memory"):
#         del st.session_state.memory_cards
#         del st.session_state.memory_flipped
#         del st.session_state.memory_matched
#         del st.session_state.memory_first
#         del st.session_state.memory_moves
#         st.rerun()

# def flip_card(idx):
#     # Can't flip if already matched or already flipped
#     if st.session_state.memory_matched[idx] or st.session_state.memory_flipped[idx]:
#         return
#     
#     # Flip the card
#     st.session_state.memory_flipped[idx] = True
#     
#     if st.session_state.memory_first is None:
#         # First card flipped
#         st.session_state.memory_first = idx
#     else:
#         # Second card flipped
#         st.session_state.memory_moves += 1
#         first_idx = st.session_state.memory_first
#         
#         if st.session_state.memory_cards[first_idx] == st.session_state.memory_cards[idx]:
#             # Match!
#             st.session_state.memory_matched[first_idx] = True
#             st.session_state.memory_matched[idx] = True
#         else:
#             # No match - flip back after showing
#             import time
#             time.sleep(0.5)
#             st.session_state.memory_flipped[first_idx] = False
#             st.session_state.memory_flipped[idx] = False
#         
#         st.session_state.memory_first = None
#     
#     st.rerun()

# --------------- Run -----------------
if __name__ == "__main__":
    main()
