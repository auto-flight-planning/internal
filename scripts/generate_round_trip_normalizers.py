#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
왕복 운항 우선순위 지수 정규화 함수 생성기
각 항공사의 profile.py 특성을 반영하여 개별적인 가중치 적용
"""

import os
import sys
import importlib.util

def load_airline_profile(airline_id: str) -> dict:
    """항공사별 profile.py 로드"""
    profile_path = os.path.join("output", airline_id, "profile.py")
    
    # 동적으로 profile.py 모듈 로드
    spec = importlib.util.spec_from_file_location("profile", profile_path)
    profile_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(profile_module)
    
    return profile_module.AIRLINE_PROFILE

def calculate_weights(profile: dict) -> tuple:
    """프로필 데이터를 기반으로 가중치 계산"""
    # 기본 값들 추출
    brand_recognition = profile.get("brand_recognition", 0.5)
    base_demand = profile.get("base_demand", 100)
    operation_scales = profile.get("operation_scales", [])
    route_count_avg = sum(profile.get("route_count_range", (10, 20))) / 2
    
    # 규모 점수 (1~3점)
    scale_score = len(operation_scales)
    
    # 자원 여유도 점수 계산 (0~1)
    resource_abundance = (
        brand_recognition * 0.3 +           # 브랜드 영향력 30%
        (base_demand / 200) * 0.3 +         # 수요 규모 30%
        (scale_score / 3) * 0.25 +          # 운항 규모 25%
        (route_count_avg / 35) * 0.15       # 노선 수 15%
    )
    
    # 자원낭비 가중치 계산 (자원이 많을수록 낮게)
    resource_waste_weight = 0.35 - (resource_abundance * 0.2)
    resource_waste_weight = max(0.10, min(0.30, resource_waste_weight))  # 0.10~0.30 범위
    
    # 우선순위 가중치
    priority_weight = 1.0 - resource_waste_weight
    
    return round(resource_waste_weight, 3), round(priority_weight, 3)

def get_airline_description(airline_id: str, profile: dict) -> str:
    """항공사 설명 생성"""
    scales = profile.get("operation_scales", [])
    scale_desc = "/".join([s.replace("規模運航", "") for s in scales])
    
    if len(scales) == 3:
        size_desc = "대형 항공사"
    elif len(scales) == 2:
        size_desc = "중형 항공사"
    else:
        size_desc = "소형 항공사"
    
    return f"{airline_id} ({scale_desc} 규모 보유 - {size_desc})"

def generate_typescript_file(airline_id: str, profile: dict, resource_weight: float, priority_weight: float):
    """TypeScript 정규화 함수 파일 생성"""
    
    description = get_airline_description(airline_id, profile)
    
    typescript_content = f'''/**
 * 往復運航優先順位指数正規化関数
 * {description}
 */

// 데이터 타입 정의
interface FlightData {{
  日付: string; // 日付 (예: "1日", "2日")
  出発時刻: string; // 出発時刻 (예: "07:00", "14:30")
  飛行時間: number; // 飛行時間 (분)
  優先順位指数: number; // 優先順位指数
  飛行前必要時間: number; // 飛行前必要時間 (분)
  飛行後必要時間: number; // 飛行後必要時間 (분)
}}

interface NormalizedResult {{
  score: number;
  gapHours: number;
  resourceWasteScore: number;
  combinedPriority: number;
}}

/**
 * 시간 문자열을 분 단위로 변환 (예: "14:30" → 870분)
 * @param timeStr - 시간 문자열 (HH:MM 형식)
 * @returns 분 단위 시간
 */
function timeStringToMinutes(timeStr: string): number {{
  const [hours, minutes] = timeStr.split(":").map(Number);
  return hours * 60 + minutes;
}}

/**
 * 왕복운항 우선순위지수 정규화 함수
 * @param outboundData - 가는편 데이터 (일본 출발)
 * @param inboundData - 오는편 데이터 (일본 도착)
 * @returns 정규화된 왕복 우선순위지수와 상세 정보
 */
export function normalizeRoundTripPriority(
  outboundData: FlightData,
  inboundData: FlightData
): NormalizedResult {{
  // 기본 파라미터 (항공사별 특성 반영)
  const RESOURCE_WASTE_WEIGHT = {resource_weight}; // 자원낭비 가중치
  const PRIORITY_WEIGHT = {priority_weight}; // 우선순위지수 가중치

  // 1. 우선순위지수 정규화 (0-100)
  const normalizedOutboundPriority = outboundData.優先順位指数 / 100;
  const normalizedInboundPriority = inboundData.優先順位指数 / 100;

  // 2. 공백시간 계산 (시간 단위)
  const outboundDay = parseInt(outboundData.日付.replace("日", ""));
  const inboundDay = parseInt(inboundData.日付.replace("日", ""));

  // 도착시각 = 출발시각 + 비행시간
  const outboundDepartureMinutes = timeStringToMinutes(outboundData.出発時刻);
  const outboundFlightMinutes = outboundData.飛行時間;
  const outboundArrivalMinutes =
    outboundDepartureMinutes + outboundFlightMinutes;

  const outboundPostFlightMinutes = outboundData.飛行後必要時間;
  const outboundAvailableMinutes =
    outboundArrivalMinutes + outboundPostFlightMinutes;

  const inboundDepartureMinutes = timeStringToMinutes(inboundData.出発時刻);
  const inboundPreFlightMinutes = inboundData.飛行前必要時間;
  const inboundRequiredMinutes =
    inboundDepartureMinutes - inboundPreFlightMinutes;

  // 일자 차이를 분 단위로 계산
  const dayDifference = (inboundDay - outboundDay) * 24 * 60;
  const timeDifference = inboundRequiredMinutes - outboundAvailableMinutes;
  const totalGapMinutes = dayDifference + timeDifference;

  const gapHours = totalGapMinutes / 60;

  // 3. 공백시간 자원낭비 점수 계산
  let resourceWasteScore = 0;

  if (gapHours <= 4) {{
    // 이상적인 간격 - 자원낭비 최소
    resourceWasteScore = 1.0;
  }} else if (gapHours <= 8) {{
    // 적절한 간격 - 약간의 자원낭비
    resourceWasteScore = 0.8;
  }} else if (gapHours <= 16) {{
    // 긴 간격 - 중간 정도 자원낭비
    resourceWasteScore = 0.5;
  }} else {{
    // 매우 긴 간격 - 높은 자원낭비
    resourceWasteScore = 0.2;
  }}

  // 4. 왕복 우선순위지수 계산
  const combinedPriority =
    (normalizedOutboundPriority + normalizedInboundPriority) / 2;

  // 5. 최종 정규화 (가중 평균)
  const finalScore =
    PRIORITY_WEIGHT * combinedPriority +
    RESOURCE_WASTE_WEIGHT * resourceWasteScore;

  // 6. 0-100 범위로 정규화
  const normalizedScore = Math.round(finalScore * 100);

  return {{
    score: normalizedScore,
    gapHours: gapHours,
    resourceWasteScore: resourceWasteScore,
    combinedPriority: combinedPriority,
  }};
}}

// 기본 내보내기
export default normalizeRoundTripPriority;
'''
    
    # 파일 저장
    output_dir = os.path.join("output", airline_id, "analytics_data")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "round_trip_priority_normalizer.ts")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(typescript_content)
    
    return output_path

def main():
    """메인 함수 - 모든 항공사의 정규화 함수 생성"""
    print("🚀 왕복 운항 우선순위 지수 정규화 함수 생성 시작...")
    
    for i in range(1, 16):
        airline_id = f"airline_{i:02d}"
        print(f"\n📁 {airline_id} 처리 중...")
        
        try:
            # 프로필 로드
            profile = load_airline_profile(airline_id)
            
            # 가중치 계산
            resource_weight, priority_weight = calculate_weights(profile)
            
            # TypeScript 파일 생성
            output_path = generate_typescript_file(airline_id, profile, resource_weight, priority_weight)
            
            print(f"   브랜드 인지도: {profile['brand_recognition']}")
            print(f"   기본 수요: {profile['base_demand']}")
            print(f"   운항 규모: {len(profile['operation_scales'])}개")
            print(f"   → 자원낭비 가중치: {resource_weight}")
            print(f"   → 우선순위 가중치: {priority_weight}")
            print(f"✅ 생성 완료: {output_path}")
            
        except Exception as e:
            print(f"❌ Error processing {airline_id}: {e}")
    
    print("\n🎉 모든 항공사 정규화 함수 생성 완료!")

if __name__ == "__main__":
    main()
