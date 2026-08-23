import streamlit as st
import google.generativeai as genai
import os
import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import urllib.request

# 1. 모바일 뷰포트 및 기본 설정
st.set_page_config(
    page_title="박영선의 AI 여행 플래너",
    page_icon="🏍️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 모바일 상하 터치 스크롤 완전 복구 및 스타일 최적화 CSS
st.markdown("""
<style>
    /* 스마트폰 터치 스크롤 정상화 및 상하 스크롤 강제 */
    html, body, [data-testid="stAppViewContainer"], .main {
        touch-action: pan-y !important;
        -webkit-overflow-scrolling: touch !important;
        overflow-y: auto !important;
        overscroll-behavior-y: none !important;
    }
    
    .block-container { 
        padding-top: 1.2rem !important; 
        padding-bottom: 5rem !important; 
        padding-left: 1rem !important; 
        padding-right: 1rem !important; 
    }
    
    /* 깔끔하고 시원한 본문 가독성 */
    p, span, div, li { 
        font-size: 1.1rem !important; 
        line-height: 1.6 !important; 
    }
    
    h1 { font-size: 1.55rem !important; font-weight: bold !important; }
    h2 { font-size: 1.35rem !important; font-weight: bold !important; color: #1e3d59 !important; }
    h3 { font-size: 1.2rem !important; font-weight: bold !important; color: #17b978 !important; }
    
    /* 지도 링크 강조 */
    a {
        font-size: 1.1rem !important;
        font-weight: bold !important;
        text-decoration: underline !important;
    }
    
    /* 세련된 버튼 스타일 */
    .stButton>button { 
        width: 100% !important; 
        border-radius: 10px !important; 
        height: 3.4rem !important; 
        font-size: 1.15rem !important;
        font-weight: bold !important; 
    }
    
    div[role="radiogroup"] {
        gap: 0.5rem;
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
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(name='NormalStyle', fontName=MAIN_FONT, fontSize=10, leading=15, textColor='#333333')
    title_style = ParagraphStyle(name='TitleStyle', fontName=MAIN_FONT, fontSize=14, leading=18, textColor='#1a5fb4', spaceAfter=10)
    
    story = []
    lines = text_content.split('\n')
    for line in lines:
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        cleaned_line = re.sub(r'[*#_`]', '', line).strip()
        if not cleaned_line:
            story.append(Spacer(1, 6))
            continue
        if line.startswith('#') or '일차' in line or 'Day' in line:
            story.append(Paragraph(cleaned_line, title_style))
        else:
            story.append(Paragraph(cleaned_line, normal_style))
            
    doc.build(story)
    buffer.seek(0)
    return buffer

API_KEY = "AQ.Ab8RN6KNyTYb9CRCpApOtdKKdV5AhjT07NZ5PVbe7ZSIzCXOPw"

if "plan_result" not in st.session_state:
    st.session_state.plan_result = ""

st.title("🏍️ 박영선의 AI 여행 플래너")

if not st.session_state.plan_result:
    region_type = st.radio("지역 구분", ["🇰🇷 국내", "✈️ 해외"], horizontal=True)
    
    if region_type == "🇰🇷 국내":
        start_type = st.radio("출발지 설정", ["📍 현재 위치 (경기 여주)", "✏️ 직접 입력"], horizontal=True)
        if start_type == "✏️ 직접 입력":
            start_location = st.text_input("출발지 입력", placeholder="예: 서울 강남, 수원, 대전 등")
        else:
            start_location = "경기 여주(현재 위치)"
        destination = st.text_input("목적지", placeholder="예: 영월, 속초, 남해, 양평")
    else:
        start_location = st.text_input("출발지 (공항/항구/도시)", placeholder="예: 후쿠오카 공항, 시모노세키항, 도쿄")
        destination = st.text_input("목적지 (도시/지역/명소)", placeholder="예: 규슈 아소산, 홋카이도, 교토")
    
    st.write("**여행 기간**")
    duration = st.radio("기간 선택", ["당일치기", "1박 2일", "2박 3일", "3박 4일", "4박 5일 이상"], horizontal=True, label_visibility="collapsed")
    
    is_bike_mode = st.checkbox("🏍️ 바이크 전용 경로", value=True)
    avoid_large_roads = False
    if is_bike_mode:
        avoid_large_roads = st.checkbox("🚜 4차선 대로 완전 배제 (시골길/2차선 국도·지방도 전용)", value=True)
    
    st.write("**여행 스타일**")
    style = st.radio("스타일 선택", ["자연/풍경 감상", "맛집/카페 투어", "관광지 위주", "액티비티/체험", "휴양/힐링"], horizontal=True, label_visibility="collapsed")
    
    extra_requests = st.text_input("기타 요청사항", placeholder="예: 한적한 와인딩 코스, 뷰 맛집 위주")

    if st.button("🚀 일정 생성하기"):
        if not destination or (region_type == "🇰🇷 국내" and start_type == "✏️ 직접 입력" and not start_location) or (region_type == "✈️ 해외" and not start_location):
            st.warning("출발지와 목적지를 모두 입력해주세요.")
        else:
            with st.spinner("최적의 여행 코스를 구성하고 있습니다..."):
                try:
                    genai.configure(api_key=API_KEY)
                    model = genai.GenerativeModel("gemini-3.6-flash")
                    
                    prompt = f"""
                    다음 조건으로 여행/라이딩 일정을 작성해줘.
                    - 지역: {region_type}
                    - 출발지: {start_location}
                    - 목적지: {destination}
                    - 일정: {duration}
                    - 스타일: {style}
                    - 추가 요청: {extra_requests}

                    [🚫 출발지 인근 경유지 절대 배제 규칙]
                    - 출발지 내부 또는 인근의 관광지/카페는 첫 경유지로 잡지 말 것.
                    - 출발지에서 목적지 방향으로 최소 1시간 이상 이동/주행한 후 첫 경유지 및 휴식지가 나오도록 할 것.
                    """
                    
                    if is_bike_mode:
                        if region_type == "🇰🇷 국내":
                            prompt += "\n- 고속도로 및 자동차 전용도로 진입 금지 (이륜차 통행 금지 도로 절대 배제)."
                        
                        if avoid_large_roads:
                            prompt += "\n- [4차선 대로 완전 배제]: 4차선 이상 넓은 도로는 완전히 제외하고, 멀리 돌더라도 1.5~2차선 한적한 시골길/산길 와인딩 지방도로만 연결할 것."
                        else:
                            prompt += "\n- [일반 도로 허용]: 빠른 이동과 주행 편의를 위해 4차선 일반 국도 및 주요 도로 주행을 적극 포함할 것."
                    
                    if region_type == "🇰🇷 국내":
                        prompt += """
                    [국내 지도 링크 규칙]
                    - 주요 경유지 장소명 뒤에 아래 형식으로 네이버/카카오 지도 링크를 작성할 것:
                      [네이버지도](https://map.naver.com/v5/search/{장소명}) | [카카오맵](https://map.kakao.com/link/search/{장소명})
                        """
                    else:
                        prompt += """
                    [해외 지도 링크 규칙]
                    - 해외 여행이므로 주요 경유지 장소명 뒤에 아래 형식으로 구글 지도 링크를 작성할 것:
                      [구글지도 내비](https://www.google.com/maps/search/?api=1&query={장소명})
                        """

                    prompt += """
                    [작성 형식]
                    - 모바일 화면에서 한눈에 들어오도록 일차별 오전/오후/저녁 동선으로 명확히 정리할 것.
                    - 코스, 소요 시간, 추천 이유를 깔끔하게 안내할 것.
                    """
                    
                    response = model.generate_content(prompt)
                    st.session_state.plan_result = response.text
                    st.session_state.destination_saved = destination
                    st.rerun()
                except Exception as e:
                    st.error(f"생성 오류: {e}")

else:
    st.markdown("### 🗺️ 생성된 맞춤 여행 일정")
    st.markdown(st.session_state.plan_result)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        dest_name = st.session_state.get("destination_saved", "맞춤")
        pdf_bytes = generate_pdf(st.session_state.plan_result)
        st.download_button(
            label="📄 PDF 다운로드",
            data=pdf_bytes,
            file_name=f"{dest_name}_여행일정.pdf",
            mime="application/pdf"
        )
    with col2:
        if st.button("🔄 다시 설정하기"):
            st.session_state.plan_result = ""
            st.rerun()
