import streamlit as st
import requests

st.set_page_config(page_title="Smart Drug Safety Checker", layout="centered")
st.title("💊 Smart Drug Safety Checker")

# User Inputs
age = st.number_input("Enter patient's age", min_value=1, max_value=120, step=1)
drugs_input = st.text_input("Enter drug names (comma-separated)", placeholder="e.g., aspirin, warfarin")

if st.button("Analyze Prescription"):
    if not drugs_input.strip():
        st.warning("Please enter at least one drug.")
    else:
        drugs = [d.strip().lower() for d in drugs_input.split(",") if d.strip()]
        payload = {"drugs": drugs, "age": age}

        try:
            response = requests.post("http://127.0.0.1:8000/check", json=payload)

            # ✅ Add this to show the full raw JSON response
            st.markdown("### 🛠️ Raw API Response (for debugging)")
            st.json(response.json())  # 👈 THIS LINE is what you add

            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    st.success("✅ Analysis complete")
                    for entry in results:
                        st.markdown("---")
                        st.markdown(f"### 💊 {entry['drug'].capitalize()}")
                        st.write(f"**🚨 Interactions:** {entry['interactions']}")
                        st.write(f"**🎂 Age Risk:** {entry['age_risk']}")
                        st.write(f"**⚠️ Organ Risks:** {entry['organ_risks']}")
                        st.write(f"**❌ Reason:** {entry['reason']}")
                        if entry["alternatives"]:
                            st.success("✅ Safer Alternatives: " + ", ".join(entry["alternatives"]))
                else:
                    st.warning("No result returned.")
            else:
                st.error("🚫 API error. Please check the backend server.")
        except Exception as e:
            st.error(f"❌ Request failed: {e}")
