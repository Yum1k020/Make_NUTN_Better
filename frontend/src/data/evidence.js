export const proposalBrief = {
  title: "學生個人安排系統 Retrieval + Generator Gate",
  users: [
    "需要整合課表、待辦、私人行程與複習安排的大學生",
    "需要追蹤必修、學分與講座條件的大三、大四學生",
  ],
  claim:
    "系統只根據可引用的課表、待辦、複習計畫與畢業規則回答，資料不足時必須拒答並說明缺少哪個來源。",
  dataScope: [
    "本機示範課表、待辦、私人行程與複習建議",
    "README 驗收條件中的畢業規則",
    "未串接的真實教務、停課公告、個人正式成績不列入回答依據",
  ],
  refusalConditions: [
    "查不到可引用來源",
    "來源過期或不是使用者授權範圍",
    "問題需要真實個資、正式成績或即時校務資料",
  ],
};

export const sourceCards = [
  {
    id: "weekly-classes-fixture",
    name: "本機課表示範資料",
    authority: "團隊建立的固定 fixture，用來驗證課表與時間衝突邏輯",
    permission: "僅本機展示；正式版需由使用者匯入或授權讀取",
    freshness: "示範日期 2026-09-17；不宣稱代表最新校務資料",
    pii: "不含真實學號、姓名或帳號",
    revocation: "使用者可清除瀏覽器 localStorage；正式版需提供來源撤回",
    status: "allowed",
  },
  {
    id: "tasks-events-local",
    name: "待辦與私人行程 localStorage",
    authority: "由使用者在前端新增或編輯，屬於使用者自管資料",
    permission: "只在目前瀏覽器保存；未上傳到遠端服務",
    freshness: "畫面即時讀取 localStorage，目前沒有雲端同步",
    pii: "可能包含個人行程文字；本示範資料已去識別化",
    revocation: "刪除事項或清除瀏覽器資料即可撤回",
    status: "allowed",
  },
  {
    id: "graduation-rule-readme",
    name: "README 畢業條件測試規則",
    authority: "來自專案 README 的驗收條件，用於 UI 原型驗證",
    permission: "公開於團隊 repo，可供本機 fixture 使用",
    freshness: "固定測試規則；正式資格仍需校方最新公告確認",
    pii: "不含真實學生修課紀錄",
    revocation: "若 README 規則更新，需重新產生比較 JSON",
    status: "allowed",
  },
  {
    id: "live-school-notice",
    name: "即時校務公告",
    authority: "尚未串接的外部來源",
    permission: "未取得使用者授權與 API 存取",
    freshness: "目前無 live snapshot",
    pii: "未知，不能假設可用",
    revocation: "未啟用",
    status: "blocked",
  },
];

export const evidenceDocuments = [
  {
    id: "class-data-structures",
    sourceId: "weekly-classes-fixture",
    title: "資料結構課表",
    quote: "2026-09-17 09:00-10:50，資料結構，文薈樓 J201。",
    facts: ["資料結構課程在週四 09:00-10:50", "地點是文薈樓 J201"],
  },
  {
    id: "class-psychology",
    sourceId: "weekly-classes-fixture",
    title: "普通心理學課表",
    quote: "2026-09-17 11:00-12:50，普通心理學，文華樓 G202。",
    facts: ["普通心理學在 11:00-12:50", "地點是文華樓 G202"],
  },
  {
    id: "task-quiz",
    sourceId: "tasks-events-local",
    title: "離散數學小考待辦",
    quote: "2026-09-17 15:00，準備離散數學小考，狀態未完成。",
    facts: ["15:00 有離散數學小考準備事項", "狀態未完成"],
  },
  {
    id: "event-club",
    sourceId: "tasks-events-local",
    title: "社團會議私人行程",
    quote: "2026-09-17 17:00-18:00，社團會議，活動中心 3 樓。",
    facts: ["17:00-18:00 有社團會議", "複習安排需避開此行程"],
  },
  {
    id: "study-plan-six-hours",
    sourceId: "tasks-events-local",
    title: "資料結構 6 小時複習建議",
    quote:
      "在考試前安排 3 個 2 小時複習時段，避開課程與私人行程，remainingMinutes 為 0。",
    facts: ["共安排 6 小時", "沒有與既有行程重疊"],
  },
  {
    id: "graduation-gap",
    sourceId: "graduation-rule-readme",
    title: "畢業缺項",
    quote: "需 128 學分；已取得 100 學分；缺資料庫系統；講座完成 4/6。",
    facts: ["尚缺 28 學分", "缺資料庫系統", "尚缺 2 場講座"],
  },
];

export const fixedQueries = [
  {
    id: "today-schedule",
    label: "今日課程與待辦",
    question: "2026-09-17 上午到下午有哪些課和待辦需要注意？",
    expectation: "列出資料結構、普通心理學、離散數學小考準備與社團會議。",
    category: "supported",
  },
  {
    id: "study-plan",
    label: "複習安排可行性",
    question: "資料結構考前要安排 6 小時複習，是否能避開課程與私人行程？",
    expectation: "回答可安排 3 個 2 小時時段，且 remainingMinutes 為 0。",
    category: "supported",
  },
  {
    id: "live-notice",
    label: "No-answer / coverage failure",
    question: "今天是否有最新停課公告會影響我的課表？",
    expectation: "拒答，因為沒有即時校務公告來源與授權。",
    category: "no-answer",
  },
];

export const topKTraces = {
  "today-schedule": [
    {
      rank: 1,
      documentId: "class-data-structures",
      score: 0.94,
      selected: true,
      reason: "日期、課程名稱與時段完全命中",
    },
    {
      rank: 2,
      documentId: "class-psychology",
      score: 0.91,
      selected: true,
      reason: "同日課表命中，提供第二堂課",
    },
    {
      rank: 3,
      documentId: "task-quiz",
      score: 0.86,
      selected: true,
      reason: "同日待辦命中，補足下午事項",
    },
    {
      rank: 4,
      documentId: "event-club",
      score: 0.79,
      selected: true,
      reason: "同日私人行程，影響晚間複習安排",
    },
  ],
  "study-plan": [
    {
      rank: 1,
      documentId: "study-plan-six-hours",
      score: 0.96,
      selected: true,
      reason: "直接回答複習時數與剩餘時數",
    },
    {
      rank: 2,
      documentId: "event-club",
      score: 0.81,
      selected: true,
      reason: "用來確認 17:00-18:00 不可安排",
    },
    {
      rank: 3,
      documentId: "class-data-structures",
      score: 0.74,
      selected: true,
      reason: "用來確認課程時段避讓",
    },
  ],
  "live-notice": [
    {
      rank: 1,
      documentId: "live-school-notice",
      score: 0.33,
      selected: false,
      reason: "來源未授權且沒有 live snapshot，必須拒答",
    },
    {
      rank: 2,
      documentId: "class-data-structures",
      score: 0.28,
      selected: false,
      reason: "只證明既有課表，不能證明最新停課公告",
    },
    {
      rank: 3,
      documentId: "class-psychology",
      score: 0.24,
      selected: false,
      reason: "只證明既有課表，不能推論停課資訊",
    },
  ],
};

export const generatorComparisons = {
  "today-schedule": {
    baseline: {
      name: "Baseline generator",
      answer:
        "今天上午有資料結構和普通心理學，下午要準備離散數學小考，傍晚有社團會議。",
      citations: [],
      factCoverage: "3/4",
      unsupportedClaims: 1,
      observation: "答案方向接近，但沒有引用來源，也漏掉私人行程的地點。",
    },
    evidenceLocked: {
      name: "Evidence-locked generator",
      answer:
        "2026-09-17 09:00-10:50 有資料結構（文薈樓 J201），11:00-12:50 有普通心理學（文華樓 G202）；15:00 有未完成的離散數學小考準備，17:00-18:00 有社團會議。",
      citations: [
        "class-data-structures",
        "class-psychology",
        "task-quiz",
        "event-club",
      ],
      factCoverage: "4/4",
      unsupportedClaims: 0,
      observation: "selected evidence 與 citation 一致。",
    },
  },
  "study-plan": {
    baseline: {
      name: "Baseline generator",
      answer: "可以，系統會自動排入空堂，必要時也能壓縮到更短時段。",
      citations: ["study-plan-six-hours"],
      factCoverage: "1/2",
      unsupportedClaims: 1,
      observation: "壓縮時段沒有證據支持，會造成 unsupported claim。",
    },
    evidenceLocked: {
      name: "Evidence-locked generator",
      answer:
        "可以。示範結果安排 3 個 2 小時的資料結構複習時段，總計 6 小時；remainingMinutes 為 0，代表沒有不足時數。",
      citations: [
        "study-plan-six-hours",
        "event-club",
        "class-data-structures",
      ],
      factCoverage: "2/2",
      unsupportedClaims: 0,
      observation: "同時引用複習結果與避讓用的行程證據。",
    },
  },
  "live-notice": {
    baseline: {
      name: "Baseline generator",
      answer: "今天沒有停課公告，可以照常上課。",
      citations: [],
      factCoverage: "0/1",
      unsupportedClaims: 1,
      observation: "沒有 live source 卻給肯定答案，是 coverage failure。",
    },
    evidenceLocked: {
      name: "Evidence-locked generator",
      answer:
        "目前不能判定。此問題需要即時校務公告，但系統尚未取得授權來源或 live snapshot；只能顯示既有課表，不能回答是否停課。",
      citations: [],
      factCoverage: "1/1",
      unsupportedClaims: 0,
      observation: "正確拒答並指出缺少來源。",
    },
  },
};
