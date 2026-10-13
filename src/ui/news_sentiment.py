import os
import time
from google import genai
from google.genai import types
import pandas as pd
import streamlit as st


def show_news_sentiment_page(user_id: int, cookies=None):
    """뉴스 검색 및 Gemini 감성 분석 대시보드 화면을 렌더링합니다."""

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
            .news-card {
                background-color: #161b22;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #30363d;
                margin-bottom: 10px;
                color: #f0f6fc;
            }
            .sentiment-box {
                background-color: #1c2128;
                padding: 20px;
                border-radius: 10px;
                border: 1px solid #30363d;
                color: #f0f6fc;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📰 AI 실시간 뉴스 & 감성 분석 대시보드")
    st.markdown(
        "Google Search 웹 검색 도구와 Gemini AI를 연동하여 선택한 종목의 최근"
        " 이슈와 뉴스 동향을 수집하고, **종합 감성 분석(Sentiment"
        " Analysis)** 및 투자 의견을 제공합니다."
    )
    st.markdown("")

    # 대상 종목 딕셔너리
    TOP_STOCKS = {
        "TIGER 미국S&P500": "360750",
        "KODEX 미국나스닥100": "379800",
        "KODEX 미국배당다우존스": "458730",
        "KODEX 주주환원고배당주": "0153K0",
        "KODEX 200타겟위클리커버드콜": "498400",
        "KODEX 단기채권PLUS": "214980",
    }

    # 종목 선택 셀렉트박스
    selected_stock_name = st.selectbox(
        "감성 분석을 수행할 종목을 선택하세요",
        options=list(TOP_STOCKS.keys()),
        key="news_sentiment_selectbox",
    )
    selected_ticker = TOP_STOCKS[selected_stock_name]

    st.caption(f"선택된 종목 코드: **{selected_ticker}**")
    st.markdown("")

    if st.button(
        "🚀 최신 뉴스 수집 및 AI 감성 분석 실행",
        use_container_width=True,
        type="primary",
    ):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            st.error(
                "⚠️ GEMINI_API_KEY 환경변수가 설정되지 않아 AI 분석을 수행할 수"
                " 없습니다."
            )
            return

        with st.spinner(
            f"🔍 Google Search로 '{selected_stock_name}' 관련 최신 뉴스를"
            " 수집하고 Gemini가 분석 중입니다..."
        ):
            try:
                client = genai.Client(api_key=gemini_api_key)

                # Google Search Tool(Grounding) 설정
                search_tool = types.Tool(google_search=types.GoogleSearch())

                prompt = f"""
                당신은 수석 금융 애널리스트이자 글로벌 시장 감성 분석 전문가입니다.
                종목명: {selected_stock_name} (종목코드: {selected_ticker})
                
                최근 이 종목(또는 연계된 기초지수/미국 증시 및 관련 섹터)과 관련된 최신 뉴스, 시장 동향, 경제 이슈들을 구글 검색을 통해 조사해 주세요.
                그 후 아래 항목에 맞추어 마크다운 형식으로 상세히 분석해 주세요.

                1. **최근 주요 뉴스 및 시장 동향 요약**: 최근 보도되거나 언급된 핵심 이슈 3가지 이상 정리.
                2. **감성 분석 결과 (Sentiment Analysis)**: 
                   - 종합 감성 평가: [매우 긍정 / 긍정 / 중립 / 부정 / 매우 부정 중 택일]
                   - 투자 심리 점수: (0점 ~ 100점 사이의 점수 부여)
                   - 판단 근거 상세 설명.
                3. **주가 및 투자에 미치는 영향**: 호재 및 악재 요인 분석.
                4. **향후 전망 및 대응 전략**: 단기/중장기 관점에서의 투자 참고 조언.
                """

                max_retries = 3
                delay = 3
                response = None

                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model="gemini-3.8-flash",
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                tools=[search_tool],
                                temperature=0.3,
                            ),
                        )
                        break
                    except Exception as e:
                        err_msg = str(e)
                        if (
                            "429" in err_msg
                            or "RESOURCE_EXHAUSTED" in err_msg
                            or "503" in err_msg
                        ):
                            if attempt < max_retries - 1:
                                time.sleep(delay)
                                delay *= 2  # 백오프 지연 시간 증가
                                continue
                        raise e

                if not response:
                    st.error(
                        "⚠️ API 요청 횟수 한도를 초과(429 오류)했거나 서버가 혼잡합니다."
                        " 잠시 후 다시 시도해 주세요."
                    )
                    return

                st.session_state["last_news_report"] = response.text

                # 검색된 그라운딩(참조 링크) 정보 추출
                grounding_chunks = []
                if response.candidates and response.candidates[0].grounding_metadata:
                    metadata = response.candidates[0].grounding_metadata
                    if metadata.grounding_chunks:
                        for chunk in metadata.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web and chunk.web.uri:
                                grounding_chunks.append(
                                    {
                                        "title": chunk.web.title or "참조 링크",
                                        "uri": chunk.web.uri,
                                    }
                                )

                st.session_state["last_grounding_sources"] = grounding_chunks

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    st.error(
                        "🚨 **API 할당량 초과 (Rate Limit Exceeded)**\n\n현재"
                        " 사용 중인 Gemini API 키의 요금제 한도(Quotas)를"
                        " 초과하였습니다. 무료 버전(Free Tier)을 사용 중이신 경우 잠시"
                        " 후(몇 분 뒤) 다시 시도하시거나, Google AI Studio에서 사용량을"
                        " 확인해 주세요.\n\n상세 내용: "
                        f"`{error_str}`"
                    )
                else:
                    st.error(
                        "⚠️ 뉴스 분석 중 오류가 발생했습니다. 상세 내용:"
                        f" `{error_str}`"
                    )
                return

    # 결과가 세션에 있으면 출력
    if "last_news_report" in st.session_state and st.session_state["last_news_report"]:
        st.markdown("---")
        st.subheader(f"📊 [{selected_stock_name}] AI 뉴스 및 감성 분석 리포트")
        st.markdown(
            f'<div class="sentiment-box">{st.session_state["last_news_report"]}</div>',
            unsafe_allow_html=True,
        )

        # 참조된 웹 뉴스 출처(Citations) 표시
        if (
            "last_grounding_sources" in st.session_state
            and st.session_state["last_grounding_sources"]
        ):
            st.markdown("")
            with st.expander("🔗 참고한 웹 뉴스 및 출처 링크 보기"):
                for source in st.session_state["last_grounding_sources"]:
                    st.markdown(f"- [{source['title']}]({source['uri']})")
