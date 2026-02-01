# AI Feature Rebuild - From Scratch

## TL;DR

> **Quick Summary**: AICAMPUS의 작동하지 않는 AI 샌드박스 기능을 완전히 재구축. 기존 코드 전체 삭제 후 TDD 방식으로 재작성. Supabase 스키마부터 Python 백엔드, React 프론트엔드까지 전체 재설계.
> 
> **Deliverables**:
> - 새로운 Supabase 데이터베이스 스키마 (opencode_sessions, opencode_messages 등)
> - Python FastAPI 백엔드 (agentic loop 포함)
> - Next.js 프론트엔드 (Turn 기반 채팅 UI)
> - Vitest + pytest 테스트 인프라
> - Phase 0 의존성 분리 작업 (빌드 안정성 확보)
> 
> **Estimated Effort**: Large (2-3주)
> **Parallel Execution**: YES - 각 Phase 내에서 병렬 작업 가능
> **Critical Path**: Phase 0 → Phase 1 (삭제) → Phase 2 (테스트 인프라) → Phase 3 (DB) → Phase 4 (백엔드) → Phase 5 (프론트엔드)

---

## Context

### Original Request
"We will start from scratch for ai feature in ai campus, copying the agentic loop and opencode web experience on frontend."

기존 AI 기능이 꼬여서 작동하지 않아, 처음부터 완전히 재작성하기로 결정.

### Interview Summary
**Key Discussions**:
- **재구축 이유**: 기존 코드가 작동하지 않음. 이전에는 작동했으나 현재 문제 발생.
- **삭제 범위**: 프론트엔드 + 백엔드 모두 삭제
- **DB 스키마**: Supabase 스키마 재설계
- **참조 수준**: 기존 코드 복사 후 리팩토링
- **테스트 전략**: TDD 방식 (Vitest + pytest)
- **작업 순서**: DB 스키마 → 백엔드 → 프론트엔드
- **목표**: 코드 품질, 성능, 확장성 + 작동하는 코드

**Research Findings**:
- 현재 구조: Next.js 16 + React 19 + Python FastAPI
- 기존 agentic loop: `src/opencode_api/session/prompt.py`의 `_agentic_loop`
- 기존 UI: Turn 기반 아키텍처, SSE 스트리밍
- 테스트 인프라: 현재 없음 (구축 필요)
- OpenCode 패턴: ThreadProvider + StreamProvider, LangGraph 통합 등

### Metis Review
**Identified Gaps** (addressed):
1. **삭제 범위 불완전**: 13개 파일/디렉토리 누락 → 완전한 삭제 목록 작성
2. **공유 컴포넌트 파괴**: ChatInputBar, MarkdownEditor 등 5개 파일 의존성 → Phase 0 의존성 분리 선행
3. **레슨 시스템 연계**: lesson.ts, admin.ts 참조 → 레슨 AI 기능도 삭제 후 재작성
4. **이중 시스템**: conversations vs opencode_sessions → 모두 DROP 후 재설계
5. **getitdone-api 중복**: src/opencode_api 복사본 → src/opencode_api 삭제, getitdone-api만 재작성
6. **테스트 인프라 없음**: → Phase 2에서 Vitest + pytest 설정

**해결 방법**:
- Phase 0 (의존성 분리) 선행 작업으로 추가
- 완전한 삭제 목록 확정 (95개 파일)
- 레슨 AI 기능도 재구축 범위에 포함
- 프로덕션 데이터는 DROP (사용자 확인 완료)

---

## Work Objectives

### Core Objective
작동하지 않는 AICAMPUS의 AI 샌드박스 기능을 완전히 재구축하여, 안정적이고 확장 가능하며 고품질의 agentic loop 기반 대화형 AI 시스템을 제공한다.

### Concrete Deliverables
1. **Supabase 데이터베이스 스키마** (`.sql` 마이그레이션 파일)
   - `opencode_sessions` 테이블
   - `opencode_messages` 테이블
   - `lesson_sandbox_templates` 테이블 (재설계)
   - `sandbox_usage` 테이블 (재설계)

2. **Python FastAPI 백엔드** (`getitdone-api/`)
   - Agentic loop 구현
   - SSE 스트리밍 API
   - LLM 프로바이더 통합 (Gemini, OpenAI, Anthropic)
   - 도구(Tool) 시스템
   - 세션 관리

3. **Next.js 프론트엔드** (`aicampus/`)
   - Turn 기반 채팅 UI
   - SSE 스트리밍 핸들러
   - Zustand 상태 관리
   - 메시지/도구 렌더링 컴포넌트

4. **테스트 인프라**
   - Vitest 설정 (프론트엔드)
   - pytest 설정 (백엔드)
   - 각 주요 기능에 대한 테스트 스위트

### Definition of Done
- [ ] `npm run build` 성공 (프론트엔드)
- [ ] `pytest` 모든 테스트 통과 (백엔드)
- [ ] `npx vitest run` 모든 테스트 통과 (프론트엔드)
- [ ] AI 대화 세션 생성 및 메시지 전송/수신 작동 확인
- [ ] SSE 스트리밍을 통한 실시간 응답 작동 확인
- [ ] 도구 호출 및 결과 표시 작동 확인
- [ ] 레슨 페이지의 ChatInputBar 정상 작동 확인 (Phase 0 성공)
- [ ] 홈페이지, 관리자 페이지 정상 작동 확인 (Phase 0 성공)

### Must Have
- **Phase 0 완료**: 의존성 분리하여 sandbox 삭제 시 다른 부분 안 깨지게
- **TDD 준수**: 각 기능에 테스트 먼저 작성 (RED-GREEN-REFACTOR)
- **Supabase RLS 정책**: 세션 및 메시지 접근 권한 정책
- **에러 핸들링**: LLM API 실패, 네트워크 오류 등 graceful degradation
- **SSE 스트리밍**: 실시간 응답 필수
- **기존 UI 패턴 참조**: Turn 기반, MessageBubble, ToolCollapsible 등

### Must NOT Have (Guardrails)
**MUST NOT touch** (Phase 0 제외):
- `aicampus/src/lib/supabase/` (Supabase 클라이언트)
- `aicampus/src/components/auth/` (인증 시스템)
- `aicampus/src/components/course/` (강의 시스템)

**MUST NOT include**:
- Mock 데이터 기반 개발 (실제 API 연동)
- 과도한 추상화 (YAGNI 원칙)
- AI-slop 패턴 (불필요한 validation, 과도한 JSDoc 등)
- 사용자 수동 검증 acceptance criteria

**MUST NOT skip**:
- Phase 0 (의존성 분리) - 필수 선행 작업
- 테스트 코드 작성 (TDD)
- 빌드 검증 (각 Phase 완료 시)

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (구축 필요)
- **User wants tests**: YES (TDD)
- **Framework**: Vitest (frontend), pytest (backend)
- **QA approach**: TDD (RED-GREEN-REFACTOR)

### Test Setup Tasks

**프론트엔드 (Vitest + React Testing Library)**:
```bash
# Phase 2에서 실행
cd aicampus
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event happy-dom
```

`aicampus/vitest.config.ts` 생성:
```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

**백엔드 (pytest + pytest-asyncio)**:
```bash
# Phase 2에서 실행
cd getitdone-api
pip install pytest pytest-asyncio httpx
```

`getitdone-api/pytest.ini` 생성:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```

---

## Execution Strategy

### Parallel Execution Waves

```
Phase 0 (선행 작업 - 순차 필수):
├── 0-1: ChatInputBar 의존성 분리
├── 0-2: MarkdownEditor 의존성 분리
├── 0-3: Sidebar 의존성 분리
├── 0-4: HomePageClient 의존성 분리
├── 0-5: HeroInput 의존성 분리
├── 0-6: lesson.ts AI 타입 분리
└── 0-7: 빌드 검증

Phase 1 (삭제 - 순차):
└── 1-1: 코드 삭제 (95개 파일)

Phase 2 (테스트 인프라 - 병렬 가능):
├── 2-1: Vitest 설정 (프론트엔드)
└── 2-2: pytest 설정 (백엔드)

Phase 3 (DB 스키마 - 순차):
├── 3-1: 마이그레이션 SQL 작성
└── 3-2: Supabase 적용 및 검증

Phase 4 (백엔드 - 병렬 가능):
├── Wave 1 (독립):
│   ├── 4-1: Core types (RED)
│   ├── 4-2: Provider integration (RED)
│   └── 4-3: Tool system base (RED)
├── Wave 2 (Wave 1 의존):
│   ├── 4-4: Session processor (RED)
│   └── 4-5: Agentic loop (RED)
└── Wave 3 (Wave 2 의존):
    └── 4-6: API routes (RED)

Phase 5 (프론트엔드 - 병렬 가능):
├── Wave 1 (독립):
│   ├── 5-1: Types (RED)
│   ├── 5-2: API client (RED)
│   └── 5-3: SSE handler (RED)
├── Wave 2 (Wave 1 의존):
│   ├── 5-4: Zustand stores (RED)
│   └── 5-5: Custom hooks (RED)
└── Wave 3 (Wave 2 의존):
    ├── 5-6: Message rendering components (RED)
    ├── 5-7: ChatInputBar (RED)
    └── 5-8: Session page (RED)

Critical Path: 0-7 → 1-1 → 3-2 → 4-6 → 5-8
Parallel Speedup: ~35% faster than sequential
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 0-1 | None | 0-7 | 0-2, 0-3, 0-4, 0-5, 0-6 |
| 0-7 | 0-1~0-6 | 1-1 | None |
| 1-1 | 0-7 | 2-1, 2-2 | None |
| 2-1 | 1-1 | 5-* | 2-2, 3-1 |
| 2-2 | 1-1 | 4-* | 2-1, 3-1 |
| 3-1 | 1-1 | 3-2 | 2-1, 2-2 |
| 3-2 | 3-1 | 4-*, 5-* | None |
| 4-1 | 2-2, 3-2 | 4-4, 4-5 | 4-2, 4-3 |
| 5-1 | 2-1, 3-2 | 5-4, 5-5 | 5-2, 5-3 |

---

## TODOs

### Phase 0: 의존성 분리 (선행 작업 - 필수)

- [x] 0-1. ChatInputBar에서 ModelSelector import 제거/교체

  **What to do**:
  - `aicampus/src/components/ui/ChatInputBar.tsx`에서 `ModelSelector` import 확인
  - ModelSelector가 sandbox에서만 사용되면 ChatInputBar 내부로 이동
  - 또는 `components/ui/ModelSelector.tsx`로 별도 분리
  - 테스트: ChatInputBar 단독 렌더링 성공

  **Must NOT do**:
  - ChatInputBar의 기능 변경 (UI/UX 동일하게 유지)
  - 다른 컴포넌트 동시 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 단일 파일 import 변경, 간단한 리팩토링
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React 컴포넌트 구조 이해 및 의존성 분리

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-2, 0-3, 0-4, 0-5, 0-6)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/components/ui/ChatInputBar.tsx` - 현재 ModelSelector 사용 위치
  - `aicampus/src/components/sandbox/ModelSelector.tsx` - 이동/복사할 컴포넌트

  **Acceptance Criteria**:
  ```bash
  # 프론트엔드 빌드 성공
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `refactor(ui): isolate ModelSelector from sandbox`
  - Files: `src/components/ui/ChatInputBar.tsx`, `src/components/ui/ModelSelector.tsx`
  - Pre-commit: `npm run build`

---

- [x] 0-2. MarkdownEditor에서 MarkdownRenderer import 제거/교체

  **What to do**:
  - `aicampus/src/components/admin/MarkdownEditor.tsx`에서 MarkdownRenderer import 확인
  - MarkdownRenderer를 `components/ui/MarkdownRenderer.tsx`로 이동
  - admin 컴포넌트에서 새 위치로 import 변경
  - 테스트: MarkdownEditor 단독 렌더링 성공

  **Must NOT do**:
  - MarkdownRenderer의 기능 변경
  - 다른 admin 컴포넌트 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 단일 파일 이동, import 경로 변경
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React 컴포넌트 리팩토링

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-1, 0-3, 0-4, 0-5, 0-6)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/components/admin/MarkdownEditor.tsx` - 현재 사용 위치
  - `aicampus/src/components/sandbox/MarkdownRenderer.tsx` - 이동할 컴포넌트

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `refactor(admin): move MarkdownRenderer to ui/`
  - Files: `src/components/ui/MarkdownRenderer.tsx`, `src/components/admin/MarkdownEditor.tsx`
  - Pre-commit: `npm run build`

---

- [x] 0-3. Sidebar에서 ConversationWithPreview 타입 로컬 정의

  **What to do**:
  - `aicampus/src/components/layout/Sidebar.tsx` 확인
  - `ConversationWithPreview` 타입을 Sidebar 파일 내 또는 `types/layout.ts`에 로컬 정의
  - sandbox.ts import 제거
  - 테스트: Sidebar 렌더링 성공

  **Must NOT do**:
  - Sidebar UI/기능 변경
  - 다른 layout 컴포넌트 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 타입 정의만 로컬로 복사
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: TypeScript 타입 관리

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-1, 0-2, 0-4, 0-5, 0-6)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/components/layout/Sidebar.tsx` - ConversationWithPreview 사용 위치
  - `aicampus/src/lib/types/sandbox.ts` - 현재 타입 정의 위치

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `refactor(layout): localize ConversationWithPreview type`
  - Files: `src/components/layout/Sidebar.tsx`, `src/lib/types/layout.ts`
  - Pre-commit: `npm run build`

---

- [x] 0-4. HomePageClient에서 opencode API 참조 분리

  **What to do**:
  - `aicampus/src/components/home/HomePageClient.tsx`에서 opencode API 호출 확인
  - 임시로 mock 데이터 또는 빈 상태로 대체
  - ConversationWithPreview 타입을 로컬 정의
  - 테스트: HomePageClient 렌더링 성공

  **Must NOT do**:
  - 홈페이지 UI 변경
  - 다른 home 컴포넌트 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: API 호출 임시 비활성화
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React 상태 관리

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-1, 0-2, 0-3, 0-5, 0-6)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/components/home/HomePageClient.tsx` - API 사용 위치
  - `aicampus/src/lib/api/opencode-client.ts` - 현재 API 클라이언트

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  
  # 홈페이지 접속 확인 (임시로 빈 상태/mock 데이터 표시)
  # 브라우저 접속 시 에러 없이 렌더링
  ```

  **Commit**: YES
  - Message: `refactor(home): temporarily disable opencode API calls`
  - Files: `src/components/home/HomePageClient.tsx`
  - Pre-commit: `npm run build`

---

- [x] 0-5. HeroInput에서 ModelInfo 타입 로컬 정의

  **What to do**:
  - `aicampus/src/components/home/HeroInput.tsx`에서 ModelInfo 타입 사용 확인
  - ModelInfo 타입을 HeroInput 내부 또는 `types/home.ts`에 로컬 정의
  - opencode.ts import 제거
  - 테스트: HeroInput 렌더링 성공

  **Must NOT do**:
  - HeroInput UI/기능 변경
  - 다른 home 컴포넌트 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 타입만 로컬로 복사
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: TypeScript 타입 관리

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-1, 0-2, 0-3, 0-4, 0-6)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/components/home/HeroInput.tsx` - ModelInfo 사용 위치
  - `aicampus/src/lib/types/opencode.ts` - 현재 타입 정의 위치

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `refactor(home): localize ModelInfo type`
  - Files: `src/components/home/HeroInput.tsx`, `src/lib/types/home.ts`
  - Pre-commit: `npm run build`

---

- [x] 0-6. lesson.ts 내 AI 타입 분리

  **What to do**:
  - `aicampus/src/lib/types/lesson.ts` 확인
  - AI 관련 타입 (`Message`, `MessagePart`, `ToolCallInfo`, `SandboxUsage`) 식별
  - 새로운 `aicampus/src/lib/types/ai.ts` 파일 생성
  - AI 타입들을 ai.ts로 이동
  - lesson.ts에서 ai.ts import로 변경
  - 테스트: lesson.ts 사용하는 컴포넌트 빌드 성공

  **Must NOT do**:
  - 레슨 전용 타입 (`LessonContext`, `LessonWithDetails`) 수정
  - lesson.ts 외 다른 파일 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 타입 파일 분리 작업
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: TypeScript 타입 시스템 리팩토링

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 0 (with 0-1, 0-2, 0-3, 0-4, 0-5)
  - **Blocks**: 0-7
  - **Blocked By**: None

  **References**:
  - `aicampus/src/lib/types/lesson.ts` - 현재 혼재된 타입 위치
  - `aicampus/src/lib/actions/lesson.ts` - lesson.ts 타입 사용 위치
  - `aicampus/src/lib/actions/admin.ts` - lesson.ts 타입 사용 위치

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `refactor(types): separate AI types from lesson types`
  - Files: `src/lib/types/ai.ts`, `src/lib/types/lesson.ts`
  - Pre-commit: `npm run build`

---

- [x] 0-7. 빌드 검증 (Phase 0 완료 확인) ✓ Build successful

  **What to do**:
  - 프론트엔드 빌드 실행: `cd aicampus && npm run build`
  - 빌드 성공 확인 (에러 0개)
  - 이 시점에서 sandbox 디렉토리를 삭제해도 빌드가 깨지지 않음을 보장
  - 테스트: 빌드 성공 + 주요 페이지 (홈, 레슨, 관리자) 접속 확인

  **Must NOT do**:
  - 코드 수정 (검증만)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 빌드 명령 실행 및 검증
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Wave 0)
  - **Blocks**: 1-1
  - **Blocked By**: 0-1, 0-2, 0-3, 0-4, 0-5, 0-6

  **References**:
  - None (검증 단계)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  # 예상: 0 errors, 0 warnings
  
  # 개발 서버 실행 및 주요 페이지 접속
  npm run dev
  # http://localhost:3000 → 홈페이지 렌더링
  # http://localhost:3000/lesson/1 → 레슨 페이지 렌더링
  # http://localhost:3000/admin/courses → 관리자 페이지 렌더링
  ```

  **Commit**: NO (검증만)

---

### Phase 1: 코드 삭제

- [ ] 1-1. 전체 sandbox 관련 코드 삭제 (95개 파일)

  **What to do**:
  - **프론트엔드 삭제**:
    ```bash
    rm -rf aicampus/src/components/sandbox/
    rm -rf aicampus/src/app/api/opencode/
    rm -rf aicampus/src/app/api/sandbox/
    rm aicampus/src/app/sandbox/page.tsx
    rm -rf aicampus/src/lib/api/
    rm aicampus/src/lib/types/opencode.ts
    rm aicampus/src/lib/types/sandbox.ts
    rm aicampus/src/lib/hooks/useOpencode.ts
    rm aicampus/src/lib/hooks/useModels.ts
    rm aicampus/src/lib/stores/session-store.ts
    rm aicampus/src/lib/stores/prompt-store.ts
    rm aicampus/src/lib/stores/local-store.ts
    rm aicampus/src/lib/stores/index.ts
    rm aicampus/src/lib/actions/sandbox.ts
    rm aicampus/src/app/\[id\]/page.tsx
    ```
  
  - **백엔드 삭제** (복사본):
    ```bash
    rm -rf src/opencode_api/
    rm app.py
    rm -rf tests/
    rm pyproject.toml
    rm requirements.txt
    rm Dockerfile
    ```
  
  - **SQL 마이그레이션 삭제**:
    ```bash
    rm sql/*.sql
    ```
  
  - 빌드 검증: `cd aicampus && npm run build` → 성공 확인

  **Must NOT do**:
  - `getitdone-api/` 삭제 (실제 배포 코드)
  - `aicampus/src/lib/supabase/` 삭제
  - `aicampus/src/components/auth/` 삭제

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 파일 삭제 작업
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after 0-7)
  - **Blocks**: 2-1, 2-2, 3-1
  - **Blocked By**: 0-7

  **References**:
  - Metis 보고서의 "완전한 삭제 목록" 참조

  **Acceptance Criteria**:
  ```bash
  # 삭제 확인
  ls aicampus/src/components/sandbox 2>/dev/null
  # 예상: No such file or directory
  
  ls src/opencode_api 2>/dev/null
  # 예상: No such file or directory
  
  # 빌드 성공 (Phase 0 덕분에 깨지지 않음)
  cd aicampus && npm run build
  # 예상: ✓ built in XXXms
  ```

  **Commit**: YES
  - Message: `chore: remove all sandbox-related code for rebuild`
  - Files: (95개 파일 삭제)
  - Pre-commit: `npm run build`

---

### Phase 2: 테스트 인프라 구축

- [ ] 2-1. Vitest 설정 (프론트엔드)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/example.test.ts` 작성 (failing test)
    ```typescript
    import { describe, it, expect } from 'vitest'
    
    describe('example', () => {
      it('should fail initially', () => {
        expect(true).toBe(false) // RED
      })
    })
    ```
  - **GREEN**: Vitest 설치 및 설정
    ```bash
    cd aicampus
    npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/jest-dom @testing-library/user-event happy-dom
    ```
  - `vitest.config.ts` 생성 (위 Verification Strategy 참조)
  - `vitest.setup.ts` 생성:
    ```typescript
    import '@testing-library/jest-dom'
    ```
  - `package.json`에 스크립트 추가:
    ```json
    {
      "scripts": {
        "test": "vitest",
        "test:ui": "vitest --ui",
        "test:run": "vitest run"
      }
    }
    ```
  - **GREEN**: 테스트 통과하도록 수정
    ```typescript
    expect(true).toBe(true) // GREEN
    ```
  - **REFACTOR**: 필요 시 설정 최적화
  - 테스트 실행: `npm test`

  **Must NOT do**:
  - 실제 컴포넌트 테스트 작성 (Phase 5에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 테스트 인프라 설정 작업
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2-A (with 2-2, 3-1)
  - **Blocks**: 5-*
  - **Blocked By**: 1-1

  **References**:
  - Verification Strategy의 "Test Setup Task" 섹션
  - `opencode/packages/opencode/package.json` - Bun test 설정 참조

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test
  # 예상: ✓ example > should fail initially (now passing)
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES
  - Message: `test: setup Vitest infrastructure`
  - Files: `vitest.config.ts`, `vitest.setup.ts`, `package.json`, `src/__tests__/example.test.ts`
  - Pre-commit: `npm test`

---

- [ ] 2-2. pytest 설정 (백엔드)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_example.py` 작성 (failing test)
    ```python
    def test_example():
        assert True == False  # RED
    ```
  - **GREEN**: pytest 설치 및 설정
    ```bash
    cd getitdone-api
    pip install pytest pytest-asyncio httpx
    ```
  - `pytest.ini` 생성 (위 Verification Strategy 참조)
  - `requirements.txt`에 테스트 의존성 추가:
    ```
    pytest==7.4.3
    pytest-asyncio==0.21.1
    httpx==0.25.2
    ```
  - **GREEN**: 테스트 통과하도록 수정
    ```python
    assert True == True  # GREEN
    ```
  - **REFACTOR**: 필요 시 설정 최적화
  - 테스트 실행: `pytest`

  **Must NOT do**:
  - 실제 API 테스트 작성 (Phase 4에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: 테스트 인프라 설정
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2-A (with 2-1, 3-1)
  - **Blocks**: 4-*
  - **Blocked By**: 1-1

  **References**:
  - `getitdone-api/tests/test_agents.py` - 기존 테스트 파일 (삭제됨, 패턴 참조용)

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest
  # 예상: tests/test_example.py .                                   [100%]
  # 예상: 1 passed in 0.XXs
  ```

  **Commit**: YES
  - Message: `test: setup pytest infrastructure`
  - Files: `pytest.ini`, `requirements.txt`, `tests/test_example.py`
  - Pre-commit: `pytest`

---

### Phase 3: DB 스키마 재설계

- [ ] 3-1. Supabase 마이그레이션 SQL 작성

  **What to do**:
  - 새로운 마이그레이션 파일 생성: `getitdone-api/sql/001_initial_schema.sql`
  - 다음 테이블 정의:
    1. `opencode_sessions` (id, user_id, agent_id, created_at, total_cost, total_tokens, status)
    2. `opencode_messages` (id, session_id, role, parts JSONB, created_at)
    3. `lesson_sandbox_templates` (id, lesson_id, template_name, config JSONB)
    4. `sandbox_usage` (user_id, date, message_count, session_count)
  - RLS 정책 설정:
    - `opencode_sessions`: 자신의 세션만 조회/생성
    - `opencode_messages`: 자신의 세션 메시지만 조회/생성
  - 인덱스 생성:
    - `idx_sessions_user_id` on `opencode_sessions(user_id)`
    - `idx_messages_session_id` on `opencode_messages(session_id)`
  
  **Must NOT do**:
  - Supabase에 직접 적용 (3-2에서)
  - 기존 테이블 건드리기 (DROP 후 재생성)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: SQL 스키마 작성, 중간 난이도
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2-A (with 2-1, 2-2)
  - **Blocks**: 3-2
  - **Blocked By**: 1-1

  **References**:
  - `sql/` 디렉토리 (삭제된 파일들 참조 가능 - Git 히스토리)
  - Supabase 공식 문서: https://supabase.com/docs/guides/database

  **Acceptance Criteria**:
  ```bash
  # SQL 파일 존재 확인
  ls getitdone-api/sql/001_initial_schema.sql
  # 예상: getitdone-api/sql/001_initial_schema.sql
  
  # SQL 구문 검증 (로컬 PostgreSQL)
  psql -d test_db -f getitdone-api/sql/001_initial_schema.sql --dry-run
  # 예상: 구문 에러 없음
  ```

  **Commit**: YES
  - Message: `db: create initial Supabase schema migration`
  - Files: `getitdone-api/sql/001_initial_schema.sql`
  - Pre-commit: None (SQL 파일만)

---

- [ ] 3-2. Supabase 적용 및 검증

  **What to do**:
  - Supabase 대시보드 접속
  - SQL Editor에서 `001_initial_schema.sql` 실행
  - 테이블 생성 확인:
    ```sql
    SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
    ```
  - RLS 정책 확인:
    ```sql
    SELECT * FROM pg_policies WHERE tablename IN ('opencode_sessions', 'opencode_messages');
    ```
  - 인덱스 확인:
    ```sql
    SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public';
    ```
  - 테스트 레코드 삽입/조회:
    ```sql
    -- 테스트 세션 생성
    INSERT INTO opencode_sessions (user_id, agent_id) VALUES ('test-user', 'build') RETURNING *;
    
    -- 테스트 메시지 생성
    INSERT INTO opencode_messages (session_id, role, parts) VALUES (...) RETURNING *;
    
    -- 정리
    DELETE FROM opencode_messages WHERE session_id = '...';
    DELETE FROM opencode_sessions WHERE user_id = 'test-user';
    ```

  **Must NOT do**:
  - 프로덕션 데이터 삭제 (이미 DROP 확인 완료)
  - 다른 테이블 수정

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Supabase 대시보드 작업
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after 3-1)
  - **Blocks**: 4-*, 5-*
  - **Blocked By**: 3-1

  **References**:
  - `getitdone-api/sql/001_initial_schema.sql` - 적용할 스키마

  **Acceptance Criteria**:
  ```sql
  -- Supabase SQL Editor에서 실행
  SELECT table_name FROM information_schema.tables 
  WHERE table_schema = 'public' 
  AND table_name IN ('opencode_sessions', 'opencode_messages', 'lesson_sandbox_templates', 'sandbox_usage');
  -- 예상: 4개 테이블 존재
  
  -- RLS 정책 확인
  SELECT COUNT(*) FROM pg_policies WHERE tablename = 'opencode_sessions';
  -- 예상: 2개 이상 (SELECT, INSERT 정책)
  ```

  **Commit**: NO (Supabase 작업)

---

### Phase 4: 백엔드 재구축 (TDD)

- [ ] 4-1. Core types 정의 (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_types.py` 작성
    ```python
    from getitdone_api.types import SessionInfo, MessagePart
    
    def test_session_info_validation():
        # session ID 없으면 실패해야 함
        with pytest.raises(ValidationError):
            SessionInfo(user_id="test")
    ```
  - **GREEN**: `getitdone-api/getitdone_api/types.py` 작성
    - `SessionInfo` (Pydantic model)
    - `MessagePart` (text, reasoning, tool_call, tool_result)
    - `AgentInfo`
    - `ToolCall`, `ToolResult`
  - **REFACTOR**: 타입 정리, 중복 제거
  - 테스트: `pytest tests/test_types.py`

  **Must NOT do**:
  - 비즈니스 로직 포함 (순수 타입 정의만)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pydantic 모델 정의
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4-1 (with 4-2, 4-3)
  - **Blocks**: 4-4, 4-5
  - **Blocked By**: 2-2, 3-2

  **References**:
  - `src/opencode_api/types.py` (삭제된 파일, Git 히스토리 참조)
  - Pydantic 공식 문서: https://docs.pydantic.dev/

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_types.py
  # 예상: tests/test_types.py ....                                 [100%]
  # 예상: 4 passed in 0.XXs
  ```

  **Commit**: YES (4-1, 4-2, 4-3 완료 후)
  - Message: `feat(backend): add core types, provider integration, and tool base`
  - Files: `getitdone_api/types.py`, `getitdone_api/provider/`, `getitdone_api/tool/`
  - Pre-commit: `pytest`

---

- [ ] 4-2. Provider integration (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_provider.py` 작성
    ```python
    from getitdone_api.provider import GeminiProvider
    
    @pytest.mark.asyncio
    async def test_gemini_stream():
        provider = GeminiProvider(api_key="test-key")
        messages = [{"role": "user", "content": "Hello"}]
        
        chunks = []
        async for chunk in provider.stream(messages):
            chunks.append(chunk)
        
        assert len(chunks) > 0
    ```
  - **GREEN**: Provider 구현
    - `getitdone_api/provider/base.py` (BaseProvider 추상 클래스)
    - `getitdone_api/provider/gemini.py` (Gemini 통합)
    - `getitdone_api/provider/openai.py` (OpenAI 통합)
    - `getitdone_api/provider/anthropic.py` (Anthropic 통합)
  - **REFACTOR**: 공통 로직 base로 추출
  - 테스트: `pytest tests/test_provider.py` (mock 사용)

  **Must NOT do**:
  - 실제 API 키로 테스트 (mock 사용)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: LLM API 통합, 중간 난이도
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4-1 (with 4-1, 4-3)
  - **Blocks**: 4-4, 4-5
  - **Blocked By**: 2-2, 3-2

  **References**:
  - `src/opencode_api/provider/` (삭제된 파일, Git 히스토리 참조)
  - Google Gemini API 문서: https://ai.google.dev/api/python/google/generativeai
  - OpenAI API 문서: https://platform.openai.com/docs/api-reference

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_provider.py
  # 예상: tests/test_provider.py .....                             [100%]
  # 예상: 5 passed in 0.XXs
  ```

  **Commit**: YES (4-1과 함께)

---

- [ ] 4-3. Tool system base (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_tool.py` 작성
    ```python
    from getitdone_api.tool import TodoWriteTool
    
    @pytest.mark.asyncio
    async def test_todo_write():
        tool = TodoWriteTool()
        result = await tool.execute({"todos": [{"id": "1", "content": "Test", "status": "pending"}]})
        
        assert result["metadata"]["todos"][0]["id"] == "1"
    ```
  - **GREEN**: Tool 구현
    - `getitdone_api/tool/base.py` (BaseTool 추상 클래스)
    - `getitdone_api/tool/todo.py` (TodoWrite, TodoRead)
    - `getitdone_api/tool/bash.py` (Bash 도구)
    - `getitdone_api/tool/read.py` (Read 도구)
  - **REFACTOR**: 도구 등록 시스템
  - 테스트: `pytest tests/test_tool.py`

  **Must NOT do**:
  - 실제 파일 시스템 조작 (mock 사용)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: 도구 시스템 구현
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4-1 (with 4-1, 4-2)
  - **Blocks**: 4-4, 4-5
  - **Blocked By**: 2-2, 3-2

  **References**:
  - `src/opencode_api/tool/` (삭제된 파일, Git 히스토리 참조)
  - `opencode/packages/opencode/src/tools/` (TypeScript 구현 참조)

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_tool.py
  # 예상: tests/test_tool.py ....                                  [100%]
  # 예상: 4 passed in 0.XXs
  ```

  **Commit**: YES (4-1과 함께)

---

- [ ] 4-4. Session processor (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_session.py` 작성
    ```python
    from getitdone_api.session import SessionProcessor
    
    @pytest.mark.asyncio
    async def test_session_create():
        processor = SessionProcessor(session_id="test-session", user_id="test-user")
        await processor.initialize()
        
        assert processor.session_id == "test-session"
    ```
  - **GREEN**: Session processor 구현
    - `getitdone_api/session/processor.py`
    - `getitdone_api/session/message.py`
    - Supabase 연동 (세션/메시지 CRUD)
  - **REFACTOR**: 상태 관리 정리
  - 테스트: `pytest tests/test_session.py`

  **Must NOT do**:
  - Agentic loop 로직 (4-5에서)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: 세션 관리 핵심 로직
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4-2 (with 4-5)
  - **Blocks**: 4-6
  - **Blocked By**: 4-1, 4-2, 4-3

  **References**:
  - `src/opencode_api/session/processor.py` (삭제된 파일, Git 히스토리 참조)
  - `opencode/packages/opencode/src/session/processor.ts` (TypeScript 구현 참조)

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_session.py
  # 예상: tests/test_session.py ....                               [100%]
  # 예상: 4 passed in 0.XXs
  ```

  **Commit**: YES (4-4, 4-5 완료 후)
  - Message: `feat(backend): implement session processor and agentic loop`
  - Files: `getitdone_api/session/`
  - Pre-commit: `pytest`

---

- [ ] 4-5. Agentic loop 구현 (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_agentic_loop.py` 작성
    ```python
    from getitdone_api.session import AgenticLoop
    
    @pytest.mark.asyncio
    async def test_agentic_loop():
        loop = AgenticLoop(session_id="test", user_id="test-user")
        
        messages = []
        async for message in loop.run("Hello"):
            messages.append(message)
        
        assert any(m.get("type") == "message_start" for m in messages)
    ```
  - **GREEN**: Agentic loop 구현
    - `getitdone_api/session/prompt.py`의 `_agentic_loop` 메서드
    - `while processor.should_continue()` 루프
    - 도구 호출 처리
    - 사용자 질문 대기 (question 도구)
  - **REFACTOR**: 루프 로직 정리
  - 테스트: `pytest tests/test_agentic_loop.py`

  **Must NOT do**:
  - API 라우트 (4-6에서)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: 복잡한 agentic loop 로직, 핵심 알고리즘
  - **Skills**: []
    - No special skills needed
  - **Skills Evaluated but Omitted**:
    - None (핵심 로직, 특수 스킬 불필요)

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4-2 (with 4-4)
  - **Blocks**: 4-6
  - **Blocked By**: 4-1, 4-2, 4-3

  **References**:
  - `src/opencode_api/session/prompt.py`의 `_agentic_loop` (삭제된 파일, Git 히스토리 참조)
  - `opencode/packages/opencode/src/session/processor.ts`의 `process` 메서드 (TypeScript 구현 참조)
  - Metis 보고서의 "Agentic Loop 구현 패턴" 섹션

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_agentic_loop.py
  # 예상: tests/test_agentic_loop.py ....                          [100%]
  # 예상: 4 passed in 0.XXs
  
  # mock LLM으로 full loop 테스트
  # 예상: message_start → tool_call → tool_result → message_end 이벤트 시퀀스
  ```

  **Commit**: YES (4-4와 함께)

---

- [ ] 4-6. API routes (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `getitdone-api/tests/test_routes.py` 작성
    ```python
    import pytest
    from httpx import AsyncClient
    from getitdone_api.main import app
    
    @pytest.mark.asyncio
    async def test_create_session():
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post("/session", json={"agent_id": "build"})
            assert response.status_code == 200
            assert "session_id" in response.json()
    ```
  - **GREEN**: FastAPI 라우트 구현
    - `getitdone_api/routes/session.py`
      - `POST /session` (세션 생성)
      - `GET /session/{id}` (세션 조회)
      - `POST /session/{id}/message` (메시지 전송 - SSE)
      - `GET /health` (헬스체크)
    - `getitdone_api/main.py` (FastAPI 앱)
  - **REFACTOR**: 라우트 정리
  - 테스트: `pytest tests/test_routes.py`

  **Must NOT do**:
  - 프론트엔드 연동 (Phase 5에서)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: FastAPI 라우트 정의
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (after Wave 4-2)
  - **Blocks**: 5-2
  - **Blocked By**: 4-4, 4-5

  **References**:
  - `src/opencode_api/routes/session.py` (삭제된 파일, Git 히스토리 참조)
  - FastAPI SSE 스트리밍 예제: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse

  **Acceptance Criteria**:
  ```bash
  cd getitdone-api && pytest tests/test_routes.py
  # 예상: tests/test_routes.py .....                               [100%]
  # 예상: 5 passed in 0.XXs
  
  # 수동 헬스체크
  uvicorn getitdone_api.main:app --reload &
  sleep 2
  curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='healthy'"
  # 예상: 성공 (assertion 통과)
  
  # SSE 스트리밍 확인
  curl -N -X POST http://localhost:8000/session/test-id/message \
    -H "Content-Type: application/json" \
    -d '{"content":"hello"}' \
    | head -5
  # 예상: data: {"type":"message_start"...
  ```

  **Commit**: YES
  - Message: `feat(backend): add FastAPI routes with SSE streaming`
  - Files: `getitdone_api/routes/`, `getitdone_api/main.py`
  - Pre-commit: `pytest`

---

### Phase 5: 프론트엔드 재구축 (TDD)

- [ ] 5-1. Types 정의 (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/types.test.ts` 작성
    ```typescript
    import { SessionInfo, MessagePart } from '@/lib/types/ai'
    
    describe('types', () => {
      it('should validate SessionInfo', () => {
        const session: SessionInfo = {
          id: 'test-id',
          user_id: 'test-user',
          agent_id: 'build',
          created_at: new Date().toISOString()
        }
        expect(session.id).toBe('test-id')
      })
    })
    ```
  - **GREEN**: `aicampus/src/lib/types/ai.ts` 작성
    - `SessionInfo` interface
    - `MessagePart` (text, reasoning, tool_call, tool_result)
    - `Message` interface
    - `ToolCall`, `ToolResult` interface
  - **REFACTOR**: 타입 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - API 연동 로직 (5-2에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: TypeScript 타입 정의
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: TypeScript 타입 시스템

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-1 (with 5-2, 5-3)
  - **Blocks**: 5-4, 5-5
  - **Blocked By**: 2-1, 3-2

  **References**:
  - `aicampus/src/lib/types/opencode.ts` (삭제된 파일, Git 히스토리 참조)
  - `getitdone_api/types.py` (백엔드 타입과 일치해야 함)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- types.test.ts
  # 예상: ✓ types > should validate SessionInfo
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-1, 5-2, 5-3 완료 후)
  - Message: `feat(frontend): add AI types, API client, and SSE handler`
  - Files: `src/lib/types/ai.ts`, `src/lib/api/`, `src/__tests__/`
  - Pre-commit: `npm test`

---

- [ ] 5-2. API client (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/api-client.test.ts` 작성
    ```typescript
    import { createSession } from '@/lib/api/opencode-client'
    
    describe('API client', () => {
      it('should create session', async () => {
        const session = await createSession({ agent_id: 'build' })
        expect(session.id).toBeDefined()
      })
    })
    ```
  - **GREEN**: `aicampus/src/lib/api/opencode-client.ts` 작성
    - `createSession()`
    - `getSession(id)`
    - `sendMessage(sessionId, content)`
  - **REFACTOR**: API 클라이언트 정리
  - 테스트: `npm test` (mock 사용)

  **Must NOT do**:
  - SSE 스트리밍 (5-3에서)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: HTTP API 클라이언트
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React/Next.js API 통합

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-1 (with 5-1, 5-3)
  - **Blocks**: 5-4, 5-5
  - **Blocked By**: 2-1, 3-2, 4-6

  **References**:
  - `aicampus/src/lib/api/opencode-client.ts` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- api-client.test.ts
  # 예상: ✓ API client > should create session
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-1과 함께)

---

- [ ] 5-3. SSE handler (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/sse-handler.test.ts` 작성
    ```typescript
    import { parseSSEChunk } from '@/lib/api/sse-handler'
    
    describe('SSE handler', () => {
      it('should parse SSE chunk', () => {
        const chunk = 'data: {"type":"message_start"}\n\n'
        const parsed = parseSSEChunk(chunk)
        expect(parsed.type).toBe('message_start')
      })
    })
    ```
  - **GREEN**: `aicampus/src/lib/api/sse-handler.ts` 작성
    - `parseSSEChunk()` - buffer 기반 line parsing
    - SSE 연결 관리
  - **REFACTOR**: 파싱 로직 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - UI 컴포넌트 (5-6에서)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: SSE 파싱 로직
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 실시간 데이터 스트리밍

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-1 (with 5-1, 5-2)
  - **Blocks**: 5-4, 5-5
  - **Blocked By**: 2-1, 3-2

  **References**:
  - `aicampus/src/lib/api/sse-handler.ts` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- sse-handler.test.ts
  # 예상: ✓ SSE handler > should parse SSE chunk
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-1과 함께)

---

- [ ] 5-4. Zustand stores (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/stores.test.ts` 작성
    ```typescript
    import { useSessionStore } from '@/lib/stores/session-store'
    
    describe('session store', () => {
      it('should add message', () => {
        const { addMessage, messages } = useSessionStore.getState()
        addMessage({ role: 'user', content: 'test' })
        expect(messages).toHaveLength(1)
      })
    })
    ```
  - **GREEN**: `aicampus/src/lib/stores/session-store.ts` 작성
    - `useSessionStore` (Zustand)
    - `messages`, `currentSession`, `isStreaming` 상태
    - `addMessage`, `setSession`, `setStreaming` 액션
  - **REFACTOR**: 상태 관리 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - 컴포넌트 연동 (5-6에서)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Zustand 스토어 정의
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React 상태 관리

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-2 (with 5-5)
  - **Blocks**: 5-6, 5-7, 5-8
  - **Blocked By**: 5-1, 5-2, 5-3

  **References**:
  - `aicampus/src/lib/stores/session-store.ts` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- stores.test.ts
  # 예상: ✓ session store > should add message
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-4, 5-5 완료 후)
  - Message: `feat(frontend): add Zustand stores and custom hooks`
  - Files: `src/lib/stores/`, `src/lib/hooks/`
  - Pre-commit: `npm test`

---

- [ ] 5-5. Custom hooks (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/hooks.test.ts` 작성
    ```typescript
    import { renderHook, waitFor } from '@testing-library/react'
    import { useOpencode } from '@/lib/hooks/useOpencode'
    
    describe('useOpencode', () => {
      it('should send message', async () => {
        const { result } = renderHook(() => useOpencode('test-session'))
        
        await result.current.sendMessage('hello')
        
        await waitFor(() => {
          expect(result.current.isStreaming).toBe(true)
        })
      })
    })
    ```
  - **GREEN**: `aicampus/src/lib/hooks/useOpencode.ts` 작성
    - `useOpencode` hook
    - SSE 스트리밍 관리
    - 메시지 상태 업데이트
    - Throttling (100ms)
  - **REFACTOR**: 훅 로직 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - UI 컴포넌트 (5-6에서)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: React 커스텀 훅
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React hooks 패턴

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-2 (with 5-4)
  - **Blocks**: 5-6, 5-7, 5-8
  - **Blocked By**: 5-1, 5-2, 5-3

  **References**:
  - `aicampus/src/lib/hooks/useOpencode.ts` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- hooks.test.ts
  # 예상: ✓ useOpencode > should send message
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-4와 함께)

---

- [ ] 5-6. Message rendering components (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/MessageBubble.test.tsx` 작성
    ```typescript
    import { render, screen } from '@testing-library/react'
    import { MessageBubble } from '@/components/sandbox/MessageBubble'
    
    describe('MessageBubble', () => {
      it('should render user message', () => {
        render(<MessageBubble role="user" content="Hello" />)
        expect(screen.getByText('Hello')).toBeInTheDocument()
      })
    })
    ```
  - **GREEN**: 컴포넌트 구현
    - `aicampus/src/components/sandbox/MessageBubble.tsx`
    - `aicampus/src/components/sandbox/message/TextPart.tsx`
    - `aicampus/src/components/sandbox/message/ToolCollapsible.tsx`
    - `aicampus/src/components/sandbox/MarkdownRenderer.tsx` (Phase 0에서 이동한 것 재활용)
  - **REFACTOR**: 컴포넌트 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - ChatInterface 전체 (5-8에서)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: UI 컴포넌트 구현
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: React 컴포넌트 디자인

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-3 (with 5-7, 5-8)
  - **Blocks**: None
  - **Blocked By**: 5-4, 5-5

  **References**:
  - `aicampus/src/components/sandbox/MessageBubble.tsx` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- MessageBubble.test.tsx
  # 예상: ✓ MessageBubble > should render user message
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-6, 5-7 완료 후)
  - Message: `feat(frontend): add message rendering and input components`
  - Files: `src/components/sandbox/`
  - Pre-commit: `npm test`

---

- [ ] 5-7. ChatInputBar (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/ChatInputBar.test.tsx` 작성
    ```typescript
    import { render, screen } from '@testing-library/react'
    import { ChatInputBar } from '@/components/ui/ChatInputBar'
    
    describe('ChatInputBar', () => {
      it('should render input', () => {
        render(<ChatInputBar onSend={jest.fn()} />)
        expect(screen.getByRole('textbox')).toBeInTheDocument()
      })
    })
    ```
  - **GREEN**: `aicampus/src/components/ui/ChatInputBar.tsx` 재작성
    - 자동 높이 조절
    - 한글 composition 처리
    - ModelSelector 통합 (Phase 0에서 분리한 것)
  - **REFACTOR**: 컴포넌트 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - 사용량 제한 표시 (나중에 추가 가능)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 입력 UI 컴포넌트
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: 입력 폼 UX 최적화

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-3 (with 5-6, 5-8)
  - **Blocks**: None
  - **Blocked By**: 5-4, 5-5

  **References**:
  - `aicampus/src/components/ui/ChatInputBar.tsx` (Phase 0에서 수정한 버전)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- ChatInputBar.test.tsx
  # 예상: ✓ ChatInputBar > should render input
  # 예상: Test Files  1 passed (1)
  ```

  **Commit**: YES (5-6과 함께)

---

- [ ] 5-8. Session page (RED-GREEN-REFACTOR)

  **What to do**:
  - **RED**: `aicampus/src/__tests__/session-page.test.tsx` 작성
    ```typescript
    import { render, screen } from '@testing-library/react'
    import SessionPage from '@/app/[id]/page'
    
    describe('Session page', () => {
      it('should render session', async () => {
        render(<SessionPage params={{ id: 'test-id' }} />)
        expect(await screen.findByText(/Session/i)).toBeInTheDocument()
      })
    })
    ```
  - **GREEN**: `aicampus/src/app/[id]/page.tsx` 재작성
    - ChatInterface 조합
    - Turn 기반 렌더링
    - 무한 스크롤 (이전 메시지)
  - **REFACTOR**: 페이지 정리
  - 테스트: `npm test`

  **Must NOT do**:
  - 다른 페이지 수정

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: 페이지 레이아웃 구성
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Next.js 페이지 라우팅

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 5-3 (with 5-6, 5-7)
  - **Blocks**: None
  - **Blocked By**: 5-4, 5-5

  **References**:
  - `aicampus/src/app/[id]/page.tsx` (삭제된 파일, Git 히스토리 참조)
  - `aicampus/src/components/sandbox/ChatInterface.tsx` (삭제된 파일, Git 히스토리 참조)

  **Acceptance Criteria**:
  ```bash
  cd aicampus && npm test -- session-page.test.tsx
  # 예상: ✓ Session page > should render session
  # 예상: Test Files  1 passed (1)
  
  # E2E 확인 (수동)
  npm run dev
  # http://localhost:3000/test-session-id 접속
  # 예상: ChatInputBar 표시, 메시지 전송 가능
  ```

  **Commit**: YES
  - Message: `feat(frontend): add session page with full chat UI`
  - Files: `src/app/[id]/page.tsx`, `src/components/sandbox/ChatInterface.tsx`
  - Pre-commit: `npm test && npm run build`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 0-1~0-6 | `refactor(ui): isolate sandbox dependencies (Phase 0)` | Phase 0 관련 파일들 | `npm run build` |
| 0-7 | No commit (검증만) | - | `npm run build` |
| 1-1 | `chore: remove all sandbox-related code for rebuild` | 95개 파일 삭제 | `npm run build` |
| 2-1 | `test: setup Vitest infrastructure` | `vitest.config.ts`, `package.json` | `npm test` |
| 2-2 | `test: setup pytest infrastructure` | `pytest.ini`, `requirements.txt` | `pytest` |
| 3-1 | `db: create initial Supabase schema migration` | `sql/001_initial_schema.sql` | None |
| 3-2 | No commit (Supabase 작업) | - | SQL 검증 |
| 4-1~4-3 | `feat(backend): add core types, provider integration, and tool base` | `types.py`, `provider/`, `tool/` | `pytest` |
| 4-4~4-5 | `feat(backend): implement session processor and agentic loop` | `session/` | `pytest` |
| 4-6 | `feat(backend): add FastAPI routes with SSE streaming` | `routes/`, `main.py` | `pytest`, `curl` |
| 5-1~5-3 | `feat(frontend): add AI types, API client, and SSE handler` | `types/ai.ts`, `lib/api/` | `npm test` |
| 5-4~5-5 | `feat(frontend): add Zustand stores and custom hooks` | `stores/`, `hooks/` | `npm test` |
| 5-6~5-7 | `feat(frontend): add message rendering and input components` | `components/sandbox/`, `components/ui/ChatInputBar.tsx` | `npm test` |
| 5-8 | `feat(frontend): add session page with full chat UI` | `app/[id]/page.tsx`, `components/sandbox/ChatInterface.tsx` | `npm test`, `npm run build` |

---

## Success Criteria

### Verification Commands
```bash
# Phase 0 완료
cd aicampus && npm run build
# 예상: ✓ built in XXXms, 0 errors

# Phase 1 완료
ls aicampus/src/components/sandbox 2>/dev/null
# 예상: No such file or directory

cd aicampus && npm run build
# 예상: ✓ built in XXXms, 0 errors (sandbox 없어도 빌드 성공)

# Phase 2 완료
cd aicampus && npm test
# 예상: Test Files  1 passed (1)

cd getitdone-api && pytest
# 예상: 1 passed in 0.XXs

# Phase 3 완료
# Supabase SQL Editor에서 실행
SELECT COUNT(*) FROM opencode_sessions;
# 예상: 0 (테이블 존재)

# Phase 4 완료
cd getitdone-api && pytest
# 예상: All tests passed

curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='healthy'"
# 예상: 성공

# Phase 5 완료
cd aicampus && npm run build
# 예상: ✓ built in XXXms, 0 errors

npm run dev
# http://localhost:3000/test-session-id 접속
# 예상: ChatInputBar 표시, 메시지 전송 가능, 실시간 스트리밍 응답 확인
```

### Final Checklist
- [ ] `npm run build` 성공 (프론트엔드)
- [ ] `pytest` 모든 테스트 통과 (백엔드)
- [ ] `npx vitest run` 모든 테스트 통과 (프론트엔드)
- [ ] Phase 0 완료: 의존성 분리로 sandbox 삭제해도 빌드 안 깨짐
- [ ] AI 대화 세션 생성 작동
- [ ] 메시지 전송/수신 작동
- [ ] SSE 스트리밍 실시간 응답 작동
- [ ] 도구 호출 및 결과 표시 작동
- [ ] 레슨 페이지 ChatInputBar 정상 작동 (Phase 0 성공)
- [ ] 홈페이지, 관리자 페이지 정상 작동 (Phase 0 성공)
- [ ] Supabase 스키마 적용 완료
- [ ] RLS 정책 작동 확인
- [ ] 백엔드 헬스체크 통과
- [ ] 프론트엔드-백엔드 통합 작동
