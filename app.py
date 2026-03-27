import streamlit as st
import requests
import time
from PIL import Image
import io
import base64
from datetime import datetime

# ─────────────────────────────────────────────
# 1. PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="சம்பவ இட ஆய்வு மகஜர் — AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Dark Police-theme */
    .main { background-color: #0d1117; }
    .stTextArea textarea {
        font-family: 'Latha', 'Tamil MN', serif;
        font-size: 14px;
        background-color: #161b22;
        color: #e6edf3;
        border: 1px solid #30363d;
    }
    .stButton>button {
        background: linear-gradient(135deg, #1f6feb, #388bfd);
        color: white;
        border-radius: 8px;
        height: 3em;
        width: 100%;
        font-weight: bold;
        font-size: 16px;
        border: none;
    }
    .stButton>button:hover { background: linear-gradient(135deg, #388bfd, #58a6ff); }
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
        margin: 4px 0;
    }
    h1, h2, h3 { color: #58a6ff; }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. SIDEBAR — API KEY + CASE METADATA
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/en/thumb/f/f9/Tamil_Nadu_Police_Logo.svg/200px-Tamil_Nadu_Police_Logo.svg.png", width=80)
    st.title("🔍 Case Details")
    st.divider()

    # Secrets-ல் இருந்தால் auto-load, இல்லாவிட்டால் manual input
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("🔑 API Key: Auto-loaded ✅")
    except Exception:
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")

    st.divider()
    st.subheader("📋 வழக்கு விவரங்கள்")
    fir_no   = st.text_input("குற்றம் எண் / ஆண்டு", placeholder="e.g., 123/2025")
    ps_name  = st.text_input("காவல் நிலையம்", placeholder="e.g., Virudhunagar Town PS")
    sections = st.text_input("சட்டப் பிரிவுகள்", placeholder="e.g., IPC 380, 457")
    ps_distance = st.text_input("காவல் நிலையத்திலிருந்து தூரம் & திசை", placeholder="e.g., 2 கி.மீ., வடக்கு")
    io_name  = st.text_input("IO பெயர் / பதவி", placeholder="e.g., SI of Police Rajan")

    now = datetime.now()
    exam_date = st.date_input("ஆய்வு தேதி", value=now.date())
    exam_time = st.time_input("ஆய்வு நேரம்", value=now.time())

    st.divider()
    st.subheader("⚙️ Output Settings")
    model_choice = st.selectbox(
        "Gemini Model",
        ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        index=0,
        help="gemini-2.0-flash is faster and cheaper"
    )
    detail_level = st.select_slider(
        "Detail Level",
        options=["Basic", "Standard", "Detailed", "Exhaustive"],
        value="Detailed"
    )

# ─────────────────────────────────────────────
# 3. SYSTEM PROMPT (DYNAMIC)
# ─────────────────────────────────────────────
def build_system_prompt(fir, ps, sec, io_n, date_str, time_str, detail, ps_dist=""):
    detail_map = {
        "Basic":     "ஒவ்வொரு பகுதிக்கும் 2-3 பத்திகள்.",
        "Standard":  "முக்கிய விவரங்களுடன் 4-5 பத்திகள்.",
        "Detailed":  "ஒவ்வொரு பொருளுக்கும் தனி பத்தி. நிறம், நிலை, அமைவிடம், காயங்கள், ரத்தத் தடயங்கள் அனைத்தும் சேர்க்கவும்.",
        "Exhaustive":"அதிகபட்ச விவரம். காணப்படும் ஒவ்வொரு தடயமும், காயமும், சூழலும் — நிறம், அளவு மதிப்பீடு, இட தொடர்பு மற்றும் நிலை ஆகியவை பதிவு செய்யப்பட வேண்டும்.",
    }
    return f"""
நீங்கள் ஒரு நிபுணத்துவமிக்க மூத்த ஆய்வு அதிகாரி (Senior Investigation Officer), தமிழ்நாடு காவல்துறை.
பணி: கீழே கொடுக்கப்பட்ட புகைப்படங்களை முழுமையாக ஆய்வு செய்து, விரிவான "சம்பவ இட ஆய்வு மகஜர்" (Spot Inspection Report / Observation Mahazar) முறையான சட்ட தமிழில் தயாரிக்கவும்.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL INTEGRATION RULE (கட்டாயம் பின்பற்றவும்):

சில புகைப்படங்கள் இறந்த நிலையிலான உடல்களை சவக்கிடங்கு (Mortuary) அல்லது மருத்துவமனை (Hospital) சூழலில் காட்டினாலும், அந்த காயங்கள், ரத்தக் கறைகள், மற்றும் உடல் நிலை ஆகியவை அனைத்தும் சம்பவ இடத்தில் நேரடியாக காணப்பட்டவை (Direct Scene Observation) என்று விவரிக்கவும். "Mortuary-ல் காணப்பட்டது" அல்லது "மருத்துவமனையில் எடுக்கப்பட்டது" என்று எந்த குறிப்பும் சேர்க்கவேண்டாம்.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
படம் ஆய்வு வழிகாட்டுதல்கள் (STRICT):

1. உடல் விவரிப்பு — காயங்கள் (Injury Description):
   - உடலில் காணப்படும் ஒவ்வொரு காயத்தையும் (வெட்டுக்காயம், உடைந்த எலும்பு, தலை காயம், மூளை திசு) சம்பவ இடத்தில் நேரடியாக காணப்பட்டது என விவரிக்கவும்.
   - காயத்தின் வகை, அமைவிடம் (உடலின் எந்த பகுதி), ஆழம் மற்றும் அளவு மதிப்பீடு கொடுக்கவும்.
   - எ.கா.: 'தலையின் இடதுபக்க பகுதியில் சுமார் 5 செ.மீ. நீளமுள்ள ஆழமான வெட்டுக்காயம் காணப்பட்டது. காயத்திலிருந்து ரத்தம் வழிந்து கீழே படர்ந்திருந்தது.'

2. ரத்தம் மற்றும் தடயங்கள் (Blood & Tracks):
   - ரத்தக் கறைகள் (புள்ளிகள், தெறிப்புகள், குட்டைகள்), அவை உலர்ந்த நிலையில் உள்ளதா அல்லது ஈரமான நிலையில் உள்ளதா என குறிப்பிடவும்.
   - சுவர்கள், தூண்கள், தரை ஆகியவற்றில் உள்ள ரத்தத் தெறிப்புகளின் பரவல் திசை கொடுக்கவும்.
   - தடம் (Drag marks / Footprints / Shoe impressions) காணப்படின் அவற்றின் திசையும் தொலைவும் பதிவிடவும்.

3. சூழல் விவரிப்பு (Environmental Context):
   - மண் வகை (செம்மண் / கரிமண் / மணல்), செடிகொடிகள், சுற்றுப்புற கட்டமைப்புகள் (சுவர், வேலி, மரம், கிணறு) ஆகியவற்றை விவரிக்கவும்.
   - சுவர் நிறம், தரை வகை (Marble / Tiles / Mosaic / Cement / கூழாங்கல்), ஒளி மூலம் ஆகியவற்றை குறிப்பிடவும்.

4. பொருள் விவரிப்பு (Object Description):
   - படத்தில் காணப்படும் ஒவ்வொரு பொருளையும் முழுமையாக விவரிக்கவும்.
   - பிராண்ட் பெயர், நிறம், நிலை (சேதமடைந்துள்ளதா/இல்லையா), அமைவிடம் ஆகியவற்றை குறிப்பிடவும்.

5. இட அமைப்பு (Spatial Layout):
   - பொருட்கள் மற்றும் தடயங்களுக்கிடையேயான திசை மற்றும் தூரத் தொடர்பை குறிப்பிடவும்.
   - எ.கா.: 'தரைமட்டத்திலிருந்து சுமார் 4 அடி உயரத்தில்', 'வடக்கு சுவரின் மத்தியில்', 'கதவிலிருந்து 2 அடி தொலைவில்'

6. மொழி விதி: முறையான சட்ட தமிழ் (நீதிமன்ற தமிழ்) மட்டுமே. எந்த ஆங்கில வார்த்தையும் வேண்டாம் (பிராண்ட் பெயர்களை தமிழ் எழுத்தில் எழுதவும்).

7. விவர அளவு: {detail_map[detail]}

8. கட்டாய தடை:
   - இந்த மகஜரில் எவ்விதமான ஒப்புதல் வாக்குமூலமோ (Confession Statement) அல்லது இந்திய சாட்சியச் சட்டம் பிரிவு 27-ன் கீழான தகவல்களோ சேர்க்கக் கூடாது.
   - "Mortuary", "Hospital", "Post-mortem" என்ற வார்த்தைகள் சேர்க்கவே கூடாது.
   - இது முற்றிலும் ஒரு நேரடிப் பார்வை ஆய்வறிக்கை (Direct Observation Report) மட்டுமே.

━━━━━━━━━━━━━━━━━━━━━━━━━━━
மகஜர் EXACT FORMAT (இந்த வடிவமைப்பை மட்டுமே பயன்படுத்தவும்):

சம்பவ இட ஆய்வு மகஜர்
(நேரடிப் பார்வை ஆய்வறிக்கை)

குற்றம் எண் மற்றும் ஆண்டு   : {fir or '________'}
காவல் நிலையம்               : {ps or '________'}
சட்டப் பிரிவுகள்             : {sec or '________'}
காவல் நிலையத்திலிருந்து தூரம் : {ps_dist or '________ கி.மீ., ________ திசை'}
ஆய்வு நடத்திய தேதி           : {date_str}
ஆய்வு நடத்திய நேரம்          : {time_str}
ஆய்வு நடத்திய அதிகாரி        : {io_n or '________'}

இடம் (சம்பவ இட முழு விவரம்):
[சம்பவ இட முழு முகவரி மற்றும் விவரம்]

நான்கு எல்லைகள்:
  • கிழக்கு  : ________
  • மேற்கு   : ________
  • வடக்கு   : ________
  • தெற்கு   : ________

ஒளி மூலம்:
[இயற்கை வெளிச்சம் / மின்விளக்கு வெளிச்சம் — இரண்டையும் குறிப்பிடவும்]

ஆய்வு விபரம்:
[ஒவ்வொரு புகைப்படத்திற்கும் / பகுதிக்கும் மேற்கண்ட வழிகாட்டுதல்களின்படி விரிவான விவரிப்பு — காயங்கள், ரத்தத் தடயங்கள், சூழல் அனைத்தும்]

காணப்பட்ட முக்கிய தடயங்கள்:
[துல்லியமான இட குறிப்புகளுடன் சான்று பொருட்கள் மற்றும் காய விவரங்களின் பட்டியல்]

முடிவுரை (Mudivurai):
மேற்கண்ட விவரங்கள் அனைத்தும் எவ்வித மாற்றமுமின்றி, சம்பவ இடத்தில் காணப்பட்டவாறு துல்லியமாகப் பதிவு செய்யப்பட்டுள்ளன. இச்சம்பவ இட மகஜர் கீழே கண்ட சாட்சிகள் முன்னிலையில் விவரிக்கப்பட்டு, அவர்களது சம்மதத்தின் பேரில் கையொப்பம் பெறப்பட்டது.

சாட்சிகள் கையொப்பம்:
1. பெயர்: ________________  முகவரி: ________________  கையொப்பம்: ________________
2. பெயர்: ________________  முகவரி: ________________  கையொப்பம்: ________________

தயார் செய்தவர் (IO): ____________________
பதவி: ____________________
காவல் நிலையம்: {ps or '____________________'}
தேதி: {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ─────────────────────────────────────────────
# 4. MAIN UI
# ─────────────────────────────────────────────
st.title("🔍 சம்பவ இட ஆய்வு மகஜர் — AI")
st.caption("Tamil Nadu Police | Powered by Google Gemini Vision | Anti-Gravity Systems")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📸 புகைப்படங்கள் பதிவேற்றம்")
    uploaded_images = st.file_uploader(
        "குற்றச் சம்பவ இட புகைப்படங்களை பதிவேற்றவும்",
        accept_multiple_files=True,
        type=["jpg", "jpeg", "png", "webp"],
        help="Multiple photos supported — AI will fuse them into one 360° scene map"
    )

    if uploaded_images:
        st.success(f"✅ {len(uploaded_images)} புகைப்படம்(கள்) பதிவேற்றப்பட்டது")
        img_cols = st.columns(min(len(uploaded_images), 3))
        for i, img_file in enumerate(uploaded_images):
            with img_cols[i % 3]:
                img = Image.open(img_file)
                st.image(img, caption=f"Photo {i+1}", use_container_width=True)

    st.subheader("📝 கள குறிப்புகள் (விருப்பம்)")
    extra_notes = st.text_area(
        "கூடுதல் குறிப்புகள் (Tanglish/Local OK):",
        placeholder="எ.கா.: Switch ON-la irunthuchu, floor-la ரத்தக்கறை இருந்துச்சு, main door lock உடைஞ்சிருந்துச்சு...",
        height=120
    )

with col2:
    st.subheader("📄 மகஜர் முன்னோட்டம்")

    if not api_key:
        st.info("👈 Sidebar-ல் API Key உள்ளிடவும்")
    elif not uploaded_images:
        st.info("👈 குறைந்தது ஒரு புகைப்படம் பதிவேற்றவும்")
    else:
        generate_btn = st.button("⚡ மகஜர் தயாரிக்கவும்", use_container_width=True)

        if generate_btn:
            with st.spinner("🔍 AI ஆய்வு செய்கிறது... சற்று நேரம் காத்திருங்கள்..."):
                try:
                    date_str = exam_date.strftime("%d.%m.%Y")
                    time_str = exam_time.strftime("%H:%M")
                    system_prompt = build_system_prompt(
                        fir_no, ps_name, sections, io_name,
                        date_str, time_str, detail_level, ps_distance
                    )

                    # Build image parts — IO-Assist style (system_instruction separate)
                    img_parts = []
                    for i, img_file in enumerate(uploaded_images):
                        img_file.seek(0)
                        img = Image.open(img_file)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        img.thumbnail((1024, 1024), Image.LANCZOS)
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=60)
                        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                        img_parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64}})
                        img_parts.append({"text": f"[புகைப்படம் {i+1}]"})

                    if extra_notes.strip():
                        img_parts.append({"text": f"\nகள குறிப்புகள்: {extra_notes.strip()}"})

                    # IO-Assist exact structure — system_instruction தனியாக
                    payload = {
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": img_parts}],
                        "generationConfig": {
                            "temperature": 0.2,
                            "maxOutputTokens": 8192,
                            "candidateCount": 1
                        }
                    }

                    # IO-Assist exact API call — single model, no loop
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
                    resp = requests.post(url, json=payload, timeout=90)

                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            mahazar_text = candidates[0]["content"]["parts"][0]["text"]
                        else:
                            st.error("🚨 AI-யிடமிருந்து பதில் வரவில்லை. மீண்டும் try பண்ணவும்.")
                            st.stop()
                    elif resp.status_code == 400:
                        st.error("🚨 API Key தவறானது. சரிபார்க்கவும்.")
                        st.stop()
                    elif resp.status_code == 429:
                        st.error("🚨 Quota முடிந்தது. 1 நிமிடம் காத்து மீண்டும் try பண்ணவும்.")
                        st.stop()
                    elif resp.status_code == 503:
                        st.error("🚨 Server busy. சற்று நேரம் பொறுத்து மீண்டும் try பண்ணவும்.")
                        st.stop()
                    else:
                        st.error(f"🚨 API Error ({resp.status_code}): {resp.text[:300]}")
                        st.stop()

                    st.success("✅ மகஜர் தயாரிக்கப்பட்டது!")

                    # Display in editable text area
                    edited_text = st.text_area(
                        "மகஜர் (திருத்தம் செய்யலாம் | CCTNS Ready):",
                        value=mahazar_text,
                        height=500,
                        key="mahazar_output"
                    )

                    # Download buttons
                    dl_col1, dl_col2 = st.columns(2)
                    with dl_col1:
                        st.download_button(
                            "📥 .txt பதிவிறக்கம்",
                            data=edited_text.encode("utf-8"),
                            file_name=f"Mahazar_{fir_no or 'Draft'}_{date_str}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with dl_col2:
                        # UTF-8 encoded for Tamil Unicode support
                        st.download_button(
                            "📥 .md பதிவிறக்கம்",
                            data=edited_text.encode("utf-8"),
                            file_name=f"Mahazar_{fir_no or 'Draft'}_{date_str}.md",
                            mime="text/markdown",
                            use_container_width=True
                        )

                except requests.exceptions.Timeout:
                    st.error("❌ Timeout: Server நேரம் எடுத்தது. மீண்டும் try பண்ணவும்.")
                except Exception as e:
                    st.error(f"❌ பிழை ஏற்பட்டது: {str(e)}")
                    st.info("API Key சரியானதா? இணைய இணைப்பு சரியாக உள்ளதா என சரிபார்க்கவும்.")

# ─────────────────────────────────────────────
# 5. FOOTER
# ─────────────────────────────────────────────
st.divider()
st.caption("Anti-Gravity Systems | Tamil Nadu Police | For Official Use Only | சட்டப்பூர்வ ஆவணம்")
