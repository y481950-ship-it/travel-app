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

# 모바일 화면에 최적화된 CSS
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    h1, h2, h3 {
        font-size: 1.4rem !important;
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
</style>
""", unsafe_allow_html=True)

# 2. 한글 폰트 다운로드 및 등록
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
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=35,
        bottomMargin=35
    )
    
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        name='MobileNormal',
        fontName=MAIN_FONT,
        fontSize=10,
        leading=15,
        textColor='#333333'
    )
    title_style = ParagraphStyle(
        name='MobileTitle',
        fontName=MAIN_FONT,
        fontSize=14,
        leading=18,
        textColor='#1a5fb4',
        spaceAfter=10
    )
    
    story = []
    lines = text_content.split('\n')
    
    for line in lines:
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

# 4. Gemini API 키 영구 고정
API_KEY = "gen-lang-client-0836113123"

# 5. 화면 구성
st.title("📱 AI 맞춤 여행 플래너")

with st.expander("📝 여행 조건 입력하기", expanded=True):
    destination = st.text_input("여행지", placeholder="예: 제주도, 후쿠오카, 다낭")
    duration = st.selectbox("여행 기간", ["당일치기", "1박 2일", "2박 3일", "3박 4일", "4박 5일 이상"])
    style = st.selectbox("여행 스타일", ["힐링/휴양", "맛집/카페 투어", "관광지 위주", "액티비티/체험", "부모님/가족 여행"])
    extra_requests = st.text_input("기타 요청사항", placeholder="예: 뚜벅이 여행, 해산물 위주 맛집")

if "plan_result" not in st.session_state:
    st.session_state.plan_result = ""

if st.button("🚀 맞춤 여행 일정 만들기"):
    if not destination:
        st.warning("여행지를 입력해주세요.")
    else:
        with st.spinner("일정표를 생성하는 중..."):
            try:
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                prompt = f"""
                다음 조건으로 여행 일정을 작성해줘.
                여행지: {destination}
                일정: {duration}
                여행 스타일: {style}
                추가 요구사항: {extra_requests}

                [작성 가이드]
                1. 스마트폰 화면에서 한눈에 들어오도록 각 일차별 오전/오후/저녁 동선을 명확하게 정리해줘.
                2. 장소명, 추천 메뉴, 이동 팁을 짧고 간결하게 작성해줘.
                """
                response = model.generate_content(prompt)
                st.session_state.plan_result = response.text
                st.success("일정 생성이 완료되었습니다!")
            except Exception as e:
                st.error(f"생성 중 오류 발생: {e}")

if st.session_state.plan_result:
    st.divider()
    st.subheader("✏️ 일정 직접 수정하기")
    st.caption("텍스트를 자유롭게 수정한 뒤 아래 버튼을 누르면 수정된 내용 그대로 PDF로 다운로드됩니다.")
    
    edited_plan = st.text_area(
        "일정 내용",
        value=st.session_state.plan_result,
        height=320
    )
    
    try:
        pdf_bytes = generate_pdf(edited_plan)
        st.download_button(
            label="📄 수정된 일정표 PDF 다운로드",
            data=pdf_bytes,
            file_name=f"{destination}_여행일정.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"PDF 생성 오류: {e}")
