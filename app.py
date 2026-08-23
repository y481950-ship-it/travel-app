import streamlit as st
import google.generativeai as genai
import os
import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import urllib.request
import streamlit.components.v1 as components

# 1. 모바일 뷰포트 및 기본 설정
st.set_page_config(
    page_title="박영선의 AI 여행 플래너",
    page_icon="🏍️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 세션 유지 및 모바일 브라우저 오동작 방지
components.html(
    """
    <script>
    // 브라우저의 제멋대로 새로고침(Pull-to-refresh) 강제 무효화
    window.addEventListener('scroll', function() {}, {passive: true});
    document.addEventListener("visibilitychange", function() {
        if (document.visibilityState === 'visible') {
            window.dispatchEvent(new Event('resize'));
        }
    });
    </script>
    """,
    height=0,
    width=0
)

# 자유로운 터치 스크롤 허용 + 상단 튕김 방지 CSS
st.markdown("""
<style>
    html, body {
        overscroll-behavior-y: none !important;
        -webkit-overflow-scrolling: touch !important;
    }
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 4rem !important; 
        padding-left: 0.8rem !important; 
        padding-right: 0.8rem !important; 
    }
    h1, h2, h3 { 
        font-size: 1.35rem !important; 
        line-height: 1.3 !important; 
    }
    p, div, label { 
        font-size: 0.95rem !important; 
    }
    .stButton>button { 
        width: 100% !important; 
        border-radius: 8px !important; 
        height: 3rem !important; 
        font-weight: bold !important; 
    }
    div[role="radiogroup"] {
        gap: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# 2. 한글 폰트 설정 (PDF용)
FONT_PATH = "NanumGothic.ttf"
if not os.path.exists(FONT_PATH):
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(url, FONT_PATH)
    except Exception:
        pass

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("NanumGothic", FONT_PATH))
    MAIN_FONT = "NanumGothic"
else:
    MAIN_FONT = "Helvetica"

# 3. PDF 생성 함수
def generate_pdf(text_content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(name='MobileNormal', fontName=MAIN_FONT, fontSize=10, leading=15, textColor='#333333')
    title_style = ParagraphStyle(name='MobileTitle', fontName=MAIN_FONT, fontSize=14, leading=18, textColor='#1a5fb4', spaceAfter=10)
    
    story = []
    lines = text_content.split('\n')
    
    for line in lines:
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        cleaned_line = re.sub(r'[*#_`]', '', line).strip()
        if not cleaned_line:
            story.append(Spacer(1, 8))
            continue
        
        if line.startswith('#') or '일차' in line or 'Day' in line:
            story.append(Paragraph(cleaned_line, title_style))
        else:
            story.append(Paragraph(cleaned_line, normal_style))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

# 4. Gemini API 키 고정
API_KEY = "AQ.Ab8RN6KNyTYb9CRCpApOtdKKdV5AhjT07NZ5PVbe7ZSIzCXOPw"

# 5. 세션 상태 관리 (초기화 방지)
if "plan_result" not in st.session_state:
    st.session_state.plan_result = ""

# 6. 화면 구성
st.title("🏍️ 박영선의 AI 여행 플래너")

# 일정이 생성되어 있으면 입력 폼을 가리고 결과에 집중 (원할 때만 다시 설정)
if not st.session_state.plan_result:
    start_type = st.radio("출발지 설정", ["📍 현재 위치 사용 (경기 여주 기준)", "✏️ 다른 지역 직접 입력"], horizontal=True)
    
    if start_type == "✏️ 다른 지역 직접 입력":
        start_location = st.text_input("출발지 입력", placeholder="예: 서울 강남, 수원, 대전 등")
    else:
        start_location = "경기 여주(사용자 현재 위치)"
        st.success("📍 현재 계신 위치(여주)를 출발지로 자동 설정했습니다.")

    destination = st.text_input("목적지 (도착지)", placeholder="예: 영월, 속초, 남해, 양평")
    
    st.write("**여행 기간**")
    duration = st.radio("여행 기간 선택", ["당일치기", "1박 2일", "2박 3일", "3박 4일"], horizontal=True, label_visibility="collapsed")
    
    # 바이크 전용 설정
    is_bike_mode = st.checkbox("🏍️ 바이크 투어 모드 (라이딩 전용 경로)", value=True)
    avoid_large_roads = False
    if is_bike_mode:
        avoid_large_roads = st.checkbox("🚜 4차선 대로 완전 배제 (시골길/2차선 국도·지방도 전용)", value=True)
    
    st.write("**여행 스타일**")
    style = st.radio("여행 스타일 선택", ["자연/풍경 감상", "맛집/카페 투어", "관광지 위주", "액티비티/체험", "휴양/힐링"], label_visibility="collapsed")
    
    extra_requests = st.text_input("기타 요청사항", placeholder="예: 한적한 와인딩 코스, 뷰 맛집 위주")

    if st.button("🚀 맞춤 여행 일정 만들기"):
        if not destination or (start_type == "✏️ 다른 지역 직접 입력" and not start_location):
            st.warning("출발지와 목적지를 모두 입력해주세요.")
        else:
            with st.spinner("최적의 맞춤 일정을 생성하는 중..."):
                try:
                    genai.configure(api_key=API_KEY)
                    model = genai.GenerativeModel("gemini-3.6-flash")
                    
                    prompt = f"""
                    다음 조건으로 여행 일정을 작성해줘.
                    - 출발지: {start_location}
                    - 목적지: {destination}
                    - 일정: {duration}
                    - 여행 스타일: {style}
                    - 추가 요구사항: {extra_requests}

                    [🚫 출발지 인근 경유지 절대 배제 규칙]
                    - 출발지(예: 여주) 내부의 관광지, 유원지, 인근 카페 등은 절대 첫 번째 경유지로 넣지 말 것.
                    - 출발지에서는 바로 목적지 방향으로 최소 1시간 이상 라이딩/이동한 후, 첫 번째 휴식지나 목적지 방향의 본격적인 경유지가 나오도록 동선을 구성할 것.
                    """
                    
                    if is_bike_mode:
                        prompt += """
                    [🏍️ 바이크 투어 필수 원칙]
                    1. 고속도로 및 자동차 전용도로는 100% 절대 진입 불가 (이륜차 통행 금지 도로 원천 배제).
                        """
                        if avoid_large_roads:
                            prompt += """
                    2. [4차선 대로 완전 배제]:
                       - 왕복 4차선 이상의 넓은 국도, 대로, 고속화도로는 완전히 제외할 것.
                       - 소요 시간이 더 걸리고 멀리 돌아가더라도 반드시 1.5차선~2차선 한적한 시골길, 마을 안길, 산길 지방도(군도/지방도/와인딩 코스) 위주로만 동선을 짤 것.
                            """
                        else:
                            prompt += """
                    2. 경치 좋은 2차선 지방도 및 와인딩 코스를 우선하되 이동 효율을 고려할 것.
                            """
                        
                        prompt += """
                    3. 장소 추천: 라이더 카페, 경치 좋은 뷰 포인트, 오토바이 주차가 편리한 맛집 포함.
                    4. 지도 길찾기 연동 링크 (매우 중요):
                       - 주요 경유지 및 장소명 뒤에 아래 형식으로 네이버/카카오 지도 검색 링크를 반드시 포함할 것.
                       - 형식: [장소명](https://map.naver.com/v5/search/{장소명}) | [카카오맵](https://map.kakao.com/link/search/{장소명})
                        """
                    else:
                        prompt += """
                    [일반 여행 조건]
                    - 주요 장소명 뒤에 네이버 지도 검색 링크를 달아줘. 예시: [장소명](https://map.naver.com/v5/search/{장소명})
                        """

                    prompt += """
                    [작성 가이드]
                    - 모바일 가독성을 위해 일차별 오전/오후/저녁 동선으로 명확히 정리할 것.
                    - 장소명, 추천 이유, 소요 시간 및 이동 팁을 명확하게 안내할 것.
                    """
                    
                    response = model.generate_content(prompt)
                    st.session_state.plan_result = response.text
                    st.session_state.destination_saved = destination
                    st.rerun()
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")

else:
    # 일정이 생성된 후의 화면 (스크롤 간섭 완전 차단)
    st.markdown("### 🗺️ 생성된 맞춤 여행 일정")
    st.markdown(st.session_state.plan_result)
    
    st.divider()
    st.subheader("✏️ 일정 수정 및 저장")
    
    edited_plan = st.text_area("일정 내용 수정", value=st.session_state.plan_result, height=260)
    
    try:
        dest_name = st.session_state.get("destination_saved", "맞춤")
        pdf_bytes = generate_pdf(edited_plan)
        st.download_button(
            label="📄 최종 일정표 PDF 다운로드",
            data=pdf_bytes,
            file_name=f"{dest_name}_맞춤여행일정.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF 생성 오류: {e}")
        
    st.write("")
    if st.button("🔄 조건 다시 설정하기 (처음으로)"):
        st.session_state.plan_result = ""
        st.rerun()
