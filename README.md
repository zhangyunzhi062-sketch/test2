# Python 无人机路径规划

这是一个由 Excel/WPS 表格驱动的二维任务级路径规划程序，适合课程设计、算法学习和小规模实验。

它可以完成：

- 单架无人机 TSP 路径规划；
- 多架无人机 CDVRP 路径规划；
- ACO（蚁群）、GA（遗传）、HPSO（混合粒子群）、SA（模拟退火）四种算法；
- 容量、单机最大航程和最大无人机数量约束；
- 欧氏距离和经纬度球面距离；
- 路线图、收敛曲线、JSON 和 CSV 结果输出。

本项目不需要 YOLO。它不包含图像识别、障碍物避让、三维高度、动力学控制或真实无人机飞行控制。

## 零基础快速开始

1. 从 [Python 官方网站](https://www.python.org/downloads/windows/)安装 Python 3.10 或更高版本。安装时勾选 `Add Python to PATH`。
2. 双击 `安装环境.bat`，等待出现“安装完成”。
3. 用 Excel 或 WPS 打开 `无人机路径规划数据模板.xlsx`。
4. 在黄色单元格中修改航点坐标、需求量和任务限制，保存后关闭 Excel/WPS。
5. 双击 `启动程序.bat`，选择刚才保存的表格。
6. 核对程序显示的参数，输入 `Y` 开始规划。
7. 打开 `results` 文件夹查看路线图和结果表。

完整图文式文字说明见 [使用手册.md](使用手册.md)。

## Excel 中可以修改什么

- `航点数据`：编号、名称、X/纬度、Y/经度、需求量、是否启用、备注；
- `任务参数`：TSP/CDVRP、算法、距离模式、单位、容量、航程、无人机数量、随机种子；
- `算法参数`：四种算法的种群规模、迭代次数等实验参数。

编号 `0` 必须是启用的基地，需求量必须为 `0`。黄色区域可以修改，灰色区域和工作表名称不要修改。

## 输出文件

每次运行默认在 `results` 文件夹生成：

- `route.png`：路线图；
- `convergence.png`：收敛曲线；
- `routes.csv`：每架无人机的路线、距离和载荷，可用 Excel/WPS 打开；
- `solution.json`：供后续程序读取的完整结果。

程序只读取输入表格，不会改写原始 Excel 文件。

## 命令行运行

普通用户不需要使用命令行。需要批量实验时可以运行：

```powershell
python -m uav_planner --input data.xlsx --problem cdvrp --algorithm aco --distance-mode euclidean --seed 42 --output results
```

命令行参数优先于 Excel 设置；未填写的参数继续使用 Excel 中的值。

## 开发与短测试

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

项目提供新中文模板读取和原 MATLAB `City`、`Demand`、`Capacity`、`Travelcon` 工作表格式兼容。固定相同数据、算法参数和随机种子时，结果可复现。
