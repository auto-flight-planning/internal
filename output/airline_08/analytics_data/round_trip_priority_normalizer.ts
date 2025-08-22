/**
 * 往復運航優先順位指数正規化関数
 * airline_08 (中/小 규모 보유 - 중형 항공사)
 */

// 데이터 타입 정의
interface FlightData {
  日付: string; // 日付 (예: "1日", "2日")
  出発時刻: string; // 出発時刻 (예: "07:00", "14:30")
  飛行時間: number; // 飛行時間 (분)
  優先順位指数: number; // 優先順位指数
  飛行前必要時間: number; // 飛行前必要時間 (분)
  飛行後必要時間: number; // 飛行後必要時間 (분)
}

interface NormalizedResult {
  score: number;
  gapHours: number;
  resourceWasteScore: number;
  combinedPriority: number;
}

/**
 * 시간 문자열을 분 단위로 변환 (예: "14:30" → 870분)
 * @param timeStr - 시간 문자열 (HH:MM 형식)
 * @returns 분 단위 시간
 */
function timeStringToMinutes(timeStr: string): number {
  const [hours, minutes] = timeStr.split(":").map(Number);
  return hours * 60 + minutes;
}

/**
 * 왕복운항 우선순위지수 정규화 함수
 * @param outboundData - 가는편 데이터 (일본 출발)
 * @param inboundData - 오는편 데이터 (일본 도착)
 * @returns 정규화된 왕복 우선순위지수와 상세 정보
 */
export function normalizeRoundTripPriority(
  outboundData: FlightData,
  inboundData: FlightData
): NormalizedResult {
  // 기본 파라미터 (항공사별 특성 반영)
  const RESOURCE_WASTE_WEIGHT = 0.241; // 자원낭비 가중치
  const PRIORITY_WEIGHT = 0.759; // 우선순위지수 가중치

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

  if (gapHours <= 4) {
    // 이상적인 간격 - 자원낭비 최소
    resourceWasteScore = 1.0;
  } else if (gapHours <= 8) {
    // 적절한 간격 - 약간의 자원낭비
    resourceWasteScore = 0.8;
  } else if (gapHours <= 16) {
    // 긴 간격 - 중간 정도 자원낭비
    resourceWasteScore = 0.5;
  } else {
    // 매우 긴 간격 - 높은 자원낭비
    resourceWasteScore = 0.2;
  }

  // 4. 왕복 우선순위지수 계산
  const combinedPriority =
    (normalizedOutboundPriority + normalizedInboundPriority) / 2;

  // 5. 최종 정규화 (가중 평균)
  const finalScore =
    PRIORITY_WEIGHT * combinedPriority +
    RESOURCE_WASTE_WEIGHT * resourceWasteScore;

  // 6. 0-100 범위로 정규화
  const normalizedScore = Math.round(finalScore * 100);

  return {
    score: normalizedScore,
    gapHours: gapHours,
    resourceWasteScore: resourceWasteScore,
    combinedPriority: combinedPriority,
  };
}

// 기본 내보내기
export default normalizeRoundTripPriority;
