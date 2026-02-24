import { useState, useEffect } from "react";


// ─── CONFIG API ───────────────────────────────────────────────────────────────
const API = "http://localhost:8000";

const api = {
  login: (data) =>
    fetch(`${API}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",          // session cookie
      body: JSON.stringify(data),
    }).then((r) => r.json()),

  register: (role, data) =>
    fetch(`${API}/auth/register/${role}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => r.json()),

  me: (token) =>
    fetch(`${API}/auth/me/`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then((r) => r.json()),

  logout: (token) =>
    fetch(`${API}/auth/logout/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ refresh: localStorage.getItem("refresh") }),
    }),

  googleLogin: () => {
    window.location.href = `${API}/auth/social/google/login/`;
  },
};

// ─── TOKEN HELPERS ────────────────────────────────────────────────────────────
const saveTokens = ({ access, refresh }) => {
  localStorage.setItem("access", access);
  localStorage.setItem("refresh", refresh);
};
const getAccess = () => localStorage.getItem("access");
const clearTokens = () => {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
};

// ─── STYLES ───────────────────────────────────────────────────────────────────
const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --ink:     #0f0d0a;
    --paper:   #faf7f2;
    --cream:   #f0ebe0;
    --gold:    #c9a84c;
    --gold-lt: #e8d5a3;
    --rust:    #b84c2a;
    --sage:    #5a7a5a;
    --muted:   #8a8070;
    --border:  #d4ccc0;
    --radius:  2px;
    --shadow:  0 2px 24px rgba(15,13,10,.08);
  }

  body { background: var(--paper); font-family: 'DM Sans', sans-serif; color: var(--ink); }

  .auth-root {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  /* ── Left panel ── */
  .auth-visual {
    background: var(--ink);
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 3rem;
  }
  .auth-visual::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 80% 60% at 20% 80%, rgba(201,168,76,.18) 0%, transparent 60%),
      radial-gradient(ellipse 50% 40% at 80% 20%, rgba(90,122,90,.15) 0%, transparent 60%);
  }
  .visual-brand {
    position: relative;
    z-index: 1;
  }
  .visual-brand h1 {
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem;
    color: var(--gold-lt);
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .visual-brand span {
    font-size: .75rem;
    color: var(--muted);
    letter-spacing: .2em;
    text-transform: uppercase;
    display: block;
    margin-top: .25rem;
  }
  .visual-quote {
    position: relative;
    z-index: 1;
  }
  .visual-quote blockquote {
    font-family: 'Playfair Display', serif;
    font-style: italic;
    font-size: 2rem;
    line-height: 1.35;
    color: var(--paper);
    margin-bottom: 1.5rem;
  }
  .visual-quote cite {
    font-size: .8rem;
    color: var(--muted);
    letter-spacing: .15em;
    text-transform: uppercase;
  }
  .visual-decorlines {
    position: absolute;
    bottom: 0; right: 0;
    width: 200px; height: 200px;
    opacity: .06;
  }
  .visual-decorlines line { stroke: var(--gold); stroke-width: 1; }

  /* ── Right panel ── */
  .auth-form-panel {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 3rem 4rem;
    background: var(--paper);
  }

  .auth-header { margin-bottom: 2.5rem; }
  .auth-header h2 {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    color: var(--ink);
    margin-bottom: .5rem;
  }
  .auth-header p { color: var(--muted); font-size: .9rem; line-height: 1.6; }

  /* ── Tab switcher ── */
  .tab-row {
    display: flex;
    gap: .25rem;
    margin-bottom: 2rem;
    background: var(--cream);
    padding: .25rem;
    border-radius: var(--radius);
  }
  .tab-btn {
    flex: 1;
    padding: .6rem 1rem;
    border: none;
    background: transparent;
    cursor: pointer;
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    color: var(--muted);
    transition: all .2s;
    border-radius: var(--radius);
  }
  .tab-btn.active {
    background: var(--ink);
    color: var(--gold-lt);
  }

  /* ── Role selector ── */
  .role-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .75rem;
    margin-bottom: 1.5rem;
  }
  .role-card {
    padding: 1rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    transition: all .2s;
    background: transparent;
    text-align: left;
  }
  .role-card.selected {
    border-color: var(--gold);
    background: rgba(201,168,76,.06);
  }
  .role-card .role-icon { font-size: 1.4rem; margin-bottom: .4rem; }
  .role-card .role-name {
    font-size: .8rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--ink);
    font-weight: 500;
  }
  .role-card .role-desc { font-size: .75rem; color: var(--muted); margin-top: .2rem; }

  /* ── Fields ── */
  .field-group { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }
  .field { margin-bottom: 1rem; }
  .field label {
    display: block;
    font-size: .75rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .4rem;
  }
  .field input {
    width: 100%;
    padding: .75rem 1rem;
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    background: var(--paper);
    font-family: 'DM Sans', sans-serif;
    font-size: .95rem;
    color: var(--ink);
    outline: none;
    transition: border-color .2s;
  }
  .field input:focus { border-color: var(--gold); }
  .field input::placeholder { color: var(--border); }

  /* ── Buttons ── */
  .btn-primary {
    width: 100%;
    padding: .9rem;
    background: var(--ink);
    color: var(--gold-lt);
    border: none;
    border-radius: var(--radius);
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all .2s;
    margin-top: .5rem;
  }
  .btn-primary:hover { background: #1e1c17; }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; }

  .btn-google {
    width: 100%;
    padding: .85rem;
    background: var(--paper);
    border: 1.5px solid var(--border);
    border-radius: var(--radius);
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: .6rem;
    color: var(--ink);
    transition: all .2s;
    margin-bottom: 1.5rem;
  }
  .btn-google:hover { border-color: var(--gold); background: var(--cream); }

  /* ── Divider ── */
  .divider {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin: 1.25rem 0;
    color: var(--border);
    font-size: .75rem;
    letter-spacing: .1em;
    text-transform: uppercase;
  }
  .divider::before, .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  /* ── Error / success ── */
  .alert {
    padding: .75rem 1rem;
    border-radius: var(--radius);
    font-size: .85rem;
    margin-bottom: 1rem;
  }
  .alert-error { background: rgba(184,76,42,.08); color: var(--rust); border-left: 3px solid var(--rust); }
  .alert-success { background: rgba(90,122,90,.08); color: var(--sage); border-left: 3px solid var(--sage); }

  /* ── Dashboard ── */
  .dashboard {
    min-height: 100vh;
    background: var(--cream);
    padding: 0;
  }
  .dash-nav {
    background: var(--ink);
    padding: 1rem 2.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .dash-nav-brand {
    font-family: 'Playfair Display', serif;
    color: var(--gold-lt);
    font-size: 1.1rem;
    letter-spacing: .08em;
  }
  .dash-nav-user {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: .85rem;
    color: var(--muted);
  }
  .dash-nav-badge {
    padding: .25rem .75rem;
    background: rgba(201,168,76,.15);
    color: var(--gold-lt);
    border-radius: 20px;
    font-size: .7rem;
    letter-spacing: .12em;
    text-transform: uppercase;
  }
  .btn-logout {
    padding: .4rem .9rem;
    border: 1px solid #333;
    background: transparent;
    color: var(--muted);
    border-radius: var(--radius);
    cursor: pointer;
    font-size: .8rem;
    transition: all .2s;
  }
  .btn-logout:hover { border-color: var(--rust); color: var(--rust); }
  .dash-body { padding: 3rem 2.5rem; }
  .dash-title {
    font-family: 'Playfair Display', serif;
    font-size: 2rem;
    margin-bottom: .5rem;
  }
  .dash-subtitle { color: var(--muted); margin-bottom: 2.5rem; }
  .dash-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
  }
  .dash-card {
    background: var(--paper);
    padding: 1.75rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    border-top: 3px solid var(--gold);
  }
  .dash-card-label {
    font-size: .75rem;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: .75rem;
  }
  .dash-card-value {
    font-family: 'Playfair Display', serif;
    font-size: 2.5rem;
    color: var(--ink);
  }

  /* ── Spinner ── */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner {
    width: 16px; height: 16px;
    border: 2px solid var(--gold-lt);
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin .6s linear infinite;
    display: inline-block;
    margin-right: .5rem;
    vertical-align: middle;
  }

  @media (max-width: 768px) {
    .auth-root { grid-template-columns: 1fr; }
    .auth-visual { display: none; }
    .auth-form-panel { padding: 2rem 1.5rem; }
    .dash-cards { grid-template-columns: 1fr; }
    .field-group { grid-template-columns: 1fr; }
  }
`;

// ─── ICONS ────────────────────────────────────────────────────────────────────
const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

// ─── VISUAL PANEL ─────────────────────────────────────────────────────────────
const VisualPanel = () => (
  <div className="auth-visual">
    <div className="visual-brand">
      <h1>Olist</h1>
      <span>Brazilian E-Commerce</span>
    </div>
    <div className="visual-quote">
      <blockquote>
        "Commerce is the great civilizer. We exchange not just goods, but ideas."
      </blockquote>
      <cite>— Platform Philosophy</cite>
    </div>
    <svg className="visual-decorlines" viewBox="0 0 200 200">
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={i} x1={0} y1={i * 18} x2={200} y2={i * 18} />
      ))}
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={i + 12} x1={i * 18} y1={0} x2={i * 18} y2={200} />
      ))}
    </svg>
  </div>
);

// ─── LOGIN FORM ───────────────────────────────────────────────────────────────
const LoginForm = ({ onSuccess }) => {
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const res = await api.login(form);
      if (res.access) { saveTokens(res); onSuccess(res); }
      else setError(res.error || res.detail || "Identifiants invalides.");
    } catch { setError("Erreur réseau."); }
    setLoading(false);
  };

  return (
    <form onSubmit={submit}>
      {error && <div className="alert alert-error">{error}</div>}
      <button type="button" className="btn-google" onClick={api.googleLogin}>
        <GoogleIcon /> Continuer avec Google
      </button>
      <div className="divider">ou par email</div>
      <div className="field">
        <label>Email</label>
        <input name="email" type="email" placeholder="vous@exemple.com"
               value={form.email} onChange={handle} required />
      </div>
      <div className="field">
        <label>Mot de passe</label>
        <input name="password" type="password" placeholder="••••••••"
               value={form.password} onChange={handle} required />
      </div>
      <button className="btn-primary" type="submit" disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Connexion…" : "Se connecter"}
      </button>
    </form>
  );
};

// ─── REGISTER FORM ────────────────────────────────────────────────────────────
const RegisterForm = ({ onSuccess }) => {
  const [role, setRole] = useState("customer");
  const [form, setForm] = useState({
    email: "", first_name: "", last_name: "", phone_number: "",
    password: "", password2: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const res = await api.register(role, form);
      if (res.access) { saveTokens(res); onSuccess(res); }
      else {
        const msg = Object.values(res).flat().join(" ");
        setError(msg || "Erreur lors de l'inscription.");
      }
    } catch { setError("Erreur réseau."); }
    setLoading(false);
  };

  return (
    <form onSubmit={submit}>
      {error && <div className="alert alert-error">{error}</div>}

      {/* Role selector */}
      <div className="role-row">
        {[
          { key: "customer", icon: "🛍️", name: "Acheteur", desc: "Je veux commander" },
          { key: "seller",   icon: "🏪", name: "Vendeur",  desc: "Je veux vendre" },
        ].map(({ key, icon, name, desc }) => (
          <button key={key} type="button"
                  className={`role-card ${role === key ? "selected" : ""}`}
                  onClick={() => setRole(key)}>
            <div className="role-icon">{icon}</div>
            <div className="role-name">{name}</div>
            <div className="role-desc">{desc}</div>
          </button>
        ))}
      </div>

      <div className="field-group">
        <div className="field">
          <label>Prénom</label>
          <input name="first_name" placeholder="Alice" value={form.first_name} onChange={handle} required />
        </div>
        <div className="field">
          <label>Nom</label>
          <input name="last_name" placeholder="Dupont" value={form.last_name} onChange={handle} required />
        </div>
      </div>
      <div className="field">
        <label>Email</label>
        <input name="email" type="email" placeholder="vous@exemple.com"
               value={form.email} onChange={handle} required />
      </div>
      <div className="field">
        <label>Téléphone <span style={{color:"var(--border)"}}>— optionnel</span></label>
        <input name="phone_number" placeholder="+55 11 99999-9999"
               value={form.phone_number} onChange={handle} />
      </div>
      <div className="field-group">
        <div className="field">
          <label>Mot de passe</label>
          <input name="password" type="password" placeholder="••••••••"
                 value={form.password} onChange={handle} required />
        </div>
        <div className="field">
          <label>Confirmation</label>
          <input name="password2" type="password" placeholder="••••••••"
                 value={form.password2} onChange={handle} required />
        </div>
      </div>

      <button className="btn-primary" type="submit" disabled={loading}>
        {loading && <span className="spinner" />}
        {loading ? "Inscription…" : `Créer mon compte ${role === "seller" ? "vendeur" : "acheteur"}`}
      </button>
    </form>
  );
};

// ─── DASHBOARD ────────────────────────────────────────────────────────────────
const Dashboard = ({ user, onLogout }) => {
  const isCustomer = user.role === "customer";
  const cards = isCustomer
    ? [
        { label: "Commandes", value: "—" },
        { label: "En cours", value: "—" },
        { label: "Livraisons", value: "—" },
      ]
    : [
        { label: "Produits", value: "—" },
        { label: "Ventes", value: "—" },
        { label: "Revenus", value: "—" },
      ];

  const doLogout = async () => {
    await api.logout(getAccess());
    clearTokens();
    onLogout();
  };

  return (
    <div className="dashboard">
      <nav className="dash-nav">
        <span className="dash-nav-brand">Olist</span>
        <div className="dash-nav-user">
          <span>{user.email}</span>
          <span className="dash-nav-badge">{user.role}</span>
          <button className="btn-logout" onClick={doLogout}>Déconnexion</button>
        </div>
      </nav>
      <div className="dash-body">
        <h1 className="dash-title">Bonjour 👋</h1>
        <p className="dash-subtitle">
          Connecté en tant que <strong>{user.role}</strong> — token JWT actif.
        </p>
        <div className="dash-cards">
          {cards.map((c) => (
            <div key={c.label} className="dash-card">
              <div className="dash-card-label">{c.label}</div>
              <div className="dash-card-value">{c.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ─── AUTH SHELL ───────────────────────────────────────────────────────────────
const AuthShell = ({ onSuccess }) => {
  const [tab, setTab] = useState("login");

  return (
    <div className="auth-root">
      <VisualPanel />
      <div className="auth-form-panel">
        <div className="auth-header">
          <h2>{tab === "login" ? "Connexion" : "Inscription"}</h2>
          <p>
            {tab === "login"
              ? "Accédez à votre espace personnel."
              : "Rejoignez la plus grande marketplace brésilienne."}
          </p>
        </div>

        <div className="tab-row">
          <button className={`tab-btn ${tab === "login" ? "active" : ""}`}
                  onClick={() => setTab("login")}>Connexion</button>
          <button className={`tab-btn ${tab === "register" ? "active" : ""}`}
                  onClick={() => setTab("register")}>Inscription</button>
        </div>

        {tab === "login"
          ? <LoginForm onSuccess={onSuccess} />
          : <RegisterForm onSuccess={onSuccess} />}
      </div>
    </div>
  );
};

// ─── APP ROOT ─────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  // Rehydrate depuis le token existant
  useEffect(() => {
    const token = getAccess();
    if (!token) { setChecking(false); return; }
    api.me(token)
      .then((data) => { if (data.email) setUser(data); })
      .catch(() => clearTokens())
      .finally(() => setChecking(false));
  }, []);

  if (checking) return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"center",
                  height:"100vh", background:"var(--paper)" }}>
      <span className="spinner" style={{ width:32, height:32, borderWidth:3 }} />
    </div>
  );

  return (
    <>
      <style>{styles}</style>
      {user
        ? <Dashboard user={user} onLogout={() => setUser(null)} />
        : <AuthShell onSuccess={(data) => setUser({ email: data.email, role: data.role })} />}
    </>
  );
}
