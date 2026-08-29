from flask import Flask, request, jsonify, render_template_string, Response, send_from_directory
import google.generativeai as genai
import os
import re
import json

app = Flask(__name__)

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
        .btn-estimate { background: #2b8a3e; }
        .plan-content { background: #fafafa; border: 1px solid #e2e8f0; padding: 14px; border-radius: 8px; font-size: 0.95rem; line-height: 1.6; }
        .plan-content h1 { font-size: 1.25rem; color: #1e3d59; text-align: left; margin: 16px 0 8px; border-bottom: 2px solid #1e3d59; padding-bottom: 4px; }
        .plan-content h2 { font-size: 1.1rem; color: #0b7285; margin: 14px 0 6px; }
        .plan-content h3 { font-size: 1rem; color: #2b8a3e; margin: 10px 0 4px; }
        .gps-status { font-size: 0.82rem; color: #1a73e8; margin-top: -6px; margin-bottom: 8px; display: block; }

        /* 모바일 견적서/정산 모달 카드 UI */
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); backdrop-filter: blur(2px); }
        .modal-content { background: #fff; margin: 8% auto; padding: 20px; border-radius: 16px; width: 92%; max-width: 480px; max-height: 85vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,0.2); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f3f5; padding-bottom: 10px; margin-bottom: 14px; }
        .modal-header h2 { font-size: 1.15rem; color: #1e3d59; }
        .close-btn { font-size: 1.5rem; font-weight: bold; color: #888; cursor: pointer; border: none; background: none; width: auto; padding: 0; }
        
        .calc-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; margin-bottom: 12px; }
        .calc-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .calc-row label { font-size: 0.95rem; font-weight: bold; color: #475569; width: 40%; }
        .calc-row input { width: 55%; padding: 8px; font-size: 0.95rem; text-align: right; border: 1px solid #cbd5e1; border-radius: 6px; margin-bottom: 0; font-weight: bold; }
        
        .total-box { background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 12px; padding: 14px; text-align: center; margin-bottom: 14px; }
        .total-box .total-title { font-size: 0.9rem; color: #0369a1; font-weight: bold; }
        .total-box .total-val { font-size: 1.4rem; color: #0284c7; font-weight: 800; margin: 4px 0; }
        .total-box .per-person { font-size: 0.95rem; color: #0f172a; font-weight: bold; }

        .btn-copy { background: #3b82f6; font-size: 0.95rem; padding: 10px; margin-top: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏍️ 박영선의 AI 맞춤 여행 플래너</h1>
        
        <form id="plan-form">
            <div class="section-title">1. 지역 구분</div>
            <div class="radio-group">
                <label><input type="radio" name="region_type" value="국내" checked onchange="toggleRegion()"> 국내</label>
                <label><input type="radio" name="region_type" value="해외" onchange="toggleRegion()"> ✈️ 해외</label>
            </div>

            <div id="domestic-start">
                <div class="section-title">2. 출발지 설정</div>
                <div class="radio-group">
                    <label><input type="radio" name="start_mode" value="default" checked onchange="toggleStartInput()"> 📍 현재 위치</label>
                    <label><input type="radio" name="start_mode" value="custom" onchange="toggleStartInput()"> ✏️ 직접 입력</label>
                </div>
                <span id="gps-info" class="gps-status"></span>
            </div>

            <input type="text" id="start_location" placeholder="출발지 입력" style="display: none;">
            
            <div class="section-title">3. 목적지</div>
            <input type="text" id="destination" placeholder="예: 영월, 속초, 삼척, 노지 주소 등" required>

            <div class="section-title">4. 인원수</div>
            <div class="radio-group">
                <label><input type="radio" name="headcount" value="1" checked onchange="toggleHeadcountInput()"> 👤 1인(솔투)</label>
                <label><input type="radio" name="headcount" value="2" onchange="toggleHeadcountInput()"> 👥 2인</label>
                <label><input type="radio" name="headcount" value="4" onchange="toggleHeadcountInput()"> 👨‍👩‍👧 3~4인</label>
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
                <button class="btn-estimate" onclick="openEstimateModal()">💰 모바일 견적/정산표</button>
            </div>
            <div class="plan-content" id="plan-display"></div>
        </div>
    </div>

    <!-- 모바일 전용 견적 & 실시간 정산 모달 -->
    <div id="estimate-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">💰 맞춤 예상 견적서</h2>
                <button class="close-btn" onclick="closeEstimateModal()">&times;</button>
            </div>
            
            <p style="font-size:0.85rem; color:#64748b; margin-bottom:12px;">* 금액을 터치하여 직접 수정하면 합계가 실시간으로 재계산됩니다.</p>
            
            <div class="calc-box">
                <div class="calc-row">
                    <label>👥 총 인원수</label>
                    <input type="number" id="cost_people" value="1" min="1" oninput="recalculateTotal()">
                </div>
                <div class="calc-row">
                    <label>🍲 식비/음료</label>
                    <input type="number" id="cost_food" value="40000" step="1000" oninput="recalculateTotal()">
                </div>
                <div class="calc-row">
                    <label>🛏️ 숙박비</label>
                    <input type="number" id="cost_stay" value="0" step="5000" oninput="recalculateTotal()">
                </div>
                <div class="calc-row">
                    <label>⛽ 주유/교통비</label>
                    <input type="number" id="cost_fuel" value="30000" step="5000" oninput="recalculateTotal()">
                </div>
                <div class="calc-row">
                    <label>🏄 체험/기타</label>
                    <input type="number" id="cost_activity" value="0" step="5000" oninput="recalculateTotal()">
                </div>
            </div>

            <div class="total-box">
                <div class="total-title">전체 총 예상 경비</div>
                <div class="total-val" id="grand-total">70,000 원</div>
                <div class="per-person" id="per-person-total">1인당 부담금: 70,000 원</div>
            </div>

            <button type="button" class="btn-copy" onclick="copyEstimate()">📋 카톡 정산용 복사하기</button>
        </div>
    </div>

    <script>
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js');
        }

        let currentPayload = {};
        let detectedAddress = "현재 위치";

        function requestCurrentLocation() {
            if ("geolocation" in navigator) {
                const infoEl = document.getElementById('gps-info');
                infoEl.innerText = "🛰️ 현재 위치 파악 중...";
                navigator.geolocation.getCurrentPosition(async (pos) => {
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    try {
                        const controller = new AbortController();
                        const tId = setTimeout(() => controller.abort(), 2500);
                        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&accept-language=ko`, { signal: controller.signal });
                        clearTimeout(tId);
                        const data = await res.json();
                        const addr = data.address || {};
                        const province = addr.province || addr.city || addr.state || "";
                        const city = addr.city || addr.county || addr.district || "";
                        const town = addr.town || addr.village || addr.suburb || "";
                        const full = `${province} ${city} ${town}`.trim();
                        if (full) {
                            detectedAddress = full;
                            infoEl.innerText = `📍 감지된 위치: ${detectedAddress}`;
                        } else {
                            detectedAddress = "현재 위치";
                            infoEl.innerText = "📍 현재 위치 확인 완료";
                        }
                    } catch(e) {
                        detectedAddress = "현재 위치";
                        infoEl.innerText = "📍 현재 위치 확인 완료";
                    }
                }, () => {
                    detectedAddress = "현재 위치";
                    document.getElementById('gps-info').innerText = "📍 현재 위치";
                }, { timeout: 3000 });
            }
        }

        requestCurrentLocation();

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
            const infoEl = document.getElementById('gps-info');
            input.style.display = isCustom ? 'block' : 'none';
            infoEl.style.display = isCustom ? 'none' : 'block';
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
            let startLocation = detectedAddress || "현재 위치";
            if (regionType === '해외' || document.querySelector('input[name="start_mode"]:checked').value === 'custom') {
                startLocation = document.getElementById('start_location').value.trim();
                if (!startLocation) { alert('출발지를 입력해주세요.'); return; }
            }

            let headcountVal = document.querySelector('input[name="headcount"]:checked').value;
            let peopleCount = 1;
            if (headcountVal === 'custom') {
                const cVal = document.getElementById('custom_headcount').value.trim();
                if (!cVal || parseInt(cVal) < 1) { alert('정확한 단체 인원수를 입력해주세요.'); return; }
                headcountVal = `${cVal}명(단체)`;
                peopleCount = parseInt(cVal);
            } else {
                peopleCount = parseInt(headcountVal) || 1;
                headcountVal = `${headcountVal}명`;
            }

            const durationVal = document.querySelector('input[name="duration"]:checked').value;
            const isBike = document.getElementById('is_bike_mode').checked;
            const avoidRoadEl = document.getElementById('avoid_large_roads');
            const avoidLargeRoads = isBike && avoidRoadEl ? avoidRoadEl.checked : false;

            const selectedStyles = Array.from(document.querySelectorAll('input[name="travel_style"]:checked')).map(el => el.value);
            const styleString = selectedStyles.length > 0 ? selectedStyles.join(', ') : '자유 여행';

            currentPayload = {
                region_type: regionType,
                start_location: startLocation || "현재 위치",
                destination: destination,
                headcount: headcountVal,
                people_count: peopleCount,
                duration: durationVal,
                include_food: document.getElementById('include_food').checked,
                include_stay: document.getElementById('include_stay').checked,
                include_activity: document.getElementById('include_activity').checked,
                include_fishing: document.getElementById('include_fishing').checked,
                is_bike_mode: isBike,
                avoid_large_roads: avoidLargeRoads,
                styles: styleString
            };

            // 모달 초기값 자동 설정
            document.getElementById('cost_people').value = peopleCount;
            if (durationVal.includes("1박 2일")) {
                document.getElementById('cost_stay').value = 80000;
                document.getElementById('cost_food').value = 70000;
                document.getElementById('cost_fuel').value = 50000;
            } else if (durationVal.includes("2박") || durationVal.includes("3박")) {
                document.getElementById('cost_stay').value = 160000;
                document.getElementById('cost_food').value = 120000;
                document.getElementById('cost_fuel').value = 70000;
            } else {
                document.getElementById('cost_stay').value = 0;
                document.getElementById('cost_food').value = 35000;
                document.getElementById('cost_fuel').value = 25000;
            }
            recalculateTotal();

            document.getElementById('plan-form').style.display = 'none';
            document.getElementById('loading').style.display = 'block';

            try {
                const res = await fetch('/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentPayload)
                });
                
                const resText = await res.text();
                let data;
                try {
                    data = JSON.parse(resText);
                } catch(parseErr) {
                    alert('서버 응답 지연 또는 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
                    resetForm();
                    return;
                }
                
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
                alert('통신 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
                resetForm();
            }
        }

        function resetForm() {
            document.getElementById('result-area').style.display = 'none';
            document.getElementById('loading').style.display = 'none';
            document.getElementById('plan-form').style.display = 'block';
        }

        // 견적 모달 관리 및 실시간 재계산
        function openEstimateModal() {
            document.getElementById('modal-title').innerText = `💰 ${currentPayload.destination || '여행'} 견적 & 정산표`;
            document.getElementById('estimate-modal').style.display = 'block';
            recalculateTotal();
        }

        function closeEstimateModal() {
            document.getElementById('estimate-modal').style.display = 'none';
        }

        function recalculateTotal() {
            const people = parseInt(document.getElementById('cost_people').value) || 1;
            const food = parseInt(document.getElementById('cost_food').value) || 0;
            const stay = parseInt(document.getElementById('cost_stay').value) || 0;
            const fuel = parseInt(document.getElementById('cost_fuel').value) || 0;
            const activity = parseInt(document.getElementById('cost_activity').value) || 0;

            const total = (food * people) + stay + fuel + (activity * people);
            const perPerson = Math.round(total / people);

            document.getElementById('grand-total').innerText = total.toLocaleString() + ' 원';
            document.getElementById('per-person-total').innerText = `1인당 정산금: ${perPerson.toLocaleString()} 원 (${people}인 기준)`;
        }

        function copyEstimate() {
            const people = document.getElementById('cost_people').value;
            const total = document.getElementById('grand-total').innerText;
            const perPerson = document.getElementById('per-person-total').innerText;
            
            const text = `[🏍️ ${currentPayload.destination || '투어'} 예상 견적 및 정산]\n` +
                         `- 일정: ${currentPayload.duration || '당일'}\n` +
                         `- 총 경비: ${total}\n` +
                         `- ${perPerson}\n` +
                         `\n함께 즐거운 라이딩해요! 안전운전!`;

            navigator.clipboard.writeText(text).then(() => {
                alert('📋 카카오톡 정산용 텍스트가 복사되었습니다! 대화방에 붙여넣기 하세요.');
            });
        }
    </script>
</body>
</html>
"""

def markdown_to_html(text):
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
        data = request.get_json(force=True) or {}
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("gemini-3.6-flash")

        region_type = data.get('region_type', '국내')
        start_location = data.get('start_location') or '현재 위치'
        destination = data.get('destination', '목적지')
        headcount = data.get('headcount', '1명')
        duration = data.get('duration', '당일치기')
        styles = data.get('styles', '자유 여행')

        options = []
        output_sections = ["## 1. 최적 코스 및 4차선 방어용 경유지 목록"]
        sec_num = 2

        if data.get('include_food'):
            options.append("- 로컬 맛집/노포: 2곳 (상호명 및 도로명/지번 주소)")
            output_sections.append(f"## {sec_num}. 현지 로컬 맛집")
            sec_num += 1
        if data.get('include_stay'):
            options.append("- 추천 숙소: 1곳 (숙소명 및 도로명/지번 주소)")
            output_sections.append(f"## {sec_num}. 가성비 숙소")
            sec_num += 1
        if data.get('include_activity'):
            options.append("- 액티비티/체험: 1곳 (장소명 및 도로명/지번 주소)")
            output_sections.append(f"## {sec_num}. 체험 액티비티")
            sec_num += 1
        if data.get('include_fishing'):
            options.append("- 선상 낚시: 1곳 (선단/항구명 및 주소)")
            output_sections.append(f"## {sec_num}. 선상 낚시")
            sec_num += 1

        output_sections.append(f"## {sec_num}. 라이딩 주의구간 & 핵심 팁")

        options_text = "\n".join(options) if options else "경로 위주"
        output_format_text = "\n".join(output_sections)

        prompt = f"""
        당신은 대한민국 최고의 바이크 투어링 길안내 전문가입니다.
        인터넷 URL 링크는 완전히 제외하고, 네비게이션(카카오맵/티맵)에 찍을 [정확한 명칭 + 도로명/지번 주소] 위주로 군더더기 없이 간결하게 작성하세요.
        *주의: 체크 해제된 항목은 본문에 아예 적지 마세요.*

        [조건]
        - 구분: {region_type} | 출발: {start_location} | 도착: {destination}
        - 인원: {headcount} | 일정: {duration} | 테마: {styles}

        [포함 요청 항목]
        {options_text}
        """

        if data.get('is_bike_mode'):
            prompt += """
        [★ 바이크 경로 및 경유지 지정 절대 규칙 ★]
        1. 자동차 전용도로 및 고속도로 절대 배제.
        2. '경유지'는 휴게소나 쉬는 곳이 아니라, **네비가 빠른 4차선 직선 국도로 우회하지 못하도록 2차선 지방도로 강제 유도하는 [길목 방어용 경유지]**입니다.
        3. 출발지에서 첫 구간부터 4차선 국도(예: 3번, 6번, 44번 국도 등)를 절대 타지 않도록, 출발 직후 2차선 시골길/옛길로 진입하는 '첫 번째 분기점 삼거리/교차로'를 [경유지 1]로 반드시 지정할 것.
        4. 전체 경로에 걸쳐 4차선 대로 합류를 막기 위해 2차선 지방도/옛길 삼거리, 회전교차로, 고개 정상 등을 촘촘히 연결할 것.
        """
        else:
            prompt += f"""
        [일반 모드 규칙]
        - {destination} 목적지 중심 명소 및 효율 코스 위주 작성.
        """

        prompt += f"""
        [출력 양식]
        # {destination} 맞춤 코스 ({headcount}, {duration})
        {output_format_text}
        """

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.4}
        )
        raw_text = response.text
        html_text = markdown_to_html(raw_text)

        return jsonify({'raw_text': raw_text, 'html_text': html_text})
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Quota exceeded" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            return jsonify({'error': '⚠️ 오늘 무료 AI 사용량(20회)이 모두 소진되었습니다.\n한국 시간 기준 내일 오후 4시에 자동 초기화됩니다.'}), 429
        return jsonify({'error': f'서버 처리 오류: {err_msg}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
