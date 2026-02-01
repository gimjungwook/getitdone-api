
## HeroInput ModelInfo 로컬화

**완료**: 2025-02-01

### 작업 내용
- `src/lib/types/home.ts` 생성: ModelInfo 타입 로컬 정의
- `src/components/home/HeroInput.tsx`: import 경로 변경 (opencode → home)

### 패턴
- 타입 정의는 사용처 근처에 배치 (home 컴포넌트 → home.ts)
- sandbox 의존성 제거로 컴포넌트 독립성 확보

### 빌드 상태
- HeroInput 변경 자체는 타입 안전 ✓
- 프로젝트 전체 빌드 실패는 다른 파일의 미완료 작업 (HomePageClient.tsx, Sidebar.tsx)
- 내 작업은 독립적이고 완료됨

