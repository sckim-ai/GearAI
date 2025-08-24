import json
from typing import List, Dict, Any, Optional, Union
from fuzzywuzzy import fuzz
import re


class JSONPathSearcher:
    """
    JSON 데이터에서 검색어와 매칭되는 키의 경로와 값을 반환하는 클래스
    $로 시작하는 설명 키를 자동으로 감지하여 함께 반환
    """
    
    def __init__(self, json_file: Optional[str] = None, json_data: Optional[Any] = None):
        """
        초기화 메서드
        
        Args:
            json_file: JSON 파일 경로
            json_data: JSON 데이터
        """
        if json_file:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        elif json_data is not None:
            self.data = json_data
        else:
            self.data = {}
    
    def search(self, query: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        검색어와 매칭되는 모든 키의 경로와 값을 찾아 반환
        설명 키($로 시작하는 키)가 있으면 함께 반환
        
        Args:
            query: 검색할 문자열
            threshold: 유사도 임계값 (0-100, 기본값 70)
        
        Returns:
            매칭된 결과 리스트 [{"path": "경로", "value": "값", "description": "설명", "score": 점수}, ...]
        """
        results = []
        query_lower = query.lower()
        
        # 재귀적으로 JSON 탐색
        self._search_recursive(self.data, query_lower, "", results, threshold)
        
        # 점수 순으로 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _search_recursive(self, obj: Any, query: str, current_path: str, 
                         results: List[Dict], threshold: float):
        """
        재귀적으로 JSON 객체를 탐색하며 매칭되는 키 찾기
        
        Args:
            obj: 현재 탐색 중인 객체
            query: 검색 쿼리 (소문자)
            current_path: 현재까지의 경로
            results: 결과를 저장할 리스트
            threshold: 유사도 임계값
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                # 설명 키($로 시작)는 검색 대상에서 제외
                if key.startswith('$'):
                    continue
                
                # 현재 경로 생성
                if current_path:
                    new_path = f"{current_path}.{key}"
                else:
                    new_path = key
                
                # 키 이름과 쿼리 비교
                key_lower = key.lower()
                match_found = False
                result_entry = None
                
                # 1. 정확한 매칭
                if query == key_lower:
                    result_entry = {
                        'path': new_path,
                        'value': value,
                        'score': 100.0,
                        'match_type': 'exact'
                    }
                    match_found = True
                
                # 2. 부분 문자열 매칭
                elif query in key_lower:
                    score = (len(query) / len(key_lower)) * 90
                    result_entry = {
                        'path': new_path,
                        'value': value,
                        'score': score,
                        'match_type': 'partial'
                    }
                    match_found = True
                
                # 3. 퍼지 매칭 (유사도 기반)
                else:
                    similarity = fuzz.ratio(query, key_lower)
                    if similarity >= threshold:
                        result_entry = {
                            'path': new_path,
                            'value': value,
                            'score': similarity,
                            'match_type': 'fuzzy'
                        }
                        match_found = True
                
                # 매칭된 경우 설명 키 찾기
                if match_found and result_entry:
                    # 현재 레벨에서 설명 키 찾기
                    description_key = f"${key}"
                    if description_key in obj:
                        result_entry['description'] = obj[description_key]
                    
                    results.append(result_entry)
                
                # 값이 딕셔너리나 리스트인 경우 재귀 탐색
                if isinstance(value, (dict, list)):
                    self._search_recursive(value, query, new_path, results, threshold)
        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                # 리스트 인덱스를 경로에 포함
                if current_path:
                    new_path = f"{current_path}[{idx}]"
                else:
                    new_path = f"[{idx}]"
                
                # 리스트 아이템이 딕셔너리나 리스트인 경우 재귀 탐색
                if isinstance(item, (dict, list)):
                    self._search_recursive(item, query, new_path, results, threshold)
    
    def search_value(self, query: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        값(value)에서 검색어를 찾아 반환
        
        Args:
            query: 검색할 문자열
            threshold: 유사도 임계값
        
        Returns:
            매칭된 결과 리스트
        """
        results = []
        query_lower = query.lower()
        
        self._search_value_recursive(self.data, query_lower, "", results, threshold)
        
        # 점수 순으로 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results
    
    def _search_value_recursive(self, obj: Any, query: str, current_path: str,
                               results: List[Dict], threshold: float):
        """
        재귀적으로 값을 탐색하며 매칭 찾기
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                # 설명 키는 검색 대상에서 제외
                if key.startswith('$'):
                    continue
                    
                if current_path:
                    new_path = f"{current_path}.{key}"
                else:
                    new_path = key
                
                # 값이 문자열인 경우 검색
                if isinstance(value, str):
                    value_lower = value.lower()
                    match_found = False
                    result_entry = None
                    
                    if query == value_lower:
                        result_entry = {
                            'path': new_path,
                            'value': value,
                            'score': 100.0,
                            'match_type': 'exact_value'
                        }
                        match_found = True
                    elif query in value_lower:
                        score = (len(query) / len(value_lower)) * 90
                        result_entry = {
                            'path': new_path,
                            'value': value,
                            'score': score,
                            'match_type': 'partial_value'
                        }
                        match_found = True
                    else:
                        similarity = fuzz.partial_ratio(query, value_lower)
                        if similarity >= threshold:
                            result_entry = {
                                'path': new_path,
                                'value': value,
                                'score': similarity,
                                'match_type': 'fuzzy_value'
                            }
                            match_found = True
                    
                    # 매칭된 경우 설명 키 찾기
                    if match_found and result_entry:
                        description_key = f"${key}"
                        if description_key in obj:
                            result_entry['description'] = obj[description_key]
                        results.append(result_entry)
                
                # 재귀 탐색
                elif isinstance(value, (dict, list)):
                    self._search_value_recursive(value, query, new_path, results, threshold)
        
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                if current_path:
                    new_path = f"{current_path}[{idx}]"
                else:
                    new_path = f"[{idx}]"
                
                if isinstance(item, str):
                    item_lower = item.lower()
                    
                    if query == item_lower:
                        results.append({
                            'path': new_path,
                            'value': item,
                            'score': 100.0,
                            'match_type': 'exact_value'
                        })
                    elif query in item_lower:
                        score = (len(query) / len(item_lower)) * 90
                        results.append({
                            'path': new_path,
                            'value': item,
                            'score': score,
                            'match_type': 'partial_value'
                        })
                    else:
                        similarity = fuzz.partial_ratio(query, item_lower)
                        if similarity >= threshold:
                            results.append({
                                'path': new_path,
                                'value': item,
                                'score': similarity,
                                'match_type': 'fuzzy_value'
                            })
                
                elif isinstance(item, (dict, list)):
                    self._search_value_recursive(item, query, new_path, results, threshold)
    
    def search_all(self, query: str, threshold: float = 70.0) -> Dict[str, List[Dict[str, Any]]]:
        """
        키와 값 모두에서 검색
        
        Args:
            query: 검색할 문자열
            threshold: 유사도 임계값
        
        Returns:
            {'keys': [...], 'values': [...]} 형태의 결과
        """
        return {
            'keys': self.search(query, threshold),
            'values': self.search_value(query, threshold)
        }
    
    def get_value_by_path(self, path: str) -> Any:
        """
        경로를 통해 값 가져오기
        
        Args:
            path: JSON 경로 (예: "user.profile.name" 또는 "items[0].id")
        
        Returns:
            해당 경로의 값
        """
        try:
            current = self.data
            
            # 경로를 파싱 (점과 대괄호 처리)
            parts = re.split(r'\.|\[|\]', path)
            parts = [p for p in parts if p]  # 빈 문자열 제거
            
            for part in parts:
                if part.isdigit():
                    # 숫자인 경우 리스트 인덱스로 처리
                    current = current[int(part)]
                else:
                    # 문자열인 경우 딕셔너리 키로 처리
                    current = current[part]
            
            return current
        except (KeyError, IndexError, TypeError):
            return None


# 사용 예시
if __name__ == "__main__":
    # 샘플 데이터
    sample_data = {
        "user": {
            "profile": {
                "name": "김철수",
                "$name": "사용자 이름",
                "email": "kim@example.com",
                "$email": "사용자 이메일 주소",
                "module_settings": {
                    "$module_settings": "모듈 관련 설정",
                    "theme": "dark",
                    "$theme": "UI 테마 설정",
                    "language": "ko",
                    "$language": "언어 설정"
                }
            },
            "permissions": ["read", "write", "execute"],
            "$permissions": "사용자 권한 목록"
        },
        "system": {
            "modules": [
                {
                    "id": 1, 
                    "name": "auth_module", 
                    "$name": "인증 모듈",
                    "status": "active",
                    "$status": "모듈 활성화 상태"
                },
                {
                    "id": 2, 
                    "name": "data_module",
                    "$name": "데이터 처리 모듈", 
                    "status": "inactive"
                },
                {
                    "id": 3, 
                    "name": "api_module",
                    "$name": "API 모듈",
                    "status": "active"
                }
            ],
            "$modules": "시스템 모듈 목록",
            "config": {
                "module_path": "/usr/local/modules",
                "$module_path": "모듈 설치 경로",
                "module_version": "2.1.0",
                "$module_version": "모듈 버전"
            }
        },
        "module_list": ["core", "extension", "plugin"],
        "$module_list": "사용 가능한 모듈 타입"
    }
    
    # 검색기 생성
    searcher = JSONPathSearcher(json_data=sample_data)
    
    print("=" * 60)
    print("JSONPathSearcher 테스트")
    print("=" * 60)
    
    # 1. 키 검색 테스트
    print("\n1. 'module' 키 검색:")
    results = searcher.search("module")
    for r in results[:5]:  # 상위 5개만 출력
        print(f"  경로: {r['path']}")
        print(f"  값: {r['value']}")
        if 'description' in r:
            print(f"  설명: {r['description']}")
        print(f"  점수: {r['score']:.1f} ({r['match_type']})")
        print()
    
    # 2. 값 검색 테스트
    print("\n2. 'active' 값 검색:")
    results = searcher.search_value("active")
    for r in results:
        print(f"  경로: {r['path']}")
        print(f"  값: {r['value']}")
        if 'description' in r:
            print(f"  설명: {r['description']}")
        print(f"  점수: {r['score']:.1f}")
        print()
    
    # 3. 유사도 기반 검색 (오타 포함)
    print("\n3. 'modul' 검색 (오타):")
    results = searcher.search("modul", threshold=60)
    for r in results[:3]:
        print(f"  경로: {r['path']}")
        if 'description' in r:
            print(f"  설명: {r['description']}")
        print(f"  점수: {r['score']:.1f} ({r['match_type']})")
    
    # 4. 경로로 값 가져오기
    print("\n4. 특정 경로의 값 가져오기:")
    path = "system.modules[0].name"
    value = searcher.get_value_by_path(path)
    print(f"  경로: {path}")
    print(f"  값: {value}")
    
    # 5. 키와 값 모두 검색
    print("\n5. 'module' 키와 값 모두 검색:")
    all_results = searcher.search_all("module")
    print(f"  키에서 발견: {len(all_results['keys'])}개")
    print(f"  값에서 발견: {len(all_results['values'])}개")