from fastapi import APIRouter

router = APIRouter()

# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Microsoft Agent Framework API"}

# 시스템 메트릭 조회
@router.get("/telemetry/metrics")
async def get_metrics():
    # 데모용 Mock 데이터 반환
    return {
        "active_runs": 5,
        "completed_runs_today": 120,
        "tokens_used": 45000
    }
