"""mobile_app.py

A mobile-first UI wrapper for the existing Streamlit Super Bowl Squares app in `main.py`.

Run:
    streamlit run mobile_app.py

What this file does:
- Reuses your existing Firebase + game logic from `main.py`
- Provides a touch-friendly "Quick Claim" flow (no tiny 10×10 tap targets required)
- Uses query-params + a fixed bottom nav on phones for simple navigation

Notes:
- `main.py` currently calls `st.set_page_config()` at import-time. Because of that,
  this file intentionally does NOT call `st.set_page_config()`.
- This UI is designed to be an optional alternative entrypoint. Your original
  `main.py` still works as-is.
"""

from __future__ import annotations

# IMPORTANT: Do not call any Streamlit commands before importing `main`.
# `main.py` calls st.set_page_config() at import time.
import main as legacy  # noqa: F401

import streamlit as st


# ------------------------- UI / CSS -------------------------

def inject_mobile_css() -> None:
    """Mobile-first tweaks: larger tap targets + bottom safe-area + lightweight nav."""
    st.markdown(
        """
<style>
  /* Give the page some breathing room + space for the fixed bottom nav on mobile */
  .block-container {
    padding-top: 0.75rem !important;
    padding-bottom: 1.25rem !important;
  }

  /* Finger-friendly buttons */
  div[data-testid="stButton"] button {
    min-height: 44px !important;
    border-radius: 14px !important;
    font-weight: 650 !important;
  }

  /* Make common inputs easier to use on phones */
  div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input,
  div[data-testid="stSelectbox"] div,
  div[data-testid="stTextArea"] textarea {
    min-height: 44px !important;
    font-size: 1rem !important;
  }

  /* Remove some extra top padding that feels cramped on mobile */
  header[data-testid="stHeader"] {
    height: 0.25rem;
  }

  /* --- Bottom nav (mobile only) --- */
  .mobile-bottom-nav {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
    background: rgba(15, 17, 22, 0.92);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255, 255, 255, 0.10);
    z-index: 9999;
  }

  .mobile-bottom-nav .nav-inner {
    display: flex;
    gap: 10px;
    max-width: 900px;
    margin: 0 auto;
  }

  .mobile-bottom-nav a {
    flex: 1;
    text-decoration: none !important;
    color: rgba(255, 255, 255, 0.92);
    font-weight: 700;
    text-align: center;
    padding: 10px 6px;
    border-radius: 14px;
    line-height: 1.05;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }

  .mobile-bottom-nav a .icon {
    display: block;
    font-size: 20px;
    margin-bottom: 2px;
  }

  .mobile-bottom-nav a.active {
    background: rgba(255, 255, 255, 0.15);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.10) inset;
  }

  @media (min-width: 769px) {
    .mobile-bottom-nav { display: none; }
  }

  @media (max-width: 768px) {
    .block-container {
      padding-left: 0.9rem !important;
      padding-right: 0.9rem !important;
      padding-bottom: calc(5.25rem + env(safe-area-inset-bottom)) !important;
      max-width: 100vw !important;
    }

    /* Reduce whitespace between elements */
    div[data-testid="stVerticalBlock"] > div {
      gap: 0.75rem !important;
    }
  }
</style>
""",
        unsafe_allow_html=True,
    )



def link_button(label: str, url: str, *, use_container_width: bool = True) -> None:
    """
    Streamlit's `link_button()` isn't available in older versions.
    This tiny helper keeps the UI working everywhere.
    """
    if hasattr(st, "link_button"):
        st.link_button(label, url, use_container_width=use_container_width)
    else:
        # Fallback: plain markdown link (still works great on mobile).
        st.markdown(f"[{label}]({url})")


def _get_page(default: str = "squares") -> str:
    """Read `?page=` from the URL query params."""
    try:
        return st.query_params.get("page", default)
    except Exception:
        return default


def _set_page(page: str) -> None:
    """Update `?page=` in the URL query params."""
    try:
        st.query_params["page"] = page
    except Exception:
        # If query-params aren't available, just fallback to session state.
        st.session_state["page"] = page


def render_bottom_nav(active: str, is_admin: bool) -> None:
    """Fixed bottom navigation for phones (desktop hides it via CSS)."""
    links = [
        ("squares", "🏈", "Squares"),
        ("games", "🎮", "Games"),
    ]
    if is_admin:
        links.append(("admin", "🛠️", "Admin"))
    links.append(("account", "⚙️", "Account"))

    parts = [
        "<div class='mobile-bottom-nav'><div class='nav-inner'>",
    ]
    for slug, icon, label in links:
        cls = "active" if slug == active else ""
        parts.append(
            f"<a class='{cls}' href='?page={slug}'>"
            f"<span class='icon'>{icon}</span><span class='label'>{label}</span>"
            "</a>"
        )
    parts.append("</div></div>")

    st.markdown("\n".join(parts), unsafe_allow_html=True)


# ------------------------- Pages -------------------------

def show_grid_snapshot(config, all_squares, email):
    """Display a compact grid snapshot showing all claimed squares."""
    top_team = config.get("top_team", "NFC Team")
    side_team = config.get("side_team", "AFC Team")
    top_numbers = config.get("top_numbers", list(range(10)))
    side_numbers = config.get("side_numbers", list(range(10)))
    
    st.markdown("### 📸 Your Grid Snapshot")
    
    # Header row
    header_cols = st.columns([1] + [1]*10)
    header_cols[0].markdown(f"**{side_team}↓**")
    for j, num in enumerate(top_numbers):
        header_cols[j+1].markdown(f"**{num}**")
    
    # Grid rows
    for i in range(10):
        row_cols = st.columns([1] + [1]*10)
        row_cols[0].markdown(f"**{side_numbers[i]}**")
        for j in range(10):
            square_id = f"{i}-{j}"
            data = all_squares.get(square_id)
            if data:
                avatar = data.get("avatar", "❌")
                claimed_by = data.get("claimed_by")
                if claimed_by == email:
                    row_cols[j+1].markdown(f"**{avatar}**")
                else:
                    row_cols[j+1].markdown(avatar)
            else:
                row_cols[j+1].markdown("⬜")
    
    st.caption(f"**{top_team}** →")


def squares_page() -> None:
    st.markdown("## 🏈 Squares")

    # Keep the nice ticker from your legacy app.
    try:
        legacy.show_odds_ticker()
    except Exception:
        pass

    config = legacy.get_game_config()
    all_squares = legacy.get_all_squares()

    email = st.session_state.get("email")

    top_team = config.get("top_team", "NFC Team")
    side_team = config.get("side_team", "AFC Team")
    top_numbers = config.get("top_numbers", list(range(10)))
    side_numbers = config.get("side_numbers", list(range(10)))

    # Check if we just claimed a square OR viewing grid
    if st.session_state.get("show_grid_snapshot"):
        show_grid_snapshot(config, all_squares, email)
        st.markdown("---")
        if st.button("Continue", use_container_width=True):
            st.session_state.show_grid_snapshot = False
            st.rerun()
        return

    # View Grid button at top
    if st.button("🖼️ View Full Grid", use_container_width=True):
        st.session_state.show_grid_snapshot = True
        st.rerun()

    st.markdown("### 📍 Quick Claim (mobile friendly)")
    st.caption("Pick a grid reference and claim the square if it's open.")

    c1, c2 = st.columns(2)
    with c1:
        nfc_digit = st.selectbox(f"{top_team} (top) grid reference", top_numbers, key="qc_nfc")
    with c2:
        afc_digit = st.selectbox(f"{side_team} (side) grid reference", side_numbers, key="qc_afc")

    # Translate digits -> the underlying grid id (row-col)
    square_id = None
    try:
        col = list(top_numbers).index(nfc_digit)
        row = list(side_numbers).index(afc_digit)
        square_id = f"{row}-{col}"
    except Exception:
        square_id = None

    if square_id is None:
        st.error("Couldn't map those digits to a square. Try again.")
    else:
        data = all_squares.get(square_id)
        if not data:
            st.success(f"✅ Available: {side_team} {afc_digit}  ×  {top_team} {nfc_digit}")
            if st.button("Claim this square", use_container_width=True):
                legacy.claim_square(square_id)
                st.session_state.show_grid_snapshot = True
                st.rerun()
        else:
            owner = data.get("claimed_by", "Unknown")
            avatar = data.get("avatar", "❓")
            paid = bool(data.get("paid", False))

            if owner == email:
                st.info(
                    f"You already own this square: {avatar} "
                    f"({side_team} {afc_digit} × {top_team} {nfc_digit})"
                    + (" • ✅ paid" if paid else " • 💸 not paid")
                )
                if st.button("Unclaim this square", use_container_width=True):
                    legacy.unclaim_square(square_id)
                    st.rerun()
            else:
                st.warning(
                    f"Taken by {owner.split('@')[0]} {avatar}"
                    + (" • ✅ paid" if paid else "")
                )

    st.markdown("---")
    st.markdown("### 🤖 AI-Powered Random Pick")
    st.caption("Let AI help you pick the best squares!")
    
    # Count available squares
    available_squares = [sid for sid in [f"{r}-{c}" for r in range(10) for c in range(10)] if sid not in all_squares]
    
    if available_squares:
        num_to_pick = st.number_input(
            f"How many squares? (max {len(available_squares)} available)",
            min_value=1,
            max_value=min(len(available_squares), 20),
            value=1,
            key="random_count"
        )
        
        st.markdown("**Pick your strategy:**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎲 Totally Random", use_container_width=True, help="Pure random selection"):
                import random
                picked = random.sample(available_squares, num_to_pick)
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
            
            if st.button("🎯 Center Power", use_container_width=True, help="Pick center squares - statistically more action!"):
                import random
                # Center squares (rows/cols 3-6) tend to have more combinations
                center_squares = [s for s in available_squares if 3 <= int(s.split("-")[0]) <= 6 and 3 <= int(s.split("-")[1]) <= 6]
                picked = random.sample(center_squares if len(center_squares) >= num_to_pick else available_squares, num_to_pick)
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
            
            if st.button("🔲 Spread Out", use_container_width=True, help="Maximize distance between squares"):
                import random
                picked = []
                remaining = available_squares.copy()
                while len(picked) < num_to_pick and remaining:
                    if not picked:
                        choice = random.choice(remaining)
                    else:
                        # Pick square farthest from existing picks
                        best_square = None
                        best_min_dist = -1
                        for candidate in remaining:
                            r1, c1 = map(int, candidate.split("-"))
                            min_dist = min(abs(r1-int(p.split("-")[0])) + abs(c1-int(p.split("-")[1])) for p in picked)
                            if min_dist > best_min_dist:
                                best_min_dist = min_dist
                                best_square = candidate
                        choice = best_square
                    picked.append(choice)
                    remaining.remove(choice)
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
        
        with col2:
            if st.button("⛔ No Neighbors", use_container_width=True, help="No consecutive squares"):
                import random
                picked = []
                remaining = available_squares.copy()
                while len(picked) < num_to_pick and remaining:
                    choice = random.choice(remaining)
                    r, c = map(int, choice.split("-"))
                    picked.append(choice)
                    # Remove neighbors
                    neighbors = [f"{r+dr}-{c+dc}" for dr in [-1,0,1] for dc in [-1,0,1]]
                    remaining = [s for s in remaining if s not in neighbors]
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
            
            if st.button("🚫 Avoid Stacking", use_container_width=True, help="Different rows & columns"):
                import random
                picked = []
                used_rows = set()
                used_cols = set()
                remaining = available_squares.copy()
                random.shuffle(remaining)
                for candidate in remaining:
                    if len(picked) >= num_to_pick:
                        break
                    r, c = map(int, candidate.split("-"))
                    if r not in used_rows and c not in used_cols:
                        picked.append(candidate)
                        used_rows.add(r)
                        used_cols.add(c)
                # Fill remaining if needed
                while len(picked) < num_to_pick and remaining:
                    choice = random.choice([s for s in remaining if s not in picked])
                    picked.append(choice)
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
            
            if st.button("🍀 Lucky Corners", use_container_width=True, help="Prioritize corner & edge squares"):
                import random
                corners = ["0-0", "0-9", "9-0", "9-9"]
                edges = [f"{r}-{c}" for r in [0,9] for c in range(10)] + [f"{r}-{c}" for r in range(10) for c in [0,9]]
                priority = [s for s in available_squares if s in corners] + [s for s in available_squares if s in edges and s not in corners]
                picked = random.sample(priority[:num_to_pick] if len(priority) >= num_to_pick else available_squares, num_to_pick)
                for sid in picked:
                    legacy.claim_square(sid)
                st.session_state.show_grid_snapshot = True
                st.rerun()
    else:
        st.info("No squares available for random selection.")

    st.markdown("---")
    st.markdown("### 👤 My squares")

    my_square_ids = [
        sid
        for sid, data in all_squares.items()
        if (data or {}).get("claimed_by") == email
    ]

    if not my_square_ids:
        st.info("You haven't claimed any squares yet.")
    else:
        # Make a compact, readable list (digit × digit)
        lines = []
        for sid in sorted(my_square_ids):
            try:
                r, c = (int(x) for x in sid.split("-"))
                display = f"{side_numbers[r]} × {top_numbers[c]}"
            except Exception:
                display = sid

            paid = bool(all_squares.get(sid, {}).get("paid", False))
            avatar = all_squares.get(sid, {}).get("avatar", "")
            lines.append(f"- {avatar} **{display}** ({'paid ✅' if paid else 'not paid 💸'})")

        st.markdown("\n".join(lines))

        amount = len(my_square_ids) * 10
        st.success(f"Total due: **${amount}** (${10} × {len(my_square_ids)} squares)")
        venmo_url = (
            f"https://venmo.com/u/michael-williams-200?txn=pay&amount={amount}"
            f"&note=Football%20Pool%20-%20{len(my_square_ids)}%20squares"
        )
        link_button("Pay via Venmo", venmo_url, use_container_width=True)

    st.markdown("---")
    st.markdown("### 🧾 Pot & payouts")

    paid_count = sum(1 for d in all_squares.values() if (d or {}).get("paid", False))
    total_pot = paid_count * 10

    q1_payout = int(total_pot * 0.10)
    q2_payout = int(total_pot * 0.15)
    q3_payout = int(total_pot * 0.25)
    final_payout = int(total_pot * 0.50)

    st.write(f"🎫 **{paid_count}** paid squares → **${total_pot}** total pot")

    p1, p2 = st.columns(2)
    with p1:
        st.metric("Q1 (10%)", f"${q1_payout}")
        st.metric("Q3 (25%)", f"${q3_payout}")
    with p2:
        st.metric("Q2 (15%)", f"${q2_payout}")
        st.metric("Final (50%)", f"${final_payout}")

    winners = config.get("winners", {}) or {}
    if any(winners.values()):
        st.markdown("---")
        st.markdown("### 🏆 Winners")
        for quarter in ["Q1", "Q2", "Q3", "Final"]:
            w = winners.get(quarter)
            if not w:
                st.write(f"**{quarter}**: not set")
                continue
            name = (w.get("winner_email") or "Unclaimed").split("@")[0]
            avatar = w.get("winner_avatar", "❓")
            st.write(f"**{quarter}**: {avatar} {name} — score {w.get('nfc')}-{w.get('afc')}")

    # Games button
    st.markdown("---")
    if st.button("🎮 Play Games (Line Battle, Field Goal Kicker & More!)", use_container_width=True):
        _set_page("games")
        st.rerun()

    # Optional full grid (for people who want the classic view)
    with st.expander("🧩 Full grid view (optional)"):
        try:
            st.session_state.compact_grid = True
        except Exception:
            pass
        legacy.draw_grid()


def games_page() -> None:
    st.markdown("## 🎮 Games")
    legacy.show_games_page()


def admin_page() -> None:
    st.markdown("## 🛠️ Admin")
    st.info("Admin tools from the legacy app")

    # Reuse the existing admin pages if you want.
    try:
        legacy.show_outreach_page()
    except Exception:
        st.warning("Outreach page not available.")


def account_page() -> None:
    st.markdown("## ⚙️ Account")

    email = st.session_state.get("email")
    st.write(f"Signed in as: **{email}**")

    config = legacy.get_game_config()
    all_squares = legacy.get_all_squares()

    # Claimed squares
    my_square_ids = [
        sid
        for sid, data in all_squares.items()
        if (data or {}).get("claimed_by") == email
    ]

    st.markdown("### 🎟️ My squares")
    st.write(f"You have **{len(my_square_ids)}** square(s) claimed.")

    # Avatar management (mobile-friendly version of the sidebar picker)
    if my_square_ids:
        st.markdown("### 🎨 Avatar")

        taken_avatars = set()
        current_user_avatar = None
        for sid, data in all_squares.items():
            if not data:
                continue
            avatar = data.get("avatar")
            claimed_by = data.get("claimed_by")
            if claimed_by == email:
                current_user_avatar = avatar
            elif claimed_by and claimed_by != email:
                taken_avatars.add(avatar)

        available_avatars = [a for a in legacy.AVATARS if a not in taken_avatars]
        if not available_avatars:
            st.warning("No avatars available (unexpected).")
        else:
            try:
                current_index = available_avatars.index(current_user_avatar)
            except Exception:
                current_index = 0

            selected_avatar = st.selectbox(
                "Pick your icon",
                available_avatars,
                index=current_index,
                key="acct_avatar",
            )
            if selected_avatar != current_user_avatar:
                if st.button("Update avatar on all my squares", use_container_width=True):
                    for sid in my_square_ids:
                        legacy.db.collection("squares").document(sid).update({"avatar": selected_avatar})
                    legacy.get_all_squares.clear()
                    st.success(f"Updated avatar to {selected_avatar}!")
                    st.rerun()

    # Payment
    st.markdown("---")
    st.markdown("### 💰 Payment")
    amount = len(my_square_ids) * 10
    if amount > 0:
        venmo_url = (
            f"https://venmo.com/u/michael-williams-200?txn=pay&amount={amount}"
            f"&note=Football%20Pool%20-%20{len(my_square_ids)}%20squares"
        )
        link_button(f"Pay ${amount} via Venmo", venmo_url, use_container_width=True)
    else:
        st.info("Claim squares to pay.")

    # Logout
    st.markdown("---")
    if st.button("Log out", use_container_width=True):
        for key in [
            "user",
            "email",
            "confirm_unclaim",
            "compact_grid",
            "battle_user_team",
            "battle_cpu_team",
        ]:
            st.session_state.pop(key, None)
        _set_page("squares")
        st.rerun()


# ------------------------- App -------------------------

def run() -> None:
    inject_mobile_css()

    # Auth (reuse legacy login)
    if "user" not in st.session_state:
        legacy.login_user()
        # No nav if not logged in
        return

    email = st.session_state.get("email")
    is_admin = email == "mwill1003@gmail.com"

    active = _get_page("squares")

    # Route
    if active == "games":
        games_page()
    elif active == "admin" and is_admin:
        admin_page()
    elif active == "account":
        account_page()
    else:
        squares_page()

    # Bottom nav (mobile)
    render_bottom_nav(active if (active != "admin" or is_admin) else "squares", is_admin=is_admin)


if __name__ == "__main__":
    run()
