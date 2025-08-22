#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
운항후보별 최적수익・우선순위 데이터 생성 스크립트
運航候補別の最適収益・優先順位データ

각 airline별로 internal_resource_data.json과 profile.py를 읽어서
운항후보별 최적수익・우선순위 데이터를 생성합니다.
"""

import json
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CandidateDataGenerator:
    """운항후보별 최적수익・우선순위 데이터 생성기"""
    
    def __init__(self):
        self.output_dir = "output"
        self.airlines = [f"airline_{i:02d}" for i in range(1, 16)]
        
        # 주요 공항 정보 (일본, 한국, 중국, 대만, 홍콩, 동남아시아)
        self.airports = {
            "日本": ["羽田", "成田", "関西", "中部", "福岡", "新千歳", "那覇"],
            "韓国": ["仁川", "金浦", "金海", "済州"],
            "中国": ["北京大興", "首都", "浦東", "虹橋", "白雲"],
            "台湾": ["桃園", "松山"],
            "香港": ["赤鱲角"],
            "マカオ": ["マカオ"],
            "タイ": ["スワンナプーム", "ドンムアン"],
            "シンガポール": ["チャンギ"],
            "マレーシア": ["クアラルンプール"],
            "ベトナム": ["ノイバイ", "タンソンニャット"]
        }
        
        # 국가별 공항 코드
        self.airport_codes = {
            "羽田": "HND", "成田": "NRT", "関西": "KIX", "中部": "NGO",
            "福岡": "FUK", "新千歳": "CTS", "那覇": "OKA",
            "仁川": "ICN", "金浦": "GMP", "金海": "PUS", "済州": "CJU",
            "北京大興": "PKX", "首都": "PEK", "浦東": "PVG", "虹橋": "SHA", "白雲": "CAN",
            "桃園": "TPE", "松山": "TSA",
            "赤鱲角": "HKG", "マカオ": "MFM",
            "スワンナプーム": "BKK", "ドンムアン": "DMK",
            "チャンギ": "SIN", "クアラルンプール": "KUL",
            "ノイバイ": "HAN", "タンソンニャット": "SGN"
        }
        
        # 공항별 대략적인 좌표 (위도, 경도) - 거리 계산용
        self.airport_coordinates = {
            # 일본 공항들
            "羽田": (35.6762, 139.6503), "成田": (35.6762, 140.3863),
            "関西": (34.4273, 135.2441), "中部": (34.8584, 136.8054),
            "福岡": (33.5902, 130.4017), "那覇": (26.2124, 127.6809),
            "新千歳": (42.7752, 141.6928),
            
            # 한국 공항들
            "仁川": (37.4602, 126.4407), "済州": (33.5112, 126.4930),
            
            # 중국 공항들
            "北京大興": (39.5098, 116.4105), "首都": (39.9088, 116.3975),
            "浦東": (31.1443, 121.8083), "白雲": (23.3924, 113.2988),
            
            # 대만 공항들
            "桃園": (25.0800, 121.2320),
            
            # 동남아시아 공항들
            "赤鱲角": (22.3080, 113.9185), "マカオ": (22.1566, 113.5589),
            "スワンナプーム": (13.6900, 100.7501), "ドンムアン": (13.9126, 100.6068),
            "チャンギ": (1.3644, 103.9915), "クアラルンプール": (2.7456, 101.7072),
            "ノイバイ": (21.2214, 105.8074), "タンソンニャット": (10.8189, 106.6519)
        }
        
        # 공항별 기본 비행시간 (30분 단위로 깔끔하게)
        self.flight_times = {}
        
        # 출발시각 설정 (7시~22시, 30분 간격) - 31개 시간대
        self.departure_times = []
        for hour in range(7, 23):  # 7시~22시
            for minute in [0, 30]:
                self.departure_times.append(f"{hour:02d}:{minute:02d}")
        
        # 월별 날짜 범위 설정
        self.month_days = {
            2: 28,      # 2월 (윤년 고려하지 않음)
            4: 30,      # 4월
            6: 30,      # 6월
            9: 30,      # 9월
            11: 30,     # 11월
            1: 31,      # 1월
            3: 31,      # 3월
            5: 31,      # 5월
            7: 31,      # 7월
            8: 31,      # 8월
            10: 31,     # 10월
            12: 31      # 12월
        }
        
    def get_random_month_and_days(self) -> Tuple[int, int]:
        """랜덤한 월과 해당 월의 날짜 범위 반환"""
        month = np.random.choice(list(self.month_days.keys()))
        max_days = self.month_days[month]
        return month, max_days
    
    def calculate_distance(self, airport1: str, airport2: str) -> float:
        """두 공항 간의 거리 계산 (km) - Haversine 공식 사용"""
        if airport1 not in self.airport_coordinates or airport2 not in self.airport_coordinates:
            return 1000.0  # 기본값
        
        lat1, lon1 = self.airport_coordinates[airport1]
        lat2, lon2 = self.airport_coordinates[airport2]
        
        # Haversine 공식으로 거리 계산
        R = 6371  # 지구 반지름 (km)
        dlat = np.radians(lat2 - lat1)
        dlon = np.radians(lon2 - lon1)
        a = (np.sin(dlat/2)**2 + 
             np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2)
        c = 2 * np.arcsin(np.sqrt(a))
        distance = R * c
        
        return distance
    
    def calculate_flight_time(self, departure: str, arrival: str) -> int:
        """거리 기반으로 비행시간 계산 (30분 단위로 반올림)"""
        # 이미 계산된 비행시간이 있으면 반환
        route_key = (departure, arrival)
        if route_key in self.flight_times:
            return self.flight_times[route_key]
        
        # 거리 계산
        distance = self.calculate_distance(departure, arrival)
        
        # 거리에 따른 비행시간 계산 (평균 속도 800km/h 가정)
        # 실제로는 바람, 고도 등에 따라 달라지지만 여기서는 단순화
        flight_time_hours = distance / 800.0
        
        # 30분 단위로 반올림 (분 단위)
        flight_time_minutes = round(flight_time_hours * 60 / 30) * 30
        
        # 최소/최대 비행시간 제한
        if flight_time_minutes < 30:
            flight_time_minutes = 30
        elif flight_time_minutes > 480:  # 8시간
            flight_time_minutes = 480
        
        # 계산된 비행시간 저장 (다음번에 재사용)
        self.flight_times[route_key] = flight_time_minutes
        
        return flight_time_minutes
    
    def load_airline_data(self, airline_id: str) -> Tuple[Dict, Dict]:
        """항공사별 internal_resource_data.json과 profile.py 로드"""
        try:
            print(f"📁 {airline_id} 데이터 로딩 중...")
            
            # internal_resource_data.json 로드
            internal_path = os.path.join(self.output_dir, airline_id, "internal_resource_data.json")
            with open(internal_path, 'r', encoding='utf-8') as f:
                internal_data = json.load(f)
            
            # profile.py 로드
            profile_path = os.path.join(self.output_dir, airline_id, "profile.py")
            sys.path.insert(0, os.path.join(self.output_dir, airline_id))
            from profile import AIRLINE_PROFILE
            sys.path.pop(0)
            
            print(f"✅ {airline_id} 데이터 로딩 완료")
            return internal_data, AIRLINE_PROFILE
            
        except Exception as e:
            print(f"❌ Error loading data for {airline_id}: {e}")
            return None, None
    
    def generate_routes(self, airline_profile: Dict) -> List[Dict]:
        """항공사별 연계공항 및 노선 생성"""
        print(f"🛫 {airline_profile['route_count_range']}개 노선 생성 중...")
        
        routes = []
        route_count = np.random.randint(*airline_profile["route_count_range"])
        
        # 일본 공항들을 중심으로 노선 생성
        japan_airports = self.airports["日本"]
        other_countries = [k for k in self.airports.keys() if k != "日本"]
        
        # 국제선 생성 (일본 ↔ 해외)
        international_count = int(route_count * 0.6)  # 60%는 국제선
        for _ in range(international_count):
            japan_airport = np.random.choice(japan_airports)
            other_country = np.random.choice(other_countries)
            other_airport = np.random.choice(self.airports[other_country])
            
            # 일본 출발 노선
            routes.append({
                "departure": japan_airport,
                "arrival": other_airport,
                "departure_country": "日本",
                "arrival_country": other_country,
                "type": "international",
                "direction": "departure"  # 일본 출발
            })
            
            # 외국 출발 노선 (일본 도착)
            routes.append({
                "departure": other_airport,
                "arrival": japan_airport,
                "departure_country": other_country,
                "arrival_country": "日本",
                "type": "international",
                "direction": "arrival"   # 일본 도착
            })
        
        # 국내선 생성 (일본 ↔ 일본)
        domestic_count = route_count - international_count
        for _ in range(domestic_count):
            airport1, airport2 = np.random.choice(japan_airports, 2, replace=False)
            routes.append({
                "departure": airport1,
                "arrival": airport2,
                "departure_country": "日本",
                "arrival_country": "日本",
                "type": "domestic",
                "direction": "both"      # 국내선은 양방향
            })
        
        print(f"✅ {len(routes)}개 노선 생성 완료")
        return routes
    
    def generate_demand_function(self, airline_profile: Dict, route_type: str, 
                                departure_time: str) -> Dict:
        """수요함수 생성 (가격-수요 관계)"""
        # 기본 수요량
        base_demand = airline_profile["base_demand"]
        
        # 브랜드 인지도 영향
        brand_multiplier = airline_profile["brand_recognition"]
        
        # 노선 타입별 영향
        if route_type == "international":
            route_multiplier = airline_profile["international_focus"]
        else:  # domestic
            route_multiplier = airline_profile["domestic_focus"]
        
        # 시간대별 영향 (피크시간, 오프피크)
        time_multiplier = self.get_time_multiplier(departure_time)
        
        # 최종 수요량
        final_demand = int(base_demand * brand_multiplier * route_multiplier * time_multiplier)
        
        # 가격 민감도
        price_elasticity = airline_profile["price_elasticity"]
        
        return {
            "base_demand": final_demand,
            "price_elasticity": price_elasticity
        }
    
    def get_time_multiplier(self, departure_time: str) -> float:
        """시간대별 수요 배수 계산 (7시~22시)"""
        hour = int(departure_time.split(":")[0])
        
        # 피크시간: 8-9시, 17-19시
        if hour in [8, 9, 17, 18, 19]:
            return np.random.uniform(1.1, 1.3)
        # 오프피크: 7시, 22시
        elif hour in [7, 22]:
            return np.random.uniform(0.7, 0.9)
        # 일반시간: 10-16시, 20-21시
        else:
            return np.random.uniform(0.9, 1.1)
    
    def get_price_range(self, flight_time: str, route_type: str) -> Tuple[int, int]:
        """비행시간과 노선타입에 따른 가격 범위 결정"""
        # 비행시간을 분으로 변환
        time_minutes = int(flight_time.replace('分', ''))
        
        if route_type == "domestic":
            # 국내선: 1만엔 ~ 3만엔
            min_price = 10000
            max_price = 30000
        else:  # international
            if time_minutes <= 120:  # 2시간 이하 (한국, 대만)
                min_price = 15000
                max_price = 35000
            elif time_minutes <= 240:  # 4시간 이하 (중국)
                min_price = 20000
                max_price = 45000
            else:  # 4시간 초과 (동남아시아)
                min_price = 25000
                max_price = 50000
        
        return min_price, max_price

    def calculate_optimal_revenue(self, demand_data: Dict, route_type: str, 
                                 internal_data: Dict, flight_time: str) -> Dict:
        """최적수익 계산 (수요함수 + 운항규모함수 + 수익함수)"""
        base_demand = demand_data["base_demand"]
        price_elasticity = demand_data["price_elasticity"]
        
        # 거리와 노선타입에 따른 가격 범위 결정
        min_price, max_price = self.get_price_range(flight_time, route_type)
        prices = np.arange(min_price, max_price + 1000, 1000)
        
        # 수요함수: 수요 = 기본수요 * (가격/기본가격)^가격민감도
        base_price = 20000  # 기본가격 2만엔
        demands = []
        revenues = []
        
        for price in prices:
            demand = int(base_demand * (price / base_price) ** price_elasticity)
            demand = max(demand, 10)  # 최소 수요 10명
            demands.append(demand)
            revenues.append(price * demand)
        
        # 최적 가격과 수요 찾기
        optimal_idx = np.argmax(revenues)
        optimal_price = prices[optimal_idx]
        optimal_demand = demands[optimal_idx]
        optimal_revenue = revenues[optimal_idx]
        
        # 운항규모 결정
        operation_scale_data = self.determine_operation_scale(
            optimal_demand, internal_data, route_type
        )
        
        return {
            "収益(円)": int(optimal_revenue),
            "価格(円)": int(optimal_price),
            "需要(名)": int(optimal_demand),
            "運航規模データ": operation_scale_data
        }
    
    def determine_operation_scale(self, demand: int, internal_data: Dict, 
                                 route_type: str) -> Dict:
        """수요에 따른 운항규모 결정"""
        operation_scales = internal_data["運航規模種類"]
        
        # 수요에 따른 운항규모 선택
        if "大規模運航" in operation_scales and demand > 300:
            scale_key = "大規模運航"
        elif "中規模運航" in operation_scales and demand > 150:
            scale_key = "中規模運航"
        else:
            scale_key = "小規模運航"
        
        scale_data = internal_data["運航規模別データ"][scale_key]
        
        return {
            "運航規模": scale_key,
            "座席数": int(scale_data["座席数"]),
            "運航可能な最小収益(円)": int(scale_data["運航可能最小収益"]),
            "必要人員データ": {
                "機長・副操縦士の人数": [
                    int(scale_data["必要人員データ"]["必要機長数"]),
                    int(scale_data["必要人員データ"]["必要副操縦士数"])
                ],
                "その他必要人員指数": int(self.calculate_personnel_index(
                    demand, scale_data["必要人員データ"]["その他必要人員指数"]
                ))
            },
            "飛行前後に必要な時間": scale_data["飛行前後必要時間"]
        }
    
    def calculate_personnel_index(self, demand: int, personnel_data: List[Dict]) -> int:
        """수요에 따른 필요인력지수 계산"""
        for item in personnel_data:
            if demand <= item["最大乗客数"]:
                return item["必要人員指数"]
        return personnel_data[-1]["必要人員指数"]  # 최대값 반환
    
    def calculate_priority_index(self, revenue: int, operation_data: Dict, route_type: str, 
                                departure_time: str, airline_profile: Dict, route_info: Dict) -> float:
        """우선순위 지수 계산 (투입자원 대비 수익 효율성) - 개선된 버전"""

        # 투입자원 계산
        seats = operation_data["座席数"]  # 항공기 자원
        personnel_index = operation_data["必要人員データ"]["その他必要人員指数"]  # 인력 자원
        flight_time = operation_data["飛行前後に必要な時間"]["前"] + operation_data["飛行前後に必要な時間"]["後"]  # 시간 자원

        # 기본 자원 가중치 (항공기:인력:시간 = 5:3:2)
        aircraft_weight = 5
        personnel_weight = 3
        time_weight = 2

        # 가중 평균 자원량
        weighted_resources = (
            seats * aircraft_weight +
            personnel_index * personnel_weight +
            flight_time * time_weight
        )

        # 우선순위 지수 계산 (극도로 복잡한 공식으로 겹침 방지)
        
        # 1. 기본 수익 효율성 (복잡한 로그 함수 적용)
        efficiency_base = (revenue / weighted_resources) * 0.1
        efficiency_log = np.log10(revenue / 1000000 + 1) * 8.7642  # 로그 스케일링
        efficiency_score = min(efficiency_base + efficiency_log, 35.0)
        
        # 2. 노선 타입별 복합 점수 (시드값 활용)
        route_seed = hash(f"{route_type}_{departure_time}_{revenue}") % 1000000 / 1000000
        if route_type == "international":
            route_base = 12.0 + route_seed * 8.0
            route_multiplier = 1.0 + (airline_profile["international_focus"] - 0.5) * 0.3
        else:
            route_base = 8.0 + route_seed * 7.0
            route_multiplier = 1.0 + (airline_profile["domestic_focus"] - 0.5) * 0.2
        route_score = route_base * route_multiplier
        
        # 3. 시간대별 다층 점수 (분단위까지 고려)
        hour = int(departure_time.split(":")[0])
        minute = int(departure_time.split(":")[1])
        time_base_hour = {
            7: 5.2, 8: 18.7, 9: 17.3, 10: 12.8, 11: 14.1, 12: 13.9,
            13: 11.6, 14: 12.4, 15: 13.7, 16: 15.2, 17: 19.1, 18: 18.9,
            19: 17.8, 20: 14.3, 21: 12.1, 22: 8.4
        }.get(hour, 10.0)
        minute_factor = 1.0 + (minute - 15) * 0.001234  # 분단위 미세 조정
        time_noise = np.sin(hour * 0.7 + minute * 0.1) * 2.3456  # 사인파 노이즈
        time_score = time_base_hour * minute_factor + time_noise
        
        # 4. 브랜드 인지도 다항식 점수
        brand_raw = airline_profile["brand_recognition"]
        brand_polynomial = 3.2 * brand_raw**3 + 2.1 * brand_raw**2 + 4.7 * brand_raw
        brand_oscillation = np.cos(brand_raw * 17.234) * 0.8765
        brand_score = brand_polynomial + brand_oscillation
        
        # 5. 수익 규모별 복합 보너스 (지수함수 적용)
        revenue_factor = revenue / 1000000.0  # 백만엔 단위
        revenue_exp = np.power(revenue_factor, 0.7854) * 2.3456
        revenue_log = np.log(revenue_factor + 0.5) * 1.9876
        if revenue > 5000000:
            revenue_bonus = 7.8 + revenue_exp * 0.3 + revenue_log
        elif revenue > 3000000:
            revenue_bonus = 4.2 + revenue_exp * 0.2 + revenue_log * 0.8
        else:
            revenue_bonus = 1.5 + revenue_exp * 0.1 + revenue_log * 0.5
        
        # 6. 자원 비율 기반 복잡 점수
        seat_ratio = seats / 300.0  # 정규화
        personnel_ratio = personnel_index / 10.0  # 정규화
        time_ratio = flight_time / 120.0  # 정규화
        
        resource_harmony = np.sin(seat_ratio * 3.14159) * np.cos(personnel_ratio * 2.718) * 3.456
        resource_balance = abs(seat_ratio - personnel_ratio) * (-2.789)  # 불균형 페널티
        resource_score = resource_harmony + resource_balance + 8.0
        
        # 7. 극도로 복잡한 고유성 점수 (거의 100% 고유값 보장)
        # 더 많은 변수들을 조합하여 해시 생성
        airport_from = route_info.get("departure", "")
        airport_to = route_info.get("arrival", "")
        unique_string = f"{revenue}_{seats}_{personnel_index}_{flight_time}_{departure_time}_{route_type}_{airport_from}_{airport_to}_{airline_profile['brand_recognition']}_{efficiency_score}"
        
        # 여러 개의 다른 해시 값 생성
        hash_value1 = hash(unique_string)
        hash_value2 = hash(unique_string + "_secondary")
        hash_value3 = hash(unique_string + "_tertiary")
        hash_value4 = hash(str(revenue * seats * personnel_index))
        
        # 극도로 정밀한 해시 팩터들
        hash_factors = []
        for i, hash_val in enumerate([hash_value1, hash_value2, hash_value3, hash_value4]):
            for shift in [0, 8, 16, 24, 32, 40, 48, 56]:
                factor = ((hash_val >> shift) % 1000000007) / 1000000007.0
                hash_factors.append(factor)
        
        # 복잡한 삼각함수와 지수 조합
        uniqueness_components = []
        for i, factor in enumerate(hash_factors[:16]):  # 첫 16개 팩터 사용
            component = (
                factor * (i + 1) * 0.123456789 +
                np.sin(factor * (i + 1) * 7.891234) * 0.456789 +
                np.cos(factor * (i + 1) * 11.234567) * 0.789012 +
                np.tan(factor * 0.1 + i * 0.01) * 0.234567 +
                np.exp(factor * 0.01) * 0.012345 +
                np.log(factor + 0.001) * 0.567890
            )
            uniqueness_components.append(component)
        
        uniqueness_score = sum(uniqueness_components)
        
        # 8. 최종 가중 조합 (비선형 결합)
        components = [efficiency_score, route_score, time_score, brand_score, 
                     revenue_bonus, resource_score, uniqueness_score]
        
        # 복잡한 가중치 (황금비율과 소수 활용)
        weights = [1.618033, 0.577215, 1.414213, 0.693147, 1.732050, 0.367879, 2.302585]
        
        weighted_sum = sum(c * w for c, w in zip(components, weights))
        
        # 비선형 변환
        nonlinear_factor = np.tanh(weighted_sum / 50.0) * 85.0 + 15.0
        
        # 미세 조정 (극도로 정밀한 소수점 - 여러 레이어)
        micro_hash1 = hash_value1 % 1000000007
        micro_hash2 = hash_value2 % 1000000007  
        micro_hash3 = hash_value3 % 1000000007
        micro_hash4 = hash_value4 % 1000000007
        
        # 다층 미세 조정
        micro_adjustment1 = micro_hash1 / 100000000000.0  # 10^-11 단위
        micro_adjustment2 = micro_hash2 / 1000000000000.0  # 10^-12 단위  
        micro_adjustment3 = micro_hash3 / 10000000000000.0  # 10^-13 단위
        micro_adjustment4 = micro_hash4 / 100000000000000.0  # 10^-14 단위
        
        total_micro_adjustment = micro_adjustment1 + micro_adjustment2 + micro_adjustment3 + micro_adjustment4
        
        # 최종 점수
        final_score = nonlinear_factor + total_micro_adjustment
        
        # 0-100 범위로 정규화하되 극도로 정밀
        normalized_score = min(max(final_score, 0.0), 100.0)

        return round(normalized_score, 7)  # 소수점 7째자리까지
    
    def generate_candidate_data(self, airline_id: str) -> Dict[str, pd.DataFrame]:
        """항공사별 운항후보 데이터 생성 (국제선/국내선 분리)"""
        print(f"🚀 {airline_id} 운항후보 데이터 생성 시작...")
        
        # 항공사 데이터 로드
        internal_data, airline_profile = self.load_airline_data(airline_id)
        if not internal_data or not airline_profile:
            return None
        
        # 노선 생성
        routes = self.generate_routes(airline_profile)
        
        # 랜덤한 월과 날짜 범위 선택
        month, max_days = self.get_random_month_and_days()
        print(f"📅 {month}월 1일~{max_days}일 데이터 생성")
        
        # 데이터 분리용 딕셔너리
        data_sets = {
            "international_departure": [],    # 국제선: 일본 출발
            "international_arrival": [],      # 국제선: 일본 도착
            "domestic": []                    # 국내선: 모든 경우
        }
        
        # 각 노선별로 데이터 생성
        for route in routes:
            print(f"🛫 {route['departure']} → {route['arrival']} 노선 처리 중...")
            
            # 推奨最大運航数 설정 (노선별 인기도에 따라)
            if route["type"] == "international":
                max_operations = np.random.randint(3, 8)  # 국제선: 3-7회
            else:
                max_operations = np.random.randint(5, 12)  # 국내선: 5-11회
            
            # 모든 날짜에 대해 데이터 생성
            for day in range(1, max_days + 1):
                date = f"{day}日"
                
                for departure_time in self.departure_times:
                    # 수요함수 생성
                    demand_data = self.generate_demand_function(
                        airline_profile, route["type"], departure_time
                    )
                    
                    # 비행시간 계산 (기본값 또는 저장된 값)
                    flight_time = self.calculate_flight_time(route["departure"], route["arrival"])
                    flight_time_str = f"{flight_time}分"
                    
                    # 최적수익 계산
                    optimal_data = self.calculate_optimal_revenue(
                        demand_data, route["type"], internal_data, flight_time_str
                    )
                    
                    # 우선순위 지수 계산 (개선된 버전)
                    priority_index = self.calculate_priority_index(
                        optimal_data["収益(円)"], 
                        optimal_data["運航規模データ"], 
                        route["type"], 
                        departure_time, 
                        airline_profile,
                        route
                    )
                    
                    # 디버깅: 우선순위 지수 계산 과정 확인
                    if np.random.random() < 0.01:  # 1% 확률로 로그 출력
                        print(f"🔍 우선순위 지수 계산 디버깅:")
                        print(f"   수익: {optimal_data['収益(円)']:,}円")
                        print(f"   좌석수: {optimal_data['運航規模データ']['座席数']}")
                        print(f"   인력지수: {optimal_data['運航規模データ']['必要人員データ']['その他必要人員指数']}")
                        print(f"   비행시간: {optimal_data['運航規模データ']['飛行前後に必要な時間']['前'] + optimal_data['運航規模データ']['飛行前後に必要な時間']['後']}분")
                        print(f"   최종 우선순위 지수: {priority_index}")
                    
                    # 행 데이터 생성
                    row = {
                        "日付": date,
                        "出発国家": route["departure_country"],
                        "出発空港": route["departure"],
                        "到着国家": route["arrival_country"],
                        "到着空港": route["arrival"],
                        "出発時刻": departure_time,
                        "飛行時間": flight_time,  # 비행시간 추가 (분 단위)
                        "推奨最大運航数": max_operations,
                        "収益(円)": optimal_data["収益(円)"],
                        "価格(円)": optimal_data["価格(円)"],
                        "需要(名)": optimal_data["需要(名)"],
                        "運航規模": optimal_data["運航規模データ"]["運航規模"],
                        "座席数": optimal_data["運航規模データ"]["座席数"],
                        "運航可能な最小収益(円)": optimal_data["運航規模データ"]["運航可能な最小収益(円)"],
                        "必要機長数": optimal_data["運航規模データ"]["必要人員データ"]["機長・副操縦士の人数"][0],
                        "必要副操縦士数": optimal_data["運航規模データ"]["必要人員データ"]["機長・副操縦士の人数"][1],
                        "その他必要人員指数": optimal_data["運航規模データ"]["必要人員データ"]["その他必要人員指数"],
                        "飛行前必要時間": optimal_data["運航規模データ"]["飛行前後に必要な時間"]["前"],
                        "飛行後必要時間": optimal_data["運航規模データ"]["飛行前後に必要な時間"]["後"],
                        "優先順位指数": priority_index
                    }
                    
                    # 노선 타입과 방향에 따라 적절한 데이터셋에 추가
                    if route["type"] == "international":
                        if route["direction"] == "departure":
                            data_sets["international_departure"].append(row)
                        else:  # arrival
                            data_sets["international_arrival"].append(row)
                    else:  # domestic
                        data_sets["domestic"].append(row)
        
        print(f"✅ 데이터 생성 완료:")
        print(f"   - 국제선 출발: {len(data_sets['international_departure'])}건")
        print(f"   - 국제선 도착: {len(data_sets['international_arrival'])}건")
        print(f"   - 국내선: {len(data_sets['domestic'])}건")
        
        # DataFrame으로 변환
        result = {}
        for key, data_list in data_sets.items():
            if data_list:  # 빈 리스트가 아닌 경우만
                result[key] = pd.DataFrame(data_list)
            else:
                result[key] = pd.DataFrame()
        
        return result
    
    def save_candidate_data(self, airline_id: str, data_sets: Dict[str, pd.DataFrame]):
        """운항후보 데이터를 Excel로 저장 (국제선/국내선 분리)"""
        print(f"💾 {airline_id} 데이터 저장 시작...")
        
        # 국제선 출발 데이터 저장
        if not data_sets["international_departure"].empty:
            departure_path = os.path.join(
                self.output_dir, airline_id, "analytics_data", "candidate", "international", 
                "international_departure.xlsx"
            )
            with pd.ExcelWriter(departure_path, engine='openpyxl') as writer:
                data_sets["international_departure"].to_excel(writer, sheet_name='運航候補データ', index=False)
            print(f"✅ 국제선 출발 데이터 저장: {departure_path} ({len(data_sets['international_departure'])}건)")
        
        # 국제선 도착 데이터 저장
        if not data_sets["international_arrival"].empty:
            arrival_path = os.path.join(
                self.output_dir, airline_id, "analytics_data", "candidate", "international", 
                "international_arrival.xlsx"
            )
            with pd.ExcelWriter(arrival_path, engine='openpyxl') as writer:
                data_sets["international_arrival"].to_excel(writer, sheet_name='運航候補データ', index=False)
            print(f"✅ 국제선 도착 데이터 저장: {arrival_path} ({len(data_sets['international_arrival'])}건)")
        
        # 국내선 데이터 저장
        if not data_sets["domestic"].empty:
            domestic_path = os.path.join(
                self.output_dir, airline_id, "analytics_data", "candidate", "domestic", 
                "domestic_all.xlsx"
            )
            with pd.ExcelWriter(domestic_path, engine='openpyxl') as writer:
                data_sets["domestic"].to_excel(writer, sheet_name='運航候補データ', index=False)
            print(f"✅ 국내선 데이터 저장: {domestic_path} ({len(data_sets['domestic'])}건)")
        
        print(f"🎉 {airline_id} 모든 데이터 저장 완료!")
    
    def generate_all_airlines(self):
        """모든 항공사별 운항후보 데이터 생성"""
        print("🚀 모든 항공사 운항후보 데이터 생성 시작...")
        
        for airline_id in self.airlines:
            try:
                print(f"\n{'='*50}")
                print(f"📊 {airline_id} 처리 중...")
                print(f"{'='*50}")
                
                # 데이터 생성
                data_sets = self.generate_candidate_data(airline_id)
                
                # 저장
                if data_sets is not None:
                    self.save_candidate_data(airline_id, data_sets)
                
            except Exception as e:
                print(f"❌ Error processing {airline_id}: {e}")
                continue
        
        print("\n🎉 모든 항공사 데이터 생성 완료!")

def main():
    """메인 함수"""
    import sys
    
    generator = CandidateDataGenerator()
    
    # 명령행 인수 확인
    if len(sys.argv) > 1:
        airline_id = sys.argv[1]
        if airline_id in generator.airlines:
            print(f"🚀 {airline_id} 단일 항공사 데이터 생성 시작...")
            data_sets = generator.generate_candidate_data(airline_id)
            if data_sets is not None:
                generator.save_candidate_data(airline_id, data_sets)
        else:
            print(f"❌ 잘못된 항공사 ID: {airline_id}")
            print(f"사용 가능한 항공사: {', '.join(generator.airlines)}")
    else:
        print("🚀 모든 항공사 데이터 생성 시작...")
        generator.generate_all_airlines()

if __name__ == "__main__":
    main() 