
import streamlit as st
import matplotlib.pyplot as plt
import zipfile
import math
from pathlib import PurePosixPath

st.set_page_config(
    page_title="비행기 날개 양력 분석",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ 비행기 날개 설계 및 양력 분석 프로그램")
st.write("날개 단면을 선택하고 받음각을 조절하여 양력을 계산합니다.")

ZIP_PATH = "coord_seligFmt.zip"


@st.cache_data
def get_airfoil_files():
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        return [
            name for name in z.namelist()
            if name.lower().endswith(".dat")
            and not name.endswith("/")
        ]


def read_airfoil(member):
    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        content = z.read(member).decode("utf-8", errors="ignore")

    coordinates = []

    for line in content.splitlines():
        parts = line.replace(",", " ").split()

        if len(parts) >= 2:
            try:
                x = float(parts[0])
                y = float(parts[1])
                coordinates.append((x, y))
            except ValueError:
                continue

    if len(coordinates) < 3:
        raise ValueError("날개 좌표 데이터가 부족합니다.")

    return coordinates


# 날개 데이터 불러오기
try:
    airfoil_files = get_airfoil_files()

except FileNotFoundError:
    st.error("coord_seligFmt.zip 파일이 저장소에 있는지 확인하세요.")
    st.stop()

except zipfile.BadZipFile:
    st.error("ZIP 파일이 손상되었거나 올바른 파일이 아닙니다.")
    st.stop()


if not airfoil_files:
    st.error("ZIP 파일에서 .dat 파일을 찾을 수 없습니다.")
    st.stop()


# 1. 날개 단면 선택
st.header("1. 날개 단면 선택")

selected_file = st.selectbox(
    "분석할 날개 단면을 선택하세요.",
    airfoil_files,
    format_func=lambda name: PurePosixPath(name).name
)

try:
    coordinates = read_airfoil(selected_file)

    fig, ax = plt.subplots(figsize=(9, 3))

    x = [p[0] for p in coordinates]
    y = [p[1] for p in coordinates]

    ax.plot(x, y, linewidth=2)
    ax.set_title(PurePosixPath(selected_file).name)
    ax.set_xlabel("Chord direction")
    ax.set_ylabel("Thickness direction")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True)

    st.pyplot(fig)
    plt.close(fig)

except Exception as e:
    st.error(f"날개 데이터를 읽을 수 없습니다: {e}")
    st.stop()


# 2. 비행 조건 설정
st.header("2. 비행 조건 설정")

col1, col2 = st.columns(2)

with col1:
    span = st.number_input(
        "날개폭 (m)",
        min_value=0.1,
        max_value=100.0,
        value=10.0,
        step=0.5
    )

    chord = st.number_input(
        "날개 시위 길이 (m)",
        min_value=0.1,
        max_value=20.0,
        value=1.5,
        step=0.1
    )

    speed = st.number_input(
        "비행 속도 (m/s)",
        min_value=0.1,
        max_value=500.0,
        value=50.0,
        step=1.0
    )

with col2:
    density = st.number_input(
        "공기 밀도 (kg/m³)",
        min_value=0.1,
        max_value=2.0,
        value=1.225,
        step=0.025
    )

    angle = st.slider(
        "받음각 조절 (°)",
        min_value=-5.0,
        max_value=15.0,
        value=5.0,
        step=0.5
    )


# 3. 양력 계산
st.header("3. 양력 계산")

# 얇은 날개 이론을 이용한 단순 근사
cl_raw = 2 * math.pi * math.radians(angle)

# 실속을 포함하지 않는 단순 모델의 제한
cl = max(-1.2, min(1.2, cl_raw))

area = span * chord

dynamic_pressure = 0.5 * density * speed ** 2

lift = dynamic_pressure * area * cl


# 결과 표시
result1, result2, result3 = st.columns(3)

result1.metric("날개 면적", f"{area:.2f} m²")
result2.metric("양력 계수 CL", f"{cl:.3f}")
result3.metric("계산된 양력", f"{lift:,.2f} N")


st.write(f"현재 받음각: **{angle}°**")


# 4. 받음각에 따른 양력 변화 그래프
st.header("4. 받음각에 따른 양력 변화")

angles = [i / 2 for i in range(-10, 31)]

lifts = []

for a in angles:
    coefficient = 2 * math.pi * math.radians(a)
    coefficient = max(-1.2, min(1.2, coefficient))

    l = dynamic_pressure * area * coefficient
    lifts.append(l)

fig2, ax2 = plt.subplots(figsize=(9, 4))

ax2.plot(angles, lifts, label="Lift")
ax2.axvline(
    angle,
    linestyle="--",
    label=f"Current angle: {angle}°"
)

ax2.scatter([angle], [lift], zorder=3)

ax2.set_xlabel("Angle of Attack (degrees)")
ax2.set_ylabel("Lift (N)")
ax2.set_title("Lift vs Angle of Attack")
ax2.grid(True)
ax2.legend()

st.pyplot(fig2)
plt.close(fig2)


st.info(
    "주의: 이 프로그램은 얇은 날개 이론을 이용한 교육용 근사 계산입니다. "
    "선택한 날개 단면은 실제 좌표로 표시되지만, 현재 양력 계산에는 "
    "단면별 실제 공력 특성이 반영되지 않습니다. "
    "실제 비행에서는 레이놀즈수, 실속, 날개 형상 등에 따라 결과가 달라집니다."
)
