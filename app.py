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

# 1. 모바일 뷰포트 및 반응형 레이아웃 설정
st.set_page_config(
    page_title="AI 여행 플래너",
    page_icon="✈️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding: 1.5rem 1rem 3rem 1rem !important; }
    h1, h2, h3 { font-size: 1.4rem !important; line-height: 1.3 !important; }
    p, div, label { font-size: 0.95rem !important; }
    .stButton>button { width: 100% !important; border-radius: 8px !important; height: 3rem !important; font-weight: bold !important; }
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

# 3. PDF 생성 함수 (지도 링크 등 마크다운 제거 처리 포함)
def generate_pdf(text_content):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=35, bottomMargin=35)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(name='MobileNormal', fontName=MAIN_FONT, fontSize=10, leading=15, textColor='#333333')
    title_style = ParagraphStyle(name='MobileTitle', fontName=MAIN_FONT, fontSize=14, leading=18, textColor='#1a5fb4', spaceAfter=10)
    
    story = []
    lines = text_content.split('\n')
    
    for line in lines:
        # 마크다운 링크 [텍스트](URL) 형태에서 텍스트만 남기기
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

# 4. Gemini API 키
API_KEY = "AQ.Ab8RN6KNyTYb9CRCpApOtdKKdV5AhjT07NZ5PVbe7ZSIzCXOPw"

# 5. 화면 구성
st.title("📱 AI 맞춤 여행 플래너")

with st.expander("📝 여행 조건 입력하기", expanded=True):
    start_location = st.text_input("출발지", placeholder="예: 서울, 부산")
    destination = st.text_input("목적지 (여행지)", placeholder="예: 속초, 남해, 경주")
    duration = st.selectbox("여행 기간", ["당일치기", "1박 2일", "2박 3일", "3박 4일"])
    
    # 바이크 전용 모드 스위치
    is_bike_mode = st.checkbox("🏍️ 바이크 투어 모드 (라이딩 전용 경로)")
    
    style = st.selectbox("여행 스타일", ["자연/풍경 감상", "맛집/카페 투어", "관광지 위주", "액티비티/체험", "휴양/힐링"])
    extra_requests = st.text_input("기타 요청사항", placeholder="예: 해산물 위주 맛집 추천해줘")

if "plan_result" not in st.session_state:
    st.session_state.plan_result = ""

if st.button("🚀 맞춤 여행 일정 만들기"):
    if not start_location or not destination:
        st.warning("출발지와 목적지를 모두 입력해주세요.")
    else:
        with st.spinner("최적의 일정을 생성하는 중..."):
            try:
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("gemini-3.6-flash")
                
                # 프롬프트 구성
                prompt = f"""
                다음 조건으로 여행 일정을 작성해줘.
                - 출발지: {start_location}
                - 목적지: {destination}
                - 일정: {duration}
                - 여행 스타일: {style}
                - 추가 요구사항: {extra_requests}
                """
                
                if is_bike_mode:
                    prompt += """
                    [🏍️ 바이크 투어 특별 조건 - 필수 반영]
                    1. 경로: 고속도로 및 자동차 전용도로 절대 제외. 4차선 이상 대로를 피하고, 한적한 2차선 지방도/국도 및 경치가 좋은 와인딩 코스 위주로 경로를 안내할 것.
                    2. 장소: 라이더 카페나 바이크 주차 편의성이 좋은 곳을 포함할 것.
                    3. 지도 링크: 일정에 등장하는 모든 장소명(식당, 카페, 경유지 포함) 뒤에 네이버 지도와 카카오맵 검색 링크를 마크다운 형식으로 반드시 달아줄 것.
                       - 형식 예시: 장소명 ([네이버](https://map.naver.com/v5/search/장소명) | [카카오](https://map.kakao.com/link/search/장소명))
                    """
                else:
                    prompt += """
                    [일반 여행 조건]
                    일정에 등장하는 주요 장소명 뒤에 네이버 지도 검색 링크를 달아줘.
                    - 형식 예시: 장소명 ([지도보기](https://map.naver.com/v5/search/장소명))
                    """

                prompt += """
                [작성 가이드]
                - 스마트폰 화면에서 한눈에 들어오도록 일차별 오전/오후/저녁으로 명확히 구분.
                - 장소명, 추천 이유, 이동 시간 및 팁을 간결하게 작성할 것.
                """
                
                response = model.generate_content(prompt)
                st.session_state.plan_result = response.text
                st.success("일정 생성이 완료되었습니다!")
            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

if st.session_state.plan_result:
    st.divider()
    # 생성된 결과를 마크다운으로 렌더링 (클릭 가능한 지도 링크 활성화)
    st.markdown(st.session_state.plan_result)
    
    st.divider()
    st.subheader("✏️ 일정 직접 수정 및 저장")
    
    edited_plan = st.text_area("일정 내용 수정", value=st.session_state.plan_result, height=320)
    
    try:
        pdf_bytes = generate_pdf(edited_plan)
        st.download_button(
            label="📄 최종 일정표 PDF 다운로드",
            data=pdf_bytes,
            file_name=f"{start_location}_to_{destination}_여행일정.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF 생성 오류: {e}")
