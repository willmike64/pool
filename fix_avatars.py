import streamlit as st
from firebase_admin import credentials, firestore
import firebase_admin

# Initialize Firebase
cred = credentials.Certificate(dict(st.secrets["firebase_credentials"]))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Get all squares
squares_ref = db.collection("squares")
all_squares = {doc.id: doc.to_dict() for doc in squares_ref.stream()}

# Group by user
user_squares = {}
for square_id, data in all_squares.items():
    email = data.get("claimed_by")
    avatar = data.get("avatar")
    if email not in user_squares:
        user_squares[email] = []
    user_squares[email].append({"id": square_id, "avatar": avatar})

# Find and fix mismatches
print("Auditing avatars...\n")
for email, squares in user_squares.items():
    avatars = [s["avatar"] for s in squares]
    unique_avatars = set(avatars)
    
    if len(unique_avatars) > 1:
        # Mismatch found - use the most common avatar
        most_common = max(set(avatars), key=avatars.count)
        print(f"❌ {email}: Found {len(unique_avatars)} different avatars: {unique_avatars}")
        print(f"   Fixing to: {most_common}")
        
        # Update all squares to use the most common avatar
        for square in squares:
            if square["avatar"] != most_common:
                db.collection("squares").document(square["id"]).update({"avatar": most_common})
                print(f"   Updated {square['id']}: {square['avatar']} → {most_common}")
        print()
    else:
        print(f"✅ {email}: All {len(squares)} squares use {avatars[0]}")

print("\nAudit complete!")
