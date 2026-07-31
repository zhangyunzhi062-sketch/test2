import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { SpreadsheetFile, Workbook } = require("@oai/artifact-tool");

const projectRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..");
const outputPath = path.join(projectRoot, "无人机路径规划数据模板.xlsx");
const previewDir = path.join(projectRoot, ".template_previews");

const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "User" });

const COLORS = {
  navy: "#16324F",
  teal: "#1F6E78",
  paleTeal: "#DDEFF1",
  yellow: "#FFF2CC",
  paleBlue: "#EAF2F8",
  gray: "#E7E6E6",
  darkGray: "#595959",
  white: "#FFFFFF",
  red: "#F4CCCC",
  green: "#E2F0D9",
  border: "#B7C9D3",
};

function title(range, text) {
  range.merge();
  range.values = [[text]];
  range.format = {
    fill: COLORS.navy,
    font: { bold: true, color: COLORS.white, size: 18 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
  range.format.rowHeight = 34;
}

function sectionHeader(range) {
  range.format = {
    fill: COLORS.teal,
    font: { bold: true, color: COLORS.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: COLORS.border },
  };
  range.format.rowHeight = 24;
}

function editable(range) {
  range.format.fill = COLORS.yellow;
  range.format.borders = { preset: "all", style: "thin", color: COLORS.border };
}

function explanatory(range) {
  range.format.fill = COLORS.paleBlue;
  range.format.font = { color: COLORS.darkGray };
  range.format.wrapText = true;
}

// 使用说明
const instructions = workbook.worksheets.add("使用说明");
instructions.showGridLines = false;
title(instructions.getRange("A1:G1"), "无人机路径规划数据模板");
instructions.getRange("A3:G3").values = [[
  "步骤", "要做什么", "具体操作", "黄色单元格", "灰色单元格", "保存要求", "程序读取"
]];
sectionHeader(instructions.getRange("A3:G3"));
instructions.getRange("A4:G9").values = [
  [1, "修改航点", "打开“航点数据”，修改 X/Y/Z、需求量或是否启用。", "可以修改", "不要修改", "使用 .xlsx 格式", "按编号读取"],
  [2, "设置障碍", "打开“障碍物区域”，每行填写一个绝对不可穿越长方体。", "可以修改", "不要修改", "最小值要小于最大值", "可启用或停用"],
  [3, "修改限制", "打开“任务参数”，修改维度、飞行高度、容量和航程。", "可以修改", "说明文字", "不要改工作表名称", "空白数量表示不限"],
  [4, "修改算法", "普通用户可保留默认值；需要实验时再改“算法参数”。", "可以修改", "参数说明", "保存后生效", "只读取所选算法"],
  [5, "保存文件", "按 Ctrl+S 保存，然后关闭 Excel/WPS，避免文件被占用。", "—", "—", "不要另存为 CSV", "读取当前值"],
  [6, "启动程序", "双击“启动程序.bat”，按中文提示选择这个文件。", "—", "—", "原文件不会被改写", "先校验再规划"],
];
instructions.getRange("A4:A9").format = {
  fill: COLORS.paleTeal,
  font: { bold: true, color: COLORS.navy },
  horizontalAlignment: "center",
};
instructions.getRange("B4:G9").format.wrapText = true;
instructions.getRange("A4:G9").format.borders = { preset: "all", style: "thin", color: COLORS.border };
for (const [row, value] of [
  [11, "重要：编号 0 必须是基地，且需求量必须为 0。"],
  [12, "经纬度模式：X列填纬度、Y列填经度、Z列填海拔（米）。"],
  [13, "障碍物内部绝对不可穿越；安全距离大于 0 时还会向外扩张禁区。"],
  [14, "本项目不需要 YOLO，也不会控制真实无人机飞行。"],
]) {
  instructions.getRange(`A${row}:G${row}`).merge();
  instructions.getRange(`A${row}`).values = [[value]];
}
instructions.getRange("A11:G14").format = {
  fill: COLORS.green,
  font: { bold: true, color: COLORS.navy },
  wrapText: true,
  horizontalAlignment: "left",
  verticalAlignment: "center",
  borders: { preset: "outside", style: "thin", color: COLORS.border },
};
instructions.getRange("A:A").format.columnWidth = 9;
instructions.getRange("B:B").format.columnWidth = 15;
instructions.getRange("C:C").format.columnWidth = 40;
instructions.getRange("D:G").format.columnWidth = 18;
instructions.getRange("4:9").format.rowHeight = 38;
instructions.freezePanes.freezeRows(3);

// 航点数据
const waypoints = workbook.worksheets.add("航点数据");
waypoints.showGridLines = false;
title(waypoints.getRange("A1:H1"), "航点数据（黄色区域可修改）");
waypoints.getRange("A3:H3").values = [[
  "编号", "名称", "X或纬度", "Y或经度", "Z或高度", "需求量", "是否启用", "备注"
]];
sectionHeader(waypoints.getRange("A3:H3"));

const coords = [
  [400, 10], [250, 60], [396, 40], [395, 60], [401, 90], [402, 120], [399, 140],
  [392, 160], [375, 11], [370, 88], [377, 119], [369, 141], [350, 12], [352, 61],
  [348, 92], [347, 140], [349, 162], [325, 10], [323, 41], [327, 60], [300, 10],
];
const demands = [0, 4, 6, 3, 11, 10, 5, 3, 11, 5, 3, 11, 10, 5, 11, 5, 3, 11, 10, 5, 3];
const waypointRows = coords.map((coord, index) => [
  index,
  index === 0 ? "基地" : `任务点${index}`,
  coord[0],
  coord[1],
  20,
  demands[index],
  "是",
  index === 0 ? "所有航线从这里出发并返回" : "",
]);
waypoints.getRange(`A4:H${3 + waypointRows.length}`).values = waypointRows;
editable(waypoints.getRange("A4:H103"));
waypoints.getRange("A4:A103").format.numberFormat = "0";
waypoints.getRange("C4:F103").format.numberFormat = "0.00";
waypoints.getRange("A4:A103").dataValidation = {
  rule: { type: "whole", operator: "between", formula1: 0, formula2: 99999 },
};
waypoints.getRange("F4:F103").dataValidation = {
  rule: { type: "decimal", operator: "greaterThanOrEqual", formula1: 0 },
};
waypoints.getRange("G4:G103").dataValidation = {
  rule: { type: "list", values: ["是", "否"] },
};
waypoints.getRange("A4:A103").conditionalFormats.add("duplicateValues", {
  format: { fill: COLORS.red, font: { bold: true, color: "#9C0006" } },
});
waypoints.getRange("F4:F103").conditionalFormats.add("cellIs", {
  operator: "lessThan",
  formula: 0,
  format: { fill: COLORS.red, font: { color: "#9C0006" } },
});
const waypointTable = waypoints.tables.add(`A3:H${3 + waypointRows.length}`, true, "WaypointsTable");
waypointTable.style = "TableStyleMedium2";
waypointTable.showFilterButton = true;

waypoints.getRange("I2:J4").values = [
  ["自动汇总", "当前值"],
  ["启用航点数", null],
  ["启用点总需求量", null],
];
sectionHeader(waypoints.getRange("I2:J2"));
waypoints.getRange("I3:I4").format = {
  fill: COLORS.gray,
  font: { bold: true, color: COLORS.darkGray },
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
waypoints.getRange("J3").formulas = [['=COUNTIF(G4:G103,"是")']];
waypoints.getRange("J4").formulas = [['=SUMIF(G4:G103,"是",F4:F103)']];
waypoints.getRange("J3:J4").format = {
  fill: COLORS.green,
  font: { bold: true, color: COLORS.navy },
  numberFormat: "0.00",
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
waypoints.getRange("A:A").format.columnWidth = 10;
waypoints.getRange("B:B").format.columnWidth = 16;
waypoints.getRange("C:F").format.columnWidth = 15;
waypoints.getRange("G:G").format.columnWidth = 12;
waypoints.getRange("H:H").format.columnWidth = 32;
waypoints.getRange("I:I").format.columnWidth = 20;
waypoints.getRange("J:J").format.columnWidth = 14;
waypoints.freezePanes.freezeRows(3);

// 任务参数
const taskParams = workbook.worksheets.add("任务参数");
taskParams.showGridLines = false;
title(taskParams.getRange("A1:D1"), "任务参数（黄色区域可修改）");
taskParams.getRange("A3:D3").values = [["参数", "当前值", "说明", "是否必填"]];
sectionHeader(taskParams.getRange("A3:D3"));
taskParams.getRange("A4:D15").values = [
  ["问题类型", "CDVRP", "TSP=单机；CDVRP=无人机群", "是"],
  ["算法", "ACO", "可选 ACO、GA、HPSO、SA", "是"],
  ["空间维度", "3D", "2D 忽略高度；3D 使用 X/Y/Z", "是"],
  ["距离模式", "欧氏距离", "本地坐标选欧氏；GPS 选经纬度", "是"],
  ["距离单位", "km", "欧氏模式三轴必须同单位；经纬度固定 km", "是"],
  ["单机容量", 20, "CDVRP 中一架无人机最多承载的需求量", "CDVRP"],
  ["单机最大航程", 500, "每条闭环航线允许的最大距离", "CDVRP"],
  ["最大无人机数量", null, "留空表示不限制", "否"],
  ["最小飞行高度", 0, "3D 模式下所有路径点允许的最低高度", "3D"],
  ["最大飞行高度", 120, "3D 模式下所有路径点允许的最高高度", "3D"],
  ["障碍物安全距离", 0, "欧氏模式同坐标单位；经纬度模式按米", "否"],
  ["随机种子", 42, "相同数据和种子可得到相同结果", "是"],
];
taskParams.getRange("A4:A15").format = {
  fill: COLORS.gray,
  font: { bold: true, color: COLORS.darkGray },
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
editable(taskParams.getRange("B4:B15"));
explanatory(taskParams.getRange("C4:D15"));
taskParams.getRange("C4:D15").format.borders = { preset: "all", style: "thin", color: COLORS.border };
taskParams.getRange("B4").dataValidation = { rule: { type: "list", values: ["TSP", "CDVRP"] } };
taskParams.getRange("B5").dataValidation = { rule: { type: "list", values: ["ACO", "GA", "HPSO", "SA"] } };
taskParams.getRange("B6").dataValidation = { rule: { type: "list", values: ["2D", "3D"] } };
taskParams.getRange("B7").dataValidation = { rule: { type: "list", values: ["欧氏距离", "经纬度距离"] } };
taskParams.getRange("B9:B10").dataValidation = {
  rule: { type: "decimal", operator: "greaterThan", formula1: 0 },
};
taskParams.getRange("B11").dataValidation = {
  rule: { type: "whole", operator: "between", formula1: 1, formula2: 1000 },
};
taskParams.getRange("B14").dataValidation = {
  rule: { type: "decimal", operator: "greaterThanOrEqual", formula1: 0 },
};
taskParams.getRange("B15").dataValidation = {
  rule: { type: "whole", operator: "between", formula1: 0, formula2: 2147483647 },
};
taskParams.getRange("A:A").format.columnWidth = 22;
taskParams.getRange("B:B").format.columnWidth = 18;
taskParams.getRange("C:C").format.columnWidth = 48;
taskParams.getRange("D:D").format.columnWidth = 14;
taskParams.getRange("4:15").format.rowHeight = 28;
taskParams.freezePanes.freezeRows(3);

// 障碍物区域
const obstacles = workbook.worksheets.add("障碍物区域");
obstacles.showGridLines = false;
title(obstacles.getRange("A1:J1"), "绝对不可穿越长方体区域（黄色区域可修改）");
obstacles.getRange("A3:J3").values = [[
  "障碍物编号", "名称", "X最小或纬度最小", "X最大或纬度最大",
  "Y最小或经度最小", "Y最大或经度最大", "Z最小或最低高度",
  "Z最大或最高高度", "是否启用", "备注"
]];
sectionHeader(obstacles.getRange("A3:J3"));
obstacles.getRange("A4:J5").values = [
  [1, "山体禁区A", 380, 390, 75, 105, 0, 60, "是", "可从侧面绕行或从上方飞越"],
  [2, "山体禁区B", 335, 345, 70, 105, 0, 45, "是", "多个长方体可近似不规则山体"],
];
editable(obstacles.getRange("A4:J103"));
obstacles.getRange("A4:A103").format.numberFormat = "0";
obstacles.getRange("C4:H103").format.numberFormat = "0.00";
obstacles.getRange("A4:A103").dataValidation = {
  rule: { type: "whole", operator: "between", formula1: 0, formula2: 99999 },
};
obstacles.getRange("I4:I103").dataValidation = {
  rule: { type: "list", values: ["是", "否"] },
};
obstacles.getRange("A4:A103").conditionalFormats.add("duplicateValues", {
  format: { fill: COLORS.red, font: { bold: true, color: "#9C0006" } },
});
const obstacleTable = obstacles.tables.add("A3:J5", true, "ObstaclesTable");
obstacleTable.style = "TableStyleMedium2";
obstacleTable.showFilterButton = true;
obstacles.getRange("A:A").format.columnWidth = 13;
obstacles.getRange("B:B").format.columnWidth = 18;
obstacles.getRange("C:H").format.columnWidth = 20;
obstacles.getRange("I:I").format.columnWidth = 12;
obstacles.getRange("J:J").format.columnWidth = 36;
obstacles.freezePanes.freezeRows(3);

// 算法参数
const algoParams = workbook.worksheets.add("算法参数");
algoParams.showGridLines = false;
title(algoParams.getRange("A1:E1"), "算法参数（初学者建议保留默认值）");
algoParams.getRange("A3:E3").values = [["算法", "参数键", "中文名称", "当前值", "说明"]];
sectionHeader(algoParams.getRange("A3:E3"));
const algorithmRows = [
  ["ACO", "ant_count", "蚂蚁数量", 8, "每轮构造路线的蚂蚁数"],
  ["ACO", "iterations", "迭代次数", 100, "优化轮数"],
  ["ACO", "alpha", "信息素权重", 1, "越大越依赖历史路线"],
  ["ACO", "beta", "启发函数权重", 5, "越大越偏向较近航点"],
  ["ACO", "rho", "信息素挥发率", 0.1, "范围 0 到 1"],
  ["ACO", "q", "信息素常数", 1, "每轮信息素增量系数"],
  ["GA", "population_size", "种群数量", 60, "每代候选路线数量"],
  ["GA", "tsp_generations", "TSP 迭代次数", 500, "单机默认值"],
  ["GA", "cdvrp_generations", "CDVRP 迭代次数", 100, "无人机群默认值"],
  ["GA", "generation_gap", "代沟", 0.9, "每代参与繁殖的比例"],
  ["GA", "crossover_rate", "交叉概率", 0.9, "范围 0 到 1"],
  ["GA", "mutation_rate", "变异概率", 0.05, "范围 0 到 1"],
  ["HPSO", "population_size", "粒子数量", 60, "候选路线数量"],
  ["HPSO", "iterations", "迭代次数", 100, "优化轮数"],
  ["SA", "initial_temperature", "初始温度", 1000, "越大越容易接受较差解"],
  ["SA", "final_temperature", "终止温度", 0.001, "达到该温度后停止"],
  ["SA", "chain_length", "链长", 200, "每个温度下尝试次数"],
  ["SA", "cooling_rate", "降温系数", 0.9, "必须大于 0 且小于 1"],
];
algoParams.getRange(`A4:E${3 + algorithmRows.length}`).values = algorithmRows;
algoParams.getRange(`A4:C${3 + algorithmRows.length}`).format = {
  fill: COLORS.gray,
  font: { color: COLORS.darkGray },
  borders: { preset: "all", style: "thin", color: COLORS.border },
};
editable(algoParams.getRange(`D4:D${3 + algorithmRows.length}`));
explanatory(algoParams.getRange(`E4:E${3 + algorithmRows.length}`));
algoParams.getRange(`E4:E${3 + algorithmRows.length}`).format.borders = {
  preset: "all",
  style: "thin",
  color: COLORS.border,
};
algoParams.getRange(`D4:D${3 + algorithmRows.length}`).dataValidation = {
  rule: { type: "decimal", operator: "greaterThan", formula1: 0 },
};
const algoTable = algoParams.tables.add(`A3:E${3 + algorithmRows.length}`, true, "AlgorithmParametersTable");
algoTable.style = "TableStyleMedium2";
algoTable.showFilterButton = true;
algoParams.getRange("A:A").format.columnWidth = 12;
algoParams.getRange("B:B").format.columnWidth = 24;
algoParams.getRange("C:C").format.columnWidth = 20;
algoParams.getRange("D:D").format.columnWidth = 14;
algoParams.getRange("E:E").format.columnWidth = 36;
algoParams.freezePanes.freezeRows(3);

await fs.mkdir(previewDir, { recursive: true });

const overview = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 8000,
  tableMaxRows: 8,
  tableMaxCols: 8,
  tableMaxCellChars: 80,
});
console.log(overview.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

for (const sheetName of ["使用说明", "航点数据", "任务参数", "障碍物区域", "算法参数"]) {
  const preview = await workbook.render({
    sheetName,
    autoCrop: "all",
    scale: 1.5,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
