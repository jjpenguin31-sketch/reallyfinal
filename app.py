
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import numpy as np
import pandas as pd
import json
import re
import os

st.set_page_config(
    page_title="비행기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 비행기 날개 양력 분석 프로그램")
st.caption("실제 에어포일 선택 · 마우스 회전 · 실시간 양력 분석")


# -----------------------------
# ZIP 파일에서 에어포일 불러오기
# -----------------------------
@st.cache_data
def load_airfoils():
    zip_path = "coord_seligFmt.zip"

    if not os.path.exists(zip_path):
        return {}

    airfoils = {}

    with zipfile.ZipFile(zip_path, "r") as archive:
        for filename in archive.namelist():

            if not filename.lower().endswith(".dat"):
                continue

            try:
                content = archive.read(filename).decode(
                    "utf-8", errors="ignore"
                )

                points = []

                for line in content.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    values = re.split(r"[\s,]+", line)

                    if len(values) < 2:
                        continue

                    try:
                        x = float(values[0])
                        y = float(values[1])

                        if np.isfinite(x) and np.isfinite(y):
                            points.append([x, y])

                    except ValueError:
                        continue

                if len(points) >= 10:
                    name = filename.replace("\\", "/").split("/")[-1]
                    airfoils[name] = points

            except Exception:
                continue

    return airfoils


airfoils = load_airfoils()

if not airfoils:
    st.error(
        "coord_seligFmt.zip에서 날개 데이터를 찾지 못했습니다. "
        "ZIP 파일이 app.py와 같은 폴더에 있는지 확인하세요."
    )
    st.stop()


# -----------------------------
# 사이드바 설정
# -----------------------------
st.sidebar.header("⚙️ 비행 조건 설정")

selected_airfoil = st.sidebar.selectbox(
    "날개 선택",
    sorted(airfoils.keys())
)

speed = st.sidebar.slider(
    "비행 속도 (m/s)",
    10, 200, 80
)

chord = st.sidebar.slider(
    "날개 시위 길이 (m)",
    0.5, 10.0, 2.0, 0.1
)

span = st.sidebar.slider(
    "날개 폭 (m)",
    1.0, 40.0, 12.0, 0.5
)

density = st.sidebar.slider(
    "공기 밀도 (kg/m³)",
    0.5, 1.5, 1.225, 0.025
)

st.sidebar.markdown("---")
st.sidebar.info(
    "날개를 마우스로 위아래로 드래그하면 "
    "받음각과 양력이 실시간으로 바뀝니다."
)


# -----------------------------
# 선택한 날개 좌표 정리
# -----------------------------
points = np.array(airfoils[selected_airfoil], dtype=float)

# x 좌표를 0~1 범위로 정규화
x_min = np.min(points[:, 0])
x_max = np.max(points[:, 0])

if x_max == x_min:
    st.error("올바르지 않은 날개 좌표입니다.")
    st.stop()

points[:, 0] = (points[:, 0] - x_min) / (x_max - x_min)

# y 좌표도 같은 비율로 정규화
points[:, 1] = points[:, 1] / (x_max - x_min)

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
    margin: 0;
    font-family: Arial, sans-serif;
    color: #222;
}

.container {
    display: grid;
    grid-template-columns:  minmax(0, 1.8fr) minmax(300px, 1fr);
    gap: 16px;
}

.panel {
    border: 1px solid #ddd;
    border-radius: 14px;
    padding: 16px;
    min-width: 0;
    background: white;
}

h3 {
    margin-top: 0;
    font-size: 19px;
}

.description {
    color: #666;
    font-size: 13px;
    margin-bottom: 12px;
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

#wingCanvas:active {
    cursor: grabbing;
}

#angleText {
    font-size: 20px;
    font-weight: bold;
    margin-top: 12px;
}

#resultAngle, #resultLift, #resultCL {
    background: #f1f5f9;
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 10px;
}

.value {
    font-size: 23px;
    font-weight: bold;
    margin-top: 5px;
}

.blue {
    color: #0877dc;
}

.graph {
    height: 190px;
    margin-bottom: 15px;
}

table {
    border-collapse: collapse;
    width: 100%;
    font-size: 13px;
}

th, td {
    border-bottom: 1px solid #ddd;
    padding: 8px 5px;
    text-align: center;
}

th {
    background: #f1f5f9;
}

.current {
    background: #dceeff;
    font-weight: bold;
}

button {
    padding: 9px 15px;
    border: none;
    border-radius: 7px;
    background: #1677d2;
    color: white;
    cursor: pointer;
    margin-top: 10px;
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
        <h3>✈️ 선택한 날개 직접 조작</h3>

        <div class="description">
            날개를 마우스로 위아래로 드래그하세요.
            앞부분이 위로 올라가면 양의 받음각이 됩니다.
        </div>

        <canvas id="wingCanvas"></canvas>

        <div id="angleText">현재 받음각: 5.0°</div>

        <button onclick="resetAngle()">받음각 초기화</button>
    </div>


    <div class="panel">
        <h3>📊 실시간 분석 결과</h3>

        <div id="resultAngle">
            받음각
            <div class="value" id="angleValue">5.0°</div>
        </div>

        <div id="resultCL">
            양력 계수
            <div class="value blue" id="clValue">0.548</div>
        </div>

        <div id="resultLift">
            양력
            <div class="value blue" id="liftValue">0 N</div>
        </div>

        <h3>받음각에 따른 양력</h3>
        <canvas id="liftGraph" class="graph"></canvas>

        <h3>받음각에 따른 양력 계수</h3>
        <canvas id="clGraph" class="graph"></canvas>

        <h3>받음각별 계산 결과</h3>

        <table>
            <thead>
                <tr>
                    <th>받음각</th>
                    <th>양력 계수</th>
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

const wingCanvas = document.getElementById("wingCanvas");
const wingCtx = wingCanvas.getContext("2d");

const liftCanvas = document.getElementById("liftGraph");
const liftCtx = liftCanvas.getContext("2d");

const clCanvas = document.getElementById("clGraph");
const clCtx = clCanvas.getContext("2d");

let dragging = false;
let startY = 0;
let startAngle = 0;


// -----------------------------
// 양력 계산
// -----------------------------
function calculateCL(a) {
    const radians = a * Math.PI / 180;

    // 단순 얇은 날개 이론
    return Math.max(-1.2, Math.min(1.2, 2 * Math.PI * radians));
}

function calculateLift(a) {
    const cl = calculateCL(a);

    return 0.5 * density * speed * speed * area * cl;
}


// -----------------------------
// 날개 그리기
// -----------------------------
function drawWing() {
    const rect = wingCanvas.getBoundingClientRect();

    const w = rect.width;
    const h = rect.height;

    const dpr = window.devicePixelRatio || 1;

    wingCanvas.width = w * dpr;
    wingCanvas.height = h * dpr;

    wingCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

    wingCtx.clearRect(0, 0, w, h);

    // 배경
    wingCtx.fillStyle = "#ffffff";
    wingCtx.fillRect(0, 0, w, h);

    // 바람 방향 화살표
    wingCtx.strokeStyle = "#2585df";
    wingCtx.fillStyle = "#2585df";
    wingCtx.lineWidth = 2;

    for (let y = 65; y < h - 35; y += 65) {
        wingCtx.beginPath();
        wingCtx.moveTo(10, y);
        wingCtx.lineTo(65, y);
        wingCtx.stroke();

        wingCtx.beginPath();
        wingCtx.moveTo(65, y);
        wingCtx.lineTo(57, y - 5);
        wingCtx.lineTo(57, y + 5);
        wingCtx.closePath();
        wingCtx.fill();
    }

    // 날개 크기: x와 y에 같은 배율을 적용
    const scale = Math.min((w - 150), 650);

    const centerX = w / 2;
    const centerY = h / 2;

    // 회전 중심: 앞전에서 25% 지점
    const pivotX = centerX - scale * 0.25;

    wingCtx.save();

    wingCtx.translate(pivotX, centerY);

    // 양의 받음각이면 앞부분이 위로 올라가도록 회전
    wingCtx.rotate(angle * Math.PI / 180);

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

    wingCtx.fillStyle = "#8bc5ee";
    wingCtx.fill();

    wingCtx.strokeStyle = "#2878b8";
    wingCtx.lineWidth = 2.5;
    wingCtx.stroke();

    // 회전 중심 표시
    wingCtx.beginPath();
    wingCtx.arc(0, 0, 4, 0, Math.PI * 2);
    wingCtx.fillStyle = "red";
    wingCtx.fill();

    wingCtx.restore();
}


// -----------------------------
// 그래프 그리기
// -----------------------------
function drawGraph(canvas, ctx, isLift) {
    const rect = canvas.getBoundingClientRect();

    const w = rect.width;
    const h = rect.height;

    const dpr = window.devicePixelRatio || 1;

    canvas.width = w * dpr;
    canvas.height = h * dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const left = 42;
    const right = w - 12;
    const top = 12;
    const bottom = h - 28;

    const values = [];

    for (let a = -10; a <= 20; a += 1) {
        values.push(isLift ? calculateLift(a) : calculateCL(a));
    }

    const maxValue = Math.max(...values.map(v => Math.abs(v)), 1);

    function getX(a) {
        return left + (a + 10) / 30 * (right - left);
    }

    function getY(v) {
        return bottom - (v + maxValue) / (2 * maxValue) * (bottom - top);
    }

    // 축
    ctx.strokeStyle = "#aaa";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, bottom);
    ctx.lineTo(right, bottom);
    ctx.stroke();

    // 0 기준선
    ctx.beginPath();
    ctx.moveTo(left, getY(0));
    ctx.lineTo(right, getY(0));
    ctx.strokeStyle = "#bbb";
    ctx.stroke();

    // 그래프 선
    ctx.beginPath();

    for (let a = -10; a <= 20; a += 1) {
        const v = isLift ? calculateLift(a) : calculateCL(a);

        if (a === -10) {
            ctx.moveTo(getX(a), getY(v));
        } else {
            ctx.lineTo(getX(a), getY(v));
        }
    }

    ctx.strokeStyle = "#0877dc";
    ctx.lineWidth = 2.5;
    ctx.stroke();

    // 현재 받음각 위치
    const currentValue = isLift ? calculateLift(angle) : calculateCL(angle);

    ctx.beginPath();
    ctx.arc(getX(angle), getY(currentValue), 5, 0, Math.PI * 2);
    ctx.fillStyle = "#e53935";
    ctx.fill();

    // x축 숫자
    ctx.fillStyle = "#555";
    ctx.font = "11px Arial";
    ctx.textAlign = "center";

    [-10, -5, 0, 5, 10, 15, 20].forEach(a => {
        ctx.fillText(a + "°", getX(a), h - 8);
    });
}


// -----------------------------
// 표 업데이트
// -----------------------------
function updateTable() {
    const tbody = document.getElementById("resultTable");

    let html = "";

    for (let a = -10; a <= 20; a += 5) {
        const cl = calculateCL(a);
        const lift = calculateLift(a);

        const isCurrent = Math.abs(angle - a) < 2.5;

        html += `
            <tr class="${isCurrent ? "current" : ""}">
                <td>${a}°</td>
                <td>${cl.toFixed(3)}</td>
                <td>${lift.toLocaleString("ko-KR", {
                    maximumFractionDigits: 1
                })}</td>
            </tr>
        `;
    }

    tbody.innerHTML = html;
}


// -----------------------------
// 전체 화면 업데이트
// -----------------------------
function updateAll() {
    const cl = calculateCL(angle);
    const lift = calculateLift(angle);

    document.getElementById("angleValue").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("angleText").textContent =
        "현재 받음각: " + angle.toFixed(1) + "°";

    document.getElementById("clValue").textContent =
        cl.toFixed(3);

    document.getElementById("liftValue").textContent =
        lift.toLocaleString("ko-KR", {
            maximumFractionDigits: 1
        }) + " N";

    drawWing();
    drawGraph(liftCanvas, liftCtx, true);
    drawGraph(clCanvas, clCtx, false);
    updateTable();
}


// -----------------------------
// 마우스 드래그
// -----------------------------
wingCanvas.addEventListener("pointerdown", function(e) {
    dragging = true;

    startY = e.clientY;
    startAngle = angle;

    wingCanvas.setPointerCapture(e.pointerId);
});

wingCanvas.addEventListener("pointermove", function(e) {
    if (!dragging) return;

    // 위로 드래그하면 양의 받음각 증가
    angle = startAngle + (startY - e.clientY) * 0.15;

    angle = Math.max(-10, Math.min(20, angle));

    updateAll();
});

wingCanvas.addEventListener("pointerup", function() {
    dragging = false;
});

wingCanvas.addEventListener("pointercancel", function() {
    dragging = false;
});


// -----------------------------
// 초기화
// -----------------------------
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

html = (
    html.replace("__POINTS__", points_json)
    .replace("__SPEED__", str(speed))
    .replace("__CHORD__", str(chord))
    .replace("__SPAN__", str(span))
    .replace("__DENSITY__", str(density))
)

components.html(html, height=1050, scrolling=True)


st.markdown("---")
st.caption(
    "※ 양력 계수는 단순 얇은 날개 이론(CL = 2πα)을 사용한 교육용 근사값입니다. "
    "실제 날개의 실속, 레이놀즈 수, 날개별 공력 특성은 반영하지 않습니다."
)
