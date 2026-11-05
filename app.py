
import streamlit as st
import streamlit.components.v1 as components
import zipfile
import math
from pathlib import PurePosixPath
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="비행기 날개 양력 시뮬레이터",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 비행기 날개 양력 시뮬레이터")
st.write("날개를 직접 기울여 받음각과 양력의 변화를 확인하세요.")

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
                points.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass

    if len(points) < 3:
        raise ValueError("날개 좌표를 읽을 수 없습니다.")

    return points


try:
    files = get_airfoil_files()
except Exception as e:
    st.error(f"ZIP 파일을 읽을 수 없습니다: {e}")
    st.stop()

if not files:
    st.error("ZIP 파일 안에 .dat 파일이 없습니다.")
    st.stop()


# 날개 단면 선택
st.header("1. 날개 단면 선택")

selected = st.selectbox(
    "날개 단면",
    files,
    format_func=lambda n: PurePosixPath(n).name
)

try:
    points = read_airfoil(selected)

    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(
        [p[0] for p in points],
        [p[1] for p in points]
    )
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title(PurePosixPath(selected).name)
    ax.set_xlabel("Chord")
    ax.set_ylabel("Thickness")
    ax.grid(True)

    st.pyplot(fig)
    plt.close(fig)

except Exception as e:
    st.error(f"날개 데이터를 표시할 수 없습니다: {e}")
    st.stop()


# 비행 조건
st.header("2. 비행 조건")

c1, c2 = st.columns(2)

with c1:
    span = st.number_input(
        "날개폭 (m)", min_value=0.1, value=10.0
    )
    chord = st.number_input(
        "시위 길이 (m)", min_value=0.1, value=1.5
    )
    speed = st.number_input(
        "비행 속도 (m/s)", min_value=0.1, value=50.0
    )

with c2:
    density = st.number_input(
        "공기 밀도 (kg/m³)",
        min_value=0.1,
        value=1.225
    )

st.header("3. 날개 직접 기울이기")

st.write(
    "아래 날개의 가운데 부분을 마우스로 누른 뒤 "
    "위아래로 움직여 보세요."
)

# 마우스로 조작하는 시뮬레이터
html = """
<!DOCTYPE html>
<html>
<head>
<style>
body {
    font-family: Arial, sans-serif;
    margin: 0;
    background: #f5f7fa;
    color: #202124;
}
.container {
    padding: 12px;
}
canvas {
    width: 100%;
    background: white;
    border: 1px solid #d0d7de;
    border-radius: 10px;
    touch-action: none;
    cursor: grab;
}
canvas:active {
    cursor: grabbing;
}
.info {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 12px;
}
.card {
    flex: 1;
    min-width: 130px;
    padding: 14px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 9px;
}
.value {
    font-size: 23px;
    font-weight: bold;
    margin-top: 6px;
}
button {
    margin-top: 12px;
    padding: 9px 16px;
    border: 0;
    border-radius: 7px;
    background: #2563eb;
    color: white;
    cursor: pointer;
}
</style>
</head>

<body>
<div class="container">

<h3>날개 받음각 조절</h3>
<canvas id="wing" width="850" height="390"></canvas>

<div class="info">
    <div class="card">
        받음각
        <div class="value" id="angle">5°</div>
    </div>
    <div class="card">
        양력 계수 CL
        <div class="value" id="cl">0.548</div>
    </div>
    <div class="card">
        계산된 양력
        <div class="value" id="lift">-</div>
    </div>
</div>

<button onclick="resetWing()">각도 초기화</button>

<p style="font-size:12px;color:#666">
날개를 드래그하면 각도가 변합니다.
양력은 교육용 단순 근사 모델로 계산합니다.
</p>

</div>

<script>
const canvas = document.getElementById("wing");
const ctx = canvas.getContext("2d");

let angle = 5;
let dragging = false;

const span = SPAN_VALUE;
const chord = CHORD_VALUE;
const speed = SPEED_VALUE;
const density = DENSITY_VALUE;

const area = span * chord;
const centerX = 425;
const centerY = 205;
const wingLength = 230;

function drawArrow(x1, y1, x2, y2, color, label) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 3;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    let a = Math.atan2(y2-y1, x2-x1);

    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(
        x2 - 12*Math.cos(a-0.5),
        y2 - 12*Math.sin(a-0.5)
    );
    ctx.lineTo(
        x2 - 12*Math.cos(a+0.5),
        y2 - 12*Math.sin(a+0.5)
    );
    ctx.closePath();
    ctx.fill();

    ctx.font = "bold 15px Arial";
    ctx.fillText(label, x2+8, y2-8);
}

function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 공기 흐름
    for (let y of [75, 115, 155, 255, 295, 335]) {
        drawArrow(35, y, 160, y, "#60a5fa", "");
    }

    ctx.fillStyle = "#2563eb";
    ctx.font = "bold 16px Arial";
    ctx.fillText("공기 흐름 →", 35, 35);

    // 날개
    let rad = angle * Math.PI / 180;
    let dx = Math.cos(rad) * wingLength / 2;
    let dy = Math.sin(rad) * wingLength / 2;

    let x1 = centerX - dx;
    let y1 = centerY + dy;
    let x2 = centerX + dx;
    let y2 = centerY - dy;

    ctx.lineWidth = 13;
    ctx.strokeStyle = "#2563eb";
    ctx.lineCap = "round";

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    // 날개 중심
    ctx.fillStyle = "#1d4ed8";
    ctx.beginPath();
    ctx.arc(centerX, centerY, 8, 0, Math.PI*2);
    ctx.fill();

    // 받음각 표시
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(centerX+100, centerY);
    ctx.stroke();

    ctx.fillStyle = "#d97706";
    ctx.font = "bold 15px Arial";
    ctx.fillText("받음각 " + angle.toFixed(1) + "°", 540, 165);

    // 양력 계산
    let cl = 2 * Math.PI * rad;
    cl = Math.max(-1.2, Math.min(1.2, cl));

    let lift = 0.5 * density * speed * speed * area * cl;

    // 양력 방향은 공기 흐름에 수직인 위쪽 방향
    let liftLength = Math.max(-110, Math.min(110, lift / 100));

    drawArrow(
        centerX,
        centerY,
        centerX,
        centerY - liftLength,
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

function getPointerAngle(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    return Math.atan2(centerY-y, x-centerX)
        * 180 / Math.PI;
}

canvas.addEventListener("pointerdown", e => {
    dragging = true;
    canvas.setPointerCapture(e.pointerId);
});

canvas.addEventListener("pointermove", e => {
    if (!dragging) return;

    angle = Math.max(-5, Math.min(15, getPointerAngle(e)));
    update();
});

canvas.addEventListener("pointerup", () => {
    dragging = false;
});

canvas.addEventListener("pointercancel", () => {
    dragging = false;
});

function resetWing() {
    angle = 5;
    update();
}

update();
</script>
</body>
</html>
"""

html = (
    html
    .replace("SPAN_VALUE", str(span))
    .replace("CHORD_VALUE", str(chord))
    .replace("SPEED_VALUE", str(speed))
    .replace("DENSITY_VALUE", str(density))
)

components.html(html, height=650, scrolling=True)

st.caption(
    "계산식: L = 1/2 × 공기 밀도 × 속도² × 날개 면적 × 양력 계수"
)

st.warning(
    "현재 양력 계수는 얇은 날개 이론을 이용한 단순 근사입니다. "
    "실제 날개 단면별 공력 특성이나 실속 현상은 반영하지 않습니다."
)

