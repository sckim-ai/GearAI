"""
Power Load 함수 테스트 스크립트
- create_power_load: Power Load 생성 테스트
- mount_power_load: Power Load 장착 테스트
- unmount_power_load: Power Load 해제 테스트
"""

from mcp_server_MASTA_tools import (
    masta_initialize,
    create_shaft,
    create_power_load,
    mount_power_load,
    unmount_power_load,
    save_masta_file
)

def test_power_load():
    """Power Load 전체 테스트"""
    print("\n" + "="*80)
    print("Power Load 테스트 시작")
    print("="*80)

    # 1. 세션 초기화
    print("\n[1단계] 세션 초기화")
    init_result = masta_initialize()

    if not init_result.get("success"):
        print(f"[ERROR] 초기화 실패: {init_result.get('error')}")
        return False

    session_id = init_result["session_id"]
    print(f"[OK] 세션 초기화: {session_id}")

    # 2. 축 생성
    print("\n[2단계] 축 생성")
    shaft_result = create_shaft(
        session_id=session_id,
        shaft_name="Input Shaft",
        length=200.0
    )

    if not shaft_result.get("success"):
        print(f"[ERROR] 축 생성 실패: {shaft_result.get('error')}")
        return False

    print(f"[OK] 축 생성: {shaft_result['shaft_name']}")

    # 3. Power Load 생성 (입력 파워 로드)
    print("\n[3단계] 입력 Power Load 생성")
    input_pl_result = create_power_load(
        session_id=session_id,
        power_load_name="Input_Power_Load"
    )

    if not input_pl_result.get("success"):
        print(f"[ERROR] 입력 Power Load 생성 실패: {input_pl_result.get('error')}")
        return False

    print(f"[OK] 입력 Power Load 생성: {input_pl_result['power_load_name']}")
    print(f"     정보: {input_pl_result['power_load_info']}")

    # 4. Power Load 생성 (출력 파워 로드)
    print("\n[4단계] 출력 Power Load 생성")
    output_pl_result = create_power_load(
        session_id=session_id,
        power_load_name="Output_Power_Load"
    )

    if not output_pl_result.get("success"):
        print(f"[ERROR] 출력 Power Load 생성 실패: {output_pl_result.get('error')}")
        return False

    print(f"[OK] 출력 Power Load 생성: {output_pl_result['power_load_name']}")
    print(f"     정보: {output_pl_result['power_load_info']}")

    # 5. 입력 Power Load 장착
    print("\n[5단계] 입력 Power Load 장착")
    mount_input_result = mount_power_load(
        session_id=session_id,
        power_load_name="Input_Power_Load",
        shaft_name="Input Shaft",
        position=30.0
    )

    if not mount_input_result.get("success"):
        print(f"[ERROR] 입력 Power Load 장착 실패: {mount_input_result.get('error')}")
        return False

    print(f"[OK] 입력 Power Load 장착: {mount_input_result['shaft_name']} at {mount_input_result['position']}mm")

    # 6. 출력 Power Load 장착
    print("\n[6단계] 출력 Power Load 장착")
    mount_output_result = mount_power_load(
        session_id=session_id,
        power_load_name="Output_Power_Load",
        shaft_name="Input Shaft",
        position=170.0
    )

    if not mount_output_result.get("success"):
        print(f"[ERROR] 출력 Power Load 장착 실패: {mount_output_result.get('error')}")
        return False

    print(f"[OK] 출력 Power Load 장착: {mount_output_result['shaft_name']} at {mount_output_result['position']}mm")

    # 7. 입력 Power Load 위치 변경 (재장착)
    print("\n[7단계] 입력 Power Load 위치 변경")
    remount_result = mount_power_load(
        session_id=session_id,
        power_load_name="Input_Power_Load",
        shaft_name="Input Shaft",
        position=50.0  # 30mm -> 50mm로 변경
    )

    if not remount_result.get("success"):
        print(f"[ERROR] Power Load 재장착 실패: {remount_result.get('error')}")
        return False

    print(f"[OK] Power Load 재장착: {remount_result['shaft_name']} at {remount_result['position']}mm")

    # 8. 출력 Power Load 해제
    print("\n[8단계] 출력 Power Load 해제")
    unmount_result = unmount_power_load(
        session_id=session_id,
        power_load_name="Output_Power_Load"
    )

    if not unmount_result.get("success"):
        print(f"[ERROR] Power Load 해제 실패: {unmount_result.get('error')}")
        return False

    print(f"[OK] Power Load 해제: {unmount_result['power_load_name']}")

    # 9. 해제된 Power Load 재장착
    print("\n[9단계] 해제된 Power Load 재장착")
    remount_after_unmount = mount_power_load(
        session_id=session_id,
        power_load_name="Output_Power_Load",
        shaft_name="Input Shaft",
        position=160.0
    )

    if not remount_after_unmount.get("success"):
        print(f"[ERROR] 해제 후 재장착 실패: {remount_after_unmount.get('error')}")
        return False

    print(f"[OK] 해제 후 재장착: {remount_after_unmount['shaft_name']} at {remount_after_unmount['position']}mm")

    # 10. 최종 모델 저장 (1회만 수행)
    print("\n[10단계] 최종 모델 저장")
    save_result = save_masta_file(
        session_id=session_id,
        file_name="test_power_load_final.masta"
    )

    if not save_result.get("success"):
        print(f"[ERROR] 모델 저장 실패: {save_result.get('error')}")
        return False

    print(f"[OK] 모델 저장: {save_result['file_path']}")

    print("\n" + "="*80)
    print("✅ Power Load 테스트 완료!")
    print("="*80)
    return True


if __name__ == "__main__":
    try:
        success = test_power_load()
        if not success:
            print("\n❌ 테스트 실패")
            exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
