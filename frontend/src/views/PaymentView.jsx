import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  CardNumberElement,
  CardExpiryElement,
  CardCvcElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";

// ─── CONFIG ───────────────────────────────────────────────────────────────────
const API            = "http://localhost:8000";
const stripePromise  = loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY);

const authFetch = (url, opts = {}) =>
  fetch(`${API}${url}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("access")}`,
      ...(opts.headers || {}),
    },
  }).then((r) => r.json());

// ─── STYLES ───────────────────────────────────────────────────────────────────
const S = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Instrument+Serif:ital@0;1&family=DM+Mono:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0a0a08;
    --surface:  #111110;
    --card:     #161614;
    --border:   #252522;
    --gold:     #d4a853;
    --gold-dim: #8a6830;
    --text:     #e8e4dc;
    --muted:    #6b6860;
    --success:  #4a8c5c;
    --error:    #8c4a4a;
    --radius:   6px;
  }

  body { background: var(--bg); color: var(--text); font-family: 'Syne', sans-serif; }

  .pay-root {
    min-height: 100vh;
    display: grid;
    grid-template-columns: 1fr 420px;
    gap: 0;
  }

  /* ── LEFT : résumé commande ── */
  .pay-summary {
    background: var(--surface);
    padding: 3rem;
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .pay-brand {
    font-family: 'Instrument Serif', serif;
    font-size: 1.4rem;
    color: var(--gold);
    letter-spacing: .04em;
  }

  .pay-order-title {
    font-size: .7rem;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 1rem;
  }

  .pay-items { display: flex; flex-direction: column; gap: .75rem; }

  .pay-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  .pay-item-name { font-size: .9rem; color: var(--text); }
  .pay-item-meta { font-size: .75rem; color: var(--muted); margin-top: .2rem; font-family: 'DM Mono', monospace; }
  .pay-item-price {
    font-family: 'DM Mono', monospace;
    font-size: .95rem;
    color: var(--gold);
    white-space: nowrap;
  }

  .pay-divider { border: none; border-top: 1px solid var(--border); }

  .pay-total-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
  }
  .pay-total-label { font-size: .8rem; letter-spacing: .15em; text-transform: uppercase; color: var(--muted); }
  .pay-total-value {
    font-family: 'Instrument Serif', serif;
    font-size: 2.4rem;
    color: var(--gold);
  }
  .pay-total-currency { font-size: 1rem; color: var(--gold-dim); margin-right: .3rem; }

  /* ── RIGHT : formulaire paiement ── */
  .pay-form-panel {
    background: var(--bg);
    padding: 3rem 2.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .pay-form-title {
    font-family: 'Instrument Serif', serif;
    font-size: 1.8rem;
    color: var(--text);
  }
  .pay-form-subtitle { font-size: .8rem; color: var(--muted); margin-top: .3rem; }

  /* ── Method selector ── */
  .pay-methods {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: .5rem;
  }
  .pay-method-btn {
    padding: .75rem .5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    cursor: pointer;
    text-align: center;
    transition: all .2s;
    color: var(--muted);
    font-size: .75rem;
    font-family: 'Syne', sans-serif;
    letter-spacing: .08em;
  }
  .pay-method-btn .method-icon { font-size: 1.3rem; display: block; margin-bottom: .3rem; }
  .pay-method-btn.active {
    border-color: var(--gold-dim);
    background: rgba(212,168,83,.08);
    color: var(--gold);
  }

  /* ── Stripe fields ── */
  .stripe-field-group { display: flex; flex-direction: column; gap: .75rem; }
  .stripe-row { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; }

  .stripe-field-wrap { display: flex; flex-direction: column; gap: .4rem; }
  .stripe-label {
    font-size: .65rem;
    letter-spacing: .18em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .stripe-input-box {
    padding: .85rem 1rem;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: border-color .2s;
  }
  .stripe-input-box.focused { border-color: var(--gold-dim); }

  /* ── Installments ── */
  .installments-row { display: flex; gap: .5rem; flex-wrap: wrap; }
  .installment-btn {
    padding: .4rem .9rem;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--card);
    color: var(--muted);
    font-size: .75rem;
    font-family: 'DM Mono', monospace;
    cursor: pointer;
    transition: all .2s;
  }
  .installment-btn.active { border-color: var(--gold-dim); color: var(--gold); background: rgba(212,168,83,.08); }

  /* ── Submit ── */
  .pay-submit {
    padding: 1rem;
    background: var(--gold);
    color: var(--bg);
    border: none;
    border-radius: var(--radius);
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: .9rem;
    letter-spacing: .1em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all .25s;
    position: relative;
    overflow: hidden;
  }
  .pay-submit:hover:not(:disabled) { background: #e0b96a; }
  .pay-submit:disabled { opacity: .4; cursor: not-allowed; }

  /* ── Security badge ── */
  .security-badge {
    display: flex;
    align-items: center;
    gap: .5rem;
    font-size: .72rem;
    color: var(--muted);
    padding: .75rem;
    background: var(--card);
    border-radius: var(--radius);
    border: 1px solid var(--border);
  }

  /* ── States ── */
  .alert {
    padding: .85rem 1rem;
    border-radius: var(--radius);
    font-size: .85rem;
    border-left: 3px solid;
  }
  .alert-error   { background: rgba(140,74,74,.12);  color: #c47a7a; border-color: var(--error);   }
  .alert-success { background: rgba(74,140,92,.12);  color: #7ac494; border-color: var(--success); }

  /* ── Success screen ── */
  .success-screen {
    min-height: 100vh;
    background: var(--bg);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1.5rem;
    text-align: center;
    padding: 2rem;
  }
  .success-icon {
    width: 80px; height: 80px;
    border-radius: 50%;
    background: rgba(74,140,92,.15);
    border: 2px solid var(--success);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
  }
  .success-title {
    font-family: 'Instrument Serif', serif;
    font-size: 2.5rem;
    color: var(--text);
  }
  .success-ref {
    font-family: 'DM Mono', monospace;
    font-size: .8rem;
    color: var(--muted);
    background: var(--card);
    padding: .5rem 1rem;
    border-radius: 20px;
    border: 1px solid var(--border);
  }
  .btn-back {
    padding: .75rem 2rem;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: var(--radius);
    font-family: 'Syne', sans-serif;
    font-size: .85rem;
    cursor: pointer;
    transition: all .2s;
  }
  .btn-back:hover { border-color: var(--gold-dim); color: var(--gold); }

  /* ── Spinner ── */
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner {
    width: 14px; height: 14px;
    border: 2px solid rgba(10,10,8,.3);
    border-top-color: var(--bg);
    border-radius: 50%;
    animation: spin .6s linear infinite;
    display: inline-block;
    vertical-align: middle;
    margin-right: .5rem;
  }

  @media (max-width: 768px) {
    .pay-root { grid-template-columns: 1fr; }
    .pay-summary { display: none; }
  }
`;

// ─── STRIPE ELEMENT OPTIONS ────────────────────────────────────────────────
const stripeStyle = {
  style: {
    base: {
      color: "#e8e4dc",
      fontFamily: "'DM Mono', monospace",
      fontSize: "14px",
      "::placeholder": { color: "#3a3a36" },
    },
    invalid: { color: "#c47a7a" },
  },
};

// ─── ORDER SUMMARY ────────────────────────────────────────────────────────────
const OrderSummary = ({ order }) => {
  if (!order) return (
    <div className="pay-summary">
      <div className="pay-brand">Olist</div>
      <p style={{ color: "var(--muted)", fontSize: ".85rem" }}>Chargement…</p>
    </div>
  );

  const total = order.total || 0;
  return (
    <div className="pay-summary">
      <div className="pay-brand">Olist</div>
      <div>
        <p className="pay-order-title">Récapitulatif · #{String(order.order_id).slice(0, 8)}</p>
        <div className="pay-items">
          {(order.items || []).map((item, i) => (
            <div key={i} className="pay-item">
              <div>
                <div className="pay-item-name">Produit #{String(item.product_id).slice(0, 8)}</div>
                <div className="pay-item-meta">Qté 1 · Livraison R$ {item.freight?.toFixed(2)}</div>
              </div>
              <div className="pay-item-price">R$ {item.price?.toFixed(2)}</div>
            </div>
          ))}
        </div>
      </div>
      <hr className="pay-divider" />
      <div className="pay-total-row">
        <span className="pay-total-label">Total à payer</span>
        <span className="pay-total-value">
          <span className="pay-total-currency">R$</span>
          {total.toFixed(2)}
        </span>
      </div>
    </div>
  );
};

// ─── CARD FORM ────────────────────────────────────────────────────────────────
const CardForm = ({ clientSecret, orderId, amount, onSuccess }) => {
  const stripe   = useStripe();
  const elements = useElements();
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState("");
  const [installments, setInstallments] = useState(1);
  const [focused,      setFocused]      = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setError(""); setLoading(true);

    const { error: stripeErr, paymentIntent } = await stripe.confirmCardPayment(
      clientSecret,
      { payment_method: { card: elements.getElement(CardNumberElement) } }
    );

    if (stripeErr) {
      setError(stripeErr.message);
      setLoading(false);
      return;
    }

    // Confirmer côté Django
    const res = await authFetch("/payments/confirm/", {
      method: "POST",
      body: JSON.stringify({ payment_intent_id: paymentIntent.id, order_id: orderId }),
    });

    setLoading(false);
    if (res.payment_id) onSuccess(res);
    else setError(res.error || "Erreur de confirmation.");
  };

  const wrapProps = (name) => ({
    className: `stripe-input-box${focused === name ? " focused" : ""}`,
  });

  return (
    <form onSubmit={submit}>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="stripe-field-group">
        <div className="stripe-field-wrap">
          <label className="stripe-label">Numéro de carte</label>
          <div {...wrapProps("number")}>
            <CardNumberElement
              options={stripeStyle}
              onFocus={() => setFocused("number")}
              onBlur={() => setFocused("")}
            />
          </div>
        </div>
        <div className="stripe-row">
          <div className="stripe-field-wrap">
            <label className="stripe-label">Expiration</label>
            <div {...wrapProps("expiry")}>
              <CardExpiryElement
                options={stripeStyle}
                onFocus={() => setFocused("expiry")}
                onBlur={() => setFocused("")}
              />
            </div>
          </div>
          <div className="stripe-field-wrap">
            <label className="stripe-label">CVC</label>
            <div {...wrapProps("cvc")}>
              <CardCvcElement
                options={stripeStyle}
                onFocus={() => setFocused("cvc")}
                onBlur={() => setFocused("")}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Installments */}
      <div>
        <p className="stripe-label" style={{ marginBottom: ".6rem" }}>Paiement en</p>
        <div className="installments-row">
          {[1, 2, 3, 6, 12].map((n) => (
            <button key={n} type="button"
                    className={`installment-btn ${installments === n ? "active" : ""}`}
                    onClick={() => setInstallments(n)}>
              {n === 1 ? "1× comptant" : `${n}× R$ ${(amount / n).toFixed(2)}`}
            </button>
          ))}
        </div>
      </div>

      <button className="pay-submit" type="submit" disabled={!stripe || loading}>
        {loading && <span className="spinner" />}
        {loading ? "Traitement…" : `Payer R$ ${amount?.toFixed(2)}`}
      </button>

      <div className="security-badge">
        🔒 Paiement sécurisé par Stripe · Vos données ne transitent pas par nos serveurs
      </div>
    </form>
  );
};

// ─── PAYMENT METHODS TABS ─────────────────────────────────────────────────────
const METHODS = [
  { key: "credit_card", icon: "💳", label: "Carte" },
  { key: "boleto",      icon: "📄", label: "Boleto" },
  { key: "pix",         icon: "⚡", label: "PIX" },
];

// ─── MAIN PAYMENT PAGE ────────────────────────────────────────────────────────
export default function PaymentView({ orderId, onBack }) {
  const [order,        setOrder]        = useState(null);
  const [method,       setMethod]       = useState("credit_card");
  const [clientSecret, setClientSecret] = useState(null);
  const [amount,       setAmount]       = useState(0);
  const [success,      setSuccess]      = useState(null);
  const [initError,    setInitError]    = useState("");

  // Charger les détails de la commande
  useEffect(() => {
    if (!orderId) return;
    authFetch(`/orders/`)
      .then((orders) => {
        const o = orders.find((x) => x.order_id === orderId);
        if (o) setOrder(o);
      })
      .catch(() => setInitError("Impossible de charger la commande."));
  }, [orderId]);

  // Créer le PaymentIntent dès que la commande est chargée
  useEffect(() => {
    if (!order) return;
    authFetch("/payments/create-intent/", {
      method: "POST",
      body: JSON.stringify({ order_id: order.order_id, payment_type: method }),
    }).then((res) => {
      if (res.client_secret) {
        setClientSecret(res.client_secret);
        setAmount(res.amount);
      } else {
        setInitError(res.error || "Impossible d'initialiser le paiement.");
      }
    });
  }, [order, method]);

  if (success) {
    return (
      <>
        <style>{S}</style>
        <div className="success-screen">
          <div className="success-icon">✓</div>
          <h1 className="success-title">Paiement confirmé</h1>
          <div className="success-ref">Réf. paiement : {String(success.payment_id).slice(0, 8).toUpperCase()}</div>
          <p style={{ color: "var(--muted)", fontSize: ".85rem" }}>
            Votre commande est maintenant <strong style={{ color: "var(--gold)" }}>approuvée</strong>.
            Un email de confirmation vous sera envoyé.
          </p>
          <button className="btn-back" onClick={onBack}>← Retour aux commandes</button>
        </div>
      </>
    );
  }

  return (
    <>
      <style>{S}</style>
      <div className="pay-root">
        <OrderSummary order={order} />

        <div className="pay-form-panel">
          <div>
            <h1 className="pay-form-title">Paiement</h1>
            <p className="pay-form-subtitle">Choisissez votre méthode de paiement</p>
          </div>

          {initError && <div className="alert alert-error">{initError}</div>}

          {/* Sélecteur de méthode */}
          <div className="pay-methods">
            {METHODS.map((m) => (
              <button key={m.key}
                      className={`pay-method-btn ${method === m.key ? "active" : ""}`}
                      onClick={() => setMethod(m.key)}>
                <span className="method-icon">{m.icon}</span>
                {m.label}
              </button>
            ))}
          </div>

          {/* Formulaire selon la méthode */}
          {method === "credit_card" && clientSecret && (
            <Elements stripe={stripePromise}>
              <CardForm
                clientSecret={clientSecret}
                orderId={order?.order_id}
                amount={amount}
                onSuccess={setSuccess}
              />
            </Elements>
          )}

          {method === "boleto" && (
            <div className="alert" style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--muted)" }}>
              📄 Le Boleto sera généré après confirmation. Délai de paiement : <strong>3 jours ouvrés</strong>.
              <br /><br />
              <button className="pay-submit" style={{ marginTop: ".5rem" }}
                      onClick={() => alert("Intégration Boleto Stripe à configurer")}>
                Générer le Boleto
              </button>
            </div>
          )}

          {method === "pix" && (
            <div className="alert" style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--muted)" }}>
              ⚡ Le QR Code PIX sera généré instantanément. Valable <strong>30 minutes</strong>.
              <br /><br />
              <button className="pay-submit" style={{ marginTop: ".5rem" }}
                      onClick={() => alert("Intégration PIX Stripe à configurer")}>
                Générer le QR PIX
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
