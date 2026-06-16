# 동물친구 보물찾기 웹게임 구현 계획 (Claude Design 핸드오프용)

> **구현 환경 안내:** 이 계획은 **Claude Design(claude.ai)** 에서 단일 HTML 아티팩트로 구현합니다. claude.ai는 테스트 러너·git이 없으므로, 각 작업의 검증은 **브라우저 수동 확인**으로 대체합니다. 아래 내용을 그대로 Claude Design에 붙여넣어 사용하세요. 체크박스(`- [ ]`)로 진행 추적 가능합니다.

**목표:** 기존 PowerPoint(VBA) 게임 "동물친구 보물찾기"를, 학기·과목별로 문제를 교체해 재배포할 수 있는 단일 HTML 웹앱으로 구현한다.

**아키텍처:** 외부 의존성 없는 단일 `.html` 파일. 엔진(HTML/CSS/JS)과 콘텐츠(문제 JSON)를 분리하고, 콘텐츠는 기본 내장 → localStorage → 파일 불러오기 순으로 로드. 4개 화면(설정/보드/문제/결과)을 JS로 전환.

**기술 스택:** Vanilla HTML + CSS + JavaScript(ES6+ 허용, claude.ai 환경), localStorage, FileReader/Blob(JSON import/export), `강원교육튼튼` 폰트 base64 임베드.

---

## Claude Design 사용 팁

- claude.ai는 한 번에 전체 아티팩트를 생성합니다. 아래 **Task를 순서대로 한 번에 제시**하되, 생성 후 각 Task의 "✅ 확인" 항목을 직접 브라우저에서 점검하세요.
- 문제가 있으면 해당 Task의 확인 항목을 인용해 "이 부분이 안 된다"고 수정 요청하면 됩니다.
- 폰트 임베드(Task 1)는 용량이 크므로, 먼저 폰트 없이 전체를 완성한 뒤 **마지막에 폰트 base64를 주입**하는 것을 권장합니다. (아래 "폰트 임베드 절차" 참조)

---

## 파일 구조

```
동물친구보물찾기_웹게임.html   ← 단일 파일 (전부 인라인)
  ├─ <style>         CSS (강원교육튼튼 @font-face 포함)
  ├─ 화면 4개 마크업  설정 / 보드 / 문제 / 결과 + 편집 모달
  └─ <script>
       ├─ DEFAULT_DATA     기본 내장 문제셋(과학 5-2)
       ├─ ContentSource    load / import / export / reset / validate
       ├─ GameState        teams / cards / phase 등 런타임 상태
       ├─ 화면 전환 router  showScreen()
       ├─ 보드/문제/결과 로직
       └─ 편집 모달 로직
```

---

## Task 1: 골격 + 화면 전환 + 폰트

**목표:** 4개 화면을 가진 단일 HTML 골격과 화면 전환 라우터, 강원교육튼튼 폰트 적용.

**요구사항:**
- `<style>`에 `@font-face { font-family:'강원교육튼튼'; src:url(data:font/woff2;base64,...) }` 자리 마련 (실제 base64는 마지막에 주입; 우선 fallback `sans-serif`로 작업)
- `body { font-family:'강원교육튼튼', 'Noto Sans KR', sans-serif }`
- 4개 컨테이너: `#screen-setup`, `#screen-board`, `#screen-question`, `#screen-result` — 한 번에 하나만 표시
- `showScreen(name)` 함수: 모든 화면 숨기고 지정 화면만 표시
- 색상 테마 CSS 변수 정의(밝고 친근한 톤, 전자칠판 대비 고려): 주색/강조/배경/카드 등
- 16:9 대화면 우선 + 일반 PC/태블릿 반응형

**✅ 확인:**
- 페이지 로드 시 설정 화면이 보인다
- `showScreen('board')`를 콘솔에서 호출하면 보드 화면으로 바뀐다
- 글꼴 fallback이 적용되어 한글이 깨지지 않는다

---

## Task 2: 데이터 계층 (ContentSource)

**목표:** 기본 문제셋 + 불러오기/내보내기/검증/localStorage 영속.

**데이터 형식:**
```jsonc
{
  "meta":     { "subject":"과학", "grade":"5학년 2학기", "unit":"3단원 동물친구 보물찾기", "version":"2026-2학기" },
  "settings": { "cardCount":15, "pointsPerCorrect":10 },
  "questions":[ { "id":1, "question":"...", "answer":"...", "explanation":"..." } ]
}
```

**요구사항:**
- `DEFAULT_DATA` 상수: 위 구조로 과학 5-2 샘플 문제 **15개 이상** 내장 (question/answer/explanation 채움)
- `const LS_KEY = 'animal_treasure_v1'`
- `ContentSource.load()`: localStorage에 저장본 있으면 그걸, 없으면 `DEFAULT_DATA`(깊은 복사) 반환
- `ContentSource.save(data)`: `localStorage.setItem(LS_KEY, JSON.stringify(data))`, 용량 초과 등 오류는 try/catch + 토스트 경고
- `ContentSource.validate(data)`: 객체이고 `Array.isArray(data.questions)` 이며 각 항목에 비어있지 않은 `question`·`answer` 존재 → `{ok:true}` 또는 `{ok:false, reason}`
- `ContentSource.import(file)`: FileReader로 JSON 파싱 → `validate` → 통과 시 save+적용, 실패 시 토스트 경고하고 기존 데이터 유지
- `ContentSource.export(data)`: `Blob`으로 JSON 다운로드, 파일명 `문제셋_${meta.subject}_${meta.version}.json`
- `ContentSource.reset()`: localStorage 삭제 후 `DEFAULT_DATA`로 복원

**✅ 확인:**
- 새로고침 후에도 localStorage 저장본이 로드된다
- 내보내기 → 같은 파일 불러오기 → 동일 문제셋 복원
- `questions`가 없는 JSON 불러오기 → 경고 토스트, 기존 데이터 유지

---

## Task 3: 설정 화면

**목표:** 모둠 수·이름, 카드 수, 정답 점수 입력 후 게임 시작.

**요구사항:**
- 모둠 수 선택(1~8) → 선택 수만큼 팀 이름 입력란 동적 생성(기본값 "1모둠","2모둠"...)
- 카드 수 입력(기본 `settings.cardCount`, 최소 4, 최대 20)
- 정답 점수 입력(기본 `settings.pointsPerCorrect`, 최소 1)
- 현재 문제셋 메타 표시: "과학 · 5학년 2학기 · 3단원 (문제 N개)"
- 버튼: `문제 편집/가져오기`(Task 8 모달 열기), `게임 시작`
- `게임 시작` 클릭 → 입력값으로 `GameState` 초기화(Task 4) → 보드로 전환

**✅ 확인:**
- 모둠 수를 3으로 바꾸면 이름 입력란 3개가 나타난다
- 게임 시작 시 입력한 팀 수·점수가 이후 보드에 반영된다

---

## Task 4: 게임 상태 + 랜덤 카드 배정

**목표:** 문제은행에서 카드 수만큼 중복 없이 랜덤 추출(원본 VBA 로직 이식).

**요구사항:**
- `GameState = { teams:[{name,score:0}], cards:[], pointsPerCorrect, currentCardSlot:null, phase }`
- `assignCards(questions, cardCount)`:
  - `questions.length >= cardCount` → 중복 없이 랜덤 `cardCount`개 추출
  - `questions.length <  cardCount` → 중복 허용하여 `cardCount`개 채움
  - 반환: `[{ slot:0..N-1, questionId, used:false }]`, 순서 셔플
- `startGame(setupValues)`: teams/pointsPerCorrect 설정 + `assignCards` 호출 + `phase='board'`

**✅ 확인:**
- 문제 20개·카드 15개 → 서로 다른 15문제 배정(중복 없음)
- 문제 5개·카드 15개 → 15칸 모두 채워짐(중복 허용)
- 매 게임 시작마다 배정이 달라진다

---

## Task 5: 메인 보드 (카드 그리드 + 우측 점수판)

**목표:** B 레이아웃 — 좌측 카드 그리드, 우측 모둠 점수판 상시 표시.

**요구사항:**
- 레이아웃: 좌측 `flex:1` 카드 영역 + 우측 고정폭(약 280px) 점수판 패널
- 카드 그리드: `cards` 수만큼 번호 카드 렌더, 자동 열 배치(예: 5열)
  - `used:false` 카드는 클릭 가능(호버 효과), `used:true` 카드는 비활성(흐림 처리, 클릭 불가)
  - 카드 클릭 → `currentCardSlot` 설정 → 문제 화면(Task 6) 전환
- 우측 점수판: 각 팀 카드에 이름·점수, 수동 `+`/`−` 버튼(점수 `pointsPerCorrect` 단위 조정) + 팀별 `초기화`(0점) 버튼, 점수 표시 실시간 갱신
- 상단: 문제셋 메타 + 남은 카드 수, `설정으로` 버튼
- 모든 카드 `used:true` 가 되면 결과 화면(Task 7) 자동 전환

**✅ 확인:**
- 카드 그리드와 우측 점수판이 한 화면에 동시 표시
- 카드 클릭 → 문제 화면 이동, 돌아오면 해당 카드 비활성
- 점수판 +/− 버튼으로 팀 점수 조정 가능

---

## Task 6: 문제 화면 + 정답/오답 판정

**목표:** 문제 표시 → 정답 공개 → 교사 판정 → 점수 반영.

**요구사항:**
- `currentCardSlot`의 `questionId`로 문제 조회 후 표시
- 초기: 문제 텍스트 + `정답 보기` 버튼 (정답·해설은 숨김)
- `정답 보기` 클릭 → 정답·해설 영역 공개 + `정답`/`오답` 버튼 노출
- `정답` 클릭 → "어느 모둠?" 팀 선택 UI(팀 버튼들) → 팀 선택 시 해당 팀 `score += pointsPerCorrect` → 카드 `used=true` → 보드 복귀
- `오답` 클릭 → 점수 변동 없이 카드 `used=true` → 보드 복귀
- `홈(보드로)` 버튼: 판정 없이 보드 복귀(이 경우 카드 `used` 유지 안 함 — 다시 풀 수 있음)
- 해설(`explanation`)이 빈 문자열이면 해설 영역 미표시

**✅ 확인:**
- 정답 보기 전에는 정답이 보이지 않는다
- 정답 → 팀 선택 → 그 팀 점수만 +pointsPerCorrect, 카드 비활성
- 오답 → 점수 변동 없음, 카드 비활성
- 해설 없는 문제는 해설칸이 안 뜬다

---

## Task 7: 결과 화면

**목표:** 모든 카드 소진 시 순위·우승팀 표시.

**요구사항:**
- `teams`를 점수 내림차순 정렬하여 순위 표시(1위 강조)
- 동점 처리: 같은 점수는 공동 순위로 표기
- 우승팀 강조 + 폭죽(confetti) 효과(간단한 CSS/JS 애니메이션)
- 버튼: `다시 하기`(같은 설정으로 카드 재배정 후 보드), `설정으로`(설정 화면)

**✅ 확인:**
- 마지막 카드 처리 직후 결과 화면 자동 표시
- 점수 높은 순으로 정렬, 1위 강조
- 다시 하기 → 새 카드 배정으로 보드 재시작

---

## Task 8: 문제 편집/가져오기 모달 (교사용)

**목표:** 앱 내에서 문제셋 편집 + JSON 불러오기/내보내기.

**요구사항:**
- 설정 화면의 `문제 편집/가져오기` 버튼으로 모달 열기
- 메타 입력: subject / grade / unit / version
- 문제 목록 편집: 각 행에 question/answer/explanation 입력 + 행 삭제 버튼, `+ 문제 추가` 버튼
- **일괄 입력**(텍스트 붙여넣기): `문제 | 정답 | 해설` 형식(구분자 `|`), 한 줄에 한 문제 → `적용` 시 목록 교체. 빈 줄·필드부족 줄은 건너뜀
- 버튼: `JSON 불러오기`(파일 선택 → `ContentSource.import`), `JSON 내보내기`(`ContentSource.export`), `기본값 복원`(`ContentSource.reset` + 확인창), `저장`(편집 내용 검증 후 `ContentSource.save` + 모달 닫기 + 메타 표시 갱신)
- 저장/적용/오류 시 토스트 알림(2초 후 사라짐)

**✅ 확인:**
- 문제 추가/삭제/수정 후 저장 → 새로고침해도 유지
- 일괄 입력 `광합성은?|엽록체|빛에너지로 양분 생성` → 적용 시 목록 반영
- JSON 내보내기 → 불러오기 왕복 정상
- 잘못된 JSON 불러오기 → 경고, 기존 유지

---

## Task 9: 마무리 — 폰트 임베드 + 반응형 점검

**목표:** 강원교육튼튼 폰트 임베드와 전 화면 반응형·접근성 마감.

**요구사항:**
- 폰트 base64 주입(아래 절차) → 모든 텍스트에 강원교육튼튼 적용 확인
- 전자칠판(대화면)·일반 PC·태블릿에서 4개 화면 레이아웃 깨짐 없는지 확인
- 버튼·카드 충분한 크기(원거리 터치/클릭), 색 대비 확보
- 빈 문제셋 등 경계 상황에서 크래시 없이 안내 메시지

**폰트 임베드 절차(별도):**
1. 로컬에서 `강원교육튼튼.otf` → WOFF2 변환 (fonttools+brotli 또는 온라인 변환기)
2. WOFF2를 base64로 인코딩
3. `@font-face`의 `src:url(data:font/woff2;base64,<여기>)` 에 주입
   - 용량이 커 claude.ai 입력이 부담되면, 폰트 없이 완성 후 **로컬에서 HTML의 base64 자리만 직접 교체**(권장)

**✅ 확인:**
- 폰트 미설치 PC에서도 강원교육튼튼으로 표시
- 모든 화면이 대화면·소화면에서 정상
- 빈 문제셋이어도 에러 없이 안내
