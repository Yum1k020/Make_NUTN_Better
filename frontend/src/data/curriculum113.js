export const CURRICULUM_ACADEMIC_YEAR = 113;

export const curriculumMeta113 = {
  institution: "國立臺南大學",
  department: "資訊工程學系",
  degree: "大學部",
  label: "113 學年度",
  verificationNote:
    "依 113 學年度課程規劃表與課程地圖整理；實際開課、抵免與畢業資格仍以校方審核為準。",
};

export const graduationRequirements113 = {
  minimumTotalCredits: 134,
  generalEducationCredits: 28,
  generalCoreCredits: 10,
  generalElectiveCredits: 18,
  minimumGeneralDomains: 3,
  collegeCoreCredits: 4,
  departmentRequiredCredits: 70,
  departmentElectiveCredits: 12,
  minimumDepartmentCredits: 82,
  freeElectiveCredits: 20,
  requiredLectureCount: 10,
  minimumCompletedPrograms: 2,
  coursesPerProgram: 3,
};

export const requiredCourses113 = [
  ["NN1001", "微積分(一)", 3, "大一上"],
  ["NN1014", "計算機概論", 3, "大一上"],
  ["NN1204", "計算機程式設計(一)", 3, "大一上"],
  ["NN1205", "計算機程式設計實習(一)", 2, "大一上"],
  ["NN1009", "微積分(二)", 3, "大一下"],
  ["NN1002", "普通物理學", 3, "大一下"],
  ["NN1106", "普通物理學實驗", 2, "大一下"],
  ["NN1013", "離散數學", 3, "大一下"],
  ["NN1206", "計算機程式設計(二)", 3, "大一下"],
  ["NN1207", "計算機程式設計實習(二)", 2, "大一下"],
  ["NN1016", "線性代數", 3, "大二上"],
  ["NN1018", "資料結構", 3, "大二上"],
  ["NN1199", "邏輯設計", 3, "大二上"],
  ["NN1200", "邏輯設計實驗", 3, "大二上"],
  ["NN1208", "機率", 3, "大二下"],
  ["NN1023", "系統程式", 3, "大二下"],
  ["NN1024", "計算機網路", 3, "大二下"],
  ["NN1066", "數位系統", 3, "大二下"],
  ["NN1067", "數位系統實驗", 3, "大二下"],
  ["NN1031", "作業系統", 3, "大三上"],
  ["NN1032", "演算法", 3, "大三上"],
  ["NN1030", "資料庫系統", 3, "大三上"],
  ["NN1033", "計算機組織", 3, "大三上"],
  ["NN1053", "畢業專題實作(一)", 2, "大三下"],
  ["NN1062", "畢業專題實作(二)", 2, "大四上"],
].map(([code, name, credits, recommendedTerm]) => ({
  id: `required-${code}`,
  code,
  name,
  credits,
  recommendedTerm,
  type: "專業必修",
}));

export const professionalElectives113 = [
  ["NN1109", "物件導向程式設計", "大二"],
  ["NN1209", "常微分方程", "大二"],
  ["NN1060", "資訊倫理與法律", "大二"],
  ["NN1198", "區塊鏈原理與應用", "大二"],
  ["NN1072", "訊號與系統", "大三"],
  ["NN1035", "軟體工程", "大三"],
  ["NN1041", "影像處理", "大三"],
  ["NN1040", "計算機圖學", "大三"],
  ["NN1027", "數值方法", "大三"],
  ["NN1100", "多媒體系統", "大三"],
  ["NN1037", "人工智慧", "大三"],
  ["NN1095", "編譯器設計", "大三"],
  ["NN1187", "業界實習(一)", "大四"],
  ["NN1188", "業界實習(二)", "大四"],
  ["NN1114", "資訊安全", "大四"],
  ["NN1210", "資通訊安全實務", "大四"],
  ["NN1211", "嵌入式系統", "大四"],
  ["NN1044", "計算機結構", "大四"],
  ["NN1054", "軟式計算", "大四"],
  ["NN1068", "無線通訊網路", "大四"],
  ["NN1091", "圖形識別", "大四"],
  ["NN1113", "電子自動化設計", "大四"],
  ["NN1178", "生物資訊學", "大四"],
  ["NN1179", "雲端計算", "大四"],
  ["NN1180", "數位訊號處理", "大四"],
  ["NN1185", "平行計算", "大四"],
  ["NN1190", "物聯網", "大四"],
  ["NN1192", "電腦對局", "大四"],
  ["NN1193", "智慧型機器人", "大四"],
  ["NN1203", "資料探勘", "大四"],
  ["NN1069", "機器學習", "大四"],
  ["NN1212", "醫學影像分析", "大四"],
  ["NN1214", "網路實務應用", "大四"],
  ["NN1194", "深度學習", "大四"],
  ["NN1213", "量子計算", "大四"],
].map(([code, name, recommendedTerm]) => ({
  id: `elective-${code}`,
  code,
  name,
  credits: 3,
  recommendedTerm,
  type: "專業選修",
}));

export const programs113 = [
  {
    id: "cloud-network",
    name: "雲端網路學程",
    requirement: "11 選 3",
    courses: [
      "物聯網",
      "平行計算",
      "無線通訊網路",
      "多媒體系統",
      "雲端計算",
      "網路程式設計",
      "網路通訊協定",
      "網路實務應用",
      "安全程式設計",
      "資訊安全",
      "區塊鏈原理與應用",
    ],
  },
  {
    id: "intelligent-computing",
    name: "智慧計算學程",
    requirement: "10 選 3",
    courses: [
      "人工智慧",
      "資訊擷取",
      "機器學習",
      "圖形識別",
      "軟式計算",
      "計算機圖學",
      "計算理論",
      "資料探勘",
      "深度學習",
      "智慧型機器人",
    ],
  },
  {
    id: "applied-information",
    name: "應用資訊學程",
    requirement: "10 選 3",
    courses: [
      "生物資訊學",
      "數位訊號處理",
      "電腦對局",
      "電子自動化設計",
      "軟體工程",
      "計算機結構",
      "影像處理",
      "嵌入式系統",
      "訊號與系統",
      "量子計算",
    ],
  },
];

export const sourceDocuments113 = [
  {
    title: "113 學年度大學部課程規劃表",
    usage: "畢業學分、必選修、講座與專業領域學程門檻",
    status: "主要依據",
  },
  {
    title: "113 學年度大學部課程規劃地圖",
    usage: "三個領域學程的採計課程清單",
    status: "主要依據",
  },
  {
    title: "大學部課程大綱及教學計畫表",
    usage: "補充課程內容；文件年代較早，不作為 113 畢業規定",
    status: "背景參考",
  },
];

export const legacySyllabusHighlights = [
  {
    course: "資料結構",
    topics: "陣列與 ADT、堆疊與佇列、鏈結串列、樹、排序、搜尋與圖形",
  },
  {
    course: "資料庫系統",
    topics: "關聯式模型、SQL、E-R 模型、正規化、交易並行、復原與安全",
  },
  {
    course: "人工智慧",
    topics: "搜尋、知識表示、推論、前向／後向鏈結、學習與發展趨勢",
  },
];

export const allCurriculumCourses113 = [
  ...requiredCourses113,
  ...professionalElectives113,
];

export function programNamesForCourse113(courseName) {
  return programs113
    .filter((program) => program.courses.includes(courseName))
    .map((program) => program.name.replace("學程", ""));
}
