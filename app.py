
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import math
import json
from pathlib import PurePosixPath

st.set_page_config(
    page_title="비행기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 비행기 날개 양력 시뮬레이터")
st.write("실제 날개 단면을 마우스로 직접 회전시켜 보세요.")

ZIP_PATH = "coord_seligFmt.zip"


@st.cache_data
def get_airfoil_files():
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        return [
            n for n in z.namelist()
            if n.lower().endswith(".dat") and not n.endswith("/")
        ]


def read_airfoil(member):
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        content = z.read(member).decode("utf-8", errors="ignore")

    points = []

    for line in content.splitlines():
        parts = line.replace(",", " ").split()

        if len(parts) >= 2:
            try:
                points.append([
                    float(parts[0]),
                    float(parts[1])
                ])
            except ValueError:
                continue

    if len(points) < 3:
        raise ValueError("날개 좌표 데이터가 부족합니다.")

    # 날개 중심을 원점으로 이동
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    return [
        [p[0] - center_x, p[1] - center_y]
        for p in points
    ]


try:
    files = get_airfoil_files()
except Exception as e:
    st.error(f"ZIP 파일 오류: {e}")
    st.stop()

if not files:
    st.error("ZIP 파일에 날개 데이터가 없습니다.")
    st.stop()


# 날개 선택
st.header("1. 실제 날개 단면 선택")

selected = st.selectbox(
    "날개 모양 선택",
    files,
    format_func=lambda n: PurePosixPath(n).name
)

try:
    points = read_airfoil(selected)
except Exception as e:
    st.error(str(e))
    st.stop()


# 비행 조건
st.header("2. 비행 조건")

c1, c2 = st.columns(2)

with c1:
    span = st.number_input(
        "날개폭 (m)",
        min_value=0.1,
        value=10.0
    )

    chord = st.number_input(
        "시위 길이 (m)",
        min_value=0.1,
        value=1.5
    )

with c2:
    speed = st.number_input(
        "비행 속도 (m/s)",
        min_value=0.1,
        value=50.0
    )

    density = st.number_input(
        "공기 밀도 (kg/m³)",
        min_value=0.1,
        value=1.225
    )


# 마우스 회전 시뮬레이터
st.header("3. 날개 모양 직접 회전")

st.write(
    "날개 모양을 마우스로 드래그해 보세요. "
    "날개 전체가 회전합니다."
)

points_json = json.dumps(points)

html = """
<!DOCTYPE html>
<html>
<head>
<style>
body {
    margin: 0;
    font-family: Arial;
    background: #f4f7fb;
}
.container {
    padding: 12px;
}
canvas {
    width: 100%;
    background: white;
    border: 1px solid #ccd4df;
    border-radius: 10px;
    touch-action: none;
    cursor: grab;
}
canvas:active {
    cursor: grabbing;
}
.info {
    background: white;
    padding: 13px;
    margin-top: 10px;
    border-radius: 8px;
    border: 1px solid #ddd;
}
.value {
    font-size: 25px;
    font-weight: bold;
}
</style>
</head>

<body>
<div class="container">

<h3>선택한 실제 날개 단면</h3>
<canvas id="canvas" width="900" height="450"></canvas>

<div class="info">
    받음각
    <div class="value" id="angle">5°</div>
    양력
    <div class="value" id="lift">-</div>
    양력 계수
    <div class="value" id="cl">-</div>
</div>

<p>마우스로 날개를 드래그해서 각도를 조절하세요.</p>

</div>

<script>
const points = POINTS_DATA;

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

let angle = 5;
let dragging = false;

const centerX = 450;
const centerY = 220;
const scale = 290;

const span = SPAN_VALUE;
const chord = CHORD_VALUE;
const speed = SPEED_VALUE;
const density = DENSITY_VALUE;

const area = span * chord;

function rotatePoint(p, a) {
    const rad = a * Math.PI / 180;

    return {
        x: p[0] * Math.cos(rad) - p[1] * Math.sin(rad),
        y: p[0] * Math.sin(rad) + p[1] * Math.cos(rad)
    };
}

function drawArrow(x1, y1, x2, y2, color, label) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    const a = Math.atan2(y2-y1, x2-x1);

    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(
        x2-12*Math.cos(a-0.5),
        y2-12*Math.sin(a-0.5)
    );
    ctx.lineTo(
        x2-12*Math.cos(a+0.5),
        y2-12*Math.sin(a+0.5)
    );
    ctx.closePath();
    ctx.fill();

    ctx.font = "bold 15px Arial";
    ctx.fillText(label, x2+8, y2-8);
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 공기 흐름
    ctx.font = "bold 16px Arial";
    ctx.fillStyle = "#2563eb";
    ctx.fillText("공기 흐름 →", 35, 35);

    for (let y of [80, 130, 180, 260, 310, 360]) {
        drawArrow(35, y, 150, y, "#60a5fa", "");
    }

    // 실제 좌표를 회전시켜 날개 그리기
    const rotated = points.map(p => rotatePoint(p, angle));

    ctx.beginPath();

    rotated.forEach((p, i) => {
        const x = centerX + p.x * scale;
        const y = centerY - p.y * scale;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.closePath();

    ctx.fillStyle = "#93c5fd";
    ctx.fill();

    ctx.strokeStyle = "#1d4ed8";
    ctx.lineWidth = 3;
    ctx.stroke();

    // 회전 중심
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, Math.PI*2);
    ctx.fillStyle = "#1d4ed8";
    ctx.fill();

    // 기준선
    ctx.setLineDash([6, 5]);
    ctx.strokeStyle = "#999";
    ctx.beginPath();
    ctx.moveTo(centerX-170, centerY);
    ctx.lineTo(centerX+170, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    // 받음각 표시
    ctx.fillStyle = "#d97706";
    ctx.font = "bold 17px Arial";
    ctx.fillText("받음각: " + angle.toFixed(1) + "°", 650, 100);

    // 양력 계산
    const rad = angle * Math.PI / 180;

    let cl = 2 * Math.PI * rad;
    cl = Math.max(-1.2, Math.min(1.2, cl));

    const lift =
        0.5 * density * speed * speed * area * cl;

    // 양력 화살표
    const arrowLength = Math.max(
        -120,
        Math.min(120, lift / 100)
    );

    drawArrow(
        centerX,
        centerY,
        centerX,
        centerY-arrowLength,
        "#16a34a",
        "양력"
    );

    document.getElementById("angle").textContent =
        angle.toFixed(1) + "°";

    document.getElementById("cl").textContent =
        cl.toFixed(3);

    document.getElementById("lift").textContent =
        lift.toLocaleString("ko-KR", {
            maximumFractionDigits: 1
        }) + " N";
}

// 드래그로 회전
function pointerAngle(e) {
    const rect = canvas.getBoundingClientRect();

    const x =
        (e.clientX - rect.left) * canvas.width / rect.width;

    const y =
        (e.clientY - rect.top) * canvas.height / rect.height;

    return Math.atan2(
        centerY-y,
        x-centerX
    ) * 180 / Math.PI;
}

canvas.addEventListener("pointerdown", e => {
    dragging = true;
    canvas.setPointerCapture(e.pointerId);
});

canvas.addEventListener("pointermove", e => {
    if (!dragging) return;

    angle = Math.max(
        -5,
        Math.min(15, pointerAngle(e))
    );

    update();
});

canvas.addEventListener("pointerup", () => {
    dragging = false;
});

canvas.addEventListener("pointercancel", () => {
    dragging = false;
});

update();
</script>
</body>
</html>
"""

html = (
    html
    .replace("POINTS_DATA", points_json)
    .replace("SPAN_VALUE", str(span))
    .replace("CHORD_VALUE", str(chord))
    .replace("SPEED_VALUE", str(speed))
    .replace("DENSITY_VALUE", str(density))
)

components.html(html, height=680, scrolling=True)

st.info(
    "양력 계산은 얇은 날개 이론을 이용한 교육용 근사입니다. "
    "실제 날개 단면별 양력 특성과 실속은 아직 반영하지 않습니다."
)

