
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import numpy as np
import json
import re

st.set_page_config(
    page_title="항공기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 항공기 날개 양력 분석")
st.caption("실제 에어포일 선택 · 마우스 회전 · 실시간 양력 분석")


# =====================================
# 1. 기존 ZIP 파일에서 에어포일 불러오기
# =====================================

@st.cache_data
def load_airfoils():

    airfoils = {}

    with zipfile.ZipFile("coord_seligFmt.zip", "r") as z:

        for filename in z.namelist():

            if not filename.lower().endswith(".dat"):
                continue

            try:
                content = z.read(filename).decode(
                    "utf-8",
                    errors="ignore"
                )

                points = []

                for line in content.splitlines():

                    numbers = re.findall(
                        r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
                        line
                    )

                    if len(numbers) >= 2:

                        x = float(numbers[0])
                        y = float(numbers[1])

                        if np.isfinite(x) and np.isfinite(y):
                            points.append([x, y])

                if len(points) >= 10:

                    name = filename.split("/")[-1]

                    # 중복 파일명 방지
                    if name in airfoils:
                        name = filename

                    airfoils[name] = points

            except Exception:
                continue

    return airfoils


try:
    airfoils = load_airfoils()

except FileNotFoundError:
    st.error("coord_seligFmt.zip 파일을 찾을 수 없습니다.")
    st.stop()

if not airfoils:
    st.error("ZIP 파일에서 날개 좌표를 찾지 못했습니다.")
    st.stop()


# =====================================
# 2. 날개 선택 및 비행 조건
# =====================================

st.sidebar.header("✈️ 날개 선택")

selected = st.sidebar.selectbox(
    "사용할 에어포일",
    list(airfoils.keys())
)

st.sidebar.divider()
st.sidebar.header("비행 조건")

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

st.sidebar.caption("선택한 날개: " + selected)


# =====================================
# 3. 좌표 정규화
# =====================================

points = np.array(airfoils[selected], dtype=float)

x_min = np.min(points[:, 0])
x_max = np.max(points[:, 0])

if x_max <= x_min:
    st.error("잘못된 에어포일 좌표입니다.")
    st.stop()

# 시위 길이를 0~1로 정규화
points[:, 0] = (
    points[:, 0] - x_min
) / (x_max - x_min)

points_json = json.dumps(points.tolist())

# =====================================
# 4. JavaScript 화면
# =====================================

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
    margin: 0;
    font-family: Arial, sans-serif;
    color: #222;
}

.container {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 16px;
}

.panel {
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 15px;
    background: white;
    min-width: 0;
}

h3 {
    margin-top: 0;
}

canvas {
    width: 100%;
    display: block;
    border: 1px solid #eee;
    border-radius: 8px;
}

#wingCanvas {
    height: 420px;
    cursor: grab;
    touch-action: none;
}

.graph {
    height: 190px;
    margin: 10px 0 20px;
}

.metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}

.metric {
    background: #f1f5f9;
    padding: 13px;
    border-radius: 9px;
}

.metric small {
    color: #666;
}

.metric strong {
    display: block;
    font-size: 22px;
    margin-top: 7px;
}

#liftValue {
    color: #1675d1;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13px;
}

td, th {
    padding: 9px 5px;
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
    background: #1675d1;
    color: white;
    border: none;
    border-radius: 7px;
    padding: 9px 14px;
    cursor: pointer;
}

.hint {
    font-size: 13px;
    color: #666;
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

    <!-- 왼쪽: 날개 조작 -->

    <div class="panel">

        <h3>✈️ 선택한 날개 직접 조작</h3>

        <p class="hint">
            날개를 마우스로 위아래로 드래그하세요.
            위로 움직이면 받음각이 증가합니다.
        </p>

        <canvas id="wingCanvas"></canvas>

        <h3>
            현재 받음각:
            <span id="angleText">5.0°</span>
        </h3>

        <button onclick="resetAngle()">
            각도 초기화
        </button>

    </div>


    <!-- 오른쪽: 분석 결과 -->

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
                <strong id="liftValue">0 N</strong>
            </div>

            <div class="metric">
                <small>날개 면적</small>
                <strong id="areaValue">0 m²</strong>
            </div>

        </div>

        <h3 style="margin-top:22px;">
            받음각에 따른 양력
        </h3>

        <canvas id="liftGraph" class="graph"></canvas>

        <h3>
            받음각에 따른 양력 계수
        </h3>

        <canvas id="clGraph" class="graph"></canvas>

        <h3>📋 계산 결과 표</h3>

        <table>
            <thead>
                <tr>
                    <th>받음각</th>
                    <th>양력 계수</th>
                    <th>양력 (N)</th>
                </tr>
            </thead>

            <tbody id="resultTable"></tbody>
        </table>

    </div>

</div>


<script>

// =====================================
// Python에서 전달된 데이터
// =====================================

const points = __POINTS__;

const speed = __SPEED__;
const chord = __CHORD__;
const span = __SPAN__;
const density = __DENSITY__;

const area = chord * span;

let angle = 5;


// =====================================
// 캔버스 설정
// =====================================

const wingCanvas = document.getElementById("wingCanvas");
const wingCtx = wingCanvas.getContext("2d");

const liftCanvas = document.getElementById("liftGraph");
const liftCtx = liftCanvas.getContext("2d");

const clCanvas = document.getElementById("clGraph");
const clCtx = clCanvas.getContext("2d");


// =====================================
// 양력 계산
// =====================================

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


// =====================================
// 실제 에어포일 그리기
// =====================================

function drawWing() {

    const w = wingCanvas.clientWidth;
    const h = wingCanvas.clientHeight;

    const dpr = window.devicePixelRatio || 1;

    wingCanvas.width = w * dpr;
    wingCanvas.height = h * dpr;

    wingCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

    wingCtx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;

    const scale = Math.min(w * 0.68, h * 1.5);

    const rad = angle * Math.PI / 180;


    // 공기 흐름 화살표

    wingCtx.strokeStyle = "#2784d9";
    wingCtx.fillStyle = "#2784d9";
    wingCtx.lineWidth = 2;

    for (let i = 0; i < 5; i++) {

        const y = 65 + i * 65;

        wingCtx.beginPath();
        wingCtx.moveTo(8, y);
        wingCtx.lineTo(70, y);
        wingCtx.stroke();

        wingCtx.beginPath();
        wingCtx.moveTo(70, y);
        wingCtx.lineTo(60, y - 6);
        wingCtx.lineTo(60, y + 6);
        wingCtx.closePath();
        wingCtx.fill();

    }


    // 실제 선택한 에어포일 회전

    wingCtx.save();

    wingCtx.translate(cx, cy);

    // 앞전이 위로 올라가는 방향을 양의 받음각으로 표시
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


    // 회전 중심 표시

    wingCtx.beginPath();
    wingCtx.arc(cx, cy, 4, 0, Math.PI * 2);

    wingCtx.fillStyle = "red";
    wingCtx.fill();

    wingCtx.fillStyle = "#333";
    wingCtx.font = "13px Arial";
    wingCtx.fillText("회전 중심", cx + 10, cy - 10);

}


// =====================================
// 그래프 그리기
// =====================================

function drawGraph(canvas, ctx, type) {

    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    const dpr = window.devicePixelRatio || 1;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, w, h);

    const left = 42;
    const right = 12;
    const top = 12;
    const bottom = 28;

    const minA = -10;
    const maxA = 20;

    const maxValue = type === "lift"
        ? Math.max(100, Math.abs(calculateLift(20)) * 1.15)
        : 1.3;


    function px(a) {

        return left +
            (a - minA) / (maxA - minA) *
            (w - left - right);

    }

    function py(v) {

        return top +
            (maxValue - v) / (2 * maxValue) *
            (h - top - bottom);

    }


    // 축

    ctx.strokeStyle = "#999";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, h - bottom);
    ctx.lineTo(w - right, h - bottom);
    ctx.stroke();


    // 0 기준선

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


    // 현재 받음각 위치

    const current = type === "lift"
        ? calculateLift(angle)
        : calculateCL(angle);

    ctx.beginPath();

    ctx.arc(
        px(angle),
        py(current),
        5,
        0,
        Math.PI * 2
    );

    ctx.fillStyle = "#e34b4b";
    ctx.fill();


    // X축 눈금

    ctx.fillStyle = "#555";
    ctx.font = "11px Arial";
    ctx.textAlign = "center";

    for (let a = -10; a <= 20; a += 5) {
        ctx.fillText(a + "°", px(a), h - 9);
    }

}


// =====================================
// 결과 표
// =====================================

function updateTable() {

    let html = "";

    for (let a = -10; a <= 20; a += 5) {

        const cl = calculateCL(a);
        const lift = calculateLift(a);

        const active = Math.abs(a - angle) < 2.5;

        html += `
            <tr class="${active ? "active" : ""}">
                <td>${a}°</td>
                <td>${cl.toFixed(3)}</td>
                <td>${lift.toFixed(1)}</td>
            </tr>
        `;

    }

    document.getElementById("resultTable").innerHTML = html;

}


// =====================================
// 전체 화면 갱신
// =====================================

function updateAll() {

    const cl = calculateCL(angle);
    const lift = calculateLift(angle);

    document.getElementById("angleText").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("angleValue").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("clValue").textContent =
        cl.toFixed(3);

    document.getElementById("liftValue").textContent =
        lift.toLocaleString("ko-KR", {
            maximumFractionDigits: 1
        }) + " N";

    document.getElementById("areaValue").textContent =
        area.toFixed(2) + " m²";

    drawWing();

    drawGraph(liftCanvas, liftCtx, "lift");
    drawGraph(clCanvas, clCtx, "cl");

    updateTable();

}


// =====================================
// 마우스로 실제 날개 기울이기
// =====================================

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


// =====================================
// 각도 초기화
// =====================================

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

# =====================================
# 5. Python 값 전달
# =====================================

html = html.replace("__POINTS__", points_json)
html = html.replace("__SPEED__", str(speed))
html = html.replace("__CHORD__", str(chord))
html = html.replace("__SPAN__", str(span))
html = html.replace("__DENSITY__", str(density))

components.html(
    html,
    height=950,
    scrolling=True
)

st.divider()

st.info(
    "양력 계산은 얇은 에어포일 이론(CL = 2π α)을 이용한 "
    "교육용 근사 모델입니다. 실제 날개별 공력 특성, "
    "실속 및 레이놀즈 수 효과는 반영하지 않습니다."
)

