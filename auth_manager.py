"""
Auth Manager for Trading Journal
=================================
Multi-user authentication with device lock feature.

Features:
- Password hashing with bcrypt
- Device fingerprinting
- Session management
- Admin panel for user management
"""

import streamlit as st
import hashlib
import uuid
from datetime import datetime

# Optional imports
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

try:
    from google.cloud import firestore
    from google.oauth2 import service_account
    import os
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None


# =============================================================================
# DATABASE CONNECTION
# =============================================================================

def get_auth_db():
    """Get Firestore client for auth operations."""
    if not FIRESTORE_AVAILABLE:
        return None
    
    try:
        if "gcp_service_account" in st.secrets:
            key_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return firestore.Client(credentials=creds)
        elif os.environ.get("GCP_SERVICE_ACCOUNT_JSON"):
            import json
            key_dict = json.loads(os.environ["GCP_SERVICE_ACCOUNT_JSON"])
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return firestore.Client(credentials=creds)
        else:
            return firestore.Client()
    except Exception as e:
        st.error(f"❌ Auth DB Error: {e}")
        return None


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt or fallback to SHA256."""
    if BCRYPT_AVAILABLE:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    else:
        # Fallback: SHA256 with salt (less secure but works without bcrypt)
        salt = uuid.uuid4().hex
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash."""
    if BCRYPT_AVAILABLE and password_hash.startswith('$2'):
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    else:
        # Fallback verification
        if '$' in password_hash:
            salt, hashed = password_hash.split('$', 1)
            return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
        return False


# =============================================================================
# DEVICE FINGERPRINT
# =============================================================================

def get_device_id() -> str:
    """
    Get device ID using a simple approach that works in Streamlit Cloud.
    Uses session-based ID that persists during browser session.
    """
    # If device_id already in session, use it
    if "device_id" in st.session_state:
        return st.session_state.device_id
    
    # Generate a unique device ID based on session
    # This will be unique per browser session
    device_id = f"DEV-{uuid.uuid4().hex[:12].upper()}"
    st.session_state.device_id = device_id
    
    return device_id


# =============================================================================
# USER MANAGEMENT
# =============================================================================

def ensure_admin_exists():
    """Create default admin user if no users exist."""
    db = get_auth_db()
    if not db:
        return
    
    users_ref = db.collection('users')
    
    # Check if any admin exists
    admin_check = users_ref.where('role', '==', 'admin').limit(1).get()
    
    if len(list(admin_check)) == 0:
        # Create default admin
        users_ref.add({
            'username': 'admin',
            'password_hash': hash_password('admin123'),
            'role': 'admin',
            'device_id': None,
            'device_info': None,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        })


def create_user(username: str, password: str, role: str = 'user') -> tuple[bool, str]:
    """Create a new user. Returns (success, message)."""
    db = get_auth_db()
    if not db:
        return False, "Database tidak tersedia"
    
    users_ref = db.collection('users')
    
    # Check if username exists
    existing = users_ref.where('username', '==', username).limit(1).get()
    if len(list(existing)) > 0:
        return False, f"Username '{username}' sudah digunakan"
    
    # Create user
    users_ref.add({
        'username': username,
        'password_hash': hash_password(password),
        'role': role,
        'device_id': None,
        'device_info': None,
        'created_at': datetime.now().isoformat(),
        'last_login': None
    })
    
    return True, f"User '{username}' berhasil dibuat"


def authenticate(username: str, password: str, device_id: str) -> tuple[bool, str, dict]:
    """
    Authenticate user and check device lock.
    Returns (success, message, user_data)
    """
    db = get_auth_db()
    if not db:
        return False, "Database tidak tersedia", {}
    
    users_ref = db.collection('users')
    
    # Find user
    user_docs = users_ref.where('username', '==', username).limit(1).get()
    user_list = list(user_docs)
    
    if len(user_list) == 0:
        return False, "Username tidak ditemukan", {}
    
    user_doc = user_list[0]
    user_data = user_doc.to_dict()
    user_data['_id'] = user_doc.id
    
    # Verify password
    if not verify_password(password, user_data['password_hash']):
        return False, "Password salah", {}
    
    # Check device lock
    stored_device = user_data.get('device_id')
    
    if stored_device is None:
        # First login - lock to this device
        users_ref.document(user_doc.id).update({
            'device_id': device_id,
            'device_info': f"Locked on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'last_login': datetime.now().isoformat()
        })
        user_data['device_id'] = device_id
        return True, "Login berhasil! Device terdaftar.", user_data
    
    elif stored_device != device_id:
        # Different device - blocked!
        return False, "⚠️ Akun terkunci ke device lain. Hubungi admin untuk reset.", {}
    
    else:
        # Same device - OK
        users_ref.document(user_doc.id).update({
            'last_login': datetime.now().isoformat()
        })
        return True, "Login berhasil!", user_data


def reset_device(username: str) -> tuple[bool, str]:
    """Reset device lock for a user (admin only)."""
    db = get_auth_db()
    if not db:
        return False, "Database tidak tersedia"
    
    users_ref = db.collection('users')
    
    # Find user
    user_docs = users_ref.where('username', '==', username).limit(1).get()
    user_list = list(user_docs)
    
    if len(user_list) == 0:
        return False, f"User '{username}' tidak ditemukan"
    
    user_doc = user_list[0]
    
    # Reset device
    users_ref.document(user_doc.id).update({
        'device_id': None,
        'device_info': f"Reset on {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    })
    
    return True, f"Device lock untuk '{username}' berhasil direset"


def delete_user(username: str) -> tuple[bool, str]:
    """Delete a user (cannot delete admin)."""
    if username == 'admin':
        return False, "Tidak bisa hapus admin utama"
    
    db = get_auth_db()
    if not db:
        return False, "Database tidak tersedia"
    
    users_ref = db.collection('users')
    
    # Find user
    user_docs = users_ref.where('username', '==', username).limit(1).get()
    user_list = list(user_docs)
    
    if len(user_list) == 0:
        return False, f"User '{username}' tidak ditemukan"
    
    user_doc = user_list[0]
    users_ref.document(user_doc.id).delete()
    
    return True, f"User '{username}' berhasil dihapus"


def get_all_users() -> list:
    """Get all users (for admin panel)."""
    db = get_auth_db()
    if not db:
        return []
    
    users_ref = db.collection('users')
    docs = users_ref.stream()
    
    users = []
    for doc in docs:
        data = doc.to_dict()
        users.append({
            'username': data.get('username'),
            'role': data.get('role'),
            'device_id': data.get('device_id'),
            'device_info': data.get('device_info'),
            'last_login': data.get('last_login'),
            'created_at': data.get('created_at')
        })
    
    return users


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)


def get_current_user() -> dict:
    """Get current logged-in user data."""
    return st.session_state.get('current_user', {})


def logout():
    """Logout current user."""
    if 'authenticated' in st.session_state:
        del st.session_state['authenticated']
    if 'current_user' in st.session_state:
        del st.session_state['current_user']


# =============================================================================
# UI COMPONENTS
# =============================================================================

def render_login_page():
    """Render the login page UI."""
    # Get device ID (session-based, no JavaScript needed)
    device_id = get_device_id()
    
    # Ensure admin exists
    ensure_admin_exists()
    
    # Custom CSS for login page
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header h1 {
            color: #e94560 !important;
            font-size: 2.5rem;
        }
        .login-header p {
            color: #888;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Login form
    st.markdown("<div class='login-header'>", unsafe_allow_html=True)
    st.markdown("# 🔐 Login")
    st.markdown("*Trading Journal Pro*")
    st.markdown("</div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("👤 Username", placeholder="Masukkan username")
            password = st.text_input("🔑 Password", type="password", placeholder="Masukkan password")
            
            submitted = st.form_submit_button("🚀 Login", use_container_width=True)
            
            if submitted:
                if not username or not password:
                    st.error("Username dan password harus diisi!")
                else:
                    success, message, user_data = authenticate(username, password, device_id)
                    
                    if success:
                        st.session_state['authenticated'] = True
                        st.session_state['current_user'] = user_data
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown("---")
        st.caption(f"🖥️ Device ID: `{device_id}`")
        st.caption("Hubungi admin jika butuh akses atau reset device.")


def render_admin_panel():
    """Render admin panel for user management."""
    st.markdown("### 👑 Admin Panel")
    
    # Tabs for different admin functions
    admin_tab1, admin_tab2, admin_tab3 = st.tabs(["📋 Users", "➕ Add", "🔧 Manage"])
    
    with admin_tab1:
        # List all users
        users = get_all_users()
        if users:
            for user in users:
                device_status = "🔒 Locked" if user['device_id'] else "🔓 Open"
                role_badge = "👑" if user['role'] == 'admin' else "👤"
                
                with st.expander(f"{role_badge} {user['username']} | {device_status}"):
                    st.caption(f"**Role:** {user['role']}")
                    st.caption(f"**Device ID:** {user['device_id'] or 'Belum terdaftar'}")
                    st.caption(f"**Info:** {user['device_info'] or '-'}")
                    st.caption(f"**Last Login:** {user['last_login'] or '-'}")
        else:
            st.info("Belum ada user terdaftar")
    
    with admin_tab2:
        # Add new user
        st.markdown("#### Tambah User Baru")
        
        new_username = st.text_input("Username", key="new_user_username")
        new_password = st.text_input("Password", type="password", key="new_user_password")
        new_role = st.selectbox("Role", ["user", "admin"], key="new_user_role")
        
        if st.button("➕ Buat User", key="btn_create_user"):
            if new_username and new_password:
                success, msg = create_user(new_username, new_password, new_role)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Isi username dan password!")
    
    with admin_tab3:
        # Manage existing users
        st.markdown("#### Reset Device")
        users = get_all_users()
        usernames = [u['username'] for u in users]
        
        reset_user = st.selectbox("Pilih User", usernames, key="reset_device_user")
        if st.button("🔓 Reset Device", key="btn_reset_device"):
            success, msg = reset_device(reset_user)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        
        st.markdown("---")
        st.markdown("#### Hapus User")
        
        del_user = st.selectbox("Pilih User", [u for u in usernames if u != 'admin'], key="delete_user_select")
        if st.button("🗑️ Hapus User", key="btn_delete_user", type="primary"):
            success, msg = delete_user(del_user)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


def render_logout_button():
    """Render a logout button in sidebar."""
    user = get_current_user()
    if user:
        st.sidebar.markdown("---")
        role_badge = "👑" if user.get('role') == 'admin' else "👤"
        st.sidebar.markdown(f"**{role_badge} {user.get('username', 'User')}**")
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout()
            st.rerun()
