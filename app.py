"""
============================================================
  KBO 승부 예측 Streamlit 앱 v3
============================================================
팀 로고 처리:
  1순위: logos/ 폴더의 로컬 이미지 파일 (가장 안전)
  2순위: 이모지 폴백

사용법:
  1. KBO 공식 사이트에서 팀 로고 다운로드
  2. logos/ 폴더에 파일명으로 저장:
     kia.png, kt.png, lg.png, nc.png, ssg.png,
     doosan.png, lotte.png, samsung.png, kiwoom.png, hanwha.png
  3. python -m streamlit run app.py
============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from kbo_predictor import predict_with_defaults, get_feature_info, load_model

st.set_page_config(
    page_title="KBO 승부 예측",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 커스텀 CSS - 팀 선택 버튼을 카드 전체로
# ============================================================
st.markdown("""
<style>
/* 팀 선택 버튼 (secondary) - 카드 전체가 버튼 */
div[data-testid="stButton"] > button[kind="secondary"] {
    background-color: #FFFFFF;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    padding: 12px 4px 16px;
    height: 150px;
    min-height: 150px;
    font-weight: 500;
    color: #374151;
    font-size: 14px;
    transition: all 0.2s ease;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    white-space: normal;
    line-height: 1.3;
}

/* Hover: 노란색 하이라이트 */
div[data-testid="stButton"] > button[kind="secondary"]:hover {
    background-color: #FFFBEB;
    border-color: #FCD34D;
    color: #92400E;
}

/* 선택된 상태 (primary) - 노란색 강조 */
div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #FEF3C7;
    border: 3px solid #F59E0B;
    border-radius: 12px;
    padding: 12px 4px 16px;
    height: 150px;
    min-height: 150px;
    color: #92400E;
    font-weight: 700;
    font-size: 14px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    white-space: normal;
    line-height: 1.3;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #FDE68A;
    border-color: #D97706;
    color: #78350F;
}

/* 예측 시작 같은 form submit 버튼은 카드 스타일 제외 (우선순위 높게) */
div[data-testid="stFormSubmitButton"] button {
    background-color: #E85D04 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    height: auto !important;
    min-height: 44px !important;
    padding: 12px 24px !important;
    font-size: 16px !important;
    display: block !important;
}
div[data-testid="stFormSubmitButton"] button:hover {
    background-color: #C94D00 !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 팀 정보
# ============================================================
TEAM_INFO = {
    "KIA":  {"name": "KIA 타이거즈", "emoji": "🐯", "color": "#EA0029", "file": "kia"},
    "KT":   {"name": "KT 위즈", "emoji": "🧙", "color": "#222222", "file": "kt"},
    "LG":   {"name": "LG 트윈스", "emoji": "🦁", "color": "#C30452", "file": "lg"},
    "NC":   {"name": "NC 다이노스", "emoji": "🦖", "color": "#315288", "file": "nc"},
    "SSG":  {"name": "SSG 랜더스", "emoji": "⚓", "color": "#CE0E2D", "file": "ssg"},
    "두산": {"name": "두산 베어스", "emoji": "🐻", "color": "#131230", "file": "doosan"},
    "롯데": {"name": "롯데 자이언츠", "emoji": "🌊", "color": "#041E42", "file": "lotte"},
    "삼성": {"name": "삼성 라이온즈", "emoji": "🦁", "color": "#074CA1", "file": "samsung"},
    "키움": {"name": "키움 히어로즈", "emoji": "🦸", "color": "#820024", "file": "kiwoom"},
    "한화": {"name": "한화 이글스", "emoji": "🦅", "color": "#FF6600", "file": "hanwha"},
}

TEAMS = list(TEAM_INFO.keys())


def ti(team, key):
    return TEAM_INFO.get(team, {}).get(key, "")


def get_team_logo(team):
    """logos/ 폴더에서 로고 파일 탐색."""
    file = ti(team, "file")
    for ext in ["png", "jpg", "jpeg", "svg", "gif"]:
        path = f"logos/{file}.{ext}"
        if os.path.exists(path):
            return path
    return None


def render_team_logo(team, width=120):
    """팀 로고 표시 (로컬 파일 → 이모지 폴백)."""
    logo_path = get_team_logo(team)
    if logo_path:
        try:
            st.image(logo_path, width=width)
            return
        except Exception:
            pass
    st.markdown(
        f"<div style='font-size:{int(width*0.7)}px; text-align:center; "
        f"line-height:1.2;'>{ti(team, 'emoji')}</div>",
        unsafe_allow_html=True
    )


# ============================================================
# 로고 inline 표시 (텍스트와 함께)
# ============================================================
def get_logo_base64(team):
    """팀 로고를 base64 data URI로 반환 (inline 표시용)."""
    logo_path = get_team_logo(team)
    if not logo_path:
        return None
    try:
        import base64
        with open(logo_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        ext = logo_path.split(".")[-1].lower()
        mime = f"image/{'svg+xml' if ext == 'svg' else ext}"
        return f"data:{mime};base64,{img_data}"
    except Exception:
        return None


def team_inline(team, size=20, show_name=True):
    """이모지 대신 inline 로고 + 팀명 HTML 반환."""
    logo_src = get_logo_base64(team)
    if logo_src:
        img_html = (
            f"<img src='{logo_src}' style='width:{size}px; height:{size}px; "
            f"object-fit:contain; vertical-align:middle;'/>"
        )
    else:
        img_html = f"<span style='font-size:{size}px;'>{ti(team, 'emoji')}</span>"
    
    if show_name:
        return f"{img_html} <span style='vertical-align:middle;'>{team}</span>"
    return img_html


# ============================================================
# 데이터 로드
# ============================================================
@st.cache_data
def load_team_stats(year="2025"):
    stats = {}
    p_path = f"kbo_data/kbo_{year}_pitcher_full.csv"
    if os.path.exists(p_path):
        p = pd.read_csv(p_path)
        p["ERA"] = pd.to_numeric(p["ERA"], errors="coerce")
        
        def parse_ip(s):
            try:
                s = str(s).strip()
                if not s:
                    return 0
                parts = s.split()
                try:
                    return float(parts[0])
                except (ValueError, IndexError):
                    return 0
            except Exception:
                return 0
        
        if "IP" in p.columns:
            p["IP_num"] = p["IP"].apply(parse_ip)
        else:
            p["IP_num"] = 0
        p = p.dropna(subset=["ERA"])
        
        for team, group in p.groupby("팀명"):
            sorted_g = group.sort_values("IP_num", ascending=False)
            starters = sorted_g.head(5)
            bullpen = sorted_g.iloc[5:]
            stats[team] = {
                "ERA": round(group["ERA"].mean(), 2),
                "starter_era": round(starters["ERA"].mean(), 2) if len(starters) else 4.0,
                "bullpen_era": round(bullpen["ERA"].mean(), 2) if len(bullpen) else 5.0,
                "ace_era": round(sorted_g.iloc[0]["ERA"], 2) if len(sorted_g) else 3.5,
                "pitcher_depth": len(group),
                "ace_name": sorted_g.iloc[0]["선수명"] if len(sorted_g) else "-",
            }
    
    h_path = f"kbo_data/kbo_{year}_hitter_full.csv"
    if os.path.exists(h_path):
        h = pd.read_csv(h_path)
        h["OPS"] = pd.to_numeric(h["OPS"], errors="coerce")
        h["HR"] = pd.to_numeric(h["HR"], errors="coerce")
        h = h.dropna(subset=["OPS"])
        
        for team, group in h.groupby("팀명"):
            sorted_g = group.sort_values("OPS", ascending=False)
            top5 = sorted_g.head(5)
            stats.setdefault(team, {}).update({
                "OPS": round(group["OPS"].mean(), 3),
                "top5_ops": round(top5["OPS"].mean(), 3) if len(top5) else 0.85,
                "hr_power": int(group["HR"].sum()) if "HR" in group.columns else 100,
                "hitter_depth": int((group["OPS"] >= 0.7).sum()),
                "top_hitter": sorted_g.iloc[0]["선수명"] if len(sorted_g) else "-",
            })
    return stats


@st.cache_data
def load_all_schedule():
    dfs = []
    for year in ["2024", "2025", "2026"]:
        path = f"kbo_data/kbo_schedule_{year}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            df = df[df["status"] == "종료"].copy()
            df = df[df["home_win"].isin([0, 1])]
            df["game_date"] = pd.to_datetime(df["game_date"])
            df["season"] = int(year)
            dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True).sort_values("game_date")
    return pd.DataFrame()


@st.cache_resource
def get_model_info():
    return get_feature_info()


# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.header("⚾ KBO 승부 예측")
    st.markdown("---")
    
    st.subheader("📊 모델 정보")
    info = get_model_info()
    st.write(f"**버전:** {info.get('version', 'v3')}")
    st.write(f"**알고리즘:** {info['model_name']}")
    st.write(f"**피처 수:** {len(info['features'])}개")
    
    st.markdown("---")
    st.subheader("🎯 성능 지표")
    st.metric("검증셋 정확도", "58.6%")
    st.metric("AUC", "0.602")
    
    st.markdown("---")
    
    # 로고 상태 체크
    logos_ok = sum(1 for t in TEAMS if get_team_logo(t))
    if logos_ok == 10:
        st.success(f"✅ 로고 {logos_ok}/10 로드 완료")
    elif logos_ok > 0:
        st.warning(f"⚠️ 로고 {logos_ok}/10 로드됨")
        with st.expander("누락된 로고 보기"):
            for t in TEAMS:
                if not get_team_logo(t):
                    st.caption(f"❌ logos/{ti(t, 'file')}.png 필요")
    else:
        st.info("ℹ️ logos/ 폴더에 로고 파일을 추가하면 표시됩니다.\n\nREADME.md의 '로고 설정' 섹션 참고.")
    
    st.markdown("---")
    st.caption("🎓 캡스톤 디자인 프로젝트")
    st.caption("임안호 · 유현성 · 곽건")


# ============================================================
# 메인
# ============================================================
st.title("⚾ KBO 승부 예측 시스템")
st.caption("Random Forest 모델이 분석한 경기 승리 확률 — 검증셋 58.6% 정확도")

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 승부 예측", "📋 팀 스탯", "⚔️ 맞대결 H2H", "ℹ️ 모델 설명"
])

try:
    team_stats = load_team_stats("2026")
except Exception as e:
    st.warning(f"팀 스탯 로드 실패: {e}")
    team_stats = {}

schedule_df = load_all_schedule()


# ============================================================
# TAB 1: 승부 예측
# ============================================================
with tab1:
    st.subheader("1️⃣ 팀 선택")
    
    # 세션 상태 초기화
    if 'home_team' not in st.session_state:
        st.session_state.home_team = "LG"
    if 'away_team' not in st.session_state:
        st.session_state.away_team = "두산"
    
    def render_team_selector(title, state_key, button_prefix):
        """팀 선택: 한 버튼에 로고+팀명 모두 포함"""
        st.markdown(f"##### {title}")
        cols = st.columns(10)
        for idx, team in enumerate(TEAMS):
            with cols[idx]:
                is_selected = st.session_state[state_key] == team
                btn_type = "primary" if is_selected else "secondary"
                
                # 버튼 라벨에 이모지 + 팀명 사용
                # 로고 이미지는 버튼 내부에 직접 렌더링이 어려우므로 
                # 로고를 별도 마크다운으로 위에 표시하되, 같은 컨테이너로 처리
                logo_path = get_team_logo(team)
                
                # 로고를 버튼 위 작은 공간에 표시
                if logo_path:
                    import base64
                    with open(logo_path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    ext = logo_path.split(".")[-1].lower()
                    mime = f"image/{'svg+xml' if ext == 'svg' else ext}"
                    logo_src = f"data:{mime};base64,{img_data}"
                    # 버튼 위에 로고 (absolute positioning으로 버튼 내부처럼 보이게)
                    st.markdown(
                        f"""
                        <div class='logo-overlay-{button_prefix}-{team}' style='
                            position: relative;
                            height: 0;
                            pointer-events: none;
                            z-index: 10;
                        '>
                            <img src='{logo_src}' style='
                                position: absolute;
                                top: 25px;
                                left: 50%;
                                transform: translateX(-50%);
                                width: 75px;
                                height: 75px;
                                object-fit: contain;
                            '/>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                
                # 버튼 (팀명만 라벨로, 로고는 위에서 오버레이)
                # 버튼이 크게 (120px) 뜨니까 로고가 위쪽, 팀명이 아래쪽에 보임
                if st.button(
                    f"\n\n\n\n\n\n\n{team}",  # 공백 증가로 팀명을 더 아래로
                    key=f"{button_prefix}_{team}",
                    width="stretch",
                    type=btn_type,
                ):
                    st.session_state[state_key] = team
                    st.rerun()
    
    render_team_selector("🏠 홈팀 선택", "home_team", "home")
    st.markdown("")
    render_team_selector("✈️ 원정팀 선택", "away_team", "away")
    
    home_team = st.session_state.home_team
    away_team = st.session_state.away_team
    
    if home_team == away_team:
        st.error("⚠️ 홈팀과 원정팀은 달라야 합니다.")
        st.stop()
    
    st.subheader("2️⃣ 팀 스탯 (2026 시즌 기준)")
    home_stat = team_stats.get(home_team, {})
    away_stat = team_stats.get(away_team, {})
    
    col1, col_vs, col2 = st.columns([5, 1, 5])
    
    with col1:
        st.markdown(f"#### 🏠 {ti(home_team, 'name')}")
        render_team_logo(home_team, width=120)
        if home_stat:
            c1, c2 = st.columns(2)
            c1.metric("팀 ERA", home_stat.get("ERA", "-"))
            c2.metric("에이스 ERA", home_stat.get("ace_era", "-"))
            st.caption(f"🏆 에이스: {home_stat.get('ace_name', '-')}")
            c3, c4 = st.columns(2)
            c3.metric("Top5 OPS", home_stat.get("top5_ops", "-"))
            c4.metric("홈런 수", home_stat.get("hr_power", "-"))
        else:
            st.info("리그 평균 사용")
    
    with col_vs:
        st.markdown(
            "<div style='text-align:center; font-size:40px; margin-top:80px; "
            "color: #E85D04; font-weight: bold;'>VS</div>",
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(f"#### ✈️ {ti(away_team, 'name')}")
        render_team_logo(away_team, width=120)
        if away_stat:
            c1, c2 = st.columns(2)
            c1.metric("팀 ERA", away_stat.get("ERA", "-"))
            c2.metric("에이스 ERA", away_stat.get("ace_era", "-"))
            st.caption(f"🏆 에이스: {away_stat.get('ace_name', '-')}")
            c3, c4 = st.columns(2)
            c3.metric("Top5 OPS", away_stat.get("top5_ops", "-"))
            c4.metric("홈런 수", away_stat.get("hr_power", "-"))
        else:
            st.info("리그 평균 사용")
    
    with st.expander("🔧 고급 옵션 (선택)"):
        st.caption("경기 당일 컨디션을 세밀하게 반영합니다.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"**홈: {ti(home_team, 'name')}**",
                unsafe_allow_html=True,
            )
            home_season_wr = st.slider("시즌 승률", 0.0, 1.0, 0.52, 0.01, key="h_s")
            home_last10_wr = st.slider("최근 10경기 승률", 0.0, 1.0, 0.5, 0.1, key="h_l")
            home_streak = st.number_input("연승/연패 (+/-)", -10, 10, 0, key="h_st")
        with col2:
            st.markdown(
                f"**원정: {ti(away_team, 'name')}**",
                unsafe_allow_html=True,
            )
            away_season_wr = st.slider("시즌 승률", 0.0, 1.0, 0.50, 0.01, key="a_s")
            away_last10_wr = st.slider("최근 10경기 승률", 0.0, 1.0, 0.5, 0.1, key="a_l")
            away_streak = st.number_input("연승/연패 (+/-)", -10, 10, 0, key="a_st")
        is_weekend = st.checkbox("주말 경기", value=False)
    
    st.subheader("3️⃣ 예측 실행")
    
    # form으로 감싸서 팀 선택 버튼 CSS와 분리
    with st.form(key="predict_form", border=False):
        predict_clicked = st.form_submit_button(
            "🔮 예측 시작", type="primary", width="stretch"
        )
    
    if predict_clicked:
        with st.spinner("AI가 분석 중..."):
            result = predict_with_defaults(
                home_team=home_team, away_team=away_team,
                home_team_ops=home_stat.get("OPS"),
                away_team_ops=away_stat.get("OPS"),
                home_team_era=home_stat.get("ERA"),
                away_team_era=away_stat.get("ERA"),
                home_starter_era=home_stat.get("starter_era"),
                away_starter_era=away_stat.get("starter_era"),
                home_bullpen_era=home_stat.get("bullpen_era"),
                away_bullpen_era=away_stat.get("bullpen_era"),
                home_ace_era=home_stat.get("ace_era"),
                away_ace_era=away_stat.get("ace_era"),
                home_pitcher_depth=home_stat.get("pitcher_depth"),
                away_pitcher_depth=away_stat.get("pitcher_depth"),
                home_top5_ops=home_stat.get("top5_ops"),
                away_top5_ops=away_stat.get("top5_ops"),
                home_hr_power=home_stat.get("hr_power"),
                away_hr_power=away_stat.get("hr_power"),
                home_hitter_depth=home_stat.get("hitter_depth"),
                away_hitter_depth=away_stat.get("hitter_depth"),
                home_season_wr=home_season_wr, away_season_wr=away_season_wr,
                home_last10_wr=home_last10_wr, away_last10_wr=away_last10_wr,
                home_streak=home_streak, away_streak=away_streak,
                is_weekend=1 if is_weekend else 0,
            )
        
        st.markdown("---")
        st.subheader("📊 예측 결과")
        
        # 메트릭 대신 직접 HTML 카드로 표시 (로고 포함)
        col1, col2, col3 = st.columns(3)
        
        home_logo = get_logo_base64(home_team)
        away_logo = get_logo_base64(away_team)
        winner = home_team if result['predicted'] == '홈승' else away_team
        winner_logo = get_logo_base64(winner)
        
        def metric_card(logo_src, label, value, color="#1F2937"):
            img_html = ""
            if logo_src:
                img_html = (
                    f"<img src='{logo_src}' style='width:40px; height:40px; "
                    f"object-fit:contain; vertical-align:middle; margin-right:8px;'/>"
                )
            return f"""
            <div style='background: white; border: 1px solid #E5E7EB; 
                        border-radius: 12px; padding: 16px; text-align: center;'>
                <div style='color: #6B7280; font-size: 13px; margin-bottom: 8px;'>
                    {img_html}<span style='vertical-align:middle;'>{label}</span>
                </div>
                <div style='font-size: 32px; font-weight: 700; color: {color};'>
                    {value}
                </div>
            </div>
            """
        
        with col1:
            st.markdown(
                metric_card(
                    home_logo,
                    f"🏠 {home_team}",
                    f"{result['home_win_prob']*100:.1f}%",
                    color=ti(home_team, 'color'),
                ),
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                metric_card(
                    away_logo,
                    f"✈️ {away_team}",
                    f"{result['away_win_prob']*100:.1f}%",
                    color=ti(away_team, 'color'),
                ),
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                metric_card(
                    winner_logo,
                    "🏆 예측 승자",
                    winner,
                    color="#E85D04",
                ),
                unsafe_allow_html=True,
            )
        
        st.markdown("")  # 여백
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=[f"✈️ {away_team}"],
            x=[result['away_win_prob'] * 100], orientation='h',
            marker=dict(color=ti(away_team, 'color')),
            text=[f"{result['away_win_prob']*100:.1f}%"],
            textposition='inside', textfont=dict(size=18, color='white'),
            hovertemplate=f"<b>{away_team}</b><br>확률: {result['away_win_prob']*100:.1f}%<extra></extra>",
            name=away_team,
        ))
        fig.add_trace(go.Bar(
            y=[f"🏠 {home_team}"],
            x=[result['home_win_prob'] * 100], orientation='h',
            marker=dict(color=ti(home_team, 'color')),
            text=[f"{result['home_win_prob']*100:.1f}%"],
            textposition='inside', textfont=dict(size=18, color='white'),
            hovertemplate=f"<b>{home_team}</b><br>확률: {result['home_win_prob']*100:.1f}%<extra></extra>",
            name=home_team,
        ))
        fig.update_layout(
            title="승리 확률",
            xaxis=dict(title="승리 확률 (%)", range=[0, 100]),
            height=250, showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        )
        st.plotly_chart(fig, width="stretch")
        
        conf_icon = {"높음": "🟢", "중간": "🟡", "낮음": "🔴"}
        conf_msg = {
            "높음": "모델이 강한 확신을 보입니다.",
            "중간": "모델이 약간의 우위를 예측합니다.",
            "낮음": "박빙의 경기입니다. 결과 예측 어려움.",
        }
        st.info(f"{conf_icon[result['confidence']]} **확신도: {result['confidence']}** — "
                f"{conf_msg[result['confidence']]}")
        st.caption("⚠️ 본 예측은 학술/교육 목적이며, 실제 배팅에는 부적합합니다.")


# ============================================================
# TAB 2: 팀 스탯
# ============================================================
with tab2:
    st.subheader("📋 2026 시즌 팀별 스탯")
    
    if team_stats:
        st.markdown("### 🏟️ 팀 카드")
        cols = st.columns(5)
        for idx, team in enumerate(TEAMS):
            with cols[idx % 5]:
                s = team_stats.get(team, {})
                render_team_logo(team, width=80)
                st.markdown(f"**{ti(team, 'name')}**")
                st.caption(f"ERA: {s.get('ERA', '-')}")
                st.caption(f"OPS: {s.get('OPS', '-')}")
        
        st.markdown("---")
        st.markdown("### 📊 상세 통계")
        stat_df = pd.DataFrame(team_stats).T
        # 팀명에 이모지 빼고 깔끔하게
        stat_df.index.name = "팀"
        stat_df = stat_df.rename(columns={
            "ERA": "팀 ERA", "starter_era": "선발진 ERA",
            "bullpen_era": "불펜 ERA", "ace_era": "에이스 ERA",
            "pitcher_depth": "투수수", "OPS": "팀 OPS",
            "top5_ops": "Top5 OPS", "hr_power": "홈런",
            "hitter_depth": "강타자수", "ace_name": "에이스",
            "top_hitter": "톱타자",
        })
        col_order = [
            "에이스", "에이스 ERA", "선발진 ERA", "불펜 ERA", "팀 ERA", "투수수",
            "톱타자", "Top5 OPS", "팀 OPS", "홈런", "강타자수",
        ]
        col_order = [c for c in col_order if c in stat_df.columns]
        stat_df = stat_df[col_order]
        st.dataframe(stat_df, width="stretch")
        
        st.markdown("---")
        st.markdown("### 📈 팀별 에이스 ERA (낮을수록 좋음)")
        era_df = pd.DataFrame([
            {"team": t, "ace_era": team_stats[t].get("ace_era", 0)}
            for t in TEAMS if t in team_stats
        ]).sort_values("ace_era")
        colors = [ti(t, 'color') for t in era_df['team']]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=era_df['team'].tolist(),
            y=era_df['ace_era'], marker=dict(color=colors),
            text=era_df['ace_era'], textposition='outside',
            hovertemplate="<b>%{x}</b><br>에이스 ERA: %{y:.2f}<extra></extra>",
        ))
        fig.update_layout(height=400, yaxis=dict(title="에이스 ERA"),
                          showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width="stretch")
        
        st.markdown("### 📈 팀별 Top5 OPS (높을수록 좋음)")
        ops_df = pd.DataFrame([
            {"team": t, "top5_ops": team_stats[t].get("top5_ops", 0)}
            for t in TEAMS if t in team_stats
        ]).sort_values("top5_ops", ascending=False)
        colors = [ti(t, 'color') for t in ops_df['team']]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=ops_df['team'].tolist(),
            y=ops_df['top5_ops'], marker=dict(color=colors),
            text=ops_df['top5_ops'].round(3), textposition='outside',
            hovertemplate="<b>%{x}</b><br>Top5 OPS: %{y:.3f}<extra></extra>",
        ))
        fig2.update_layout(height=400, yaxis=dict(title="Top5 OPS"),
                           showlegend=False, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, width="stretch")
    else:
        st.warning("팀 스탯 데이터를 불러올 수 없습니다.")


# ============================================================
# TAB 3: H2H
# ============================================================
with tab3:
    st.subheader("⚔️ 팀 간 맞대결 이력")
    st.caption("2024~2026 시즌 경기 결과 기반")
    
    if schedule_df.empty:
        st.warning("경기 일정 데이터를 불러올 수 없습니다. kbo_data/ 폴더에 kbo_schedule_2024.csv 등 추가 필요.")
    else:
        # 세션 상태 초기화
        if 'h2h_a' not in st.session_state:
            st.session_state.h2h_a = "LG"
        if 'h2h_b' not in st.session_state:
            st.session_state.h2h_b = "두산"
        
        def render_h2h_selector(title, state_key, button_prefix):
            """H2H 팀 선택: 한 버튼에 로고+팀명"""
            st.markdown(f"##### {title}")
            cols = st.columns(10)
            for idx, team in enumerate(TEAMS):
                with cols[idx]:
                    is_selected = st.session_state[state_key] == team
                    btn_type = "primary" if is_selected else "secondary"
                    logo_path = get_team_logo(team)
                    
                    if logo_path:
                        import base64
                        with open(logo_path, "rb") as f:
                            img_data = base64.b64encode(f.read()).decode()
                        ext = logo_path.split(".")[-1].lower()
                        mime = f"image/{'svg+xml' if ext == 'svg' else ext}"
                        logo_src = f"data:{mime};base64,{img_data}"
                        st.markdown(
                            f"""
                            <div style='
                                position: relative;
                                height: 0;
                                pointer-events: none;
                                z-index: 10;
                            '>
                                <img src='{logo_src}' style='
                                    position: absolute;
                                    top: 25px;
                                    left: 50%;
                                    transform: translateX(-50%);
                                    width: 75px;
                                    height: 75px;
                                    object-fit: contain;
                                '/>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    
                    if st.button(
                        f"\n\n\n\n\n{team}",
                        key=f"{button_prefix}_{team}",
                        width="stretch",
                        type=btn_type,
                    ):
                        st.session_state[state_key] = team
                        st.rerun()
        
        render_h2h_selector("팀 A", "h2h_a", "h2h_a_btn")
        st.markdown("")
        render_h2h_selector("팀 B", "h2h_b", "h2h_b_btn")
        
        h2h_a = st.session_state.h2h_a
        h2h_b = st.session_state.h2h_b
        
        if h2h_a == h2h_b:
            st.error("⚠️ 서로 다른 팀을 선택하세요.")
        else:
            mask = (
                ((schedule_df["home_team"] == h2h_a) & (schedule_df["away_team"] == h2h_b)) |
                ((schedule_df["home_team"] == h2h_b) & (schedule_df["away_team"] == h2h_a))
            )
            h2h_games = schedule_df[mask].copy().sort_values("game_date", ascending=False)
            
            if h2h_games.empty:
                st.info("해당 팀 간의 경기 이력이 없습니다.")
            else:
                h2h_games["winner"] = h2h_games.apply(
                    lambda r: r["home_team"] if r["home_win"] == 1 else r["away_team"],
                    axis=1
                )
                a_wins = (h2h_games["winner"] == h2h_a).sum()
                b_wins = (h2h_games["winner"] == h2h_b).sum()
                total = len(h2h_games)
                
                st.markdown("### 📊 전체 전적")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 경기수", f"{total}경기")
                with col2:
                    st.metric(f"{h2h_a} 승",
                              f"{a_wins}승", f"{a_wins/total*100:.1f}%")
                with col3:
                    st.metric(f"{h2h_b} 승",
                              f"{b_wins}승", f"{b_wins/total*100:.1f}%")
                with col4:
                    dominance = h2h_a if a_wins > b_wins else h2h_b
                    st.metric("우위 팀", dominance)
                
                st.markdown("### 🥧 승률 분포")
                pie_fig = go.Figure(data=[go.Pie(
                    labels=[h2h_a, h2h_b],
                    values=[a_wins, b_wins],
                    marker=dict(colors=[ti(h2h_a, 'color'), ti(h2h_b, 'color')]),
                    textinfo='label+percent+value', textfont=dict(size=14),
                    hovertemplate="<b>%{label}</b><br>승리: %{value}<br>비율: %{percent}<extra></extra>",
                )])
                pie_fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(pie_fig, width="stretch")
                
                st.markdown("### 📅 시즌별 전적")
                seasons_list = sorted(h2h_games["season"].unique())
                a_wins_by_season = []
                b_wins_by_season = []
                for season in seasons_list:
                    s_games = h2h_games[h2h_games["season"] == season]
                    a_wins_by_season.append((s_games["winner"] == h2h_a).sum())
                    b_wins_by_season.append((s_games["winner"] == h2h_b).sum())
                
                bar_fig = go.Figure()
                bar_fig.add_trace(go.Bar(
                    x=[str(s) for s in seasons_list], y=a_wins_by_season,
                    name=h2h_a,
                    marker=dict(color=ti(h2h_a, 'color')),
                    text=a_wins_by_season, textposition='outside',
                    hovertemplate="<b>" + h2h_a + "</b><br>%{x}년: %{y}승<extra></extra>",
                ))
                bar_fig.add_trace(go.Bar(
                    x=[str(s) for s in seasons_list], y=b_wins_by_season,
                    name=h2h_b,
                    marker=dict(color=ti(h2h_b, 'color')),
                    text=b_wins_by_season, textposition='outside',
                    hovertemplate="<b>" + h2h_b + "</b><br>%{x}년: %{y}승<extra></extra>",
                ))
                bar_fig.update_layout(
                    barmode='group', height=400,
                    xaxis=dict(title="시즌"), yaxis=dict(title="승수"),
                    plot_bgcolor='rgba(0,0,0,0)',
                )
                st.plotly_chart(bar_fig, width="stretch")
                
                st.markdown("### 📋 최근 10경기 상세")
                recent = h2h_games.head(10).copy()
                recent_display = pd.DataFrame({
                    "경기일": recent["game_date"].dt.strftime("%Y-%m-%d"),
                    "홈팀": recent["home_team"].tolist(),
                    "원정팀": recent["away_team"].tolist(),
                    "스코어": [f"{int(h)} - {int(a)}"
                              for h, a in zip(recent["home_score"], recent["away_score"])],
                    "승자": recent["winner"].tolist(),
                })
                st.dataframe(recent_display, width="stretch", hide_index=True)


# ============================================================
# TAB 4: 모델 설명
# ============================================================
with tab4:
    st.subheader("🧠 모델 구조")
    st.markdown("""
    ### 학습 방법
    - **알고리즘:** Random Forest (GridSearchCV 튜닝)
    - **학습 데이터:** KBO 공식 데이터 1,464경기 (2024~2026)
    - **피처:** 45개 (선발/불펜/에이스 ERA 분리, 상위 5명 OPS 등)
    - **평가:** 시계열 분할 (Train 2024+2025 상반기 → Val 2025 하반기 → Test 2026)
    
    ### 성능
    | 지표 | 값 | 비교 |
    |---|---|---|
    | 검증셋 정확도 | **58.6%** | MIT MLB 논문 58.7%와 동등 |
    | AUC | 0.602 | 학술 상한 근접 |
    | 랜덤 대비 | +8.6%p | 유의미한 개선 |
    
    ### 피처 엔지니어링
    v3의 핵심은 단순 팀 평균이 아닌 **세분화된 집계** 피처입니다:
    - **투수진 3계층:** 선발진(이닝 상위 5명) / 불펜 / 에이스(1위)
    - **타선 깊이:** 팀 평균 OPS + 상위 5명 OPS + OPS 0.7 이상 타자 수
    - **롤링 폼:** 최근 10경기 승률, 득실차, 연승/연패
    - **맥락:** 홈/원정 승률, 맞대결 이력, 휴식일
    
    ### 한계
    - 선발 투수 개인 정보 미포함 (팀 레벨 집계로 대체)
    - 2026 초반 시즌은 표본이 작아 예측 불안정
    - 실제 배팅용이 아닌 학술/교육 목적
    """)
    st.markdown("---")
    st.subheader("📚 참고 문헌")
    st.markdown("""
    - Huang, M. L., & Li, Y. Z. (2021). *Use of machine learning and 
      deep learning to predict the outcomes of major league baseball matches.*
      Applied Sciences, 11(10), 4499.
    - KBO 공식 기록실: https://www.koreabaseball.com
    """)