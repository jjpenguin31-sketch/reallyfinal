
import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import json
import re

st.set_page_config(
    page_title="항공기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 항공기 날개 양력 분석")
st.write("직접 날개 파일을 업로드하고 받음각을 조절해 보세요.")

# --------------------------------
# 1. 날개 파일 업로드
# --------------------------------

st.sidebar.header("날개 설정")

uploaded_file = st.sidebar.file_uploader(
    "날개 좌표 파일 업로드 (.dat 또는 .txt)",
    type=["dat", "txt"]
)

if uploaded_file is None:
    st.info(
        "왼쪽 메뉴에서 에어포일 좌표 파일(.dat)을 업로드하세요."
    )
    st.stop()

# --------------------------------
# 2. 좌표 데이터 읽기
# --------------------------------

content = uploaded_file.getvalue().decode(
    "utf-8", errors="ignore"
)

points = []

for line in content.splitlines():

    nums = re.findall(
        r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?",
        line
    )

    if len(nums) >= 2:

        try:
            x = float(nums[0])
            y = float(nums[1])

            if np.isfinite(x) and np.isfinite(y):
                points.append([x, y])

        except ValueError:
            continue

if len(points) < 10:
    st.error("날개 좌표를 읽지 못했습니다. 올바른 DAT 파일인지 확인하세요.")
    st.stop()

points = np.array(points)

# 좌표 범위 확인
if np.ptp(points[:, 0]) == 0:
    st.error("올바른 날개 좌표가 아닙니다.")
    st.stop()

# 시위 길이 기준으로 정규화
x_min = points[:, 0].min()
x_max = points[:, 0].max()

points[:, 0] = (
    points[:, 0] - x_min
) / (x_max - x_min)

# --------------------------------
# 3. 비행 조건
# --------------------------------

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

# --------------------------------
# 4. HTML 데이터 전달
# --------------------------------

points_json = json.dumps(points.tolist())

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
    gap: 16px;
}

.panel {
    border: 1px solid #ddd;
    border-radius: 12px;
    padding: 14px;
    background: white;
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

#wing {
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
    padding: 12px;
    border-radius: 9px;
}

.metric small {
    color: #666;
}

.metric strong {
    display: block;
    font-size: 22px;
    margin-top: 6px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13px;
}

td, th {
    border-bottom: 1px solid #ddd;
    padding: 8px;
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

        <h3>✈️ 업로드한 날개 직접 조작</h3>

        <p class="hint">
            날개를 마우스로 위아래로 드래그하세요.
            위로 움직이면 받음각이 커집니다.
        </p>

        <canvas id="wing"></canvas>

        <h3>
            현재 받음각:
            <span id="angleText">5.0°</span>
        </h3>

        <button onclick="resetAngle()">각도 초기화</button>

    </div>

    <div class="panel">

        <h3>📊 실시간 양력 분석</h3>

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

        <h3 style="margin-top:20px;">
            받음각에 따른 양력
        </h3>

        <canvas id="liftGraph" class="graph"></canvas>

        <h3 style="margin-top:20px;">
            받음각에 따른 양력 계수
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

const points = __POINTS__;

const speed = __SPEED__;
const chord = __CHORD__;
const span = __SPAN__;
const density = __DENSITY__;

const area = chord * span;

let angle = 5;

const wing = document.getElementById("wing");
const wingCtx = wing.getContext("2d");

const liftGraph = document.getElementById("liftGraph");
const liftCtx = liftGraph.getContext("2d");

const clGraph = document.getElementById("clGraph");
const clCtx = clGraph.getContext("2d");

// --------------------------------
// 양력 계산
// --------------------------------

function getCL(a) {

    const rad = a * Math.PI / 180;

    return Math.max(
        -1.2,
        Math.min(1.2, 2 * Math.PI * rad)
    );

}

function getLift(a) {

    return 0.5 * density * speed ** 2 *
        area * getCL(a);

}

// --------------------------------
// 실제 날개 그리기
// --------------------------------

function drawWing() {

    const w = wing.clientWidth;
    const h = wing.clientHeight;

    const dpr = window.devicePixelRatio || 1;

    wing.width = w * dpr;
    wing.height = h * dpr;

    wingCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

    wingCtx.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;

    const scale = Math.min(w * 0.7, h * 1.5);

    const rad = angle * Math.PI / 180;

    // 공기 흐름
    wingCtx.strokeStyle = "#2784d9";
    wingCtx.fillStyle = "#2784d9";
    wingCtx.lineWidth = 2;

    for (let i = 0; i < 5; i++) {

        const y = 70 + i * 55;

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

    // 선택한 날개 좌표 회전
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

    wingCtx.fillStyle = "red";
    wingCtx.beginPath();
    wingCtx.arc(cx, cy, 4, 0, Math.PI * 2);
    wingCtx.fill();

}

// --------------------------------
// 그래프 그리기
// --------------------------------

function drawGraph(canvas, ctx, type) {

    const w = canvas.clientWidth;
    const h = canvas.clientHeight;

    const dpr = window.devicePixelRatio || 1;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const left = 42;
    const right = 10;
    const top = 12;
    const bottom = 28;

    const minA = -10;
    const maxA = 20;

    const maxValue = type === "lift"
        ? Math.max(100, Math.abs(getLift(20)) * 1.15)
        : 1.3;

    function px(a) {
        return left + (a - minA) /
            (maxA - minA) * (w - left - right);
    }

    function py(v) {
        return top + (maxValue - v) /
            (2 * maxValue) * (h - top - bottom);
    }

    ctx.strokeStyle = "#aaa";

    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, h - bottom);
    ctx.lineTo(w - right, h - bottom);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(left, py(0));
    ctx.lineTo(w - right, py(0));
    ctx.stroke();

    ctx.strokeStyle = type === "lift" ? "#1675d1" : "#15966b";
    ctx.lineWidth = 2.5;

    ctx.beginPath();

    for (let a = minA; a <= maxA; a += 0.25) {

        const value = type === "lift"
            ? getLift(a)
            : getCL(a);

        if (a === minA) {
            ctx.moveTo(px(a), py(value));
        } else {
            ctx.lineTo(px(a), py(value));
        }

    }

    ctx.stroke();

    const current = type === "lift"
        ? getLift(angle)
        : getCL(angle);

    ctx.fillStyle = "#e34b4b";

    ctx.beginPath();
    ctx.arc(px(angle), py(current), 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#555";
    ctx.font = "11px Arial";
    ctx.textAlign = "center";

    for (let a = -10; a <= 20; a += 5) {
        ctx.fillText(a + "°", px(a), h - 9);
    }

}

// --------------------------------
// 결과 표
// --------------------------------

function updateTable() {

    let html = "";

    for (let a = -10; a <= 20; a += 5) {

        const cl = getCL(a);
        const lift = getLift(a);

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

// --------------------------------
// 전체 화면 업데이트
// --------------------------------

function updateAll() {

    const cl = getCL(angle);
    const lift = getLift(angle);

    document.getElementById("angleText").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("angleValue").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("clValue").textContent =
        cl.toFixed(3);

    document.getElementById("liftValue").textContent =
        lift.toFixed(1) + " N";

    document.getElementById("areaValue").textContent =
        area.toFixed(2) + " m²";

    drawWing();

    drawGraph(liftGraph, liftCtx, "lift");
    drawGraph(clGraph, clCtx, "cl");

    updateTable();

}

// --------------------------------
// 마우스 드래그
// --------------------------------

let dragging = false;
let startY = 0;
let startAngle = 0;

wing.addEventListener("pointerdown", (e) => {

    dragging = true;

    startY = e.clientY;
    startAngle = angle;

    wing.setPointerCapture(e.pointerId);
    wing.style.cursor = "grabbing";

});

wing.addEventListener("pointermove", (e) => {

    if (!dragging) return;

    const difference = startY - e.clientY;

    angle = Math.max(
        -10,
        Math.min(20, startAngle + difference * 0.15)
    );

    updateAll();

});

wing.addEventListener("pointerup", () => {

    dragging = false;
    wing.style.cursor = "grab";

});

wing.addEventListener("pointercancel", () => {

    dragging = false;
    wing.style.cursor = "grab";

});

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

# --------------------------------
# 5. 입력값 전달
# --------------------------------

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
    "양력은 CL = 2π α를 사용하는 교육용 근사 모델입니다. "
    "실제 에어포일의 실험 양력 계수나 실속 현상까지 "
    "계산하는 CFD 프로그램은 아닙니다."
)
