
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import re
import json
import numpy as np

st.set_page_config(
    page_title="항공기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 항공기 날개 양력 분석")
st.caption("에어포일 선택 → 실제 날개 드래그 → 양력 실시간 분석")

# ---------------------------------
# 1. 에어포일 데이터 불러오기
# ---------------------------------

@st.cache_data
def load_airfoils():
    result = {}

    try:
        with zipfile.ZipFile("coord_seligFmt.zip", "r") as z:
            for filename in z.namelist():
                if not filename.lower().endswith(".dat"):
                    continue

                try:
                    content = z.read(filename).decode(
                        "utf-8", errors="ignore"
                    )

                    points = []

                    for line in content.splitlines():
                        nums = re.findall(
                            r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
                            line
                        )

                        if len(nums) >= 2:
                            x = float(nums[0])
                            y = float(nums[1])

                            if np.isfinite(x) and np.isfinite(y):
                                points.append([x, y])

                    if len(points) >= 10:
                        name = filename.split("/")[-1]
                        result[name] = points

                except Exception:
                    continue

    except FileNotFoundError:
        st.error("coord_seligFmt.zip 파일을 찾을 수 없습니다.")

    return result


airfoils = load_airfoils()

if not airfoils:
    st.error("에어포일 데이터를 찾을 수 없습니다.")
    st.stop()

# ---------------------------------
# 2. 입력 조건
# ---------------------------------

st.sidebar.header("비행 조건")

selected = st.sidebar.selectbox(
    "날개 모양 선택",
    list(airfoils.keys())
)

speed = st.sidebar.slider(
    "비행 속도 (m/s)",
    10, 150, 50
)

chord = st.sidebar.slider(
    "날개 시위 길이 (m)",
    0.1, 5.0, 1.0
)

span = st.sidebar.slider(
    "날개 폭 (m)",
    1.0, 30.0, 10.0
)

density = st.sidebar.slider(
    "공기 밀도 (kg/m³)",
    0.5, 2.0, 1.225
)

# ---------------------------------
# 3. 선택한 날개 데이터
# ---------------------------------

points_json = json.dumps(airfoils[selected])

# ---------------------------------
# 4. HTML + JavaScript
# ---------------------------------

html = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>

* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    margin: 0;
    color: #222;
}

.container {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 18px;
}

.panel {
    background: #ffffff;
    border: 1px solid #dddddd;
    border-radius: 12px;
    padding: 15px;
}

h3 {
    margin-top: 0;
}

canvas {
    width: 100%;
    display: block;
    border: 1px solid #eeeeee;
    border-radius: 8px;
}

#wingCanvas {
    height: 400px;
    cursor: grab;
    touch-action: none;
}

.graph {
    height: 190px;
    margin-top: 10px;
}

.metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.metric {
    background: #f1f5f9;
    border-radius: 9px;
    padding: 12px;
}

.metric small {
    color: #666;
}

.metric strong {
    display: block;
    font-size: 23px;
    margin-top: 6px;
}

#lift {
    color: #1675d1;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
    font-size: 13px;
}

th, td {
    padding: 8px 5px;
    border-bottom: 1px solid #ddd;
    text-align: center;
}

th {
    background: #f1f5f9;
}

.active {
    background: #dceeff;
    font-weight: bold;
}

button {
    border: none;
    background: #1675d1;
    color: white;
    border-radius: 7px;
    padding: 9px 14px;
    cursor: pointer;
    margin-top: 8px;
}

.hint {
    color: #666;
    font-size: 13px;
}

@media(max-width: 750px) {
    .container {
        grid-template-columns: 1fr;
    }
}

</style>
</head>

<body>

<div class="container">

    <div class="panel">

        <h3>✈️ 실제 날개 직접 조작</h3>

        <p class="hint">
            날개를 마우스로 드래그하세요.
            위로 움직이면 받음각이 증가합니다.
        </p>

        <canvas id="wingCanvas"></canvas>

        <h3>
            현재 받음각:
            <span id="angleText">5.0°</span>
        </h3>

        <button onclick="resetAngle()">각도 초기화</button>

    </div>

    <div class="panel">

        <h3>📊 실시간 분석 결과</h3>

        <div class="metrics">

            <div class="metric">
                <small>받음각</small>
                <strong id="angleValue">5.0°</strong>
            </div>

            <div class="metric">
                <small>양력 계수 CL</small>
                <strong id="clValue">0.000</strong>
            </div>

            <div class="metric">
                <small>양력</small>
                <strong id="lift">0 N</strong>
            </div>

            <div class="metric">
                <small>날개 면적</small>
                <strong id="areaValue">0 m²</strong>
            </div>

        </div>

        <h3 style="margin-top:20px;">
            받음각과 양력 그래프
        </h3>

        <canvas id="liftGraph" class="graph"></canvas>

        <h3 style="margin-top:20px;">
            받음각과 양력 계수 그래프
        </h3>

        <canvas id="clGraph" class="graph"></canvas>

        <h3>계산 결과 표</h3>

        <table>
            <thead>
                <tr>
                    <th>받음각</th>
                    <th>CL</th>
                    <th>양력(N)</th>
                </tr>
            </thead>

            <tbody id="resultTable"></tbody>
        </table>

    </div>

</div>

<script>

// ---------------------------------
// 데이터와 비행 조건
// ---------------------------------

const points = __POINTS__;

const speed = __SPEED__;
const chord = __CHORD__;
const span = __SPAN__;
const density = __DENSITY__;

const area = chord * span;

let angle = 5;

const wingCanvas = document.getElementById("wingCanvas");
const wingCtx = wingCanvas.getContext("2d");

const liftCanvas = document.getElementById("liftGraph");
const liftCtx = liftCanvas.getContext("2d");

const clCanvas = document.getElementById("clGraph");
const clCtx = clCanvas.getContext("2d");

// ---------------------------------
// 양력 계산
// ---------------------------------

function calculateCL(a) {
    const rad = a * Math.PI / 180;

    return Math.max(
        -1.2,
        Math.min(1.2, 2 * Math.PI * rad)
    );
}

function calculateLift(a) {
    const cl = calculateCL(a);

    return 0.5 * density * speed * speed * area * cl;
}

// ---------------------------------
// 날개 그리기
// ---------------------------------

function drawWing() {

    const rect = wingCanvas.getBoundingClientRect();

    const w = rect.width;
    const h = rect.height;

    const dpr = window.devicePixelRatio || 1;

    wingCanvas.width = w * dpr;
    wingCanvas.height = h * dpr;

    wingCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

    wingCtx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;

    const scale = Math.min(w * 0.72, h * 1.8);

    const rad = angle * Math.PI / 180;

    // 공기 흐름 화살표
    wingCtx.strokeStyle = "#2684dc";
    wingCtx.fillStyle = "#2684dc";
    wingCtx.lineWidth = 2;

    for (let i = 0; i < 5; i++) {

        const y = 70 + i * 55;

        wingCtx.beginPath();
        wingCtx.moveTo(10, y);
        wingCtx.lineTo(75, y);
        wingCtx.stroke();

        wingCtx.beginPath();
        wingCtx.moveTo(75, y);
        wingCtx.lineTo(65, y - 6);
        wingCtx.lineTo(65, y + 6);
        wingCtx.closePath();
        wingCtx.fill();
    }

    // 선택한 실제 에어포일 좌표 회전
    wingCtx.save();

    wingCtx.translate(cx, cy);
    wingCtx.rotate(-rad);

    wingCtx.beginPath();

    points.forEach((p, i) => {

        const x = (p[0] - 0.25) * scale;
        const y = -p[1] * scale;

        if (i === 0) {
            wingCtx.moveTo(x, y);
        } else {
            wingCtx.lineTo(x, y);
        }

    });

    wingCtx.closePath();

    wingCtx.fillStyle = "#8bc7f5";
    wingCtx.fill();

    wingCtx.strokeStyle = "#1767aa";
    wingCtx.lineWidth = 2.5;
    wingCtx.stroke();

    wingCtx.restore();

    // 회전 중심
    wingCtx.beginPath();
    wingCtx.arc(cx, cy, 4, 0, Math.PI * 2);
    wingCtx.fillStyle = "red";
    wingCtx.fill();

    wingCtx.fillStyle = "#333";
    wingCtx.font = "13px Arial";
    wingCtx.fillText("회전 중심", cx + 10, cy - 10);

    wingCtx.fillText(
        "받음각: " + angle.toFixed(1) + "°",
        12,
        22
    );
}

// ---------------------------------
// 그래프 그리기
// ---------------------------------

function drawGraph(canvas, ctx, currentAngle, type) {

    const rect = canvas.getBoundingClientRect();

    const w = rect.width;
    const h = rect.height;

    const dpr = window.devicePixelRatio || 1;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const left = 42;
    const right = 12;
    const top = 15;
    const bottom = 30;

    const minA = -10;
    const maxA = 20;

    const maxValue = type === "lift"
        ? Math.max(100, Math.abs(calculateLift(20)) * 1.15)
        : 1.3;

    const minValue = -maxValue;

    function px(a) {
        return left + (a - minA) / (maxA - minA) * (w - left - right);
    }

    function py(v) {
        return top + (maxValue - v) /
            (maxValue - minValue) * (h - top - bottom);
    }

    // 축
    ctx.strokeStyle = "#888";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, h - bottom);
    ctx.lineTo(w - right, h - bottom);
    ctx.stroke();

    // 0 기준선
    ctx.strokeStyle = "#bbbbbb";
    ctx.beginPath();
    ctx.moveTo(left, py(0));
    ctx.lineTo(w - right, py(0));
    ctx.stroke();

    // 그래프 선
    ctx.strokeStyle = type === "lift" ? "#1675d1" : "#15966b";
    ctx.lineWidth = 2.5;

    ctx.beginPath();

    for (let a = minA; a <= maxA; a += 0.25) {

        const value = type === "lift"
            ? calculateLift(a)
            : calculateCL(a);

        if (a === minA) {
            ctx.moveTo(px(a), py(value));
        } else {
            ctx.lineTo(px(a), py(value));
        }
    }

    ctx.stroke();

    // 현재 위치
    const currentValue = type === "lift"
        ? calculateLift(currentAngle)
        : calculateCL(currentAngle);

    ctx.beginPath();
    ctx.arc(
        px(currentAngle),
        py(currentValue),
        5,
        0,
        Math.PI * 2
    );

    ctx.fillStyle = "#e34b4b";
    ctx.fill();

    // X축 숫자
    ctx.fillStyle = "#555";
    ctx.font = "11px Arial";
    ctx.textAlign = "center";

    for (let a = -10; a <= 20; a += 5) {
        ctx.fillText(a + "°", px(a), h - 10);
    }

}

// ---------------------------------
// 표 만들기
// ---------------------------------

function updateTable() {

    const tbody = document.getElementById("resultTable");

    let html = "";

    for (let a = -10; a <= 20; a += 5) {

        const cl = calculateCL(a);
        const lift = calculateLift(a);

        const selected = Math.abs(a - angle) < 2.5;

        html += `
            <tr class="${selected ? "active" : ""}">
                <td>${a}°</td>
                <td>${cl.toFixed(3)}</td>
                <td>${lift.toFixed(1)}</td>
            </tr>
        `;
    }

    tbody.innerHTML = html;
}

// ---------------------------------
// 화면 전체 갱신
// ---------------------------------

function updateAll() {

    const cl = calculateCL(angle);
    const lift = calculateLift(angle);

    document.getElementById("angleText").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("angleValue").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("clValue").textContent =
        cl.toFixed(3);

    document.getElementById("lift").textContent =
        lift.toLocaleString("ko-KR", {
            maximumFractionDigits: 1
        }) + " N";

    document.getElementById("areaValue").textContent =
        area.toFixed(2) + " m²";

    drawWing();

    drawGraph(liftCanvas, liftCtx, angle, "lift");
    drawGraph(clCanvas, clCtx, angle, "cl");

    updateTable();
}

// ---------------------------------
// 마우스 드래그로 날개 회전
// ---------------------------------

let dragging = false;
let startY = 0;
let startAngle = 0;

wingCanvas.addEventListener("pointerdown", (e) => {

    dragging = true;

    startY = e.clientY;
    startAngle = angle;

    wingCanvas.setPointerCapture(e.pointerId);

    wingCanvas.style.cursor = "grabbing";

});

wingCanvas.addEventListener("pointermove", (e) => {

    if (!dragging) return;

    const difference = startY - e.clientY;

    angle = Math.max(
        -10,
        Math.min(20, startAngle + difference * 0.15)
    );

    updateAll();

});

wingCanvas.addEventListener("pointerup", () => {

    dragging = false;
    wingCanvas.style.cursor = "grab";

});

wingCanvas.addEventListener("pointercancel", () => {

    dragging = false;
    wingCanvas.style.cursor = "grab";

});

// ---------------------------------
// 초기화
// ---------------------------------

function resetAngle() {
    angle = 5;
    updateAll();
}

window.addEventListener("resize", updateAll);

updateAll();

</script>

</body>
</html>
"""

# ---------------------------------
# 5. Python 값 전달
# ---------------------------------

html = html.replace("__POINTS__", points_json)
html = html.replace("__SPEED__", str(speed))
html = html.replace("__CHORD__", str(chord))
html = html.replace("__SPAN__", str(span))
html = html.replace("__DENSITY__", str(density))

components.html(
    html,
    height=900,
    scrolling=True
)

st.divider()

st.info(
    "계산은 얇은 에어포일 이론(CL = 2π α)을 이용한 "
    "교육용 근사 모델입니다. 실제 에어포일별 양력 특성, "
    "실속 및 레이놀즈 수 효과는 반영하지 않습니다."
)

