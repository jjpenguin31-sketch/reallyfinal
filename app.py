
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import zipfile
import io
import re

st.set_page_config(
    page_title="비행기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 비행기 날개 양력 분석 프로그램")
st.caption("에어포일 선택 · 받음각 조절 · 양력 시각화")

# -----------------------------
# 1. 에어포일 데이터 불러오기
# -----------------------------

@st.cache_data
def load_airfoils():
    airfoils = {}

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
                        airfoils[name] = np.array(points)

                except Exception:
                    continue

    except FileNotFoundError:
        st.error("coord_seligFmt.zip 파일을 찾을 수 없습니다.")

    return airfoils


airfoils = load_airfoils()

if not airfoils:
    st.error(
        "에어포일 데이터를 불러오지 못했습니다. "
        "coord_seligFmt.zip 파일이 app.py와 같은 폴더에 있는지 확인하세요."
    )
    st.stop()

# -----------------------------
# 2. 입력 화면
# -----------------------------

st.sidebar.header("비행 조건 설정")

selected = st.sidebar.selectbox(
    "날개 모양 선택",
    list(airfoils.keys())
)

angle = st.sidebar.slider(
    "받음각 (°)",
    min_value=-10.0,
    max_value=20.0,
    value=5.0,
    step=0.5
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

# -----------------------------
# 3. 양력 계산
# -----------------------------

# 얇은 에어포일 이론을 이용한 교육용 근사 모델
alpha_rad = np.radians(angle)

cl = 2 * np.pi * alpha_rad
cl = np.clip(cl, -1.2, 1.2)

area = chord * span

lift = 0.5 * density * speed**2 * area * cl

# -----------------------------
# 4. 왼쪽 날개 / 오른쪽 분석
# -----------------------------

left, right = st.columns([1.15, 1])

with left:
    st.subheader("날개 모양 및 받음각")

    points = airfoils[selected].copy()

    # 날개 회전 중심을 25% 시위 위치로 설정
    pivot_x = 0.25
    pivot_y = 0.0

    theta = np.radians(angle)

    x = points[:, 0] - pivot_x
    y = points[:, 1] - pivot_y

    rotated_x = x * np.cos(theta) - y * np.sin(theta)
    rotated_y = x * np.sin(theta) + y * np.cos(theta)

    rotated_x += pivot_x
    rotated_y += pivot_y

    fig, ax = plt.subplots(figsize=(8, 4))

    ax.plot(
        rotated_x,
        rotated_y,
        linewidth=2,
        label="Airfoil"
    )

    # 공기 흐름 화살표
    for yy in np.linspace(-0.15, 0.15, 5):
        ax.arrow(
            -0.3, yy,
            0.25, 0,
            head_width=0.012,
            head_length=0.025,
            color="blue",
            length_includes_head=True
        )

    ax.set_title(f"{selected} | Angle of Attack: {angle}°")
    ax.set_xlabel("Chord")
    ax.set_ylabel("Thickness")
    ax.grid(True)
    ax.axis("equal")

    st.pyplot(fig)
    plt.close(fig)

with right:
    st.subheader("실시간 분석 결과")

    c1, c2 = st.columns(2)

    c1.metric("받음각", f"{angle:.1f}°")
    c2.metric("양력 계수 CL", f"{cl:.3f}")

    st.metric("계산된 양력", f"{lift:,.2f} N")

    st.metric("날개 면적", f"{area:.2f} m²")

    st.metric("비행 속도", f"{speed} m/s")

# -----------------------------
# 5. 받음각에 따른 양력 그래프
# -----------------------------

st.divider()
st.subheader("📈 받음각에 따른 양력 변화")

angles = np.arange(-10, 20.5, 0.5)
angles_rad = np.radians(angles)

cls = np.clip(2 * np.pi * angles_rad, -1.2, 1.2)

lifts = (
    0.5 * density * speed**2 * area * cls
)

angle_data = pd.DataFrame({
    "받음각 (°)": angles,
    "양력 계수 CL": cls,
    "양력 (N)": lifts
})

fig2, ax2 = plt.subplots(figsize=(10, 4))

ax2.plot(
    angles,
    lifts,
    linewidth=2,
    label="Lift"
)

ax2.axvline(
    angle,
    linestyle="--",
    label=f"Current angle: {angle}°"
)

ax2.scatter([angle], [lift], s=60)

ax2.set_xlabel("Angle of Attack (°)")
ax2.set_ylabel("Lift (N)")
ax2.set_title("Angle of Attack vs Lift")
ax2.grid(True)
ax2.legend()

st.pyplot(fig2)
plt.close(fig2)

# -----------------------------
# 6. 양력 계수 그래프
# -----------------------------

st.subheader("📊 받음각에 따른 양력 계수")

fig3, ax3 = plt.subplots(figsize=(10, 4))

ax3.plot(angles, cls, linewidth=2)
ax3.axvline(angle, linestyle="--", label=f"{angle}°")
ax3.scatter([angle], [cl], s=60)

ax3.set_xlabel("Angle of Attack (°)")
ax3.set_ylabel("Lift Coefficient (CL)")
ax3.set_title("Angle of Attack vs Lift Coefficient")
ax3.grid(True)
ax3.legend()

st.pyplot(fig3)
plt.close(fig3)

# -----------------------------
# 7. 계산 결과 표
# -----------------------------

st.subheader("📋 받음각별 계산 결과 표")

st.dataframe(
    angle_data.round(3),
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# 8. 속도에 따른 양력 그래프
# -----------------------------

st.subheader("🚀 비행 속도에 따른 양력 변화")

speeds = np.arange(10, 151, 5)

speed_lifts = (
    0.5 * density * speeds**2 * area * cl
)

fig4, ax4 = plt.subplots(figsize=(10, 4))

ax4.plot(speeds, speed_lifts, linewidth=2)
ax4.scatter([speed], [lift], s=60)

ax4.set_xlabel("Speed (m/s)")
ax4.set_ylabel("Lift (N)")
ax4.set_title("Speed vs Lift")
ax4.grid(True)

st.pyplot(fig4)
plt.close(fig4)

# -----------------------------
# 9. 안내
# -----------------------------

st.divider()

st.info(
    "이 프로그램은 얇은 에어포일 이론(CL = 2π α)을 "
    "이용한 교육용 근사 계산 프로그램입니다. "
    "실제 에어포일별 공력 특성, 실속, 레이놀즈 수 및 "
    "점성 효과는 반영하지 않습니다."
)
