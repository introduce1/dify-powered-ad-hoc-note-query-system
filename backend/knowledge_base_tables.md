# 数据库表结构说明（MySQL）

## 1. drawing_record —— 出图记录表
| 字段名 | 类型 | 说明 |
|---|---|---|
| id | INT | 主键自增 |
| project_id | VARCHAR(32) | 项目WBS节点ID，关联pm_wbsnode.WN_ID |
| sub_project_id | VARCHAR(32) | 子项WBS节点ID，关联pm_wbsnode.WN_ID |
| dept_id | VARCHAR(32) | 部门ID，关联sf_org_department.OD_Id |
| designer_id | VARCHAR(32) | 设计人员ID，关联sf_org_user.OU_UserId |
| drawing_no | VARCHAR(64) | 图纸编号 |
| drawing_name | VARCHAR(200) | 图纸名称 |
| drawing_type | VARCHAR(32) | 图纸类型（建筑/结构/暖通/电气/给排水） |
| sheet_count | INT | 图幅数（张） |
| drawing_scale | VARCHAR(16) | 比例（如1:100） |
| finish_date | DATE | 完成日期 |
| check_status | VARCHAR(16) | 审核状态（待审/已审/退回） |

查询示例：
- 查本月出图数量：SELECT COUNT(*) AS 出图数量, SUM(sheet_count) AS 总图幅数 FROM drawing_record WHERE YEAR(finish_date)=YEAR(CURDATE()) AND MONTH(finish_date)=MONTH(CURDATE())
- 查某部门出图：SELECT d.drawing_name, d.drawing_type, d.sheet_count, d.finish_date, u.OU_Name AS 设计人 FROM drawing_record d INNER JOIN sf_org_user u ON d.designer_id=u.OU_UserId WHERE d.dept_id='DEP001'
- 查各部门出图统计：SELECT dep.OD_Name AS 部门, COUNT(*) AS 出图数, SUM(d.sheet_count) AS 总图幅数 FROM drawing_record d INNER JOIN sf_org_department dep ON d.dept_id=dep.OD_Id GROUP BY d.dept_id, dep.OD_Name

## 2. production_value —— 产值记录表（月度）
| 字段名 | 类型 | 说明 |
|---|---|---|
| id | INT | 主键自增 |
| project_id | VARCHAR(32) | 项目WBS节点ID |
| dept_id | VARCHAR(32) | 部门ID |
| record_month | VARCHAR(7) | 记录月份（格式：2026-01） |
| plan_value | DECIMAL(18,2) | 计划产值（万元） |
| actual_value | DECIMAL(18,2) | 实际产值（万元） |
| completion_rate | DECIMAL(5,2) | 完成率（%） |
| create_time | DATETIME | 创建时间 |

查询示例：
- 查各部门本月产值：SELECT dep.OD_Name AS 部门, SUM(pv.plan_value) AS 计划产值, SUM(pv.actual_value) AS 实际产值 FROM production_value pv INNER JOIN sf_org_department dep ON pv.dept_id=dep.OD_Id WHERE pv.record_month=DATE_FORMAT(CURDATE(),'%Y-%m') GROUP BY pv.dept_id, dep.OD_Name
- 查某部门全年产值：SELECT record_month AS 月份, SUM(plan_value) AS 计划产值, SUM(actual_value) AS 实际产值, AVG(completion_rate) AS 平均完成率 FROM production_value WHERE dept_id='DEP001' AND record_month LIKE '2026%' GROUP BY record_month ORDER BY record_month

## 3. production_plan —— 生产计划表
| 字段名 | 类型 | 说明 |
|---|---|---|
| id | INT | 主键自增 |
| dept_id | VARCHAR(32) | 部门ID |
| plan_year | INT | 计划年份 |
| plan_quarter | INT | 计划季度（1-4，NULL表示年度计划） |
| target_value | DECIMAL(18,2) | 目标产值（万元） |
| target_drawings | INT | 目标出图数（张） |
| target_projects | INT | 目标项目数 |
| create_time | DATETIME | 创建时间 |

查询示例：
- 查今年各部门年度计划：SELECT dep.OD_Name AS 部门, pp.target_value AS 目标产值, pp.target_drawings AS 目标出图数, pp.target_projects AS 目标项目数 FROM production_plan pp INNER JOIN sf_org_department dep ON pp.dept_id=dep.OD_Id WHERE pp.plan_year=YEAR(CURDATE()) AND pp.plan_quarter IS NULL
- 查某部门季度计划：SELECT plan_quarter AS 季度, target_value AS 目标产值, target_drawings AS 目标出图数 FROM production_plan WHERE dept_id='DEP001' AND plan_year=YEAR(CURDATE()) AND plan_quarter IS NOT NULL ORDER BY plan_quarter

## 4. work_hours —— 工时记录表
| 字段名 | 类型 | 说明 |
|---|---|---|
| id | INT | 主键自增 |
| user_id | VARCHAR(32) | 用户ID，关联sf_org_user.OU_UserId |
| project_id | VARCHAR(32) | 项目WBS节点ID |
| dept_id | VARCHAR(32) | 部门ID |
| work_date | DATE | 工作日期 |
| hours | DECIMAL(4,1) | 工时（小时） |
| work_content | VARCHAR(500) | 工作内容 |

查询示例：
- 查某人本月工时：SELECT u.OU_Name AS 姓名, SUM(wh.hours) AS 总工时, COUNT(DISTINCT wh.work_date) AS 工作天数 FROM work_hours wh INNER JOIN sf_org_user u ON wh.user_id=u.OU_UserId WHERE u.OU_Name LIKE '%张伟%' AND YEAR(wh.work_date)=YEAR(CURDATE()) AND MONTH(wh.work_date)=MONTH(CURDATE()) GROUP BY u.OU_Name
- 查某部门工时汇总：SELECT u.OU_Name AS 姓名, SUM(wh.hours) AS 总工时 FROM work_hours wh INNER JOIN sf_org_user u ON wh.user_id=u.OU_UserId WHERE wh.dept_id='DEP001' AND YEAR(wh.work_date)=YEAR(CURDATE()) AND MONTH(wh.work_date)=MONTH(CURDATE()) GROUP BY wh.user_id, u.OU_Name ORDER BY 总工时 DESC

## 5. project_progress —— 项目进度表
| 字段名 | 类型 | 说明 |
|---|---|---|
| id | INT | 主键自增 |
| project_id | VARCHAR(32) | 项目WBS节点ID |
| dept_id | VARCHAR(32) | 部门ID |
| stage | VARCHAR(32) | 当前阶段（方案设计/初步设计/施工图设计） |
| plan_start | DATE | 计划开始日期 |
| plan_end | DATE | 计划结束日期 |
| actual_start | DATE | 实际开始日期 |
| actual_end | DATE | 实际结束日期（NULL表示未完成） |
| progress_pct | INT | 进度百分比（0-100） |
| status | VARCHAR(16) | 状态（未开始/进行中/已完成/暂停） |
| update_time | DATETIME | 更新时间 |

查询示例：
- 查进行中的项目：SELECT wn.WN_Name AS 项目名称, wn.WN_Code AS 工号, dep.OD_Name AS 部门, pp.stage AS 阶段, pp.progress_pct AS 进度, pp.plan_end AS 计划完成日期 FROM project_progress pp INNER JOIN pm_wbsnode wn ON pp.project_id=wn.WN_ID INNER JOIN sf_org_department dep ON pp.dept_id=dep.OD_Id WHERE pp.status='进行中' ORDER BY pp.progress_pct DESC
- 查延期项目：SELECT wn.WN_Name AS 项目名称, pp.stage AS 阶段, pp.plan_end AS 计划完成, pp.progress_pct AS 进度 FROM project_progress pp INNER JOIN pm_wbsnode wn ON pp.project_id=wn.WN_ID WHERE pp.status='进行中' AND pp.plan_end < CURDATE()

## 6. 已有业务表（简要说明）

### sf_org_department —— 部门表
OD_Id(部门ID), OD_Name(部门名称), OD_ShowIndex(排序), OD_IsDel(是否删除)

### sf_org_user —— 用户表
OU_UserId(用户ID), OU_Code(工号), OU_Name(姓名)

### pm_project —— 项目表
WN_ID(项目WBS节点ID), PR_LXBM(立项部门ID), PR_CreateTime(立项时间), PR_ItemDepment(所属部门)

### pm_wbsnode —— WBS节点表（四层结构：项目→阶段→子项→专业）
WN_ID(节点ID), WN_Name(名称), WN_Code(编号), WN_ParentID(父节点ID)

### pm_contract —— 合同表
CT_ID(合同ID), WN_Id(项目WBS节点ID), CT_Money(合同额万元), CT_GDRQ(签约日期), ZDSJBM(主导设计部门ID)

### pm_contractgathering —— 收费表
RG_Money(收费金额万元), RG_Date(收费日期), CT_ID(合同ID), HTBM(部门ID)

### lz_misdepartment —— 部门组表
UG_UserGrpID(部门组ID), UG_UserGrpName(部门组名称)

### lz_misdepartmentuser —— 部门用户关联表
SU_UserID(用户ID), UG_UserGrpID(部门组ID)

### r_dynamicroleuser —— 动态角色用户表
SU_UserID(用户ID), ProjectID(项目ID), WN_ID(专业节点ID), DR_IsValid(是否有效)

### cod_fileinfo —— 协同图纸文件表
CWF_SubProjectID(子项WBS节点ID), CWF_FileName(文件名)

### choose_by_jd —— 阶段出图单表
zx_id(子项ID), fiid(流程实例ID)

### wf_his_instance —— 工作流历史实例表
FI_ID(流程实例ID)
