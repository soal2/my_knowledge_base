-- ============================================================================
-- Fix MessageRole ENUM to use lowercase values
-- 修复 MessageRole 枚举值为小写
-- ============================================================================

USE knowledge_base_db;

-- Step 1: 备份现有数据（可选，建议在生产环境执行）
-- CREATE TABLE chat_messages_backup AS SELECT * FROM chat_messages;

-- Step 2: 修改 ENUM 定义为小写
ALTER TABLE chat_messages 
MODIFY COLUMN role ENUM('user', 'ai', 'system') NOT NULL;

-- Step 3: 如果表中已有大写数据，需要更新
-- UPDATE chat_messages SET role = LOWER(role);

-- Step 4: 验证修改
SELECT 
    COLUMN_NAME,
    COLUMN_TYPE,
    DATA_TYPE
FROM 
    INFORMATION_SCHEMA.COLUMNS
WHERE 
    TABLE_SCHEMA = 'knowledge_base_db' 
    AND TABLE_NAME = 'chat_messages' 
    AND COLUMN_NAME = 'role';

-- Step 5: 显示表中现有的 role 值
SELECT DISTINCT role FROM chat_messages;
