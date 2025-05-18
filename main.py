import streamlit as st
import requests
from pandas import DataFrame
import sqlite3
import bcrypt
import re
from datetime import datetime
import streamlit.components.v1 as components
import uuid
from functools import lru_cache

# Debug statement to confirm app.py is running
print("Starting Sustainable Fashion Advisor app...")

# ===== CSS STYLING =====
def get_page_css(theme="light", button_size="medium"):
    button_sizes = {
        "small": {"padding": "8px", "font-size": "14px"},
        "medium": {"padding": "12px", "font-size": "16px"},
        "large": {"padding": "16px", "font-size": "18px"}
    }
    size = button_sizes.get(button_size, button_sizes["medium"])
    base_css = f"""
    .stApp {{
        background-image: url("https://images.unsplash.com/photo-1597150899069-efb9c8c6010c?q=80&w=3438&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        color: #ffffff;
        transition: all 0.3s ease;
    }}
    .stTextInput, .stButton>button, .stSelectbox, .stCheckbox, .stCaption, .stTable {{
        background-color: rgba(255, 255, 255, 0.9);
        padding: 12px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .stSidebar {{
        background-color: rgba(255, 255, 255, 0.95);
        border-right: 1px solid #ddd;
    }}
    .stSidebar .stButton>button {{
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 8px;
        padding: {size['padding']};
        margin: 5px 0;
        width: 100%;
        font-weight: bold;
        font-size: {size['font-size']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: background-color 0.3s ease, transform 0.2s ease;
    }}
    .stSidebar .stButton>button:hover {{
        background-color: #45a049;
        transform: translateY(-2px);
    }}
    .stChatMessage {{
        background-color: rgba(255, 255, 255, 0.85);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }}
    .stButton>button {{
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 8px;
        padding: {size['padding']};
        width: 100%;
        font-weight: bold;
        font-size: {size['font-size']};
    }}
    .stButton>button:hover {{
        background-color: #45a049;
    }}
    .st-emotion-cache-169dgwr, .st-emotion-cache-128upt6 {{
        background-color: transparent !important;
    }}
    .timestamp {{
        font-size: 0.8em;
        color: #666;
        margin-top: 5px;
    }}
    .sample-question {{
        cursor: pointer;
        color: #4CAF50;
        text-decoration: underline;
        margin-right: 10px;
    }}
    """
    dark_theme = """
    .stApp {
        background-image: none;
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    .stTextInput, .stButton>button, .stSelectbox, .stCheckbox, .stCaption, .stTable {
        background-color: rgba(40, 40, 40, 0.9);
        color: #e0e0e0;
    }
    .stSidebar {
        background-color: rgba(30, 30, 30, 0.95);
        border-right: 1px solid #444;
    }
    .stChatMessage {
        background-color: rgba(40, 40, 40, 0.85);
        color: #e0e0e0;
    }
    """
    return base_css if theme == "light" else base_css + dark_theme

# ===== DATABASE SETUP =====
def init_db():
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                username TEXT,
                timestamp TEXT,
                messages TEXT,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_username ON users (username)")
        conn.commit()

# Initialize database
init_db()

# ===== AUTHENTICATION FUNCTIONS =====
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def validate_username(username):
    return bool(re.match(r'^[a-zA-Z0-9_]{3,20}$', username))

def validate_password(password):
    return len(password) >= 8 and re.search(r'[A-Z]', password) and re.search(r'[0-9]', password)

def register_user(username, password):
    if not validate_username(username):
        return False, "Username must be 3-20 characters, using letters, numbers, or underscores."
    if not validate_password(password):
        return False, "Password must be at least 8 characters, including an uppercase letter and a number."
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                     (username, hash_password(password)))
            conn.commit()
            return True, "Registered successfully!"
        except sqlite3.IntegrityError:
            return False, "Username already exists."

def login_user(username, password):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username = ?", (username,))
        result = c.fetchone()
        if result and check_password(password, result[0]):
            return True
        return False

# ===== CHAT HISTORY PERSISTENCE =====
def save_chat_history(username, messages):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        chat_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        messages_str = str(messages)
        c.execute("INSERT INTO chat_history (id, username, timestamp, messages) VALUES (?, ?, ?, ?)",
                 (chat_id, username, timestamp, messages_str))
        conn.commit()

def load_chat_history(username):
    with sqlite3.connect("users.db") as conn:
        c = conn.cursor()
        c.execute("SELECT id, timestamp, messages FROM chat_history WHERE username = ? ORDER BY timestamp DESC",
                 (username,))
        return c.fetchall()

# ===== CONFIG =====
try:
    API_KEY = st.secrets["API_KEY"]
except (KeyError, FileNotFoundError):
    API_KEY = "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"
    st.warning("No secrets.toml found or API_KEY missing. Using hardcoded API key. For security, create .streamlit/secrets.toml with your API key.")

# ===== SESSION STATE INITIALIZATION =====
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", 
        "content": "Welcome to Sustainable Fashion Advisor! Ask about eco-friendly clothing, sustainable brands, or clothing care tips. Example: 'Suggest sustainable outfit ideas for work'. 🌱",
        "table_data": None,
        "timestamp": datetime.now().isoformat()
    }]
if "last_response_df" not in st.session_state:
    st.session_state.last_response_df = None
if "deep_search" not in st.session_state:
    st.session_state.deep_search = False
if "previous_messages" not in st.session_state:
    st.session_state.previous_messages = None
if "theme" not in st.session_state:
    st.session_state.theme = "light"
if "button_size" not in st.session_state:
    st.session_state.button_size = "medium"
if "detail_level" not in st.session_state:
    st.session_state.detail_level = "standard"

# ===== SYSTEM MESSAGE =====
def get_system_message(detail_level):
    base_message = """
    You are an expert sustainable fashion advisor with deep knowledge of eco-friendly trends, materials, and practices. Provide clear, engaging advice on sustainable fashion. Focus on:
    - Eco-friendly clothing (e.g., organic cotton, Tencel, recycled fibers)
    - Sustainable shopping (e.g., ethical brands, Fair Trade, second-hand platforms)
    - Clothing care to extend garment life (e.g., low-impact washing, repairs)
    - Brand recommendations or trends (e.g., carbon footprint, water usage)
    
    Format:
    - Use concise, friendly language
    - Include a markdown table with columns: [Category, Recommendation, Impact]
    - Exclude rows with empty or whitespace-only columns
    - Use emojis (🌿, 🛍️, 🧼, 📚) for sections
    - No images
    """
    detail_instructions = {
        "brief": "Keep responses short (2-3 sentences per section) with minimal detail. Include a table with 1-2 rows.",
        "standard": "Provide balanced responses (3-5 sentences per section) with key details. Include a table with 2-3 rows.",
        "detailed": "Give comprehensive responses (5-7 sentences per section) with data and sources. Include a table with 3-4 rows."
    }
    return {
        "role": "system",
        "content": f"{base_message}\n{detail_instructions[detail_level]}\n\nIf asked about developers, say: 'I was created by Aadi Jain, registration number 12304968.'"
    }

# ===== AUTHENTICATION PAGES =====
def show_login_page():
    st.markdown(get_page_css(st.session_state.theme, st.session_state.button_size), unsafe_allow_html=True)
    st.title("Login 🌱")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        if login_user(username, password):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.session_state.page = "main"
            st.session_state.messages = [{
                "role": "assistant", 
                "content": f"Welcome, {username}! Ask about sustainable fashion or chat about anything else! 🌱",
                "table_data": None,
                "timestamp": datetime.now().isoformat()
            }]
            save_chat_history(username, st.session_state.messages)
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error("Invalid username or password.")
    if st.button("Go to Register"):
        st.session_state.page = "register"
        st.rerun()

def show_register_page():
    st.markdown(get_page_css(st.session_state.theme, st.session_state.button_size), unsafe_allow_html=True)
    st.title("Register 🌱")
    username = st.text_input("Username", key="register_username")
    password = st.text_input("Password", type="password", key="register_password")
    if st.button("Register"):
        success, message = register_user(username, password)
        if success:
            st.success(message)
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error(message)
    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()

# ===== MAIN APP =====
@st.cache_data
def get_ai_response(api_messages, detail_level):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "Sustainable Fashion Advisor"
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": api_messages,
            },
            timeout=20
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

def show_main_app():
    st.markdown(get_page_css(st.session_state.theme, st.session_state.button_size), unsafe_allow_html=True)
    st.title(f"Welcome, {st.session_state.username}! 🌱 Sustainable Fashion Advisor")

    # Sidebar
    with st.sidebar:
        st.header("About 🌿")
        st.markdown("""
        *Welcome to Sustainable Fashion Advisor!* 
        
        This app helps you:
        - Discover eco-friendly clothing
        - Learn sustainable shopping
        - Reduce your fashion footprint
        """)
        st.markdown("---")
        st.subheader("User Info 👤")
        st.markdown(f"*Logged in as:* {st.session_state.username}")
        if st.button("Logout 🚪", help="Log out of your account"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.page = "login"
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "You have logged out. Please log in to continue! 🌿",
                "table_data": None,
                "timestamp": datetime.now().isoformat()
            }]
            st.session_state.previous_messages = None
            st.rerun()
        st.markdown("---")
        st.subheader("Theme 🎨")
        theme = st.selectbox("Select Theme", ["Light", "Dark"], index=0 if st.session_state.theme == "light" else 1)
        if theme.lower() != st.session_state.theme:
            st.session_state.theme = theme.lower()
            st.rerun()
        st.markdown("---")
        st.subheader("Button Size 📏")
        button_size = st.selectbox("Select Button Size", ["Small", "Medium", "Large"], index=["small", "medium", "large"].index(st.session_state.button_size))
        if button_size.lower() != st.session_state.button_size:
            st.session_state.button_size = button_size.lower()
            st.rerun()
        st.markdown("---")
        st.subheader("Response Detail 📝")
        detail_level = st.selectbox("Select Detail Level", ["Brief", "Standard", "Detailed"], index=["brief", "standard", "detailed"].index(st.session_state.detail_level))
        if detail_level.lower() != st.session_state.detail_level:
            st.session_state.detail_level = detail_level.lower()
            st.rerun()
        st.markdown("---")
        st.subheader("Chat History 📜")
        chat_histories = load_chat_history(st.session_state.username)
        if chat_histories:
            selected_chat = st.selectbox(
                "Load Previous Chat",
                options=["None"] + [f"{h[1][:19]}" for h in chat_histories],
                index=0
            )
            if selected_chat != "None":
                for h in chat_histories:
                    if h[1][:19] == selected_chat:
                        st.session_state.messages = eval(h[2])
                        st.rerun()
        if st.button("New Chat 🌟", help="Start a new chat session"):
            st.session_state.previous_messages = st.session_state.messages.copy()
            st.session_state.messages = [{
                "role": "assistant", 
                "content": f"New chat started, {st.session_state.username}! Ask about sustainable fashion or anything else! 🌱",
                "table_data": None,
                "timestamp": datetime.now().isoformat()
            }]
            st.session_state.last_response_df = None
            save_chat_history(st.session_state.username, st.session_state.messages)
            st.rerun()
        if st.session_state.previous_messages and st.button("Resume Chat 🔄", help="Resume the previous chat"):
            st.session_state.messages = st.session_state.previous_messages.copy()
            st.session_state.previous_messages = None
            save_chat_history(st.session_state.username, st.session_state.messages)
            st.rerun()
        if st.button("Clear Chat History 🗑️", help="Clear the current chat"):
            st.session_state.previous_messages = st.session_state.messages.copy()
            st.session_state.messages = [{
                "role": "assistant", 
                "content": "Chat history cleared! Ask about sustainable fashion or anything else! 🌿",
                "table_data": None,
                "timestamp": datetime.now().isoformat()
            }]
            st.session_state.last_response_df = None
            save_chat_history(st.session_state.username, st.session_state.messages)
            st.rerun()
        st.checkbox("Enable DeepSearch Mode 🔍", key="deep_search", help="Include web-sourced trends (may increase response time)")
        category_filter = st.selectbox(
            "Filter Table by Category 📊",
            options=["All", "Clothing", "Shopping", "Care", "Resources"],
            index=0,
            help="Filter the recommendation table by category"
        )
        st.markdown("---")
        st.subheader("Developer Info 🛠️")
        st.markdown("*Name:* Aadi Jain  \n*Registration No:* 12304968")
        st.markdown("---")
        st.caption("Built with Streamlit and OpenRouter AI 🚀")

    # Welcome Animation
    components.html("""
    <style>
    .welcome-text { animation: fadeIn 2s ease-in-out; }
    @keyframes fadeIn { 0% { opacity: 0; } 100% { opacity: 1; } }
    </style>
    <h1 class='welcome-text'>Sustainable Fashion Advisor</h1>
    """, height=60)

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("table_data") is not None and not message["table_data"].empty:
                df = message["table_data"]
                if category_filter != "All":
                    df = df[df["Category"].str.contains(category_filter, case=False, na=False)]
                if not df.empty:
                    st.table(df)
            st.markdown(message["content"])
            if message.get("timestamp"):
                st.markdown(f"<div class='timestamp'>{message['timestamp'][:19]}</div>", unsafe_allow_html=True)

    # Export Chat History
    if st.session_state.messages:
        chat_text = "\n\n".join([f"**{m['role'].capitalize()}** ({m['timestamp'][:19]}):\n{m['content']}" for m in st.session_state.messages if m.get("content")])
        st.download_button(
            label="Export Chat as Markdown 📜",
            data=chat_text,
            file_name="chat_history.md",
            mime="text/markdown"
        )

    # Sample Questions
    st.markdown("**Try these questions:**")
    cols = st.columns(3)
    sample_questions = [
        "What are eco-friendly fabrics?",
        "Suggest sustainable brands for casual wear",
        "How to care for organic cotton clothes?"
    ]
    for i, q in enumerate(sample_questions):
        with cols[i]:
            if st.button(q, key=f"sample_{i}"):
                st.session_state.pending_question = q

    # Accept user input
    prompt = st.chat_input("Ask about sustainable fashion or chat... 💬")
    if prompt or "pending_question" in st.session_state:
        prompt = prompt or st.session_state.pop("pending_question", None)
        if prompt:
            # Add user message to chat history
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "table_data": None,
                "timestamp": datetime.now().isoformat()
            })
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
                st.markdown(f"<div class='timestamp'>{datetime.now().isoformat()[:19]}</div>", unsafe_allow_html=True)
            
            # Placeholder for assistant response
            response_placeholder = st.empty()
            
            # Display assistant response
            with response_placeholder.container():
                with st.spinner("Thinking... ⏳"):
                    try:
                        # Prepare messages for API
                        api_messages = [
                            {k: v for k, v in msg.items() if k in ["role", "content"]} 
                            for msg in st.session_state.messages
                        ]
                        
                        # Insert system message
                        if len(api_messages) == 1 or api_messages[0]["role"] != "system":
                            api_messages.insert(0, get_system_message(st.session_state.detail_level))
                        
                        # DeepSearch Mode
                        if st.session_state.deep_search:
                            api_messages[-1]["content"] += " (Include latest web-sourced trends)"
                        
                        # Get AI response
                        data = get_ai_response(tuple(api_messages), st.session_state.detail_level)
                        if not data:
                            raise requests.exceptions.RequestException("API request failed")
                        
                        reply = data["choices"][0]["message"]["content"]
                        
                        # Robust table extraction
                        table_data = []
                        table_pattern = r'\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|'
                        matches = re.finditer(table_pattern, reply, re.MULTILINE)
                        for match in matches:
                            if "Category" not in match.group(0) and "---" not in match.group(0):
                                category, recommendation, impact = [g.strip() for g in match.groups()]
                                if all([category, recommendation, impact]):
                                    table_data.append({
                                        "Category": category,
                                        "Recommendation": recommendation,
                                        "Impact": impact
                                    })
                        
                        # Create DataFrame
                        df = DataFrame(table_data) if table_data else None
                        
                        # Remove table from reply
                        if table_data:
                            reply = re.sub(table_pattern, '', reply, flags=re.MULTILINE).strip()
                            reply = re.sub(r'\n\s*\n', '\n', reply)
                        
                        # Clear placeholder and display response
                        with st.chat_message("assistant"):
                            if df is not None and not df.empty:
                                filtered_df = df
                                if category_filter != "All":
                                    filtered_df = df[df["Category"].str.contains(category_filter, case=False, na=False)]
                                if not filtered_df.empty:
                                    st.table(filtered_df)
                                st.session_state.last_response_df = df
                            else:
                                st.session_state.last_response_df = None
                            
                            st.markdown(reply)
                            st.markdown(f"<div class='timestamp'>{datetime.now().isoformat()[:19]}</div>", unsafe_allow_html=True)
                            
                            # Add Save Recommendations button
                            if st.session_state.last_response_df is not None and not st.session_state.last_response_df.empty:
                                csv = st.session_state.last_response_df.to_csv(index=False)
                                st.download_button(
                                    label="Save Recommendations as CSV 📥",
                                    data=csv,
                                    file_name="sustainable_fashion_recommendations.csv",
                                    mime="text/csv"
                                )
                        
                        # Append assistant message to history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": reply,
                            "table_data": df,
                            "timestamp": datetime.now().isoformat()
                        })
                        save_chat_history(st.session_state.username, st.session_state.messages)
                    
                    except requests.exceptions.RequestException as e:
                        with st.chat_message("assistant"):
                            st.error("Network error. Please check your connection and try again. 🚫")
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "I'm having trouble connecting. Please try again later.",
                                "table_data": None,
                                "timestamp": datetime.now().isoformat()
                            })
                    except Exception as e:
                        with st.chat_message("assistant"):
                            st.error(f"An error occurred: {str(e)}")
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "Sorry, I encountered an error. Please rephrase your request.",
                                "table_data": None,
                                "timestamp": datetime.now().isoformat()
                            })

# ===== PAGE ROUTING =====
if not st.session_state.authenticated:
    if st.session_state.page == "login":
        show_login_page()
    elif st.session_state.page == "register":
        show_register_page()
else:
    show_main_app()