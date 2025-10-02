"""Utility"""
import math
import matplotlib.pyplot as plt

def calculate_normal_module(Centerdistance, z1, z2, beta):
                total_teeth = z1 + z2
                helix_angle_rad = math.radians(beta)  # 헬리컬 각도를 라디안으로 변환
                normal_module = (2 * Centerdistance * math.cos(helix_angle_rad)) / total_teeth
                return normal_module

def get_nearest_bearing_code(inner_diameter: float) -> str:
    # 내경별 62xx 시리즈 형번 매핑 (최대 100mm까지)
    bearing_codes = {
        10: "6200", 12: "6201", 15: "6202", 17: "6203", 20: "6204",
        25: "6205", 30: "6206", 35: "6207", 40: "6208", 45: "6209",
        50: "6210", 55: "6211", 60: "6212", 65: "6213", 70: "6214",
        75: "6215", 80: "6216", 85: "6217", 90: "6218", 95: "6219",
        100: "6220"
    }
    
    # 정확히 매칭되는 형번이 있는지 확인
    if inner_diameter in bearing_codes:
        return bearing_codes[inner_diameter]
    
    # 매칭이 없는 경우 가장 가까운 내경을 찾아 형번 반환
    nearest_diameter = min(bearing_codes.keys(), key=lambda x: abs(x - inner_diameter))
    return bearing_codes[nearest_diameter]


def plot_images(assembly):
    plt.figure(figsize=(12, 12))
    plt.subplot(1, 3, 1)
    plt.imshow(assembly.three_d_isometric_view)
    plt.subplot(1, 3, 2)
    plt.imshow(assembly.three_d_view_orientated_in_xz_plane_with_y_axis_pointing_into_the_screen)
    plt.subplot(1, 3, 3)
    plt.imshow(assembly.three_d_view_orientated_in_xy_plane_with_z_axis_pointing_into_the_screen)
