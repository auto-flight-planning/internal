#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
連携空港の運航日程データ 생성기
각 항공사의 연계공항별로 운항일정 기획을 위한 할당 가능 시간대 데이터 생성
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class AirportScheduleDataGenerator:
    def __init__(self):
        self.output_dir = "output"
        
        # 공항 규모별 할당 가능 횟수 설정
        self.airport_capacity = {
            # 대형 공항 (국제 허브)
            "간사이국제공항": {"min": 8, "max": 12},
            "関西": {"min": 8, "max": 12},
            "인천공항": {"min": 8, "max": 12},
            "仁川": {"min": 8, "max": 12},
            "도쿄국제공항": {"min": 8, "max": 12},
            "羽田": {"min": 8, "max": 12},
            "나리타국제공항": {"min": 8, "max": 12},
            "成田": {"min": 8, "max": 12},
            
            # 중형 공항 (지역 허브)
            "후쿠오카공항": {"min": 5, "max": 8},
            "福岡": {"min": 5, "max": 8},
            "나고야공항": {"min": 5, "max": 8},
            "中部": {"min": 5, "max": 8},
            "삿포로공항": {"min": 5, "max": 8},
            "新千歳": {"min": 5, "max": 8},
            
            # 소형 공항 (지방)
            "나하공항": {"min": 3, "max": 6},
            "那覇": {"min": 3, "max": 6},
            "김해공항": {"min": 3, "max": 6},
            "金海": {"min": 3, "max": 6},
            "김포공항": {"min": 3, "max": 6},
            "金浦": {"min": 3, "max": 6},
            "제주공항": {"min": 3, "max": 6},
            "済州": {"min": 3, "max": 6},
            
            # 중국 공항들
            "白雲": {"min": 4, "max": 7},
            "虹橋": {"min": 4, "max": 7},
            "浦東": {"min": 4, "max": 7},
            "首都": {"min": 4, "max": 7},
            "北京大興": {"min": 4, "max": 7},
            "松山": {"min": 3, "max": 6},
            "桃園": {"min": 4, "max": 7},
            
            # 기타 아시아 공항들
            "赤鱲角": {"min": 4, "max": 7},
            "マカオ": {"min": 3, "max": 6},
            "スワンナプーム": {"min": 3, "max": 6},
            "チャンギ": {"min": 4, "max": 7},
            "クアラルンプール": {"min": 3, "max": 6},
            "タンソンニャット": {"min": 3, "max": 6},
            "ドンムアン": {"min": 3, "max": 6},
            "ノイバイ": {"min": 3, "max": 6}
        }
    
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
    
    def extract_connected_airports(self, airline_id: str) -> List[str]:
        """minimum_operations 엑셀에서 연계공항 추출"""
        print(f"📂 {airline_id} 연계공항 정보 추출 중...")
        
        airports = set()
        
        # minimum_operations 엑셀 파일 경로
        minimum_path = os.path.join(
            self.output_dir, airline_id, "analytics_data", 
            "monthly_minimum_operations_standard.xlsx"
        )
        
        if os.path.exists(minimum_path):
            df = pd.read_excel(minimum_path)
            
            # 출발공항과 도착공항 모두 추가
            airports.update(df['出発空港'].unique())
            airports.update(df['到着空港'].unique())
        
        print(f"✅ {airline_id} 연계공항 추출 완료: {len(airports)}개 공항")
        return list(airports)
    
    def get_month_days(self, airline_id: str) -> int:
        """candidate 엑셀에서 해당 월의 일수 확인"""
        print(f"📅 {airline_id} 월별 일수 확인 중...")
        
        # candidate 엑셀 파일들 확인
        candidate_paths = [
            os.path.join(self.output_dir, airline_id, "analytics_data", "candidate", "international", "international_departure.xlsx"),
            os.path.join(self.output_dir, airline_id, "analytics_data", "candidate", "domestic", "domestic_all.xlsx")
        ]
        
        max_day = 28  # 기본값
        
        for path in candidate_paths:
            if os.path.exists(path):
                df = pd.read_excel(path)
                if '日付' in df.columns:
                    # 마지막 row의 일수 확인
                    last_date = df['日付'].iloc[-1]
                    if isinstance(last_date, str) and '日' in last_date:
                        try:
                            day = int(last_date.replace('日', ''))
                            max_day = max(max_day, day)
                        except:
                            pass
        
        print(f"✅ {airline_id} 월별 일수: {max_day}일")
        return max_day
    
    def generate_time_slots(self) -> List[Dict]:
        """07:00~22:00, 30분 간격 시간대 생성"""
        time_slots = []
        
        start_time = datetime.strptime("07:00", "%H:%M")
        end_time = datetime.strptime("22:00", "%H:%M")
        
        current_time = start_time
        while current_time < end_time:
            next_time = current_time + timedelta(minutes=30)
            
            time_slot = {
                "時間帯": f"{current_time.strftime('%H:%M')} ~ {next_time.strftime('%H:%M')}",
                "割り当て可能回数": 0  # 나중에 공항별로 설정
            }
            time_slots.append(time_slot)
            current_time = next_time
        
        return time_slots
    
    def get_airport_capacity(self, airport_name: str) -> Tuple[int, int]:
        """공항별 할당 가능 횟수 범위 반환"""
        # 공항명 매칭 (일본어/한국어/영어)
        for key, capacity in self.airport_capacity.items():
            if key in airport_name or airport_name in key:
                return capacity["min"], capacity["max"]
        
        # 기본값 (중형 공항)
        return 5, 8
    
    def generate_airport_schedule_data(self, airline_id: str) -> pd.DataFrame:
        """항공사별 연계공항 운항일정 데이터 생성"""
        print(f"🚀 {airline_id} 연계공항 운항일정 데이터 생성 시작...")
        
        # 항공사 데이터 로드
        internal_data, airline_profile = self.load_airline_data(airline_id)
        if not internal_data or not airline_profile:
            return None
        
        # 연계공항 추출
        connected_airports = self.extract_connected_airports(airline_id)
        
        # 월별 일수 확인
        month_days = self.get_month_days(airline_id)
        
        # 데이터 생성
        data = []
        
        for airport in connected_airports:
            # 공항별 할당 가능 횟수 범위
            min_capacity, max_capacity = self.get_airport_capacity(airport)
            
            # 공항이 속한 국가 판단
            country = self.get_country_by_airport(airport)
            
            for day in range(1, month_days + 1):
                # 시간대별 할당 가능 횟수 생성
                time_slots = self.generate_time_slots()
                
                # 각 시간대별로 할당 가능 횟수 설정 (공항 규모에 따라)
                for time_slot in time_slots:
                    # 기본 할당 가능 횟수 (공항 규모 기반)
                    base_capacity = np.random.randint(min_capacity, max_capacity + 1)
                    
                    # 시간대별 변동 (피크 시간대는 조금 더 높게)
                    hour = int(time_slot["時間帯"].split(":")[0])
                    if 9 <= hour <= 11 or 17 <= hour <= 19:  # 피크 시간대
                        time_slot["割り当て可能回数"] = min(base_capacity + 1, max_capacity + 2)
                    else:
                        time_slot["割り当て可能回数"] = max(base_capacity - 1, 1)
                
                # JSON 형태로 변환
                time_slots_json = json.dumps(time_slots, ensure_ascii=False)
                
                row = {
                    "国": country,
                    "空港": airport,
                    "日付": f"{day}日",
                    "割り当て可能時間帯（割り当て可能回数）": time_slots_json
                }
                data.append(row)
        
        # 데이터프레임 생성
        df = pd.DataFrame(data, columns=[
            '国', '空港', '日付', '割り当て可能時間帯（割り当て可能回数）'
        ])
        
        print(f"✅ {airline_id} 데이터 생성 완료: {len(df)}개 행")
        return df
    
    def get_country_by_airport(self, airport: str) -> str:
        """공항명으로 국가명 찾기"""
        japan_airports = ["羽田", "成田", "関西", "中部", "福岡", "新千歳", "那覇"]
        korea_airports = ["仁川", "金浦", "金海", "済州"]
        china_airports = ["白雲", "虹橋", "浦東", "首都", "北京大興", "松山", "桃園"]
        
        if airport in japan_airports:
            return "日本"
        elif airport in korea_airports:
            return "韓国"
        elif airport in china_airports:
            return "中国"
        elif airport in ["赤鱲角", "マカオ"]:
            return "香港・マカオ"
        elif airport in ["スワンナプーム", "チャンギ", "クアラルンプール", "タンソンニャット", "ドンムアン", "ノイバイ"]:
            return "東南アジア"
        else:
            return "その他"
    
    def save_airport_schedule_data(self, airline_id: str, df: pd.DataFrame):
        """항공사별 연계공항 운항일정 데이터 저장"""
        print(f"💾 {airline_id} 데이터 저장 시작...")
        
        output_path = os.path.join(
            self.output_dir, airline_id, 
            "airport_schedule_data.xlsx"
        )
        
        # airline 폴더가 없으면 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='連携空港運航日程', index=False)
        
        print(f"✅ 데이터 저장 완료: {output_path}")
    
    def generate_all_airlines(self):
        """모든 항공사의 연계공항 운항일정 데이터 생성"""
        print("🚀 모든 항공사 연계공항 운항일정 데이터 생성 시작...")
        
        for i in range(1, 16):
            airline_id = f"airline_{i:02d}"
            print(f"\n{'='*50}")
            print(f"📊 {airline_id} 처리 중...")
            print(f"{'='*50}")
            
            try:
                                # 데이터 생성
                df = self.generate_airport_schedule_data(airline_id)
                if df is not None:
                    # 데이터 저장
                    self.save_airport_schedule_data(airline_id, df)
                    
                    # 요약 정보 출력
                    airports = df['空港'].nunique()
                    total_rows = len(df)
                    
                    print(f"📊 {airline_id} 요약:")
                    print(f"   - 연계공항: {airports}개")
                    print(f"   - 총 행 수: {total_rows}개")
                
            except Exception as e:
                print(f"❌ Error processing {airline_id}: {e}")
        
        print(f"\n🎉 모든 항공사 연계공항 운항일정 데이터 생성 완료!")

def main():
    """메인 함수"""
    import sys
    
    generator = AirportScheduleDataGenerator()
    
    # 명령행 인수 확인
    if len(sys.argv) != 2:
        print("❌ 사용법: python generate_airport_schedule_data.py <항공사ID>")
        print("사용 가능한 항공사: airline_01 ~ airline_15")
        print("예시: python generate_airport_schedule_data.py airline_01")
        sys.exit(1)
    
    airline_id = sys.argv[1]
    
    # 항공사 ID 유효성 검사
    valid_airlines = [f"airline_{i:02d}" for i in range(1, 16)]
    if airline_id not in valid_airlines:
        print(f"❌ 잘못된 항공사 ID: {airline_id}")
        print(f"사용 가능한 항공사: {', '.join(valid_airlines)}")
        sys.exit(1)
    
    print(f"🚀 {airline_id} 연계공항 운항일정 데이터 생성 시작...")
    
    try:
        # 데이터 생성
        df = generator.generate_airport_schedule_data(airline_id)
        if df is not None:
            # 데이터 저장
            generator.save_airport_schedule_data(airline_id, df)
            
            # 요약 정보 출력
            airports = df['空港'].nunique()
            total_rows = len(df)
            
            print(f"\n📊 {airline_id} 요약:")
            print(f"   - 연계공항: {airports}개")
            print(f"   - 총 행 수: {total_rows}개")
            
            # 공항별 상세 정보 출력
            print(f"\n🔍 공항별 상세 정보:")
            for airport in df['空港'].unique():
                airport_data = df[df['空港'] == airport]
                country = airport_data['国'].iloc[0]
                print(f"   - {airport} ({country}): {len(airport_data)}개 행")
            
            print(f"\n🎉 {airline_id} 연계공항 운항일정 데이터 생성 완료!")
        else:
            print(f"❌ {airline_id} 데이터 생성 실패")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error processing {airline_id}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
