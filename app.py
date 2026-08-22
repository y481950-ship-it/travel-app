import io
import json
import time
import streamlit as st
from PIL import Image as PILImage, ImageDraw, ImageFont
from google import genai
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 페이지 기본 설정
st.set_page_config(page_title="AI 맞춤 여행 플래너", page_icon="✈️", layout="centered")

GEMINI_API_KEY = "AQ.Ab8RN6KNyTYb9CRCpApOtdKKdV5AhjT07NZ5PVbe7ZSIzCXOPw"

try:
    pdfmetrics.registerFont(TTFont('Malgun', 'c:/Windows/Fonts/malgun.ttf'))
    FONT_NAME = 'Malgun'
except:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
    FONT_NAME = 'HYSMyeongJo-Medium'

def create_theme_banner_image(title_text, subtitle_text, bg_hex="#1E3A8A", width=570, height=360):
    img = PILImage.new('RGB', (width, height), color=bg_hex)
    draw = ImageDraw.Draw(img)
    draw.rectangle([15, 15, width-15, height-15], outline="#FFFFFF", width=3)
    draw.rectangle([22, 22, width-22, height-22], outline="#CBD5E1", width=1)
    try:
        font_main = ImageFont.truetype("c:/Windows/Fonts/malgunbd.ttf", 36)
        font_sub = ImageFont.truetype("c:/Windows/Fonts/malgun.ttf", 22)
    except:
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    draw.text((width//2, height//2 - 25), title_text, fill="#FFFFFF", font=font_main, anchor="mm")
    draw.text((width//2, height//2 + 35), subtitle_text, fill="#F1F5F9", font=font_sub, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return Image(buf, width=285, height=180)

def fetch_realtime_travel_plan(origin, destination, duration, people_count):
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    당신은 대한민국 최고의 맞춤형 전문 여행 플래너입니다.
    • 출발지: {origin}
    • 목적지: {destination}
    • 여행 기간: {duration}
    • 여행 인원: {people_count}

    [필수 반영 지침]
    1. 출발지({origin})에서 목적지({destination})까지의 이동 경로, 소요시간, 출발시간, 교통팁.
    2. {people_count} 맞춤 예상 경비(총액 및 1인당 금액) 산출.
    3. 일정별 시간대별 최적 동선 타임테이블(Day 1, Day 2 등)을 6~7개 시간대로 상세 구성.
    4. 숙소는 반드시 {people_count} 맞춤 객실 타입으로 추천.
    5. 목적지 맞춤 3~4개 테마(숙소, 숨은맛집, 액티비티, 핵심명소) 가이드.
    6. 각 항목마다 예상 가격(price) 명시.

    반드시 아래 JSON 포맷으로만 응답하세요:
    {{
      "itinerary_page": {{
        "title": "{destination} 맞춤 이동 동선 & {duration} 완벽 일정표",
        "bg_color": "#0F172A",
        "route_info": {{
          "transport": "추천 이동수단/경로",
          "est_time": "예상 소요 시간",
          "rec_departure": "추천 출발 시간",
          "traffic_tip": "교통 팁"
        }},
        "budget_info": {{
          "people_desc": "{people_count} 기준 예상 총 경비",
          "transport_cost": "교통비 약 X원",
          "stay_cost": "숙박비 약 X원",
          "food_cost": "식비/카페 약 X원",
          "activity_cost": "체험비 약 X원",
          "total_estimated": "총 약 X원 ({people_count} 기준 / 1인당 약 X원)"
        }},
        "days": [
          {{
            "day_title": "Day 1 : 핵심 명소 투어",
            "schedule": [
              {{"time": "08:00 ~ 10:20", "activity": "{origin} 출발 -> {destination} 도착"}},
              {{"time": "10:20 ~ 12:00", "activity": "명소 및 포토존 탐방"}},
              {{"time": "12:00 ~ 13:30", "activity": "현지 로컬 숨은 맛집 점심 식사"}},
              {{"time": "13:30 ~ 15:30", "activity": "지역 힐링 산책로 트레킹"}},
              {{"time": "15:30 ~ 17:00", "activity": "카페 디저트 타임"}},
              {{"time": "17:00 ~ 18:30", "activity": "특산물 시장 및 저녁 식사"}},
              {{"time": "18:30 ~ 20:30", "activity": "일정 마무리 및 숙소 체크인/복귀"}}
            ]
          }}
        ]
      }},
      "sections": [
        {{
          "category": "추천 숙소 & 펜션 ({people_count} 맞춤)",
          "icon": "🏡",
          "bg_color": "#1E3A8A",
          "subtitle": "{people_count} 맞춤 엄선 숙소",
          "guide_tips": ["추가요금 확인", "바비큐 사전 문의", "입실/퇴실 시간 준수", "주차 확인"],
          "items": [
            {{"name": "숙소 1", "tag": "{people_count} 추천룸", "desc": "상세설명", "price": "1박 약 X원~", "address": "위치", "tip": "팁"}},
            {{"name": "숙소 2", "tag": "{people_count} 추천룸", "desc": "상세설명", "price": "1박 약 X원~", "address": "위치", "tip": "팁"}},
            {{"name": "숙소 3", "tag": "{people_count} 추천룸", "desc": "상세설명", "price": "1박 약 X원~", "address": "위치", "tip": "팁"}},
            {{"name": "숙소 4", "tag": "{people_count} 추천룸", "desc": "상세설명", "price": "1박 약 X원~", "address": "위치", "tip": "팁"}}
          ]
        }},
        {{
          "category": "로컬 숨은 맛집 & 대표 먹거리",
          "icon": "🍽️",
          "bg_color": "#B45309",
          "subtitle": "현지인 추천 대표 맛집",
          "guide_tips": ["웨이팅 유의", "재료소진 확인", "주차 확인", "대표메뉴 추천"],
          "items": [
            {{"name": "맛집 1", "tag": "대표메뉴", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "맛집 2", "tag": "대표메뉴", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "맛집 3", "tag": "대표메뉴", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "맛집 4", "tag": "대표메뉴", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}}
          ]
        }},
        {{
          "category": "핵심 명소 & 필수 체험",
          "icon": "🏄",
          "bg_color": "#047857",
          "subtitle": "{destination} 필수 관광 명소",
          "guide_tips": ["사전 예매 할인", "운영시간 확인", "편한 복장", "포토존 확인"],
          "items": [
            {{"name": "명소 1", "tag": "필수코스", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "명소 2", "tag": "필수코스", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "명소 3", "tag": "필수코스", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}},
            {{"name": "명소 4", "tag": "필수코스", "desc": "상세설명", "price": "약 X원", "address": "위치", "tip": "팁"}}
          ]
        }}
      ]
    }}
    """
    candidate_models = ['gemini-2.5-flash', 'gemini-3.5-flash-lite', 'gemini-3.5-flash']
    last_err = None
    for model_name in candidate_models:
        for _ in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={'response_mime_type': 'application/json'}
                )
                raw_text = response.text.strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip())
            except Exception as e:
                last_err = e
                time.sleep(2)
                continue
    raise last_err

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    def draw_page_number(self, page_count):
        self.setFont(FONT_NAME, 9.5)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawRightString(815, 12, f"Page {self._pageNumber} / {page_count}")

def build_pdf_bytes(origin, destination, duration, people_count):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        leftMargin=18,
        rightMargin=18,
        topMargin=15,
        bottomMargin=15
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('MainTitle', fontName=FONT_NAME, fontSize=18, textColor=colors.white, leading=22)
    sub_style = ParagraphStyle('MainSub', fontName=FONT_NAME, fontSize=10, textColor=colors.HexColor("#E2E8F0"), leading=13)
    sec_badge_style = ParagraphStyle('SecBadge', fontName=FONT_NAME, fontSize=11.5, textColor=colors.HexColor("#1E3A8A"), leading=15)
    item_title_style = ParagraphStyle('ItemTitle', fontName=FONT_NAME, fontSize=12.5, textColor=colors.HexColor("#0F172A"), leading=16)
    tag_style = ParagraphStyle('Tag', fontName=FONT_NAME, fontSize=9.5, textColor=colors.HexColor("#2563EB"), leading=12)
    desc_style = ParagraphStyle('Desc', fontName=FONT_NAME, fontSize=10, textColor=colors.HexColor("#334155"), leading=15)
    price_style = ParagraphStyle('Price', fontName=FONT_NAME, fontSize=10, textColor=colors.HexColor("#B91C1C"), leading=14)
    info_style = ParagraphStyle('Info', fontName=FONT_NAME, fontSize=9, textColor=colors.HexColor("#475569"), leading=13)
    guide_text_style = ParagraphStyle('GuideText', fontName=FONT_NAME, fontSize=9.5, textColor=colors.HexColor("#334155"), leading=16)
    sched_time_style = ParagraphStyle('SchedTime', fontName=FONT_NAME, fontSize=11.5, textColor=colors.HexColor("#0F172A"), leading=16)
    sched_act_style = ParagraphStyle('SchedAct', fontName=FONT_NAME, fontSize=11.5, textColor=colors.HexColor("#334155"), leading=17)
    day_head_style = ParagraphStyle('DayHead', fontName=FONT_NAME, fontSize=12.5, textColor=colors.HexColor("#1E293B"), leading=16)

    data = fetch_realtime_travel_plan(origin, destination, duration, people_count)
    elements = []

    # 1페이지
    itin = data.get("itinerary_page", {})
    route = itin.get("route_info", {})
    budget = itin.get("budget_info", {})
    
    header_data = [
        [Paragraph(f"<b>[{destination}] {origin} 출발 -> {destination} 이동 동선 & {duration} 시간표 ({people_count})</b>", title_style)],
        [Paragraph(f"출발지({origin}) 기준 소요 시간, {people_count} 맞춤 실시간 예상 경비 및 최적 동선 가이드입니다.", sub_style)]
    ]
    header_table = Table(header_data, colWidths=[805])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(itin.get("bg_color", "#0F172A"))),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))

    route_box_data = [
        [Paragraph("<b>🚗 이동 동선 및 교통 정보</b>", sec_badge_style)],
        [Paragraph(f"• <b>경로:</b> {route.get('transport', '-')}<br/>• <b>예상 소요시간:</b> {route.get('est_time', '-')}<br/>• <b>권장 출발:</b> {route.get('rec_departure', '-')}<br/>• <b>교통 팁:</b> {route.get('traffic_tip', '-')}", guide_text_style)]
    ]
    route_table = Table(route_box_data, colWidths=[285])
    route_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.7, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))

    budget_badge_style = ParagraphStyle('BudBadge', fontName=FONT_NAME, fontSize=11, textColor=colors.HexColor("#B91C1C"), leading=14)
    budget_total_style = ParagraphStyle('BudTotal', fontName=FONT_NAME, fontSize=10, textColor=colors.HexColor("#B91C1C"), leading=14)
    budget_box_data = [
        [Paragraph(f"<b>💰 {budget.get('people_desc', f'{people_count} 맞춤 예상 경비')}</b>", budget_badge_style)],
        [Paragraph(f"• <b>교통비:</b> {budget.get('transport_cost', '-')}<br/>• <b>숙박비:</b> {budget.get('stay_cost', '-')}<br/>• <b>식사/카페:</b> {budget.get('food_cost', '-')}<br/>• <b>체험/기타:</b> {budget.get('activity_cost', '-')}", guide_text_style)],
        [Paragraph(f"<b>총액:</b> {budget.get('total_estimated', '-')}", budget_total_style)]
    ]
    budget_table = Table(budget_box_data, colWidths=[285])
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF2F2")),
        ('BOX', (0,0), (-1,-1), 0.7, colors.HexColor("#FECACA")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,1), (-1,1), 0.5, colors.HexColor("#FCA5A5")),
    ]))

    first_banner = create_theme_banner_image(f"{destination} ROAD TRIP", f"{origin} -> {destination} ({duration})", bg_hex="#1E293B", width=570, height=270)
    left_itin_flow = [route_table, Spacer(1, 8), budget_table, Spacer(1, 8), first_banner]

    right_itin_flow = []
    days = itin.get("days", [])
    for d_idx, d in enumerate(days):
        day_rows = [[Paragraph(f"<b>📅 {d.get('day_title', f'Day {d_idx+1}')}</b>", day_head_style), Paragraph("", day_head_style)]]
        for s in d.get("schedule", []):
            day_rows.append([
                Paragraph(f"<b>{s.get('time', '-')}</b>", sched_time_style),
                Paragraph(s.get('activity', '-'), sched_act_style)
            ])
        day_table = Table(day_rows, colWidths=[120, 390])
        day_table.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#FFFFFF")),
            ('BOX', (0,0), (-1,-1), 0.7, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('PADDING', (0,0), (-1,-1), 14),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        right_itin_flow.append(day_table)
        if d_idx < len(days) - 1:
            right_itin_flow.append(Spacer(1, 8))

    itin_page_table = Table([[left_itin_flow, right_itin_flow]], colWidths=[290, 515])
    itin_page_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(itin_page_table)
    elements.append(PageBreak())

    # 2페이지 이후
    sections = data.get("sections", [])
    for sec_idx, sec in enumerate(sections):
        sec_name = sec.get('category', '여행 가이드')
        subtitle = sec.get('subtitle', f"{destination} 지역의 엄선 가이드입니다.")
        bg_col = sec.get('bg_color', '#1E3A8A')

        header_data = [
            [Paragraph(f"<b>[{destination}] 테마 가이드 : {sec.get('icon', '📍')} {sec_name}</b>", title_style)],
            [Paragraph(subtitle, sub_style)]
        ]
        header_table = Table(header_data, colWidths=[805])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_col)),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 8))

        theme_banner = create_theme_banner_image(sec_name.split(' ')[0], f"{destination} SPECIAL", bg_hex=bg_col, width=570, height=360)
        tips = sec.get('guide_tips', ["사전 예약 필수", "현장 상황 확인"])
        tips_html = "<br/>".join([f"• {tip}" for tip in tips])
        guide_box_data = [
            [Paragraph(f"<b>💡 이용 꿀팁 & 가이드</b>", sec_badge_style)],
            [Paragraph(tips_html, guide_text_style)]
        ]
        guide_table = Table(guide_box_data, colWidths=[285])
        guide_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('PADDING', (0,0), (-1,-1), 12),
        ]))
        left_flow = [theme_banner, Spacer(1, 10), guide_table]

        right_flow = []
        for idx, item in enumerate(sec.get('items', []), 1):
            item_table_data = [
                [Paragraph(f"<b>{idx}. {item['name']}</b>", item_title_style), Paragraph(f"<b>[{item.get('tag', '추천')}]</b>", tag_style)],
                [Paragraph(item.get('desc', ''), desc_style), Paragraph("", desc_style)],
                [Paragraph(f"💵 <b>예상 가격:</b> {item.get('price', '현장 확인')}", price_style), Paragraph("", price_style)],
                [Paragraph(f"📍 <b>위치:</b> {item.get('address', '-')}  |  💡 <b>팁:</b> {item.get('tip', '-')}", info_style), Paragraph("", info_style)]
            ]
            item_table = Table(item_table_data, colWidths=[395, 115])
            item_table.setStyle(TableStyle([
                ('SPAN', (0, 1), (1, 1)),
                ('SPAN', (0, 2), (1, 2)),
                ('SPAN', (0, 3), (1, 3)),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
                ('BOX', (0,0), (-1,-1), 0.6, colors.HexColor("#CBD5E1")),
                ('PADDING', (0,0), (-1,-1), 11),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ]))
            right_flow.append(item_table)
            if idx < len(sec.get('items', [])):
                right_flow.append(Spacer(1, 8))

        main_page_table = Table([[left_flow, right_flow]], colWidths=[290, 515])
        main_page_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('PADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(main_page_table)
        if sec_idx < len(sections) - 1:
            elements.append(PageBreak())

    doc.build(elements, canvasmaker=NumberedCanvas)
    pdf_buffer.seek(0)
    return pdf_buffer

# ----------------- 모바일 웹 UI -----------------
st.title("🚗 AI 맞춤 여행 가이드")
st.caption("출발지, 목적지, 일정, 인원수에 맞춘 PDF 일정표를 생성합니다.")

col1, col2 = st.columns(2)
with col1:
    origin = st.text_input("📍 출발지", value="여주")
    duration = st.selectbox("⏱️ 여행 기간", ["당일치기", "1박2일", "2박3일", "3박4일"])
with col2:
    destination = st.text_input("🎯 목적지", value="맹방해수욕장")
    people_count = st.text_input("👥 여행 인원", value="2명")

if st.button("🚀 여행 가이드 PDF 생성하기", use_container_width=True, type="primary"):
    with st.spinner("AI가 실시간 일정, 예상 경비, 맞춤 숙소를 기획하고 있습니다..."):
        try:
            pdf_bytes = build_pdf_bytes(origin, destination, duration, people_count)
            st.success("✅ 생성이 완료되었습니다! 아래 버튼을 눌러 PDF를 다운로드하세요.")
            st.download_button(
                label="📥 완성된 PDF 가이드 다운로드",
                data=pdf_bytes,
                file_name=f"[{origin}출발]_{destination}_{duration}_{people_count}_여행가이드.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")