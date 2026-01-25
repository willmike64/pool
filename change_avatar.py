import streamlit as st
from firebase_admin import credentials, firestore
import firebase_admin

# Initialize Firebase
cred = credentials.Certificate(dict(st.secrets["firebase_credentials"]))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Change Therese.balistrieri@gmail.com to butterfly 🦋
email = "Therese.balistrieri@gmail.com"
new_avatar = "🦋"

squares_ref = db.collection("squares")
all_squares = squares_ref.stream()

count = 0
for doc in all_squares:
    data = doc.to_dict()
    if data.get("claimed_by") == email:
        doc.reference.update({"avatar": new_avatar})
        count += 1
        print(f"Updated {doc.id}: {data.get('avatar')} → {new_avatar}")

print(f"\n✅ Changed {count} squares for {email} to {new_avatar}")
