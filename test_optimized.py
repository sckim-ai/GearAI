"""
최적화된 GearDesign 테스트 스크립트
기존 test.py의 기능을 클래스 기반으로 재구성하여 가독성과 유지보수성 향상
"""
import os
import sys
from pathlib import Path
import datetime

# 현재 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from gear_design_manager import GearDesignManager


def main():
    """메인 실행 함수"""
    
    # 경로 설정
    gear_design_path = r"D:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"
    default_json_path = r"D:\SW\Streamlit\agents\data\schema\Default.json"
    
    print("=== GearDesign 최적화 테스트 시작 ===")
    
    try:
        # GearDesignManager 초기화
        print("1. GearDesignManager 초기화 중...")
        manager = GearDesignManager(gear_design_path, default_json_path)
        
        # Form 초기화
        print("2. Form 초기화 중...")
        if not manager.initialize_form():
            print("❌ Form 초기화 실패")
            return False
            
        # 기본 설정 저장
        print("3. 기본 설정 저장 중...")
        default_config = manager.save_default_config()
        
        # 설정 수정 (기본 설정 그대로 사용하되, 몇 가지만 수정)
        print("4. 설정 수정 및 로드 중...")
        # 직접 설정 수정
        if "Basic Data" in default_config:
            default_config["Basic Data"]["GearTypeNum"] = "0"
            default_config["Basic Data"]["Normal Module"] = "3"
            default_config["Basic Data"]["CDMethod"] = 1
        
        if not manager.load_and_validate_config(default_config):
            print("❌ 설정 로드 및 검증 실패")
            return False
            
        # 기하학적 계산
        print("5. 기하학적 계산 수행 중...")
        geometry_result = manager.calculate_geometry()
        
        # 하중 계산
        print("6. 하중 계산 수행 중...")
        rating_result = manager.calculate_load_case(geometry_result)
        
        # 메시지 추출
        print("메시지 추출 중...")
        messages = manager.get_messages()
        print(messages)

        # 기어 이미지 추출
        print("기어 이미지 추출 중...")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        original_dir = r"D:\SW\Streamlit"   # 경로 지정
        output_file = os.path.join(original_dir, f"gear_image_{timestamp}.png") 
        getimage = manager.get_gearimage(output_file)
        if getimage:
            print("success!")
        # SimpleSizing 계산 수행
        print("7. SimpleSizing 계산 수행 중...")
        sizing_input = manager.create_simple_sizing_input()
        
        # SimpleSizingInput 설정을 직접 수행
        sizing_input.target_GR = 3
        sizing_input.target_GR_dev = 5 / 100.0
        sizing_input.z_pinion_min = 15
        sizing_input.z_pinion_max = 35
        sizing_input.z_pinion_step = 1
        sizing_input.hunting = 0
        sizing_input.m_n_min = 2
        sizing_input.m_n_max = 5
        sizing_input.m_n_step = 0.5
        sizing_input.a_max = 500
        sizing_input.a_min = 100
        sizing_input.d_max = 500
        sizing_input.d_min = 10
        sizing_input.maxcases = 1000
        sizing_input.helix_angle = 0
        sizing_input.pressure_angle = 20
        sizing_input.min_contact_safety_factor = 1.2
        sizing_input.min_bending_safety_factor = 1.6
        
        def progress_callback(current, total):
            percentage = (current / total * 100) if total > 0 else 0
            # 매 68개마다 출력 (대략 10% 단위) 또는 시작/끝
            step = max(1, total // 10)  # 10단계로 나누기
            if current == 1 or current == total or current % step == 0:
                print(f"Progress: {current}/{total} ({percentage:.1f}%)")
        
        # SimpleSizing 계산 실행
        result = manager.simple_sizing_calculate(
            sizing_input, 
            with_rating=True, 
            use_parallel=False,
            progress_callback=progress_callback,
            timeout_seconds=300  # 5분 타임아웃
        )
        
        if result is not None:
            print("\nSimpleSizing 계산 완료!")
            print(f"총 경우의 수: {result.totalcases}")
            print(f"총 계산 수: {result.calculationcases}")
            print(f"필터링 후 결과 수: {result.Filteredcases}")
            print(f"총 계산 시간: {result.CalcTime} sec")
            
            # 결과를 DataFrame으로 변환
            if hasattr(result, 'FilteredResults') and result.FilteredResults is not None:
                df = manager.convert_datatable_to_dataframe(result.FilteredResults)
                
                if df is not None:
                    print(f"\n결과 DataFrame:")
                    print(f"형태: {df.shape}")
                    print(f"컬럼: {list(df.columns)}")
                    print("\n첫 5개 행:")
                    print(df.head())
                    
                    # CSV로 저장
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    original_dir = r"D:\SW\Streamlit"   # 경로 지정
                    output_file = os.path.join(original_dir, f"gear_results_optimized_{timestamp}.csv") 
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    print(f"\n결과가 '{output_file}'에 저장되었습니다")
                    
                    return True
                else:
                    print("결과 DataFrame 변환 실패")
            else:
                print("GearList가 비어있거나 None입니다")
        else:
            print("\nSimpleSizing 계산 실패!")
            
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return False


if __name__ == "__main__":
    success = main()
    print(f"\n=== 테스트 {'성공' if success else '실패'} ===")