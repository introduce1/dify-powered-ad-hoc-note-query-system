-- ============================================================
-- 建筑行业业务表（MySQL）—— 演示用
-- 在 record_db 库中执行，或自行修改库名
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. 部门表
DROP TABLE IF EXISTS sf_org_department;
CREATE TABLE sf_org_department (
    OD_Id          VARCHAR(32) PRIMARY KEY COMMENT '部门ID',
    OD_Name        VARCHAR(100) NOT NULL COMMENT '部门名称',
    OD_ShowIndex   INT DEFAULT 0 COMMENT '排序序号',
    OD_IsDel       TINYINT(1) DEFAULT 0 COMMENT '是否删除'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门表';

-- 2. 用户表
DROP TABLE IF EXISTS sf_org_user;
CREATE TABLE sf_org_user (
    OU_UserId   VARCHAR(32) PRIMARY KEY COMMENT '用户ID',
    OU_Code     VARCHAR(32) COMMENT '工号',
    OU_Name     VARCHAR(64) COMMENT '姓名'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 3. 部门组表
DROP TABLE IF EXISTS lz_misdepartment;
CREATE TABLE lz_misdepartment (
    UG_UserGrpID    VARCHAR(32) PRIMARY KEY COMMENT '部门组ID',
    UG_UserGrpName  VARCHAR(100) COMMENT '部门组名称'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门组表';

-- 4. 部门用户关联表
DROP TABLE IF EXISTS lz_misdepartmentuser;
CREATE TABLE lz_misdepartmentuser (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    SU_UserID     VARCHAR(32) COMMENT '用户ID',
    UG_UserGrpID  VARCHAR(32) COMMENT '部门组ID',
    INDEX idx_user (SU_UserID),
    INDEX idx_grp (UG_UserGrpID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='部门用户关联表';

-- 5. WBS节点表
DROP TABLE IF EXISTS pm_wbsnode;
CREATE TABLE pm_wbsnode (
    WN_ID        VARCHAR(32) PRIMARY KEY COMMENT '节点ID',
    WN_Name      VARCHAR(200) COMMENT '节点名称',
    WN_Code      VARCHAR(64) COMMENT '节点编号/工号',
    WN_ParentID  VARCHAR(32) COMMENT '父节点ID',
    INDEX idx_parent (WN_ParentID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WBS节点表';

-- 6. 项目表
DROP TABLE IF EXISTS pm_project;
CREATE TABLE pm_project (
    WN_ID          VARCHAR(32) PRIMARY KEY COMMENT '项目WBS节点ID',
    PR_LXBM        VARCHAR(32) COMMENT '立项部门ID',
    PR_CreateTime  DATETIME COMMENT '立项时间',
    PR_ItemDepment VARCHAR(32) COMMENT '项目所属部门',
    INDEX idx_lxbm (PR_LXBM)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目表';

-- 7. 合同表
DROP TABLE IF EXISTS pm_contract;
CREATE TABLE pm_contract (
    CT_ID      VARCHAR(32) PRIMARY KEY COMMENT '合同ID',
    WN_Id      VARCHAR(32) COMMENT '关联项目WBS节点ID',
    CT_Money   DECIMAL(18,2) DEFAULT 0 COMMENT '合同额（万元）',
    CT_GDRQ    DATE COMMENT '归档日期/签约日期',
    ZDSJBM     VARCHAR(32) COMMENT '主导设计部门ID',
    INDEX idx_wn (WN_Id),
    INDEX idx_zdsjbm (ZDSJBM)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同表';

-- 8. 收费表
DROP TABLE IF EXISTS pm_contractgathering;
CREATE TABLE pm_contractgathering (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    RG_Money   DECIMAL(18,2) DEFAULT 0 COMMENT '收费金额（万元）',
    RG_Date    DATE COMMENT '收费日期',
    CT_ID      VARCHAR(32) COMMENT '关联合同ID',
    HTBM       VARCHAR(32) COMMENT '合同编码/部门ID（无合同时）',
    INDEX idx_ct (CT_ID),
    INDEX idx_date (RG_Date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='收费表';

-- 9. 动态角色用户表
DROP TABLE IF EXISTS r_dynamicroleuser;
CREATE TABLE r_dynamicroleuser (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    SU_UserID    VARCHAR(32) COMMENT '用户ID',
    ProjectID    VARCHAR(32) COMMENT '项目WBS节点ID',
    WN_ID        VARCHAR(32) COMMENT '专业WBS节点ID',
    DR_IsValid   TINYINT(1) DEFAULT 1 COMMENT '是否有效',
    INDEX idx_user (SU_UserID),
    INDEX idx_proj (ProjectID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='动态角色用户表';

-- 10. 协同图纸文件表
DROP TABLE IF EXISTS cod_fileinfo;
CREATE TABLE cod_fileinfo (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    CWF_SubProjectID    VARCHAR(32) COMMENT '子项WBS节点ID',
    CWF_FileName        VARCHAR(200) COMMENT '文件名',
    INDEX idx_sub (CWF_SubProjectID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='协同图纸文件表';

-- 11. 工作流历史实例表
DROP TABLE IF EXISTS wf_his_instance;
CREATE TABLE wf_his_instance (
    FI_ID    VARCHAR(32) PRIMARY KEY COMMENT '流程实例ID'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流历史实例表';

-- 12. 阶段出图单表
DROP TABLE IF EXISTS choose_by_jd;
CREATE TABLE choose_by_jd (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    zx_id   VARCHAR(32) COMMENT '子项WBS节点ID',
    fiid    VARCHAR(32) COMMENT '流程实例ID',
    INDEX idx_zx (zx_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='阶段出图单表';

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 插入模拟数据
-- ============================================================

-- ── 部门（6个设计院 + 2个职能部门）──
INSERT INTO sf_org_department (OD_Id, OD_Name, OD_ShowIndex, OD_IsDel) VALUES
('DEP001', '建筑设计一院', 1, 0),
('DEP002', '建筑设计二院', 2, 0),
('DEP003', '建筑设计三院', 3, 0),
('DEP004', '建筑设计四院', 4, 0),
('DEP005', '建筑设计五院', 5, 0),
('DEP006', '建筑设计六院', 6, 0),
('DEP007', '市场经营部',   7, 0),
('DEP008', '技术质量部',   8, 0);

-- ── 部门组（与部门对应）──
INSERT INTO lz_misdepartment (UG_UserGrpID, UG_UserGrpName) VALUES
('GRP001', '建筑设计一院'),
('GRP002', '建筑设计二院'),
('GRP003', '建筑设计三院'),
('GRP004', '建筑设计四院'),
('GRP005', '建筑设计五院'),
('GRP006', '建筑设计六院');

-- ── 用户（24人，每院4人）──
INSERT INTO sf_org_user (OU_UserId, OU_Code, OU_Name) VALUES
('SU000000000001', 'ADMIN', '系统管理员'),
('U001', 'LZ1001', '张伟'),   ('U002', 'LZ1002', '李娜'),   ('U003', 'LZ1003', '王磊'),   ('U004', 'LZ1004', '赵敏'),
('U005', 'LZ2001', '刘洋'),   ('U006', 'LZ2002', '陈静'),   ('U007', 'LZ2003', '杨帆'),   ('U008', 'LZ2004', '吴昊'),
('U009', 'LZ3001', '孙鹏'),   ('U010', 'LZ3002', '周琳'),   ('U011', 'LZ3003', '黄海'),   ('U012', 'LZ3004', '朱丽'),
('U013', 'LZ4001', '徐明'),   ('U014', 'LZ4002', '马芳'),   ('U015', 'LZ4003', '胡斌'),   ('U016', 'LZ4004', '郭颖'),
('U017', 'LZ5001', '林涛'),   ('U018', 'LZ5002', '何雪'),   ('U019', 'LZ5003', '罗杰'),   ('U020', 'LZ5004', '梁月'),
('U021', 'LZ6001', '宋超'),   ('U022', 'LZ6002', '唐薇'),   ('U023', 'LZ6003', '韩冰'),   ('U024', 'LZ6004', '冯瑞');

-- ── 部门用户关联 ──
INSERT INTO lz_misdepartmentuser (SU_UserID, UG_UserGrpID) VALUES
('U001','GRP001'),('U002','GRP001'),('U003','GRP001'),('U004','GRP001'),
('U005','GRP002'),('U006','GRP002'),('U007','GRP002'),('U008','GRP002'),
('U009','GRP003'),('U010','GRP003'),('U011','GRP003'),('U012','GRP003'),
('U013','GRP004'),('U014','GRP004'),('U015','GRP004'),('U016','GRP004'),
('U017','GRP005'),('U018','GRP005'),('U019','GRP005'),('U020','GRP005'),
('U021','GRP006'),('U022','GRP006'),('U023','GRP006'),('U024','GRP006');

-- ── WBS节点（4层结构：项目→阶段→子项→专业）──
-- 项目1: 城市综合体项目
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P001', '万达城市综合体', 'GH-2024-001', NULL),
  ('S001', '方案设计', NULL, 'P001'),
    ('SUB001', '商业裙楼', 'GH-2024-001-01', 'S001'),
      ('PRO001', '建筑专业', NULL, 'SUB001'),
      ('PRO002', '结构专业', NULL, 'SUB001'),
      ('PRO003', '暖通专业', NULL, 'SUB001'),
    ('SUB002', '办公塔楼', 'GH-2024-001-02', 'S001'),
      ('PRO004', '建筑专业', NULL, 'SUB002'),
      ('PRO005', '结构专业', NULL, 'SUB002'),
  ('S002', '施工图设计', NULL, 'P001'),
    ('SUB003', '地下车库', 'GH-2024-001-03', 'S002'),
      ('PRO006', '建筑专业', NULL, 'SUB003'),
      ('PRO007', '给排水专业', NULL, 'SUB003');

-- 项目2: 医院项目
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P002', '市第三人民医院', 'GH-2024-002', NULL),
  ('S003', '方案设计', NULL, 'P002'),
    ('SUB004', '门诊楼', 'GH-2024-002-01', 'S003'),
      ('PRO008', '建筑专业', NULL, 'SUB004'),
      ('PRO009', '结构专业', NULL, 'SUB004'),
      ('PRO010', '电气专业', NULL, 'SUB004'),
    ('SUB005', '住院楼', 'GH-2024-002-02', 'S003'),
      ('PRO011', '建筑专业', NULL, 'SUB005'),
      ('PRO012', '暖通专业', NULL, 'SUB005');

-- 项目3: 学校项目
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P003', '实验中学新校区', 'GH-2025-001', NULL),
  ('S004', '方案设计', NULL, 'P003'),
    ('SUB006', '教学楼A', 'GH-2025-001-01', 'S004'),
      ('PRO013', '建筑专业', NULL, 'SUB006'),
      ('PRO014', '结构专业', NULL, 'SUB006'),
    ('SUB007', '体育馆', 'GH-2025-001-02', 'S004'),
      ('PRO015', '建筑专业', NULL, 'SUB007'),
      ('PRO016', '结构专业', NULL, 'SUB007');

-- 项目4: 住宅项目
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P004', '翡翠湾花园住宅', 'GH-2025-002', NULL),
  ('S005', '施工图设计', NULL, 'P004'),
    ('SUB008', '1#住宅楼', 'GH-2025-002-01', 'S005'),
      ('PRO017', '建筑专业', NULL, 'SUB008'),
      ('PRO018', '结构专业', NULL, 'SUB008'),
    ('SUB009', '2#住宅楼', 'GH-2025-002-02', 'S005'),
      ('PRO019', '建筑专业', NULL, 'SUB009');

-- 项目5: 办公楼项目
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P005', '科技园研发中心', 'GH-2025-003', NULL),
  ('S006', '方案设计', NULL, 'P005'),
    ('SUB010', '研发主楼', 'GH-2025-003-01', 'S006'),
      ('PRO020', '建筑专业', NULL, 'SUB010'),
      ('PRO021', '结构专业', NULL, 'SUB010'),
      ('PRO022', '电气专业', NULL, 'SUB010');

-- 项目6: 去年的项目（用于去年统计）
INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P006', '滨江商务中心', 'GH-2024-003', NULL),
  ('S007', '施工图设计', NULL, 'P006'),
    ('SUB011', '商务主楼', 'GH-2024-003-01', 'S007'),
      ('PRO023', '建筑专业', NULL, 'SUB011');

INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P007', '文化艺术中心', 'GH-2024-004', NULL),
  ('S008', '方案设计', NULL, 'P007'),
    ('SUB012', '展览馆', 'GH-2024-004-01', 'S008'),
      ('PRO024', '建筑专业', NULL, 'SUB012');

INSERT INTO pm_wbsnode (WN_ID, WN_Name, WN_Code, WN_ParentID) VALUES
('P008', '绿地中央公馆', 'GH-2024-005', NULL),
  ('S009', '方案设计', NULL, 'P008'),
    ('SUB013', '公馆A座', 'GH-2024-005-01', 'S009'),
      ('PRO025', '建筑专业', NULL, 'SUB013');

-- ── 项目表 ──
INSERT INTO pm_project (WN_ID, PR_LXBM, PR_CreateTime, PR_ItemDepment) VALUES
('P001', 'DEP001', '2024-03-15 10:00:00', 'DEP001'),
('P002', 'DEP002', '2024-06-20 09:00:00', 'DEP002'),
('P003', 'DEP001', '2025-01-10 14:00:00', 'DEP001'),
('P004', 'DEP003', '2025-03-05 11:00:00', 'DEP003'),
('P005', 'DEP004', '2025-02-18 16:00:00', 'DEP004'),
('P006', 'DEP002', '2024-04-10 08:30:00', 'DEP002'),
('P007', 'DEP005', '2024-07-22 10:00:00', 'DEP005'),
('P008', 'DEP003', '2024-09-01 09:00:00', 'DEP003');

-- ── 合同表 ──
-- 今年签的合同
INSERT INTO pm_contract (CT_ID, WN_Id, CT_Money, CT_GDRQ, ZDSJBM) VALUES
('CT001', 'P001', 1200.00, '2026-01-15', 'DEP001'),
('CT002', 'P003', 580.00,  '2026-02-20', 'DEP001'),
('CT003', 'P004', 350.00,  '2026-03-10', 'DEP003'),
('CT004', 'P005', 890.00,  '2026-01-28', 'DEP004');

-- 去年签的合同
INSERT INTO pm_contract (CT_ID, WN_Id, CT_Money, CT_GDRQ, ZDSJBM) VALUES
('CT005', 'P001', 800.00,  '2025-03-20', 'DEP001'),
('CT006', 'P002', 1500.00, '2025-06-25', 'DEP002'),
('CT007', 'P006', 650.00,  '2025-05-10', 'DEP002'),
('CT008', 'P007', 420.00,  '2025-08-15', 'DEP005'),
('CT009', 'P008', 380.00,  '2025-09-20', 'DEP003'),
('CT010', 'P004', 200.00,  '2025-11-05', 'DEP003');

-- ── 收费表 ──
-- 今年收费
INSERT INTO pm_contractgathering (RG_Money, RG_Date, CT_ID, HTBM) VALUES
(300.00, '2026-01-20', 'CT001', NULL),
(200.00, '2026-02-15', 'CT002', NULL),
(150.00, '2026-03-08', 'CT003', NULL),
(50.00,  '2026-02-28', NULL,    'DEP004');

-- 去年收费（有合同的）
INSERT INTO pm_contractgathering (RG_Money, RG_Date, CT_ID, HTBM) VALUES
(400.00, '2025-04-10', 'CT005', NULL),
(600.00, '2025-07-15', 'CT006', NULL),
(300.00, '2025-06-20', 'CT007', NULL),
(200.00, '2025-09-10', 'CT008', NULL),
(180.00, '2025-10-25', 'CT009', NULL),
(100.00, '2025-12-15', 'CT010', NULL);

-- 去年收费（无合同的，直接挂部门）
INSERT INTO pm_contractgathering (RG_Money, RG_Date, CT_ID, HTBM) VALUES
(80.00,  '2025-05-20', NULL, 'DEP001'),
(120.00, '2025-08-10', NULL, 'DEP002'),
(60.00,  '2025-11-30', NULL, 'DEP003'),
(45.00,  '2025-07-18', NULL, 'DEP005');

-- ── 动态角色用户（人员参与项目专业策划）──
-- 一院人员参与
INSERT INTO r_dynamicroleuser (SU_UserID, ProjectID, WN_ID, DR_IsValid) VALUES
('U001', 'P001', 'PRO001', 1),  -- 张伟 → 综合体-商业裙楼-建筑
('U001', 'P003', 'PRO013', 1),  -- 张伟 → 中学-教学楼A-建筑
('U001', 'P003', 'PRO015', 1),  -- 张伟 → 中学-体育馆-建筑
('U002', 'P001', 'PRO002', 1),  -- 李娜 → 综合体-商业裙楼-结构
('U002', 'P003', 'PRO014', 1),  -- 李娜 → 中学-教学楼A-结构
('U003', 'P001', 'PRO004', 1),  -- 王磊 → 综合体-办公塔楼-建筑
('U003', 'P001', 'PRO006', 1),  -- 王磊 → 综合体-地下车库-建筑
('U003', 'P003', 'PRO016', 1),  -- 王磊 → 中学-体育馆-结构
('U004', 'P001', 'PRO003', 1),  -- 赵敏 → 综合体-商业裙楼-暖通

-- 二院人员参与
('U005', 'P002', 'PRO008', 1),  -- 刘洋 → 医院-门诊楼-建筑
('U005', 'P002', 'PRO011', 1),  -- 刘洋 → 医院-住院楼-建筑
('U006', 'P002', 'PRO009', 1),  -- 陈静 → 医院-门诊楼-结构
('U007', 'P002', 'PRO010', 1),  -- 杨帆 → 医院-门诊楼-电气

-- 三院人员参与
('U009', 'P004', 'PRO017', 1),  -- 孙鹏 → 住宅-1#楼-建筑
('U009', 'P004', 'PRO019', 1),  -- 孙鹏 → 住宅-2#楼-建筑
('U010', 'P004', 'PRO018', 1),  -- 周琳 → 住宅-1#楼-结构

-- 四院人员参与
('U013', 'P005', 'PRO020', 1),  -- 徐明 → 科技园-研发主楼-建筑
('U014', 'P005', 'PRO021', 1),  -- 马芳 → 科技园-研发主楼-结构
('U015', 'P005', 'PRO022', 1);  -- 胡斌 → 科技园-研发主楼-电气

-- ── 协同图纸文件（子项有设计文件=有在做）──
INSERT INTO cod_fileinfo (CWF_SubProjectID, CWF_FileName) VALUES
('SUB001', '商业裙楼-建筑平面图.dwg'),
('SUB002', '办公塔楼-建筑平面图.dwg'),
('SUB003', '地下车库-建筑平面图.dwg'),
('SUB004', '门诊楼-建筑平面图.dwg'),
('SUB005', '住院楼-建筑平面图.dwg'),
('SUB006', '教学楼A-建筑平面图.dwg'),
('SUB007', '体育馆-建筑平面图.dwg'),
('SUB008', '1#住宅楼-建筑平面图.dwg'),
('SUB009', '2#住宅楼-建筑平面图.dwg'),
('SUB010', '研发主楼-建筑平面图.dwg');

-- ── 工作流历史实例 ──
INSERT INTO wf_his_instance (FI_ID) VALUES
('FI001'), ('FI002'), ('FI003');

-- ── 阶段出图单（已完成出图的子项）──
-- SUB001 商业裙楼已出图（所以不算进行中）
INSERT INTO choose_by_jd (zx_id, fiid) VALUES
('SUB001', 'FI001'),
('SUB003', 'FI002');
-- SUB002 办公塔楼、SUB006 教学楼A、SUB007 体育馆等未出图 → 算进行中

-- ============================================================
-- 验证查询（可选执行）
-- ============================================================

-- 验证1: 项目WBS四层结构
-- SELECT WN1.WN_Name AS 项目名称, WN1.WN_Code AS 工号,
--        WN2.WN_Name AS 阶段, WN3.WN_Name AS 子项名称, WN4.WN_Name AS 专业名称
-- FROM pm_project
-- INNER JOIN pm_wbsnode AS WN1 ON pm_project.WN_ID = WN1.WN_ID
-- INNER JOIN pm_wbsnode AS WN2 ON WN2.WN_ParentID = WN1.WN_ID
-- INNER JOIN pm_wbsnode AS WN3 ON WN3.WN_ParentID = WN2.WN_ID
-- INNER JOIN pm_wbsnode AS WN4 ON WN4.WN_ParentID = WN3.WN_ID;

-- 验证2: 各部门去年合同数和合同额
-- SELECT D.OD_Name, COUNT(CT_ID) AS 合同数, SUM(CT_Money) AS 合同额
-- FROM sf_org_department D
-- LEFT JOIN pm_contract C ON C.ZDSJBM = D.OD_Id
-- WHERE YEAR(C.CT_GDRQ) = YEAR(CURDATE()) - 1
-- GROUP BY D.OD_Id, D.OD_Name;

-- 验证3: 一院人员负荷
-- SELECT utb.OU_Code AS 工号, utb.OU_Name AS 姓名, IFNULL(tb2.num, 0) AS 进行中子项数
-- FROM sf_org_user AS utb
-- INNER JOIN lz_misdepartmentuser ON utb.OU_UserId = lz_misdepartmentuser.SU_UserID
-- INNER JOIN lz_misdepartment ON lz_misdepartment.UG_UserGrpID = lz_misdepartmentuser.UG_UserGrpID
-- LEFT JOIN (
--     SELECT SU_UserID, COUNT(DISTINCT WN3.WN_ID) AS num
--     FROM r_dynamicroleuser
--     INNER JOIN pm_wbsnode AS WN1 ON r_dynamicroleuser.ProjectID = WN1.WN_ID
--     INNER JOIN pm_project ON WN1.WN_ID = pm_project.WN_ID
--     INNER JOIN pm_wbsnode AS WN4 ON WN4.WN_ID = r_dynamicroleuser.WN_ID
--     INNER JOIN pm_wbsnode AS WN3 ON WN3.WN_ID = WN4.WN_ParentID
--     WHERE r_dynamicroleuser.DR_IsValid = 1
--       AND TIMESTAMPDIFF(YEAR, PR_CreateTime, NOW()) <= 2
--       AND NOT EXISTS (SELECT 1 FROM choose_by_jd INNER JOIN wf_his_instance ON fiid = FI_ID WHERE WN3.WN_ID = zx_id)
--       AND EXISTS (SELECT 1 FROM cod_fileinfo WHERE CWF_SubProjectID = WN3.WN_ID)
--     GROUP BY SU_UserID
-- ) AS tb2 ON tb2.SU_UserID = utb.OU_UserId
-- WHERE lz_misdepartment.UG_UserGrpName LIKE '%建筑设计一院%'
--   AND utb.OU_UserId <> 'SU000000000001'
-- GROUP BY utb.OU_Code, utb.OU_Name, tb2.num
-- ORDER BY IFNULL(tb2.num, 0);
