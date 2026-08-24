#!/bin/bash
echo "🏛️ 직원용 세출 예산 포털을 실행합니다..."
cd "$(dirname "$0")"
streamlit run src/app_budget_portal.py --server.port 8507
