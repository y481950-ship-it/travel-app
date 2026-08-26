from flask import Flask, request, jsonify, send_file, render_template_string, Response, send_from_directory
import google.generativeai as genai
import os
import io
import re
import json
import xml.sax.saxutils as saxutils
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import urllib.request
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)

# 한글 폰트 설정
FONT_PATH = "NanumGothic.ttf"
if not os.path.exists(FONT_PATH):
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        urllib.request.urlretrieve(url, FONT_PATH)
    except Exception:
        pass

if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("NanumGothic", FONT_PATH))
    MAIN_FONT = "NanumGothic"
else:
    MAIN_FONT = "Helvetica"

API_KEY = "AQ.Ab8RN6KNyTYb9CRCpApOtdKKdV5AhjT07NZ5PVbe7ZSIzCXOPw"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#1e3d59">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="AI여행플래너">

    <title>박영선의 AI 맞춤 여행 플래너</title>
    
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-512.png">
    <link rel="icon" type="image/png" href="/icon-512.png">

    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f6f9; color: #333; padding: 14px; font-size: 15px; line-height: 1.5; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
        h1 { font-size: 1.35rem; color: #1e3d59; margin-bottom: 18px; text-align: center; font-weight: bold; }
        .section-title { font-size: 0.95rem; font-weight: bold; margin: 14px 0 6px 0; color: #222; }
        .radio-group, .checkbox-group { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
        .radio-group label, .checkbox-group label { background: #f1f3f5; padding: 7px 11px; border-radius: 8px; font-size: 0.9rem; cursor: pointer; display: flex; align-items: center; gap: 5px; }
        input[type="text"], input[type="number"] { width: 100%; padding: 11px; border: 1px solid #ced4da; border-radius: 8px; font-size: 0.95rem; margin-bottom: 10px; }
        button { width: 100%; padding: 13px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 1.05rem; font-weight: bold; cursor: pointer; margin-top: 10px; }
        #loading { display: none; text-align: center; padding: 24px; font-weight: bold; color: #1a73e8; font-size: 1.05rem; }
        #result-area { display: none; margin-top: 16px; }
        .btn-group { display: flex; gap: 8px; margin-bottom: 14px; }
        .btn-group button { margin-top: 0; }
        .btn-reset { background: #6c757d; }
        .btn-pdf { background: #28a745; }
        .plan-content { background: #fafafa; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; font-size: 0.95rem; line-height: 1.6; }
        .plan-content h1 { font-size: 1.25rem; color: #1e3d59; text-align: left; margin: 16px 0 8px; border-bottom: 2px solid #1e3d59; padding-bottom: 4px; }
        .plan-content h2 { font-size: 1.1rem; color: #0b7285; margin: 14px 0 6px; }
        .plan-content h3 { font-size: 1rem; color: #2b8a3e; margin: 10px 0 4px; }
        .plan-content a { color: #1a73e8; font-weight: bold; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏍️ 박영선의 AI 맞춤 여행 플래너</h1>
        
        <form id="plan-form">
            <div class="section-title">1. 지역 구분</div>
            <div class="radio-group">
                <label><input type="radio" name="region_type" value="국내" checked onchange="toggleRegion()"> 🇰🇷 국내</label>
                <label><input type="radio" name="region_type" value="해외" onchange="toggleRegion()"> ✈️ 해외</label>
            </div>

            <div id="domestic-start">
                <div class="section-title">2. 출발지 설정</div>
                <div class="radio-group">
                    <label><input type="radio" name="start_mode" value="default" checked onchange="toggleStartInput()"> 📍 현재 위치 (경기 여주)</label>
                    <label><input type="radio" name="start_mode" value="custom" onchange="toggleStartInput()"> ✏️ 직접 입력</label>
                </div>
            </div>

            <input type="text" id="start_location" placeholder="출발지 입력" style="display: none;">
            
            <div class="section-title">3. 목적지</div>
            <input type="text" id="destination" placeholder="예: 영월, 속초, 삼척, 노지 주소 등" required>

            <div class="section-title">4. 인원수</div>
            <div class="radio-group">
                <label><input type="radio" name="headcount" value="1명(솔투)" checked onchange="toggleHeadcountInput()"> 👤 1인(솔투)</label>
                <label><input type="radio" name="headcount" value="2명" onchange="toggleHeadcountInput()"> 👥 2인</label>
                <label><input type="radio" name="headcount" value="3~4명" onchange="toggleHeadcountInput()"> 👨‍👩‍👧 3~4인</label>
                <label><input type="radio" name="headcount" value="custom" onchange="toggleHeadcountInput()"> 🚌 단체 (직접 입력)</label>
            </div>
            <input type="number" id="custom_headcount" placeholder="단체 인원수 입력 (숫자만, 예: 8)" style="display: none;" min="1">

            <div class="section-title">5. 여행 기간</div>
            <div class="radio-group">
                <label><input type="radio" name="duration" value="당일치기" checked> 당일치기</label>
                <label><input type="radio" name="duration" value="1박 2일"> 1박 2일</label>
                <label><input type="radio" name="duration" value="2박 3일"> 2박 3일</label>
                <label><input type="radio" name="duration" value="3박 4일 이상"> 3박 4일 이상</label>
            </div>

            <div class="section-title">6. 필수 포함 추천 옵션</div>
            <div class="checkbox-group">
                <label><input type="checkbox" id="include_food" checked> 🍲 로컬 맛집/노포</label>
                <label><input type="checkbox" id="include_stay" checked> 🛏️ 가성비 숙소(호텔/펜션)</label>
                <label><input type="checkbox" id="include_activity" checked> 🏄 액티비티/체험</label>
                <label><input type="checkbox" id="include_fishing" checked> 🎣 선상 낚시(베테랑 선장)</label>
            </div>

            <div class="section-title">7. 여행 스타일 (중복 선택 가능)</div>
            <div class="checkbox-group">
                <label><input type="checkbox" name="travel_style" value="자연/풍경 감상" checked> 🏞️ 자연/풍경</label>
                <label><input type="checkbox" name="travel_style" value="맛집/카페 투어" checked> ☕ 맛집/카페</label>
                <label><input type="checkbox" name="travel_style" value="관광지 탐방"> 🏛️ 관광지 탐방</label>
                <label><input type="checkbox" name="travel_style" value="휴양/힐링"> 🧘 휴양/힐링</label>
            </div>

            <div class="section-title">8. 경로 설정</div>
            <div class="checkbox-group">
                <label><input type="checkbox" id="is_bike_mode" checked onchange="toggleAvoidRoad()"> 🏍️ 바이크 전용 경로</label>
                <label id="avoid_road_label"><input type="checkbox" id="avoid_large_roads" checked> 🚜 4차선 대로 완전 배제</label>
            </div>

            <button type="button" id="submit-btn" onclick="generatePlan()">🚀 맞춤 일정 생성하기</button>
        </form>

        <div id="loading">⏳ 최적의 여행 코스와 추천 정보를 구성하고 있습니다...</div>

        <div id="result-area">
            <div class="btn-group">
                <button class="btn-reset" onclick="resetForm()">🔄 다시 설정하기</button>
                <button class="btn-pdf" onclick="downloadPdf()">📄 핵심 견적서 PDF</button>
            </div>
            <div class="plan-content" id="plan-display"></div>
        </div>
    </div>

    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }

        let currentPayload = {};

        function toggleRegion() {
            const isDomestic = document.querySelector('input[name="region_type"]:checked').value === '국내';
            document.getElementById('domestic-start').style.display = isDomestic ? 'block' : 'none';
            if (!isDomestic) {
                document.getElementById('start_location').style.display = 'block';
                document.getElementById('start_location').placeholder = '출발지 (공항/도시 입력)';
            } else {
                toggleStartInput();
            }
        }

        function toggleStartInput() {
            const isCustom = document.querySelector('input[name="start_mode"]:checked').value === 'custom';
            const input = document.getElementById('start_location');
            input.style.display = isCustom ? 'block' : 'none';
            input.placeholder = '출발지 입력 (예: 서울 강남, 수원)';
        }

        function toggleHeadcountInput() {
            const isCustom = document.querySelector('input[name="headcount"]:checked').value === 'custom';
            document.getElementById('custom_headcount').style.display = isCustom ? 'block' : 'none';
        }

        function toggleAvoidRoad() {
            const isBike = document.getElementById('is_bike_mode').checked;
            const avoidLabel = document.getElementById('avoid_road_label');
            if (avoidLabel) avoidLabel.style.display = isBike ? 'inline-flex' : 'none';
        }

        async function generatePlan() {
            const destination = document.getElementById('destination').value.trim();
            if (!destination) { alert('목적지를 입력해주세요.'); return; }

            const regionType = document.querySelector('input[name="region_type"]:checked').value;
            let startLocation = "경기 여주(현재 위치)";
            if (regionType === '해외' || document.querySelector('input[name="start_mode"]:checked').value === 'custom') {
                startLocation = document.getElementById('start_location').value.trim();
                if (!startLocation) { alert('출발지를 입력해주세요.'); return; }
            }

            let headcountVal = document.querySelector('input[name="headcount"]:checked').value;
            if (headcountVal === 'custom') {
                const cVal = document.getElementById('custom_headcount').value.trim();
                if (!cVal || parseInt(cVal) < 1) { alert('정확한 단체 인원수를 입력해주세요.'); return; }
                headcountVal = `${cVal}명(단체)`;
            }

            const isBike = document.getElementById('is_bike_mode').checked;
            const avoidRoadEl = document.getElementById('avoid_large_roads');
            const avoidLargeRoads = isBike && avoidRoadEl ? avoidRoadEl.checked : false;

            const selectedStyles = Array.from(document.querySelectorAll('input[name="travel_style"]:checked')).map(el => el.value);
            const styleString = selectedStyles.length > 0 ? selectedStyles.join(', ') : '자유 여행';

            currentPayload = {
                region_type: regionType,
                start_location: startLocation,
                destination: destination,
                headcount: headcountVal,
                duration: document.querySelector('input[name="duration"]:checked').value,
                include_food: document.getElementById('include_food').checked,
                include_stay: document.getElementById('include_stay').checked,
                include_activity: document.getElementById('include_activity').checked,
                include_fishing: document.getElementById('include_fishing').checked,
                is_bike_mode: isBike,
                avoid_large_roads: avoidLargeRoads,
                styles: styleString
            };

            document.getElementById('plan-form').style.display = 'none';
            document.getElementById('loading').style.display = 'block';

            try {
                const res = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentPayload)
                });
                
                const data = await res.json();
                
                if (!res.ok || data.error) {
                    alert(data.error || '생성 중 오류가 발생했습니다.');
                    resetForm();
                    return;
                }

                document.getElementById('plan-display').innerHTML = data.html_text;
                document.getElementById('loading').style.display = 'none';
                document.getElementById('result-area').style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } catch (err) {
                alert('서버 응답 오류: 잠시 후 다시 시도해주세요.');
                resetForm();
            }
        }

        function resetForm() {
            document.getElementById('result-area').style.display = 'none';
            document.getElementById('loading').style.display = 'none';
            document.getElementById('plan-form').style.display = 'block';
        }

        function downloadPdf() {
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/download_pdf';

            for (const key in currentPayload) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = key;
                input.value = currentPayload[key];
                form.appendChild(input);
            }

            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        }
    </script>
</body>
</html>
"""

def markdown_to_html(text):
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    text = re.sub(r'^### (.*$)', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*$)', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*$)', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = text.replace('\n', '<br>')
    return text

@app.route('/icon-512.png')
def custom_icon():
    return send_from_directory(os.getcwd(), 'icon-512.png')

@app.route('/sw.js')
def service_worker():
    sw_code = "self.addEventListener('install', (e) => self.skipWaiting()); self.addEventListener('activate', (e) => self.clients.claim()); self.addEventListener('fetch', (e) => {});"
    return Response(sw_code, mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    manifest_data = {
        "name": "박영선의 AI 맞춤 여행 플래너",
        "short_name": "AI여행플래너",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1e3d59",
        "icons": [
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return Response(json.dumps(manifest_data), mimetype='application/json')

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json(force=True)
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-3.6-flash")

        options = []
        if data.get('include_food'):
            options.append("- 로컬 맛집: 현지인 추천 찐 맛집/노포 2~3곳과 지도 링크")
        if data.get('include_stay'):
            options.append("- 가성비 숙소: 평점 높은 가성비 숙소 1~2곳과 지도 링크")
        if data.get('include_activity'):
            options.append("- 액티비티/체험: 현지 대표 레저 및 이색 체험과 지도 링크")
        if data.get('include_fishing'):
            options.append("- 선상 낚시: 바다권일 경우 검증된 선단 정보와 지도 링크")

        options_text = "\n".join(options)

        prompt = f"""
        당신은 대한민국 최고의 바이크 투어링 및 여행 코스 기획 전문가입니다.
        사용자는 **카카오맵 네비게이션**을 단독으로 사용합니다.

        [조건]
        - 지역: {data.get('region_type')} | 출발지: {data.get('start_location')} | 목적지: {data.get('destination')}
        - 인원: {data.get('headcount')} | 일정: {data.get('duration')} | 스타일: {data.get('styles')}

        [필수 추천]
        {options_text}
        """

        if data.get('is_bike_mode'):
            prompt += """
        [바이크 전용 경로 규칙 - 카카오맵 최적화 & 4차선 원천 차단 지침]
        1. 자동차 전용도로 및 고속도로 절대 금지.
        2. 출발 직후 첫 경유지는 출발지 바로 앞이 아닌, 목적지 방향으로 최소 50분~1시간 주행한 지점부터 지정할 것.
        3. 카카오맵 검색창에 바로 입력할 수 있도록 정확한 **[카카오맵 검색용 명칭]**(정확한 교차로/삼거리명, 고개/재/령 정상 휴게소, 랜드마크 지번)을 번호순으로 명시할 것.
        """
            if data.get('avoid_large_roads'):
                prompt += """
        4. [4차선 국도/대로 완전 배제 & 촘촘한 갈림길 경유지 필수]:
           - 카카오맵 네비가 4차선 직선 국도(예: 6번, 42번, 44번, 7번 등)나 터널로 길을 틀지 못하도록, **4차선 합류 직전의 '옛길(구길) 입구 삼거리', '회전교차로', '2차선 지방도 진입로', '해안 안길'**을 촘촘하게 방어 경유지로 반드시 꽂아줄 것.
           - 지루한 4차선 대신 바이커들이 선호하는 **2차선 강변/계곡 지방도, 숨겨진 고갯길 와인딩 코스**만 연결할 것.
           - 각 경유지마다 [카카오맵 입력 지점명]과 [해당 도로의 라이딩 포인트]를 함께 적을 것.
        """
        else:
            prompt += f"""
        [일반 모드 규칙]
        - 목적지({data.get('destination')}) 현지의 명소, 체험, 맛집 위주로 알차게 구성.
        """

        if data.get('region_type') == "국내":
            prompt += """
        [지도 링크]
        주요 장소명 및 경유지명 뒤에 카카오맵 링크를 필수로 생성: [카카오맵](https://map.kakao.com/link/search/{장소명}) | [네이버지도](https://map.naver.com/v5/search/{장소명})
            """
        else:
            prompt += """
        [지도 링크]
        [구글지도](https://www.google.com/maps/search/?api=1&query={장소명})
            """

        prompt += f"""
        [출력 양식]
        # {data.get('destination')} 맞춤 여행 코스 ({data.get('headcount')}, {data.get('duration')})
        ## 1. 최적 라이딩/여행 코스 (카카오맵 네비 입력용 촘촘한 경유지 포함)
        ## 2. 현지 로컬 맛집 & 노포
        ## 3. 추천 숙소
        ## 4. 액티비티 & 이색 체험
        ## 5. 선상 낚시 (해당 시)
        ## 6. 라이딩/여행 꿀팁 및 코너링 주의구간
        """

        response = model.generate_content(prompt)
        raw_text = response.text
        html_text = markdown_to_html(raw_text)

        return jsonify({'raw_text': raw_text, 'html_text': html_text})
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Quota exceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return jsonify({'error': '⚠️ 오늘 무료 AI 사용량(20회)이 모두 소진되었습니다.\n한국 시간 기준 내일 오후 4시에 자동 초기화됩니다.'}), 429
        return jsonify({'error': f'오류 발생: {err_msg}'}), 500

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    try:
        destination = request.form.get('destination', '맞춤')
        headcount = request.form.get('headcount', '1명')
        duration = request.form.get('duration', '당일치기')
        styles = request.form.get('styles', '자유 여행')

        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-3.6-flash")

        pdf_prompt = f"""
        PDF 인쇄용 [여행 견적 및 핵심 요약서]를 간결히 작성하세요. 이동 코스는 제외하고 정산표와 핵심 장소만 적으세요.
        - 목적지: {destination} | 인원: {headcount} | 일정: {duration} | 스타일: {styles}

        # {destination} 여행 핵심 견적서 ({headcount}, {duration})
        ## 1. 예상 경비 견적표
        - 식비/숙박비/체험비/교통비 항목별 산출
        - [1인당 총 예상 경비]: OOO원
        - [{headcount} 전체 총 예상 경비]: OOO원
        ## 2. 엄선 맛집 / 숙소 / 액티비티 요약
        """

        res = model.generate_content(pdf_prompt)
        pdf_text = res.text

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=28,
            leftMargin=28,
            topMargin=30,
            bottomMargin=30
        )

        styles_set = getSampleStyleSheet()

        body_style = ParagraphStyle(
            name='PdfBody',
            fontName=MAIN_FONT,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor('#222222'),
            spaceAfter=4
        )
        h1_style = ParagraphStyle(
            name='PdfH1',
            fontName=MAIN_FONT,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1e3d59'),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True
        )
        h2_style = ParagraphStyle(
            name='PdfH2',
            fontName=MAIN_FONT,
            fontSize=11.5,
            leading=16,
            textColor=colors.HexColor('#0b7285'),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )

        story = []
        lines = pdf_text.split('\n')

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith('---'):
                story.append(Spacer(1, 4))
                continue

            safe_text = saxutils.escape(line_str)
            safe_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_text)

            if line_str.startswith('# '):
                clean_h1 = re.sub(r'^#\s*', '', safe_text)
                story.append(Paragraph(clean_h1, h1_style))
            elif line_str.startswith('## '):
                clean_h2 = re.sub(r'^##\s*', '', safe_text)
                story.append(Paragraph(clean_h2, h2_style))
            elif line_str.startswith('### '):
                clean_h3 = re.sub(r'^###\s*', '', safe_text)
                story.append(Paragraph(clean_h3, h2_style))
            else:
                story.append(Paragraph(safe_text, body_style))

        doc.build(story)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{destination}_여행견적서.pdf",
            mimetype="application/pdf"
        )
    except Exception as e:
        return f"PDF 생성 중 오류 발생: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
