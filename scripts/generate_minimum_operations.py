#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
運航最小配分基準 데이터 생성기
각 항공사의 운항 노선별로 일일 최소 운항 횟수 기준 생성
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class MinimumOperationsGenerator:
    def __init__(self):
        self.output_dir = "output"
    
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
    
    def extract_existing_routes(self, airline_id: str) -> List[Dict]:
        """기존 candidate 데이터에서 노선 정보 추출"""
        print(f"📂 {airline_id} 기존 노선 정보 추출 중...")
        
        all_routes = []
        
        # 국제선 출발 데이터에서 노선 추출
        international_path = os.path.join(
            self.output_dir, airline_id, "analytics_data", "candidate", 
            "international_departure.csv"
        )
        
        if os.path.exists(international_path):
            df = pd.read_csv(international_path)
            # 고유한 노선만 추출 (출발공항 + 도착공항 기준)
            unique_international = df[['出発空港', '到着空港', '出発国家', '到着国家']].drop_duplicates()
            
            for _, row in unique_international.iterrows():
                all_routes.append({
                    "departure": row['出発空港'],
                    "arrival": row['到着空港'],
                    "departure_country": row['出発国家'],
                    "arrival_country": row['到着国家'],
                    "type": "international"
                })
        
        # 국내선 데이터에서 노선 추출
        domestic_path = os.path.join(
            self.output_dir, airline_id, "analytics_data", "candidate", 
            "domestic.csv"
        )
        
        if os.path.exists(domestic_path):
            df = pd.read_csv(domestic_path)
            # 고유한 노선만 추출 (출발공항 + 도착공항 기준)
            unique_domestic = df[['出発空港', '到着空港', '出発国家', '到着国家']].drop_duplicates()
            
            for _, row in unique_domestic.iterrows():
                all_routes.append({
                    "departure": row['出発空港'],
                    "arrival": row['到着空港'],
                    "departure_country": row['出発国家'],
                    "arrival_country": row['到着国家'],
                    "type": "domestic"
                })
        
        print(f"✅ {airline_id} 노선 추출 완료: {len(all_routes)}개 노선")
        return all_routes
    
    def determine_minimum_operations(self, route: Dict, airline_profile: Dict) -> int:
        """노선별 월별 최소 운항 횟수 결정 (노선 인기도 + 항공사 전략 고려)"""
        route_type = route["type"]
        brand_recognition = airline_profile.get("brand_recognition", 0.5)
        base_demand = airline_profile.get("base_demand", 100)
        international_focus = airline_profile.get("international_focus", 0.5)
        domestic_focus = airline_profile.get("domestic_focus", 0.5)
        
        # 노선별 인기도 계산
        route_popularity = self.calculate_route_popularity(route, airline_profile)
        
        # 항공사 전략적 가중치 계산
        strategic_weight = self.calculate_strategic_weight(route, airline_profile)
        
        # 월별 최소 운항 횟수 결정 (일별보다 훨씬 적음)
        if route_type == "international":
            base_min = self.determine_international_monthly_operations(
                route, airline_profile, route_popularity, strategic_weight
            )
        else:  # domestic
            base_min = self.determine_domestic_monthly_operations(
                route, airline_profile, route_popularity, strategic_weight
            )
        
        return base_min
    
    def calculate_route_popularity(self, route: Dict, airline_profile: Dict) -> float:
        """노선별 인기도 계산 (0.0 ~ 1.0)"""
        departure = route["departure"]
        arrival = route["arrival"]
        route_type = route["type"]
        
        # 1. 거리 기반 인기도 (가까울수록 인기)
        distance_factor = self.get_distance_popularity(departure, arrival)
        
        # 2. 노선 타입별 기본 인기도
        type_factor = 0.8 if route_type == "domestic" else 0.6
        
        # 3. 특정 인기 노선 보너스
        popular_bonus = self.get_popular_route_bonus(departure, arrival)
        
        # 4. 브랜드 인지도 영향
        brand_factor = airline_profile.get("brand_recognition", 0.5)
        
        # 5. 기본 수요 영향
        demand_factor = min(airline_profile.get("base_demand", 100) / 150.0, 1.0)
        
        # 종합 인기도 계산
        popularity = (distance_factor * 0.3 + 
                     type_factor * 0.25 + 
                     popular_bonus * 0.2 + 
                     brand_factor * 0.15 + 
                     demand_factor * 0.1)
        
        return min(max(popularity, 0.0), 1.0)
    
    def get_distance_popularity(self, departure: str, arrival: str) -> float:
        """거리 기반 인기도 (가까울수록 높음)"""
        # 주요 공항 간 거리별 인기도 (실제 데이터 기반)
        route_key = f"{departure}-{arrival}"
        
        # 국내선 (거리별 인기도)
        domestic_popularity = {
            "羽田-関西": 0.95,    # 도쿄-오사카 (매우 인기)
            "羽田-中部": 0.90,    # 도쿄-나고야 (매우 인기)
            "羽田-福岡": 0.85,    # 도쿄-후쿠오카 (인기)
            "関西-中部": 0.80,    # 오사카-나고야 (인기)
            "関西-福岡": 0.75,    # 오사카-후쿠오카 (보통)
            "中部-福岡": 0.70,    # 나고야-후쿠오카 (보통)
            "新千歳-那覇": 0.65,  # 삿포로-오키나와 (보통)
        }
        
        # 국제선 (거리별 인기도)
        international_popularity = {
            "羽田-金海": 0.95,        # 도쿄-부산 (매우 인기)
            "羽田-仁川": 0.95,        # 도쿄-인천 (매우 인기)
            "羽田-桃園": 0.90,        # 도쿄-타이페이 (인기)
            "羽田-北京大興": 0.85,    # 도쿄-베이징 (인기)
            "関西-金海": 0.85,        # 오사카-부산 (인기)
            "関西-仁川": 0.85,        # 오사카-인천 (인기)
            "関西-桃園": 0.80,        # 오사카-타이페이 (보통)
            "関西-北京大興": 0.75,    # 오사카-베이징 (보통)
            "福岡-金海": 0.90,        # 후쿠오카-부산 (매우 인기)
            "福岡-仁川": 0.90,        # 후쿠오카-인천 (매우 인기)
            "福岡-桃園": 0.85,        # 후쿠오카-타이페이 (인기)
            "福岡-北京大興": 0.70,    # 후쿠오카-베이징 (보통)
        }
        
        # 정방향과 역방향 모두 확인
        if route_key in domestic_popularity:
            return domestic_popularity[route_key]
        elif route_key in international_popularity:
            return international_popularity[route_key]
        
        # 역방향 확인
        reverse_key = f"{arrival}-{departure}"
        if reverse_key in domestic_popularity:
            return domestic_popularity[reverse_key]
        elif reverse_key in international_popularity:
            return international_popularity[reverse_key]
        
        # 기본값 (거리 추정)
        return 0.6
    
    def get_popular_route_bonus(self, departure: str, arrival: str) -> float:
        """특정 인기 노선 보너스"""
        # 비즈니스/관광 중심지 연결 노선
        business_routes = [
            "羽田-関西", "関西-羽田",      # 도쿄-오사카 (비즈니스)
            "羽田-中部", "中部-羽田",      # 도쿄-나고야 (비즈니스)
            "羽田-金海", "金海-羽田",      # 도쿄-부산 (비즈니스+관광)
            "羽田-仁川", "仁川-羽田",      # 도쿄-인천 (비즈니스+관광)
            "関西-金海", "金海-関西",      # 오사카-부산 (비즈니스+관광)
            "関西-仁川", "仁川-関西",      # 오사카-인천 (비즈니스+관광)
        ]
        
        route_key = f"{departure}-{arrival}"
        if route_key in business_routes:
            return 0.2  # 20% 보너스
        
        return 0.0
    
    def calculate_strategic_weight(self, route: Dict, airline_profile: Dict) -> float:
        """항공사 전략적 가중치 계산"""
        route_type = route["type"]
        brand_recognition = airline_profile.get("brand_recognition", 0.5)
        international_focus = airline_profile.get("international_focus", 0.5)
        domestic_focus = airline_profile.get("domestic_focus", 0.5)
        
        # 1. 브랜드 인지도에 따른 전략적 가중치
        brand_strategy = brand_recognition * 0.4
        
        # 2. 노선 타입별 전략적 가중치
        if route_type == "international":
            type_strategy = international_focus * 0.3
        else:  # domestic
            type_strategy = domestic_focus * 0.3
        
        # 3. 항공사 규모별 전략적 가중치
        # 소형 항공사는 국내선에 더 집중하는 경향
        size_strategy = 0.0
        if route_type == "domestic" and brand_recognition < 0.4:
            size_strategy = 0.2  # 소형 항공사 국내선 전략적 가중치
        
        # 4. 경쟁 우위 전략
        competitive_strategy = 0.0
        if route_type == "domestic" and brand_recognition < 0.5:
            # 소형 항공사는 국내선에서 가격 경쟁력으로 승부
            competitive_strategy = 0.1
        
        total_strategy = brand_strategy + type_strategy + size_strategy + competitive_strategy
        return min(max(total_strategy, 0.0), 1.0)
    
    def determine_international_monthly_operations(self, route: Dict, airline_profile: Dict, 
                                                route_popularity: float, strategic_weight: float) -> int:
        """국제선 월별 최소 운항 횟수 결정"""
        brand_recognition = airline_profile.get("brand_recognition", 0.5)
        base_demand = airline_profile.get("base_demand", 100)
        
        # 기본 범위: 3~8회 (월별이므로 적절한 수준)
        base_min = 3
        base_max = 8
        
        # 1. 노선 인기도에 따른 조정
        if route_popularity > 0.9:      # 매우 인기
            base_min = 6
            base_max = 10
        elif route_popularity > 0.7:    # 인기
            base_min = 5
            base_max = 8
        elif route_popularity > 0.5:    # 보통
            base_min = 4
            base_max = 7
        else:                            # 낮음
            base_min = 3
            base_max = 6
        
        # 2. 항공사 전략적 가중치에 따른 조정
        if strategic_weight > 0.8:      # 매우 전략적
            base_min = min(base_min + 2, base_max)
        elif strategic_weight > 0.6:    # 전략적
            base_min = min(base_min + 1, base_max)
        
        # 3. 브랜드 인지도와 기본 수요에 따른 조정
        if brand_recognition > 0.8 and base_demand > 120:
            base_min = min(base_min + 1, base_max)
        elif brand_recognition > 0.6 and base_demand > 100:
            base_min = min(base_min + 1, base_max)
        
        return np.random.randint(base_min, base_max + 1)
    
    def determine_domestic_monthly_operations(self, route: Dict, airline_profile: Dict, 
                                           route_popularity: float, strategic_weight: float) -> int:
        """국내선 월별 최소 운항 횟수 결정"""
        brand_recognition = airline_profile.get("brand_recognition", 0.5)
        base_demand = airline_profile.get("base_demand", 100)
        
        # 기본 범위: 4~12회 (월별이므로 적절한 수준)
        base_min = 4
        base_max = 12
        
        # 1. 노선 인기도에 따른 조정
        if route_popularity > 0.9:      # 매우 인기
            base_min = 8
            base_max = 15
        elif route_popularity > 0.7:    # 인기
            base_min = 7
            base_max = 12
        elif route_popularity > 0.5:    # 보통
            base_min = 6
            base_max = 10
        else:                            # 낮음
            base_min = 4
            base_max = 8
        
        # 2. 항공사 전략적 가중치에 따른 조정
        if strategic_weight > 0.8:      # 매우 전략적
            base_min = min(base_min + 2, base_max)
        elif strategic_weight > 0.6:    # 전략적
            base_min = min(base_min + 1, base_max)
        
        # 3. 소형 항공사 국내선 전략 (가격 경쟁력)
        if brand_recognition < 0.4 and route_popularity > 0.7:
            # 소형 항공사가 인기 국내선에 더 집중
            base_min = min(base_min + 2, base_max)
            base_max = min(base_max + 3, 18)
        
        # 4. 브랜드 인지도와 기본 수요에 따른 조정
        if brand_recognition > 0.7 and base_demand > 100:
            base_min = min(base_min + 1, base_max)
        elif brand_recognition > 0.5 and base_demand > 80:
            base_min = min(base_min + 1, base_max)
        
        return np.random.randint(base_min, base_max + 1)
    
    def generate_minimum_operations_data(self, airline_id: str) -> pd.DataFrame:
        """항공사별 운항 최소 배분 기준 데이터 생성"""
        print(f"🚀 {airline_id} 운항 최소 배분 기준 데이터 생성 시작...")
        
        # 항공사 데이터 로드
        internal_data, airline_profile = self.load_airline_data(airline_id)
        if not internal_data or not airline_profile:
            return None
        
        # 노선 생성
        routes = self.extract_existing_routes(airline_id)
        
        # 데이터 생성
        data = []
        for route in routes:
            min_operations = self.determine_minimum_operations(route, airline_profile)
            
            row = {
                "出発国家": route["departure_country"],
                "出発空港": route["departure"],
                "到着国家": route["arrival_country"],
                "到着空港": route["arrival"],
                "最低維持月別運航回数": min_operations
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        print(f"✅ {airline_id} 데이터 생성 완료: {len(df)}개 노선")
        return df
    
    def save_minimum_operations_data(self, airline_id: str, df: pd.DataFrame):
        """운항 최소 배분 기준 데이터를 Excel로 저장"""
        print(f"💾 {airline_id} 데이터 저장 시작...")
        
        # CSV 파일로 저장
        output_path = os.path.join(self.output_dir, airline_id, "monthly_minimum_operations_standard.csv")
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        print(f"✅ {airline_id} 월별 최소 운항 기준 CSV 저장 완료: {output_path}")
    
    def generate_all_airlines(self):
        """모든 항공사의 운항 최소 배분 기준 데이터 생성"""
        print("🚀 모든 항공사 운항 최소 배분 기준 데이터 생성 시작...")
        
        for i in range(1, 16):
            airline_id = f"airline_{i:02d}"
            print(f"\n{'='*50}")
            print(f"📊 {airline_id} 처리 중...")
            print(f"{'='*50}")
            
            try:
                # 데이터 생성
                df = self.generate_minimum_operations_data(airline_id)
                if df is not None:
                    # 데이터 저장
                    self.save_minimum_operations_data(airline_id, df)
                    
                    # 요약 정보 출력
                    international_routes = df[df['到着国家'] != '日本'].shape[0]
                    domestic_routes = df[df['到着国家'] == '日本'].shape[0]
                    
                    print(f"📊 {airline_id} 요약:")
                    print(f"   - 총 노선: {len(df)}개")
                    print(f"   - 국제선: {international_routes}개")
                    print(f"   - 국내선: {domestic_routes}개")
                    print(f"   - 월별 최소 운항 횟수 범위: {df['最低維持月別運航回数'].min()}~{df['最低維持月別運航回数'].max()}회")
                
            except Exception as e:
                print(f"❌ Error processing {airline_id}: {e}")
        
        print(f"\n🎉 모든 항공사 운항 최소 배분 기준 데이터 생성 완료!")

def main():
    """메인 함수"""
    import sys
    
    generator = MinimumOperationsGenerator()
    
    # 명령행 인수 확인
    if len(sys.argv) != 2:
        print("❌ 사용법: python generate_minimum_operations.py <항공사ID>")
        print("사용 가능한 항공사: airline_01 ~ airline_15")
        print("예시: python generate_minimum_operations.py airline_01")
        sys.exit(1)
    
    airline_id = sys.argv[1]
    
    # 항공사 ID 유효성 검사
    valid_airlines = [f"airline_{i:02d}" for i in range(1, 16)]
    if airline_id not in valid_airlines:
        print(f"❌ 잘못된 항공사 ID: {airline_id}")
        print(f"사용 가능한 항공사: {', '.join(valid_airlines)}")
        sys.exit(1)
    
    print(f"🚀 {airline_id} 운항 최소 배분 기준 데이터 생성 시작...")
    
    try:
        # 데이터 생성
        df = generator.generate_minimum_operations_data(airline_id)
        if df is not None:
            # 데이터 저장
            generator.save_minimum_operations_data(airline_id, df)
            
            # 요약 정보 출력
            international_routes = df[df['到着国家'] != '日本'].shape[0]
            domestic_routes = df[df['到着国家'] == '日本'].shape[0]
            
            print(f"\n📊 {airline_id} 요약:")
            print(f"   - 총 노선: {len(df)}개")
            print(f"   - 국제선: {international_routes}개")
            print(f"   - 국내선: {domestic_routes}개")
            print(f"   - 월별 최소 운항 횟수 범위: {df['最低維持月別運航回数'].min()}~{df['最低維持月別運航回数'].max()}회")
            
            # 노선별 상세 정보 출력
            print(f"\n🔍 노선별 상세 정보:")
            for _, row in df.iterrows():
                route_type = "국제선" if row['到着国家'] != '日本' else "국내선"
                print(f"   - {row['出発空港']} → {row['到着空港']} ({route_type}): {row['最低維持月別運航回数']}회")
            
            print(f"\n🎉 {airline_id} 운항 최소 배분 기준 데이터 생성 완료!")
        else:
            print(f"❌ {airline_id} 데이터 생성 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error processing {airline_id}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
