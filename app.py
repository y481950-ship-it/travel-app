from flask import Flask, request, jsonify, send_file, render_template_string
import google.generativeai as genai
import os
import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
    <title>박영선의 AI 여행 플래너</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8f9fa; color: #333; padding: 16px; font-size: 16px; line-height: 1.6; }
        .container { max-width: 600px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        h1 { font-size: 1.4rem; color: #1e3d59; margin-bottom: 20px; text-align: center; }
        .section-title { font-size: 1rem; font-weight: bold; margin: 15px 0 8px 0; color: #222; }
        .radio-group, .checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
        .radio-group label, .checkbox-group label { background: #f1f3f5; padding: 8px 12px; border-radius: 8px; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; gap: 6px; }
        input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ced4da; border-radius: 8px; font-size: 1rem; margin-bottom: 12px; }
        button { width: 100%; padding: 14px; background: #1a73e8; color: #fff; border: none; border-radius: 8px; font-size: 1.1rem; font-weight: bold; cursor: pointer; margin-top: 10px; }
        #loading { display: none; text-align: center; padding: 20px; font-weight: bold; color: #1a73e8; }
        #result-area { display: none; margin-top: 20px; }
        .btn-group { display: flex; gap: 10px; margin-bottom: 15px; }
        .btn-group button { margin-top: 0; }
        .btn-reset { background: #6c757d; }
        .btn-pdf { background: #28a745; }
        .plan-content { background: #fdfdfd; border: 1px solid #e9ecef; padding: 16px; border-radius: 8px; font-size: 1.05rem; }
        .plan-content h1 { font-size: 1.3rem; color: #111; text-align: left; margin: 15px 0 8px; }
        .plan-content h2 { font-size: 1.15rem; color: #1e3d59; margin: 12px 0 6px; }
        .plan-content h3 { font-size: 1.05rem; color: #17b978; margin: 10px 0 4px; }
        .plan-content a { color: #1a73e8; font-weight: bold; text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏍️ 박영선의 AI 여행 플래너</h1>
        
        <form id="plan-form">
            <div class="section-title">지역 구분</div>
            <div class="radio-group">
                <label><input type="radio" name="region_type" value="국내" checked onchange="toggleRegion()"> 🇰🇷 국내</label>
                <label><input type="radio" name="region_type" value="해외" onchange="toggleRegion()"> ✈️ 해외</label>
            </div>

            <div id="domestic-start">
                <div class="section-title">출발지 설정</div>
                <div class="radio-group">
                    <label><input type="radio" name="start_mode" value="default" checked onchange="toggleStartInput()"> 📍 현재 위치 (경기 여주)</label>
                    <label><input type="radio" name="start_mode" value="custom" onchange="toggleStartInput()"> ✏️ 직접 입력</label>
                </div>
            </div>

            <input type="text" id="start_location" placeholder="출발지 입력" style="display: none;">
            
            <div class="section-title">목적지</div>
            <input type="text" id="destination" placeholder="예: 영월, 속초, 낙산사" required>

            <div class="section-title">여행 기간</div>
            <div class="radio-group">
                <label><input type="radio" name="duration" value="당일치기" checked> 당일치기</label>
                <label><input type="radio" name="duration" value="1박 2일"> 1박 2일</label>
                <label><input type="radio" name="duration" value="2박 3일"> 2박 3일</label>
                <label><input type="radio" name="duration" value="3박 4일"> 3박 4일</label>
                <label><input type="radio" name="duration" value="4박 5일 이상"> 4박 5일 이상</label>
            </div>

            <div class="checkbox-group">
                <label><input type="checkbox" id="is_bike_mode" checked onchange="toggleAvoidRoad()"> 🏍️ 바이크 전용 경로</label>
                <label id="avoid_road_label"><input type="checkbox" id="avoid_large_roads" checked> 🚜 4차선 대로 완전 배제</label>
            </div>

            <div class="section-title">여행 스타일</div>
            <div class="radio-group">
                <label><input type="radio" name="style" value="자연/풍경 감상" checked> 자연/풍경</label>
                <label><input type="radio" name="style" value="맛집/카페 투어"> 맛집/카페</label>
                <label><input type="radio" name="style" value="관광지 위주"> 관광지</label>
                <label><input type="radio" name="style" value="휴양/힐링"> 휴양/힐링</label>
            </div>

            <div class="section-title">기타 요청사항</div>
            <input type="text" id="extra_requests" placeholder="예: 한적한 와인딩 코스, 뷰 맛집 위주">

            <button type="button" id="submit-btn" onclick="generatePlan()">🚀 일정 생성하기</button>
        </form>

        <div id="loading">⏳ 최적의 여행 코스를 구성하고 있습니다...</div>

        <div id="result-area">
            <div class="btn-group">
                <button class="btn-reset" onclick="resetForm()">🔄 다시 설정하기</button>
                <button class="btn-pdf" onclick="downloadPdf()">📄 PDF 다운로드</button>
            </div>
            <div class="plan-content" id="plan-display"></div>
        </div>
    </div>

    <script>
        let rawPlanText = "";

        function toggleRegion() {
            const isDomestic = document.querySelector('input[name="region_type"]:checked').value === '국내';
            document.getElementById('domestic-start').style.display = isDomestic ? 'block' : 'none';
            if (!isDomestic) {
                document.getElementById('start_location').style.display = 'block';
                document.getElementById('start_location').placeholder = '출발지 (공항/항구/도시 입력)';
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

        function toggleAvoidRoad() {
            const isBike = document.getElementById('is_bike_mode').checked;
            document.getElementById('avoid_road_label').style.display = isBike ? 'inline-flex' : 'none';
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

            document.getElementById('plan-form').style.display = 'none';
            document.getElementById('loading').style.display = 'block';

            const payload = {
                region_type: regionType,
                start_location: startLocation,
                destination: destination,
                duration: document.querySelector('input[name="duration"]:checked').value,
                is_bike_mode: document.getElementById('is_bike_mode').checked,
                avoid_large_roads: document.getElementById('avoid_large_roads').checked,
                style: document.querySelector('input[name="style"]:checked').value,
                extra_requests: document.getElementById('extra_requests').value.trim()
            };

            try {
                const res = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                if (!res.ok || data.error) {
                    alert('생성 오류가 발생했습니다: ' + (data.error || '응답 없음'));
                    resetForm();
                    return;
                }

                rawPlanText = data.raw_text;
                document.getElementById('plan-display').innerHTML = data.html_text;
                document.getElementById('loading').style.display = 'none';
                document.getElementById('result-area').style.display = 'block';
                window.scrollTo({ top: 0, behavior: 'smooth' });
            } catch (err) {
                alert('서버 응답 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
                resetForm();
            }
        }

        function resetForm() {
            document.getElementById('result-area').style.display = 'none';
            document.getElementById('loading').style.display = 'none';
            document.getElementById('plan-form').style.display = 'block';
        }

        function downloadPdf() {
            const destination = document.getElementById('destination').value.trim();
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/download_pdf';

            const inputDest = document.createElement('input');
            inputDest.type = 'hidden';
            inputDest.name = 'destination';
            inputDest.value = destination;

            const inputText = document.createElement('input');
            inputText.type = 'hidden';
            inputText.name = 'text_content';
            inputText.value = rawPlanText;

            form.appendChild(inputDest);
            form.appendChild(inputText);
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

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    try:
        genai.configure(api_key=API_KEY)
        
        # 생각 예산을 0으로 설정하여 딜레이 없이 즉시 답변하도록 생성
        model = genai.GenerativeModel(
            "gemini-3.6-flash",
            generation_config={"thinking_config": {"thinking_budget": 0}}
        )

        prompt = f"""
        다음 조건으로 간결하고 명확한 여행/라이딩 일정을 작성해줘.
        - 지역: {data['region_type']}
        - 출발지: {data['start_location']}
        - 목적지: {data['destination']}
        - 일정: {data['duration']}
        - 스타일: {data['style']}
        - 추가 요청: {data['extra_requests']}

        [규칙]
        - 출발지 인근 경유지는 배제하고 목적지 방향으로 최소 1시간 주행 후 첫 경유지가 나오게 할 것.
        """

        if data.get('is_bike_mode'):
            if data['region_type'] == "국내":
                prompt += "\n- 고속도로 및 자동차 전용도로 진입 금지."
            if data.get('avoid_large_roads'):
                prompt += "\n- 4차선 대로 배제, 한적한 2차선 지방도/국도 위주 코스."

        if data['region_type'] == "국내":
            prompt += """
        [지도 링크]
        - 경유지 장소명 뒤에 링크 표기: [네이버지도](https://map.naver.com/v5/search/{장소명}) | [카카오맵](https://map.kakao.com/link/search/{장소명})
            """
        else:
            prompt += """
        [해외 지도 링크]
        - 경유지 장소명 뒤에 링크 표기: [구글지도](https://www.google.com/maps/search/?api=1&query={장소명})
            """

        response = model.generate_content(prompt)
        raw_text = response.text
        html_text = markdown_to_html(raw_text)

        return jsonify({'raw_text': raw_text, 'html_text': html_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    destination = request.form.get('destination', '맞춤')
    text_content = request.form.get('text_content', '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    
    normal_style = ParagraphStyle(name='NormalStyle', fontName=MAIN_FONT, fontSize=10, leading=16, textColor='#333333')
    h1_style = ParagraphStyle(name='H1Style', fontName=MAIN_FONT, fontSize=14, leading=20, textColor='#1e3d59', spaceBefore=10, spaceAfter=6)
    h2_style = ParagraphStyle(name='H2Style', fontName=MAIN_FONT, fontSize=12, leading=18, textColor='#17b978', spaceBefore=8, spaceAfter=4)
    
    story = []
    lines = text_content.split('\n')
    for line in lines:
        line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
        cleaned_line = line.replace('**', '').replace('###', '').replace('##', '').replace('#', '').strip()
        if not cleaned_line:
            story.append(Spacer(1, 4))
            continue
        if line.startswith('# ') or '일차' in line or 'Day' in line:
            story.append(Paragraph(cleaned_line, h1_style))
        elif line.startswith('## ') or line.startswith('### '):
            story.append(Paragraph(cleaned_line, h2_style))
        else:
            story.append(Paragraph(cleaned_line, normal_style))
            
    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{destination}_여행일정.pdf",
        mimetype="application/pdf"
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
