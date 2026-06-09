SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS zhihiku (
    id           BIGINT AUTO_INCREMENT PRIMARY KEY,
    content      TEXT         NOT NULL COMMENT '记录内容',
    rec_type     VARCHAR(64)  DEFAULT '用户输入碎片' COMMENT '记录类型：备忘录/生产记录检查',
    emp_id       VARCHAR(32)  DEFAULT '' COMMENT '员工编号',
    product_code VARCHAR(64)  DEFAULT '' COMMENT '产品编码（可选）',
    create_time  DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '记录时间',
    update_time  DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted   TINYINT(1)   DEFAULT 0 COMMENT '软删除标记',
    INDEX idx_emp_id (emp_id),
    INDEX idx_rec_type (rec_type),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='随记随查主表';
