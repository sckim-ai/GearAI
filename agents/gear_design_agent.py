"""
기어 설계 에이전트
gear_classifier_agent로부터 수집된 정보를 활용해서 실제 기어 설계를 수행
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import datetime
import re

# 상위 디렉토리를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.base_agent import BaseAgent
from gear_design_manager import GearDesignManager
from utils.llm import llm_call


class GearDesignAgent(BaseAgent):
    """기어 설계 에이전트"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 경로 설정
        self.gear_design_path = config.get(
            'gear_design_path', 
            r"C:\SW\GearDesign\GearDesign\bin\Debug\net8.0-windows"
        )
        self.template_json_path = config.get(
            'template_json_path',
            str(Path(__file__).parent.parent / "TestGD.GD1")
        )
        
        # GearDesignManager 초기화는 필요시에만 수행
        self.manager = None
        self.template_config = None
        
        # 결과 저장 경로
        self.output_dir = Path(__file__).parent.parent
        
    def initialize_gear_manager(self):
        """GearDesignManager 초기화"""
        if self.manager is None:
            try:
                self.manager = GearDesignManager(
                    self.gear_design_path,
                    self.template_json_path
                )
                
                # Form 초기화
                if not self.manager.initialize_form():
                    raise Exception("Form 초기화 실패")
                    
                # 기본 템플릿 로드
                self.template_config = self.load_template_config()
                
                return True
            except Exception as e:
                print(f"GearDesignManager 초기화 실패: {e}")
                return False
        return True
    
    def load_template_config(self) -> Dict[str, Any]:
        """템플릿 JSON 설정 파일 로드"""
        try:
            with open(self.template_json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"템플릿 설정 로드 실패: {e}")
            return {}
    
    async def process_with_callback(self, user_input: str, callback=None) -> str:
        """사용자 입력을 받아서 기어 설계를 수행"""
        try:
            # 콜백으로 진행 상황 알림
            if callback:
                callback("🔧 **기어 설계 시작**\\n\\n기어 설계 시스템을 초기화 중...")
            
            # gear_classifier_agent에서 분석된 결과 파싱
            gear_info = self.parse_gear_info(user_input)
            
            if not gear_info:
                return "❌ 기어 설계 정보를 파싱할 수 없습니다. gear_classifier_agent를 먼저 실행해주세요."
            
            if callback:
                callback("🔧 **기어 설계 진행 중**\\n\\n수집된 정보를 바탕으로 설계 파라미터를 설정 중...")
            
            # 기어 설계 매니저 초기화
            if not self.initialize_gear_manager():
                return "❌ 기어 설계 시스템 초기화에 실패했습니다."
            
            # JSON 설정 수정
            modified_config = self.modify_config_from_gear_info(gear_info)
            
            if callback:
                callback("⚙️ **기어 계산 수행 중**\\n\\n기하학적 계산 및 강도 평가를 수행하고 있습니다...")
            
            # 기어 설계 계산 수행
            result = self.perform_gear_design(modified_config)
            
            if callback:
                callback("✅ **기어 설계 완료**\\n\\n결과를 정리 중...")
            
            return result
            
        except Exception as e:
            error_msg = f"❌ 기어 설계 중 오류 발생: {str(e)}"
            if callback:
                callback(error_msg)
            return error_msg
    
    def parse_gear_info(self, user_input: str) -> Optional[Dict[str, Any]]:
        """사용자 입력에서 기어 정보를 추출 (gear_classifier_agent의 결과라고 가정)"""
        # 실제로는 gear_classifier_agent의 상태 정보를 받아야 하지만,
        # 여기서는 사용자 입력에서 직접 파싱하는 방식으로 구현
        
        try:
            # LLM을 사용해서 기어 정보 추출
            system_prompt = \"\"\"
사용자 입력에서 기어 설계에 필요한 정보를 추출하세요.
다음 정보들을 JSON 형태로 반환하세요:

{
  "gear_type": "gear_pair|three_gear|simple_planetary|double_pinion_planetary",
  "speed_info": "속도 정보 문자열",
  "power_info": "파워/토크 정보 문자열", 
  "ratio_info": "기어비/잇수 정보 문자열",
  "others_info": "추가 정보 문자열 (모듈, 치폭, 재료 등)"
}

정보가 없는 경우 해당 필드는 빈 문자열로 설정하세요.
\"\"\"
            
            prompt = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
            
            response = llm_call(prompt=prompt, model="gpt-4o-mini")
            
            # JSON 블록 제거
            response = re.sub(r'```json\\s*|\\s*```', '', response).strip()
            
            gear_info = json.loads(response)
            return gear_info
            
        except Exception as e:
            print(f"기어 정보 파싱 오류: {e}")
            return None
    
    def modify_config_from_gear_info(self, gear_info: Dict[str, Any]) -> Dict[str, Any]:
        """기어 정보를 바탕으로 JSON 설정을 수정"""
        modified_config = self.template_config.copy()
        
        try:
            # 1. 기어 타입 설정 (GearTypeNum)
            gear_type_map = {
                "gear_pair": 0,
                "three_gear": 1,
                "simple_planetary": 2,
                "double_pinion_planetary": 3
            }
            
            gear_type = gear_info.get("gear_type", "gear_pair")
            if gear_type in gear_type_map:
                modified_config["Basic Data"]["GearTypeNum"] = gear_type_map[gear_type]
            
            # 2. 기어비/잇수 정보 처리
            ratio_info = gear_info.get("ratio_info", "")
            if ratio_info:
                self.apply_ratio_info(modified_config, ratio_info, gear_type)
            
            # 3. 파워/속도 정보를 Load spectrum에 반영
            power_info = gear_info.get("power_info", "")
            speed_info = gear_info.get("speed_info", "")
            if power_info or speed_info:
                self.apply_load_spectrum(modified_config, power_info, speed_info)
            
            # 4. 추가 정보 처리 (모듈, 치폭 등)
            others_info = gear_info.get("others_info", "")
            if others_info:
                self.apply_others_info(modified_config, others_info)
            
            # 5. CDMethod를 1로 설정 (중심거리 자동계산)
            modified_config["Basic Data"]["CDMethod"] = 1
            
            return modified_config
            
        except Exception as e:
            print(f"설정 수정 오류: {e}")
            return self.template_config
    
    def apply_ratio_info(self, config: Dict[str, Any], ratio_info: str, gear_type: str):
        """기어비/잇수 정보를 JSON에 반영"""
        try:
            # 기어비 패턴 매칭
            gear_ratio_pattern = r'기어비[:\s]*([0-9.]+)'
            ratio_pattern = r'([0-9]+)[:\s]*([0-9]+)'
            teeth_pattern = r'[zZ]?1[:\s]*([0-9]+)[,\s]*[zZ]?2[:\s]*([0-9]+)'
            
            if re.search(gear_ratio_pattern, ratio_info):
                # 기어비 정보
                match = re.search(gear_ratio_pattern, ratio_info)
                if match:
                    ratio = float(match.group(1))
                    if gear_type == "gear_pair":
                        # 기본적인 잇수 설정 (ratio 기준)
                        z1 = 25  # 기본값
                        z2 = int(z1 * ratio)
                        config["Basic Data"]["z1"] = str(z1)
                        config["Basic Data"]["z2"] = str(z2)
            
            elif re.search(teeth_pattern, ratio_info):
                # 잇수 정보
                match = re.search(teeth_pattern, ratio_info)
                if match:
                    z1 = int(match.group(1))
                    z2 = int(match.group(2))
                    config["Basic Data"]["z1"] = str(z1)
                    config["Basic Data"]["z2"] = str(z2)
            
            elif re.search(ratio_pattern, ratio_info):
                # 일반적인 비율 정보
                match = re.search(ratio_pattern, ratio_info)
                if match:
                    z1 = int(match.group(1))
                    z2 = int(match.group(2))
                    config["Basic Data"]["z1"] = str(z1)
                    config["Basic Data"]["z2"] = str(z2)
                    
        except Exception as e:
            print(f"기어비 정보 적용 오류: {e}")
    
    def apply_load_spectrum(self, config: Dict[str, Any], power_info: str, speed_info: str):
        """파워/속도 정보를 Load spectrum에 반영"""
        try:
            # 기존 Load spectrum 파싱
            load_spectrum_str = config["Rating"]["Load spectrum"]
            load_spectrum = json.loads(load_spectrum_str)
            
            if not load_spectrum:
                # 기본 Load spectrum 생성
                load_spectrum = [{
                    "Duration\\r[hr]": "20000.0",
                    "Temp.\\r[deg]": "80.0",
                    "\\rSpeed1\\r[rpm]": None,
                    "Gear 1\\rTorque1\\r[N.m]": None,
                    "\\rPower1\\r[kW]": None,
                    "\\rSpeed2\\r[rpm]": None,
                    "Gear 2\\rTorque2\\r[N.m]": None,
                    "\\rPower2\\r[kW]": None,
                    "\\rSpeed3\\r[rpm]": None,
                    "Gear 3\\rTorque3\\r[N.m]": None,
                    "\\rPower3\\r[kW]": None
                }]
            
            # 속도 정보 추출 및 적용
            if speed_info:
                speed_matches = re.findall(r'([0-9.]+)\\s*rpm', speed_info, re.IGNORECASE)
                if speed_matches:
                    load_spectrum[0]["\\rSpeed1\\r[rpm]"] = speed_matches[0]
            
            # 파워 정보 추출 및 적용
            if power_info:
                power_matches = re.findall(r'([0-9.]+)\\s*([kmKM]?[wW])', power_info)
                if power_matches:
                    power_value = float(power_matches[0][0])
                    unit = power_matches[0][1].lower()
                    if unit == 'kw':
                        power_value = power_value  # 이미 kW
                    elif unit == 'w':
                        power_value = power_value / 1000  # W를 kW로 변환
                    
                    load_spectrum[0]["\\rPower1\\r[kW]"] = str(power_value)
            
            # 토크 정보 추출 및 적용
            torque_matches = re.findall(r'([0-9.]+)\\s*([nN]\\s*[mM])', power_info)
            if torque_matches:
                torque_value = float(torque_matches[0][0])
                load_spectrum[0]["Gear 1\\rTorque1\\r[N.m]"] = str(torque_value)
            
            # 수정된 Load spectrum을 다시 JSON 문자열로 변환
            config["Rating"]["Load spectrum"] = json.dumps(load_spectrum, ensure_ascii=False)
            
        except Exception as e:
            print(f"Load spectrum 적용 오류: {e}")
    
    def apply_others_info(self, config: Dict[str, Any], others_info: str):
        """추가 정보 (모듈, 치폭 등)를 JSON에 반영"""
        try:
            # 모듈 정보 추출
            module_match = re.search(r'모듈\\s*([0-9.]+)', others_info)
            if module_match:
                module_value = module_match.group(1)
                config["Basic Data"]["Normal Module"] = module_value
            
            # 치폭 정보 추출
            face_width_match = re.search(r'치폭\\s*([0-9.]+)', others_info)
            if face_width_match:
                face_width_value = face_width_match.group(1)
                config["Basic Data"]["b1"] = face_width_value
                config["Basic Data"]["b2"] = face_width_value
            
            # 압력각 정보 추출
            pressure_angle_match = re.search(r'압력각\\s*([0-9.]+)', others_info)
            if pressure_angle_match:
                pressure_angle_value = pressure_angle_match.group(1)
                config["Basic Data"]["Pressure angle"] = pressure_angle_value
                
        except Exception as e:
            print(f"추가 정보 적용 오류: {e}")
    
    def perform_gear_design(self, modified_config: Dict[str, Any]) -> str:
        """기어 설계 계산 수행"""
        try:
            # 1. 설정 로드 및 검증
            if not self.manager.load_and_validate_config(modified_config):
                return "❌ 설정 로드 및 검증에 실패했습니다."
            
            # 2. 기하학적 계산
            geometry_result = self.manager.calculate_geometry()
            if not geometry_result:
                return "❌ 기하학적 계산에 실패했습니다."
            
            # 3. 하중 계산
            rating_result = self.manager.calculate_load_case(geometry_result)
            if not rating_result:
                return "❌ 하중 계산에 실패했습니다."
            
            # 4. 메시지 추출
            messages = self.manager.get_messages()
            
            # 5. 기어 이미지 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.output_dir / f"gear_image_{timestamp}.png"
            image_success = self.manager.get_gearimage(str(image_path))
            
            # 6. 결과 정리
            result_summary = self.format_design_results(
                geometry_result, rating_result, messages, 
                str(image_path) if image_success else None
            )
            
            return result_summary
            
        except Exception as e:
            return f"❌ 기어 설계 계산 중 오류 발생: {str(e)}"
    
    def format_design_results(self, geometry_result, rating_result, messages, image_path=None) -> str:
        """설계 결과를 포맷팅"""
        try:
            result_lines = [
                "✅ **기어 설계 완료!**\\n",
                "📊 **설계 결과 요약:**",
                ""
            ]
            
            # 메시지에서 주요 정보 추출
            if messages:
                result_lines.append("🔧 **계산 결과:**")
                # 메시지를 파싱해서 주요 정보만 추출
                key_info = self.extract_key_info_from_messages(messages)
                result_lines.extend(key_info)
                result_lines.append("")
            
            # 이미지 경로 추가
            if image_path and os.path.exists(image_path):
                result_lines.append(f"🖼️ **기어 이미지**: {image_path}")
                result_lines.append("")
            
            result_lines.extend([
                "✨ **설계가 성공적으로 완료되었습니다!**",
                "상세한 설계 데이터는 생성된 파일들을 확인해주세요."
            ])
            
            return "\\n".join(result_lines)
            
        except Exception as e:
            return f"결과 포맷팅 중 오류 발생: {str(e)}"
    
    def extract_key_info_from_messages(self, messages: str) -> List[str]:
        """메시지에서 핵심 정보 추출"""
        key_info = []
        try:
            # 메시지를 줄별로 분리
            lines = messages.split('\\n')
            
            for line in lines:
                # 중요한 정보가 포함된 라인 필터링
                if any(keyword in line for keyword in [
                    '중심거리', 'Center distance', 
                    '기어비', 'Gear ratio',
                    '안전계수', 'Safety factor',
                    '모듈', 'Module',
                    '잇수', 'Teeth'
                ]):
                    key_info.append(f"  • {line.strip()}")
                    
            if not key_info:
                key_info.append("  • 계산이 성공적으로 완료되었습니다.")
                
        except Exception as e:
            key_info = [f"  • 메시지 파싱 오류: {str(e)}"]
            
        return key_info