"""
🎱 4D Lucky Number Generator
Singapore Pools 4D — Statistical + Lucky Feel Picks
Built with ❤️ for family  |  Sharing is caring 🍀
"""

import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
from itertools import permutations
from scipy.stats import chisquare
from datetime import datetime
import os
import io
import tempfile

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎱 4D Lucky Generator",
    page_icon="🎱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — red-gold lottery aesthetic ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Cinzel:wght@700&family=Inter:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.main-title {
    font-family: 'Cinzel', serif;
    font-size: 2.6rem;
    font-weight: 700;
    text-align: center;
    background: linear-gradient(135deg, #c0392b, #f39c12, #f1c40f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
    letter-spacing: 2px;
}

.sub-title {
    text-align: center;
    color: #888;
    font-size: 0.95rem;
    margin-bottom: 2rem;
    letter-spacing: 1px;
}

.ball {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    font-family: 'Cinzel', serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: white;
    margin: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    border: 2px solid rgba(255,255,255,0.3);
}

.ball-red    { background: radial-gradient(circle at 35% 35%, #e74c3c, #922b21); }
.ball-gold   { background: radial-gradient(circle at 35% 35%, #f39c12, #9a6007); color: #1a1a1a; }
.ball-blue   { background: radial-gradient(circle at 35% 35%, #2980b9, #1a5276); }
.ball-green  { background: radial-gradient(circle at 35% 35%, #27ae60, #1a6b3c); }
.ball-purple { background: radial-gradient(circle at 35% 35%, #8e44ad, #5b2c6f); }

.pick-card {
    background: linear-gradient(145deg, #1a1a2e, #16213e);
    border: 1px solid rgba(255,215,0,0.2);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.pick-header {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
}

.tag-pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    margin-left: 8px;
    background: rgba(255,215,0,0.15);
    color: #f1c40f;
    border: 1px solid rgba(255,215,0,0.3);
}

.tag-never {
    background: rgba(52,152,219,0.15);
    color: #85c1e9;
    border: 1px solid rgba(52,152,219,0.3);
}

.stat-box {
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    padding: 12px 16px;
    border: 1px solid rgba(255,255,255,0.08);
    text-align: center;
}

.lucky-reason {
    font-size: 0.78rem;
    color: #aaa;
    font-style: italic;
    margin-top: 4px;
}

.disclaimer {
    background: rgba(231,76,60,0.08);
    border-left: 3px solid #c0392b;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 0.85rem;
    color: #bbb;
    margin-top: 1rem;
}

.prize-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 8px 0;
}

.prize-item {
    background: rgba(255,215,0,0.08);
    border: 1px solid rgba(255,215,0,0.2);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.85rem;
    color: #f1c40f;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CORE LOGIC — same as notebook, extracted as functions
# ══════════════════════════════════════════════════════════════════════════════

PRIZE_COLS       = ['first_prize', 'second_prize', 'third_prize']
STARTER_COLS     = [f'starter_{i}'     for i in range(1, 11)]
CONSOLATION_COLS = [f'consolation_{i}' for i in range(1, 11)]
ALL_PRIZE_COLS   = PRIZE_COLS + STARTER_COLS + CONSOLATION_COLS


@st.cache_data(show_spinner=False)
def load_db(db_bytes: bytes) -> pd.DataFrame:
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        f.write(db_bytes)
        tmp_path = f.name
    conn = sqlite3.connect(tmp_path)
    df = pd.read_sql('SELECT * FROM draws ORDER BY draw_number ASC', conn)
    conn.close()
    os.unlink(tmp_path)
    df['draw_date'] = pd.to_datetime(df['draw_date'], format='%a, %d %b %Y', errors='coerce')
    return df


@st.cache_data(show_spinner=False)
def compute_stats(_df_bytes):
    """Compute all counters and weights from DB. Cached so it only runs once per upload."""
    df = pd.read_pickle(io.BytesIO(_df_bytes))

    all_prize_nums = []
    for col in ALL_PRIZE_COLS:
        all_prize_nums.extend(df[col].dropna().tolist())

    win_counter   = Counter(all_prize_nums)
    first_counter = Counter(df['first_prize'].dropna().tolist())

    recent_df   = df.tail(100)
    recent_nums = []
    for col in ALL_PRIZE_COLS:
        recent_nums.extend(recent_df[col].dropna().tolist())
    recent_counter = Counter(recent_nums)

    last_seen_draw = {}
    for _, row in df.iterrows():
        dn = row['draw_number']
        for col in ALL_PRIZE_COLS:
            val = row[col]
            if pd.notna(val):
                last_seen_draw[val] = dn

    latest_draw = df['draw_number'].max()
    all_possible = [f'{n:04d}' for n in range(10000)]

    num_df = pd.DataFrame({
        'number'          : all_possible,
        'all_time_wins'   : [win_counter.get(n, 0) for n in all_possible],
        'first_prize_wins': [first_counter.get(n, 0) for n in all_possible],
        'recent_100_wins' : [recent_counter.get(n, 0) for n in all_possible],
        'draws_since_seen': [latest_draw - last_seen_draw.get(n, 0) for n in all_possible],
    })

    pos_weights = {}
    for pos in range(4):
        digits = [n[pos] for n in all_prize_nums if len(str(n)) == 4]
        counts = Counter(digits)
        y = np.array([counts.get(str(d), 0) for d in range(10)], dtype=float)
        pos_weights[pos] = y / y.sum()

    hot_numbers     = num_df.nlargest(100, 'recent_100_wins')['number'].tolist()
    overdue_numbers = num_df.nlargest(100, 'draws_since_seen')['number'].tolist()

    return {
        'win_counter'    : win_counter,
        'first_counter'  : first_counter,
        'recent_counter' : recent_counter,
        'pos_weights'    : pos_weights,
        'hot_numbers'    : hot_numbers,
        'overdue_numbers': overdue_numbers,
        'num_df'         : num_df,
        'all_prize_nums' : all_prize_nums,
        'total_draws'    : len(df),
        'date_min'       : str(df['draw_date'].min().date()),
        'date_max'       : str(df['draw_date'].max().date()),
    }


def derive_lucky_numbers(events):
    derived = []
    for raw_num, desc in events:
        n = str(raw_num).zfill(4)[:4]
        digits = list(n)

        derived.append((n, f'Exact — {desc}'))

        rev = n[::-1]
        if rev != n:
            derived.append((rev, f'Reverse of {n} — {desc}'))

        perms = set(''.join(p) for p in permutations(digits))
        perms.discard(n); perms.discard(rev)
        for p in sorted(perms)[:4]:
            derived.append((p, f'Permutation of {n} — {desc}'))

        rot_l = digits[1:] + [digits[0]]
        derived.append((''.join(rot_l), f'Rotate-left {n} — {desc}'))

        rot_r = [digits[-1]] + digits[:-1]
        derived.append((''.join(rot_r), f'Rotate-right {n} — {desc}'))

        mirror = digits[:2] + digits[:2][::-1]
        derived.append((''.join(mirror), f'Mirror {n} — {desc}'))

        dsum = sum(int(d) for d in digits)
        echo = str(dsum % 10) * 4
        derived.append((echo, f'Digit-sum echo ({dsum}→{dsum%10}×4) — {desc}'))

    seen, unique = set(), []
    for num, reason in derived:
        if num not in seen and len(num) == 4 and num.isdigit():
            seen.add(num)
            unique.append((num, reason))
    return unique


def gen_pure_random(n):
    picks = set()
    while len(picks) < n:
        picks.add(f'{np.random.randint(0, 10000):04d}')
    return sorted(picks)


def gen_stat_weighted(n, weights):
    picks = set()
    while len(picks) < n:
        digits = ''.join(str(np.random.choice(10, p=weights[pos])) for pos in range(4))
        picks.add(digits)
    return sorted(picks)


def gen_from_pool(pool, n):
    if not pool:
        return []
    size = min(n, len(pool))
    idx  = np.random.choice(len(pool), size, replace=False)
    return [pool[i] for i in sorted(idx)]


def gen_from_lucky(derived, n):
    if not derived:
        return []
    exact = [x for x in derived if 'Exact' in x[1]]
    rest  = [x for x in derived if 'Exact' not in x[1]]
    return (exact + rest)[:n]


def digit_freq_chart(all_prize_nums):
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.5))
    fig.patch.set_facecolor('#0e1117')
    pos_names = ['Thousands', 'Hundreds', 'Tens', 'Units']

    for pos in range(4):
        digits  = [n[pos] for n in all_prize_nums if len(str(n)) == 4]
        counts  = Counter(digits)
        y       = np.array([counts.get(str(d), 0) for d in range(10)])
        expected = y.sum() / 10
        chi2, p  = chisquare(y)
        colors   = ['#e74c3c' if abs(v-expected)/expected > 0.015 else '#3498db' for v in y]

        ax = axes[pos]
        ax.set_facecolor('#1a1a2e')
        ax.bar(range(10), y, color=colors, edgecolor='#0e1117', linewidth=0.8)
        ax.axhline(expected, color='#f1c40f', linestyle='--', linewidth=1.2, alpha=0.7)
        ax.set_xticks(range(10))
        ax.set_xticklabels([str(d) for d in range(10)], color='#ccc', fontsize=9)
        ax.tick_params(colors='#888', labelsize=8)
        status = '⚠️ Skewed' if p < 0.05 else '✅ Uniform'
        ax.set_title(f'{pos_names[pos]}\n{status}  p={p:.3f}',
                     color='white', fontsize=9, fontweight='bold')
        for spine in ax.spines.values():
            spine.set_edgecolor('#333')

    plt.suptitle('Digit Frequency per Position — All Historical Draws',
                 color='white', fontsize=11, fontweight='bold')
    plt.tight_layout()
    return fig


def hotmap_chart(recent_counter, win_counter, lucky_events):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#0e1117')

    for ax, counter, title, cmap in [
        (axes[0], recent_counter, '🔥 Hot Zone — Last 100 Draws', 'hot'),
        (axes[1], win_counter,    '📊 All-Time Frequency',          'Blues'),
    ]:
        grid = np.zeros((100, 100))
        for num, count in counter.items():
            if len(num) == 4 and num.isdigit():
                grid[int(num[:2]), int(num[2:])] = count
        ax.set_facecolor('#0e1117')
        im = ax.imshow(grid, cmap=cmap, aspect='auto')
        plt.colorbar(im, ax=ax, label='Times appeared')
        ax.set_xlabel('Last 2 digits (00–99)', color='#aaa', fontsize=8)
        ax.set_ylabel('First 2 digits (00–99)', color='#aaa', fontsize=8)
        ax.set_title(title, color='white', fontsize=10, fontweight='bold')
        ax.tick_params(colors='#888', labelsize=7)

    # Plot lucky numbers on left chart
    for raw_num, desc in lucky_events:
        n = str(raw_num).zfill(4)[:4]
        if n.isdigit():
            axes[0].plot(int(n[2:]), int(n[:2]), 'c*', markersize=14,
                        label=n, zorder=5)
    if lucky_events:
        axes[0].legend(title='Your lucky #s', fontsize=7, title_fontsize=7,
                       facecolor='#1a1a2e', labelcolor='white')

    plt.tight_layout()
    return fig


def render_ball(num, style='red'):
    return f'<span class="ball ball-{style}">{num}</span>'


def render_pick_card(title, emoji, numbers, win_counter, recent_counter,
                     style='red', lucky_mode=False):
    html = f'<div class="pick-card">'
    html += f'<div class="pick-header">{emoji} {title}</div>'

    items = numbers if lucky_mode else [(n, '') for n in numbers]
    for num, reason in items:
        hist   = win_counter.get(num, 0)
        recent = recent_counter.get(num, 0)

        tag = ''
        if hist == 0:
            tag = '<span class="tag-pill tag-never">never won</span>'
        elif recent > 0:
            tag = f'<span class="tag-pill">🔥 {recent}× recent</span>'

        html += f'<div style="margin:8px 0; display:flex; align-items:center; gap:12px;">'
        html += render_ball(num, style)
        html += f'<div>'
        html += f'<span style="color:#ddd; font-size:0.9rem;">All-time wins: <b>{hist}</b></span>{tag}'
        if reason:
            html += f'<div class="lucky-reason">↳ {reason}</div>'
        html += '</div></div>'

    html += '</div>'
    return html


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### 📂 Upload Your 4D Database")
    uploaded = st.file_uploader(
        "Drop your 4d_results.db here",
        type=['db', 'sqlite', 'sqlite3'],
        help="The database file scraped by scrape_4d.py"
    )

    st.markdown("---")
    st.markdown("### ⚙️ Generation Settings")
    n_random   = st.slider("Pure Random picks",        1, 10, 5)
    n_weighted = st.slider("Stat-Weighted picks",       1, 10, 5)
    n_hot      = st.slider("Hot Number picks",          1, 10, 5)
    n_overdue  = st.slider("Overdue Number picks",      1, 10, 5)
    n_lucky    = st.slider("Lucky-Derived picks",       1, 15, 8)

    st.markdown("---")
    st.markdown("### 💡 How to use")
    st.markdown("""
1. Upload your `4d_results.db`
2. Enter your lucky event numbers below
3. Click **Generate My Picks**
4. Screenshot or download the results
5. Share with your uncles & aunties! 🧧
    """)

    st.markdown("---")
    st.caption("🎱 4D Lucky Generator · Built for family · Sharing is caring")
    st.caption("⚠️ For fun only. All numbers have equal 1/10,000 odds.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown('<div class="main-title">🎱 4D Lucky Number Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Singapore Pools 4D · Statistical + Lucky Feel · Wed · Sat · Sun</div>',
            unsafe_allow_html=True)

# Check DB
if uploaded is None:
    # Try to use bundled DB if present
    bundled = 'data/4d_results.db'
    if os.path.exists(bundled):
        with open(bundled, 'rb') as f:
            db_bytes = f.read()
        st.info("📂 Using bundled `data/4d_results.db`")
    else:
        st.warning("👈 Please upload your `4d_results.db` file in the sidebar to get started.")
        st.stop()
else:
    db_bytes = uploaded.read()

# Load data
with st.spinner("Loading database..."):
    df = load_db(db_bytes)
    df_bytes = io.BytesIO()
    df.to_pickle(df_bytes)
    stats = compute_stats(df_bytes.getvalue())

# Summary strip
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-box"><div style="font-size:1.6rem;font-weight:700;color:#f1c40f">{stats["total_draws"]:,}</div><div style="color:#888;font-size:0.8rem">Total Draws</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="stat-box"><div style="font-size:1.1rem;font-weight:700;color:#f1c40f">{stats["date_min"]}</div><div style="color:#888;font-size:0.8rem">First Draw</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-box"><div style="font-size:1.1rem;font-weight:700;color:#f1c40f">{stats["date_max"]}</div><div style="color:#888;font-size:0.8rem">Latest Draw</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="stat-box"><div style="font-size:1.6rem;font-weight:700;color:#f1c40f">10,000</div><div style="color:#888;font-size:0.8rem">Possible Numbers</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Lucky Events Input ────────────────────────────────────────────────────────
st.markdown("### 🔮 Your Lucky Event Numbers")
st.markdown(
    "Enter any **4-digit numbers** that felt meaningful recently — "
    "car plates at accidents you witnessed, temple fortune numbers, dream numbers, "
    "receipt totals, bus numbers, anything. The app will derive related picks from them."
)

with st.expander("➕ Add Lucky Event Numbers", expanded=True):
    lucky_input_text = st.text_area(
        "One entry per line: `NUMBER, Description`",
        placeholder=(
            "0616, Father's block address at Mandai\n"
            "5570, Ah Gong Ah Ma's new plot number\n"
            "2702, My birthday\n"
            "1234, Car plate of taxi after reunion dinner"
        ),
        height=150,
    )

# Parse lucky events
lucky_events = []
if lucky_input_text.strip():
    for line in lucky_input_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split(',', 1)
        num_str = parts[0].strip().zfill(4)[:4]
        desc    = parts[1].strip() if len(parts) > 1 else 'Lucky number'
        if num_str.isdigit():
            lucky_events.append((num_str, desc))

if lucky_events:
    st.success(f"✅ {len(lucky_events)} lucky event(s) registered")
    for n, d in lucky_events:
        st.markdown(f"&nbsp;&nbsp;🎴 **{n}** — {d}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Generate Button ───────────────────────────────────────────────────────────
col_btn, col_spacer = st.columns([1, 3])
with col_btn:
    generate = st.button("🎱 Generate My Picks", type="primary", use_container_width=True)

if not generate:
    st.markdown("""
    <div class="disclaimer">
    ⚠️ <b>Honest reminder:</b> Every 4D number from 0000 to 9999 has exactly the same 
    1-in-10,000 chance of being drawn as First Prize. This app helps you pick numbers 
    that feel meaningful — it cannot predict which numbers will be drawn. Play responsibly.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Generate all pools ────────────────────────────────────────────────────────
with st.spinner("🎲 Generating your lucky numbers..."):
    lucky_derived  = derive_lucky_numbers(lucky_events)
    pool_random    = gen_pure_random(n_random)
    pool_weighted  = gen_stat_weighted(n_weighted, stats['pos_weights'])
    pool_hot       = gen_from_pool(stats['hot_numbers'],     n_hot)
    pool_overdue   = gen_from_pool(stats['overdue_numbers'], n_overdue)
    pool_lucky     = gen_from_lucky(lucky_derived, n_lucky)

# ── Results ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"### 🏆 Your Weekly 4D Picks — {datetime.now().strftime('%A, %d %B %Y')}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔮 Lucky", "🎲 Random", "📊 Stat-Weighted", "🔥 Hot", "❄️ Overdue", "📈 Analysis"
])

wc = stats['win_counter']
rc = stats['recent_counter']

with tab1:
    if pool_lucky:
        st.markdown(render_pick_card(
            "Lucky Event Derived Numbers", "🔮",
            pool_lucky, wc, rc, style='gold', lucky_mode=True
        ), unsafe_allow_html=True)
    else:
        st.info("No lucky events entered. Add some in the Lucky Events section above.")

with tab2:
    st.markdown(render_pick_card(
        "Pure Random — Every number equally likely", "🎲",
        pool_random, wc, rc, style='blue'
    ), unsafe_allow_html=True)

with tab3:
    st.markdown(render_pick_card(
        "Statistically Weighted — Biased toward historically frequent digits", "📊",
        pool_weighted, wc, rc, style='green'
    ), unsafe_allow_html=True)

with tab4:
    st.markdown(render_pick_card(
        "Hot Numbers — Appeared most in last 100 draws", "🔥",
        pool_hot, wc, rc, style='red'
    ), unsafe_allow_html=True)

with tab5:
    st.markdown(render_pick_card(
        "Overdue Numbers — Longest cold streak", "❄️",
        pool_overdue, wc, rc, style='purple'
    ), unsafe_allow_html=True)

with tab6:
    st.markdown("#### Digit Frequency per Position")
    st.pyplot(digit_freq_chart(stats['all_prize_nums']))

    st.markdown("#### Number Space Heatmap")
    st.pyplot(hotmap_chart(stats['recent_counter'], stats['win_counter'], lucky_events))

    st.markdown("#### Most Overdue Numbers")
    st.dataframe(
        stats['num_df'].nlargest(20, 'draws_since_seen')[
            ['number','draws_since_seen','all_time_wins','recent_100_wins']
        ].rename(columns={
            'number'          : 'Number',
            'draws_since_seen': 'Draws Since Last Seen',
            'all_time_wins'   : 'All-Time Wins',
            'recent_100_wins' : 'Recent 100 Draws',
        }),
        use_container_width=True, hide_index=True
    )

# ── Prize table ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 💰 Prize Structure (Ordinary $1 bet)")
st.markdown("""
<div class="prize-row">
  <div class="prize-item">1st Prize — $2,000</div>
  <div class="prize-item">2nd Prize — $1,000</div>
  <div class="prize-item">3rd Prize — $490</div>
  <div class="prize-item">Starter — $250</div>
  <div class="prize-item">Consolation — $60</div>
</div>
""", unsafe_allow_html=True)

# ── Download CSV ──────────────────────────────────────────────────────────────
st.markdown("---")
os.makedirs('output', exist_ok=True)

all_rows = []
for n in pool_random:
    all_rows.append({'number': n, 'method': 'pure_random',    'reason': ''})
for n in pool_weighted:
    all_rows.append({'number': n, 'method': 'stat_weighted',  'reason': ''})
for n in pool_hot:
    all_rows.append({'number': n, 'method': 'hot',            'reason': ''})
for n in pool_overdue:
    all_rows.append({'number': n, 'method': 'overdue',        'reason': ''})
for n, r in pool_lucky:
    all_rows.append({'number': n, 'method': 'lucky_derived',  'reason': r})

out_df   = pd.DataFrame(all_rows)
csv_str  = out_df.to_csv(index=False)
filename = f'4d_picks_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'

# Also save locally to output folder
out_df.to_csv(f'output/{filename}', index=False)

st.download_button(
    label="💾 Download Picks as CSV",
    data=csv_str,
    file_name=filename,
    mime='text/csv',
    use_container_width=False,
)

st.markdown("""
<div class="disclaimer">
⚠️ <b>Responsible gambling reminder:</b> 4D is a game of chance. No system can improve your 
odds of winning. Set a budget you are comfortable with and stick to it. 
If gambling becomes a problem, call the <b>National Problem Gambling Helpline: 1800-6-668-668</b>.
</div>
""", unsafe_allow_html=True)
