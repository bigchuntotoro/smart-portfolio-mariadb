from datetime import datetime
import os
import json
import pandas as pd
import requests
import streamlit as st
import urllib3
import time

# Google Gemini SDK 임포트
from google import genai
from google.genai import types

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# 유틸리티 및 데이터 파싱 함수
# ============================================================
def to_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return default


def to_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", ""))
    except (ValueError, TypeError):
        return default


def format_number(value):
    return f"{value:,}"


def parse_kis_response(response, api_name="KIS API"):
    status_code = response.status_code
    response_text = response.text.strip()
    if status_code != 200 or not response_text:
        raise RuntimeError(f"{api_name} HTTP 오류 (상태코드: {status_code})")
    return response.json()


# ============================================================
# Access Token 발급 함수 (전역 캐싱 적용: 1시간)
# ============================================================
@st.cache_data(ttl=3600)
def get_kis_access_token():
    kis_app_key = os.getenv("KIS_APP_KEY")
    kis_app_secret = os.getenv("KIS_APP_SECRET")
    kis_base_url = os.getenv(
        "KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"
    ).rstrip("/")

    if not kis_app_key or not kis_app_secret:
        raise ValueError("KIS API 인증키가 설정되지 않았습니다.")

    token_url = f"{kis_base_url}/oauth2/tokenP"
    token_headers = {"content-type": "application/json; charset=UTF-8"}
    token_body = {
        "grant_type": "client_credentials",
        "appkey": kis_app_key,
        "appsecret": kis_app_secret,
    }

    token_res = requests.post(
        token_url, headers=token_headers, json=token_body, timeout=10, verify=False
    )
    token_data = parse_kis_response(token_res, "KIS Access Token API")
    access_token = token_data.get("access_token")

    if not access_token:
        raise RuntimeError("Access Token 발급 실패")

    return access_token


# ============================================================
# KIS API 실시간 데이터 조회 함수
# ============================================================
@st.cache_data(ttl=30, show_spinner="KIS API에서 실시간 시세를 불러오는 중...")
def fetch_kis_stock_data(ticker: str):
    ticker = str(ticker).strip()
    access_token = get_kis_access_token()
    kis_base_url = os.getenv(
        "KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"
    ).rstrip("/")
    kis_app_key = os.getenv("KIS_APP_KEY")
    kis_app_secret = os.getenv("KIS_APP_SECRET")

    price_url = f"{kis_base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
    price_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": kis_app_key,
        "appsecret": kis_app_secret,
        "tr_id": "FHKST01010100",
        "custtype": "P",
    }
    price_params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": ticker}

    price_res = requests.get(
        price_url, headers=price_headers, params=price_params, timeout=10, verify=False
    )
    data = parse_kis_response(price_res, "KIS 현재가 조회 API")

    if data.get("rt_cd") != "0":
        msg = data.get("msg1", "알 수 없는 오류")
        raise RuntimeError(f"주가 조회 실패: {msg}")

    output = data.get("output", {})
    trading_value = to_int(output.get("acml_tr_pbmn"))

    if trading_value >= 1000000000000:
        trading_value_text = f"{trading_value / 1000000000000:.2f}조원"
    elif trading_value >= 100000000:
        trading_value_text = f"{trading_value / 100000000:.2f}억원"
    else:
        trading_value_text = f"{trading_value:,}원"

    return {
        "current_price": to_int(output.get("stck_prpr")),
        "previous_close": to_int(output.get("stck_sdpr")),
        "prdy_vrss": to_int(output.get("prdy_vrss")),
        "prdy_ctrt": to_float(output.get("prdy_ctrt")),
        "opening_price": to_int(output.get("stck_oprc")),
        "high_price": to_int(output.get("stck_hgpr")),
        "low_price": to_int(output.get("stck_lwpr")),
        "upper_limit": to_int(output.get("stck_mxpr")),
        "lower_limit": to_int(output.get("stck_llam")),
        "volume": to_int(output.get("acml_vol")),
        "trading_value_text": trading_value_text,
        "per": to_float(output.get("per")),
        "pbr": to_float(output.get("pbr")),
        "eps": to_float(output.get("eps")),
        "bps": to_float(output.get("bps")),
        "week52_high": to_int(output.get("w52_hgpr")),
        "week52_low": to_int(output.get("w52_lwpr")),
        "foreign_holding": to_float(output.get("hts_frgn_ehrt")),
        "stck_cntg_hour": output.get("stck_cntg_hour", ""),
    }


# ============================================================
# Gemini 기반 심층 투자 분석 리포트 생성 함수
# ============================================================
def generate_investment_report(stock_name: str, ticker: str, data: dict) -> str:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return (
            "⚠️ GEMINI_API_KEY 환경변수가 설정되지 않아 AI 리포트를 생성할 수 없습니다."
        )

    client = genai.Client(api_key=gemini_api_key)

    prompt = f"""
    당신은 전문 수석 주식 애널리스트입니다. 아래 제공된 실시간 주가 및 재무 데이터를 기반으로 투자 심층 분석 리포트를 작성해 주세요.

    [종목 정보]
    - 종목명: {stock_name}
    - 종목코드: {ticker}
    - 현재가: {format_number(data['current_price'])}원 (전일대비 {data['prdy_vrss']:+,}원, {data['prdy_ctrt']:.2f}%)
    - PER: {data['per']:.2f}
    - PBR: {data['pbr']:.2f}
    - EPS: {data['eps']:,.2f}원
    - BPS: {data['bps']:,.2f}원
    - 외국인 지분율: {data['foreign_holding']:.2f}%
    - 52주 최고가: {format_number(data['week52_high'])}원
    - 52주 최저가: {format_number(data['week52_low'])}원

    [요청 사항]
    마크다운 형식으로 아래 섹션을 포함하여 친절하고 통찰력 있게 브리핑해주세요:
    1. **현재 시세 및 밸류에이션 총평**: PER, PBR 등을 고려했을 때 현재 주가가 저평가 상태인지 고평가 상태인지 분석.
    2. **투자 관점에서의 주요 장점 (Pros)**: 외국인 지분율 및 52주 가격 위치 등을 바탕으로 한 긍정적 요인.
    3. **투자 관점에서의 잠재 리스크 및 단점 (Cons)**: 주의해야 할 변수나 지표상 특징.
    4. **종합 투자 참고 의견**: 단기/중장기 관점에서의 요약 제언.
    """

    max_retries = 3
    delay = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return "⚠️ 현재 Gemini AI 서버 트래픽이 몰려 일시적으로 요청을 처리하지 못했습니다.\n\n잠시 후 다시 시도해 주세요."
            return f"⚠️ Gemini AI 리포트 생성 중 오류가 발생했습니다: {error_str}"


# ============================================================
# 메인 대시보드 화면 함수
# ============================================================
def show_market_dashboard(user_id: int, cookies=None):
    # 커스텀 CSS 적용
    st.markdown(
        """
        <style>
            .stMetric {
                background-color: #161b22;
                padding: 15px;
                border-radius: 10px;
                border: 1px solid #30363d;
            }
            .report-box {
                background-color: #161b22;
                padding: 20px;
                border-radius: 10px;
                border: 1px solid #30363d;
                color: #f0f6fc;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 사이드바 설정 (주요 ETF 및 종목)
    TOP_STOCKS = {
        "TIGER 미국S&P500": "360750",
        "KODEX 미국나스닥100": "379800",
        "KODEX 미국배당다우존스": "458730",
        "KODEX 주주환원고배당주": "278530",
        "KODEX 200타겟위클리커버드콜": "498400",
        "KODEX 단기채권PLUS": "214980",
    }

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 마켓 네비게이터")
    selected_stock_name = st.sidebar.selectbox(
        "조회 대상 종목", options=list(TOP_STOCKS.keys()), key="market_selected_stock"
    )
    selected_ticker = TOP_STOCKS[selected_stock_name]

    if st.sidebar.button(
        "🔄 실시간 데이터 새로고침", use_container_width=True, key="market_refresh_btn"
    ):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.caption(f"선택 종목 코드: **{selected_ticker}**")

    # 메인 대시보드 렌더링
    st.title("📊 국내 증시 우량주 실시간 모니터링 & AI 리포트")
    st.markdown(
        "한국투자증권(KIS) Open API 실시간 시세와 **Google Gemini AI**가 결합된 심층 분석 대시보드입니다."
    )
    st.markdown("")

    try:
        stock_info = fetch_kis_stock_data(selected_ticker)

        # 지표 카드 영역
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="현재가",
                value=f"{format_number(stock_info['current_price'])}원",
                delta=f"{stock_info['prdy_vrss']:+,}원 ({stock_info['prdy_ctrt']:.2f}%)",
                border=True,
            )

        with col2:
            st.metric(
                label="거래량 / 거래대금",
                value=f"{format_number(stock_info['volume'])}주",
                delta=stock_info["trading_value_text"],
                delta_color="off",
                border=True,
            )

        with col3:
            st.metric(
                label="밸류에이션 (PER / PBR)",
                value=f"PER {stock_info['per']:.2f}",
                delta=f"PBR {stock_info['pbr']:.2f}",
                delta_color="off",
                border=True,
            )

        with col4:
            st.metric(
                label="외국인 지분율",
                value=f"{stock_info['foreign_holding']:.2f}%",
                delta=f"체결시간: {stock_info['stck_cntg_hour'] or '장 마감'}",
                delta_color="normal",
                border=True,
            )

        st.markdown("---")

        # 테이블 상세 영역
        sub_col1, sub_col2 = st.columns(2)

        with sub_col1:
            st.subheader("📌 오늘의 가격 및 제한폭")
            price_df = pd.DataFrame(
                {
                    "구분": [
                        "시가",
                        "고가",
                        "저가",
                        "기준가(전일종가)",
                        "상한가",
                        "하한가",
                    ],
                    "가격": [
                        f"{format_number(stock_info['opening_price'])}원",
                        f"{format_number(stock_info['high_price'])}원",
                        f"{format_number(stock_info['low_price'])}원",
                        f"{format_number(stock_info['previous_close'])}원",
                        f"{format_number(stock_info['upper_limit'])}원",
                        f"{format_number(stock_info['lower_limit'])}원",
                    ],
                }
            )
            st.dataframe(price_df, hide_index=True, use_container_width=True)

        with sub_col2:
            st.subheader("🏢 재무 및 52주 최고/최저 지표")
            val_df = pd.DataFrame(
                {
                    "지표 항목": [
                        "EPS (주당순이익)",
                        "BPS (주당순자산가치)",
                        "52주 최고가",
                        "52주 최저가",
                    ],
                    "측정 값": [
                        f"{stock_info['eps']:,.2f}원",
                        f"{stock_info['bps']:,.2f}원",
                        f"{format_number(stock_info['week52_high'])}원",
                        f"{format_number(stock_info['week52_low'])}원",
                    ],
                }
            )
            st.dataframe(val_df, hide_index=True, use_container_width=True)

        # Gemini AI 투자 심층 분석 리포트 섹션
        st.markdown("---")
        st.subheader(f"🤖 Gemini AI 수석 애널리스트 리포트: {selected_stock_name}")

        with st.spinner(
            "Gemini AI가 실시간 데이터를 바탕으로 심층 분석 리포트를 작성 중입니다..."
        ):
            ai_report = generate_investment_report(
                selected_stock_name, selected_ticker, stock_info
            )

        st.markdown(
            f'<div class="report-box">{ai_report}</div>', unsafe_allow_html=True
        )

    except Exception as e:
        st.error(
            f"⚠️ 데이터를 불러오는 중 오류가 발생했습니다.\n\n**상세 내용**: `{str(e)}`"
        )
        st.info(
            "💡 환경변수(.env)의 KIS API Key 및 Gemini API Key 설정 상태를 확인해주세요."
        )
