import pandas as pd
import streamlit as st


def show_portfolio_comparison_page(user_id: int, cookies=None):
    """포트폴리오 다중 종목 비교 대시보드 화면을 렌더링합니다."""

    # 커스텀 CSS 적용 (기존 스타일과 통일감 유지)
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

    st.title("⚖️ 포트폴리오 다중 종목 비교 대시보드")
    st.markdown(
        "등록된 주요 ETF 및 우량주들의 핵심 지표(현재가, 등락률, 거래대금, PER, PBR 등)를 **한눈에 비교**할 수 있습니다."
    )
    st.markdown("")

    # 비교 대상 전체 종목 딕셔너리
    TOP_STOCKS = {
        "TIGER 미국S&P500": "360750",
        "KODEX 미국나스닥100": "379800",
        "KODEX 미국배당다우존스": "458730",
        "KODEX 주주환원고배당주": "0153K0",
        "KODEX 200타겟위클리커버드콜": "498400",
        "KODEX 단기채권PLUS": "214980",
    }

    # 사용자가 비교할 종목을 다중 선택할 수 있도록 multiselect 제공
    selected_names = st.multiselect(
        "비교할 종목을 선택하세요 (기본 전체 선택)",
        options=list(TOP_STOCKS.keys()),
        default=list(TOP_STOCKS.keys()),
        key="portfolio_multiselect",
    )

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        run_comparison = st.button(
            "🚀 일괄 비교 실행", use_container_width=True, type="primary"
        )
    with col_btn2:
        if st.button("🔄 캐시 초기화 및 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    if not selected_names:
        st.warning("⚠️ 비교할 종목을 하나 이상 선택해 주세요.")
        return

    # 버튼을 누르거나 최초 진입 시 데이터 수집 진행
    comparison_data = []

    # 프로그레스바와 함께 데이터 수집
    progress_bar = st.progress(0, text="데이터를 불러오는 중입니다...")
    total_items = len(selected_names)

    for i, name in enumerate(selected_names):
        ticker = TOP_STOCKS[name]
        try:
            # market_dashboard 모듈 등에 정의된 실시간 데이터 조회 함수 호출 가정
            # (필요에 따라 임포트 경로를 조정하여 사용하세요)
            from src.ui.market_dashboard import fetch_kis_stock_data, format_number

            stock_info = fetch_kis_stock_data(ticker)

            comparison_data.append(
                {
                    "종목명": name,
                    "종목코드": ticker,
                    "현재가": f"{format_number(stock_info['current_price'])}원",
                    "전일대비": f"{stock_info['prdy_vrss']:+,}원",
                    "등락률": f"{stock_info['prdy_ctrt']:.2f}%",
                    "거래대금": stock_info["trading_value_text"],
                    "PER": (
                        f"{stock_info['per']:.2f}" if stock_info["per"] > 0 else "-"
                    ),
                    "PBR": (
                        f"{stock_info['pbr']:.2f}" if stock_info["pbr"] > 0 else "-"
                    ),
                    "외국인 지분율": f"{stock_info['foreign_holding']:.2f}%",
                    "52주 최고가": f"{format_number(stock_info['week52_high'])}원",
                    "52주 최저가": f"{format_number(stock_info['week52_low'])}원",
                }
            )
        except Exception as e:
            comparison_data.append(
                {
                    "종목명": name,
                    "종목코드": ticker,
                    "현재가": "조회 실패",
                    "전일대비": "-",
                    "등락률": "-",
                    "거래대금": "-",
                    "PER": "-",
                    "PBR": "-",
                    "외국인 지분율": "-",
                    "52주 최고가": "-",
                    "52주 최저가": "-",
                }
            )

        progress_bar.progress(
            (i + 1) / total_items,
            text=f"[{i+1}/{total_items}] {name} 조회 완료...",
        )

    progress_bar.empty()

    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)

        st.markdown("---")
        st.subheader("📋 포트폴리오 비교 결과 요약 표")

        # Streamlit 데이터프레임으로 인터랙티브 테이블 제공
        st.dataframe(df_comparison, hide_index=True, use_container_width=True)

        # 마크다운 테이블 형태로도 확인 가능하도록 뷰 제공
        with st.expander("📝 마크다운(Markdown) 표 원본 보기"):
            st.code(df_comparison.to_markdown(index=False), language="markdown")
