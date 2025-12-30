-- Active: 1766538393446@@127.0.0.1@3306
-- ============================================================================
-- Personal Federated Learning Knowledge Base Agent
-- MySQL Database Schema
-- Generated from SQLAlchemy models
-- ============================================================================

-- Create database (if not exists)
CREATE DATABASE IF NOT EXISTS knowledge_base_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE knowledge_base_db;

-- ============================================================================
-- Drop existing tables (in reverse order of dependencies)
-- ============================================================================
DROP TABLE IF EXISTS chat_messages;
DROP TABLE IF EXISTS chat_sessions;
DROP TABLE IF EXISTS file_documents;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;

-- ============================================================================
-- Table: users
-- Core user authentication and profile
-- ============================================================================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: api_keys
-- Third-party API credentials (Qwen, DeepSeek)
-- ============================================================================
CREATE TABLE api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    provider VARCHAR(50) NOT NULL COMMENT 'API provider: qwen, deepseek, etc.',
    api_key VARCHAR(512) NOT NULL COMMENT 'Encrypted API key',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_api_keys_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_user_provider (user_id, provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: file_documents
-- Uploaded document metadata and parsing status
-- ============================================================================
CREATE TABLE file_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(512) NOT NULL,
    file_type VARCHAR(20) DEFAULT NULL COMMENT 'File extension: pdf, docx, txt, etc.',
    file_size BIGINT DEFAULT NULL COMMENT 'File size in bytes',
    parsing_status ENUM('pending', 'processing', 'completed', 'failed') 
        NOT NULL DEFAULT 'pending',
    parsing_error TEXT DEFAULT NULL COMMENT 'Error message if parsing failed',
    chunk_count INT NOT NULL DEFAULT 0 COMMENT 'Number of chunks after parsing',
    upload_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    parsed_at DATETIME DEFAULT NULL,
    
    -- Foreign Keys
    CONSTRAINT fk_file_documents_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_user_status (user_id, parsing_status),
    INDEX idx_upload_time (upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: chat_sessions
-- Conversation session grouping
-- ============================================================================
CREATE TABLE chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_chat_sessions_user 
        FOREIGN KEY (user_id) REFERENCES users(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_user_active (user_id, last_active_at),
    INDEX idx_last_active (last_active_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Table: chat_messages
-- Individual messages within a session
-- ============================================================================
CREATE TABLE chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    role ENUM('user', 'ai', 'system') NOT NULL,
    content TEXT NOT NULL,
    is_deep_thought BOOLEAN NOT NULL DEFAULT FALSE,
    thinking_content TEXT DEFAULT NULL COMMENT 'Extended reasoning process for deep thought',
    tokens_used INT DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    CONSTRAINT fk_chat_messages_session 
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id) 
        ON DELETE CASCADE ON UPDATE CASCADE,
    
    -- Indexes
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at),
    INDEX idx_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Views for common queries
-- ============================================================================

-- View: User document statistics
CREATE OR REPLACE VIEW v_user_document_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(fd.id) AS total_documents,
    SUM(CASE WHEN fd.parsing_status = 'completed' THEN 1 ELSE 0 END) AS completed_documents,
    SUM(CASE WHEN fd.parsing_status = 'pending' THEN 1 ELSE 0 END) AS pending_documents,
    SUM(CASE WHEN fd.parsing_status = 'failed' THEN 1 ELSE 0 END) AS failed_documents,
    SUM(fd.chunk_count) AS total_chunks,
    SUM(fd.file_size) AS total_file_size
FROM users u
LEFT JOIN file_documents fd ON u.id = fd.user_id
GROUP BY u.id, u.username;

-- View: User chat statistics
CREATE OR REPLACE VIEW v_user_chat_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    COUNT(DISTINCT cs.id) AS total_sessions,
    COUNT(cm.id) AS total_messages,
    SUM(CASE WHEN cm.role = 'user' THEN 1 ELSE 0 END) AS user_messages,
    SUM(CASE WHEN cm.role = 'ai' THEN 1 ELSE 0 END) AS ai_messages,
    SUM(CASE WHEN cm.is_deep_thought = TRUE THEN 1 ELSE 0 END) AS deep_thought_messages,
    MAX(cs.last_active_at) AS last_activity
FROM users u
LEFT JOIN chat_sessions cs ON u.id = cs.user_id
LEFT JOIN chat_messages cm ON cs.id = cm.session_id
GROUP BY u.id, u.username;

-- ============================================================================
-- Stored Procedures
-- ============================================================================

DELIMITER //

-- Procedure: Create new chat session with first message
CREATE PROCEDURE sp_create_chat_with_message(
    IN p_user_id INT,
    IN p_title VARCHAR(255),
    IN p_message_content TEXT,
    IN p_role VARCHAR(10)
)
BEGIN
    DECLARE v_session_id INT;
    
    -- Create session
    INSERT INTO chat_sessions (user_id, title) 
    VALUES (p_user_id, COALESCE(p_title, 'New Chat'));
    
    SET v_session_id = LAST_INSERT_ID();
    
    -- Create first message
    INSERT INTO chat_messages (session_id, role, content)
    VALUES (v_session_id, p_role, p_message_content);
    
    -- Return the new session ID
    SELECT v_session_id AS session_id;
END //

-- Procedure: Clean up old sessions (older than N days)
CREATE PROCEDURE sp_cleanup_old_sessions(
    IN p_user_id INT,
    IN p_days_old INT
)
BEGIN
    DELETE FROM chat_sessions 
    WHERE user_id = p_user_id 
    AND last_active_at < DATE_SUB(NOW(), INTERVAL p_days_old DAY);
    
    SELECT ROW_COUNT() AS deleted_sessions;
END //

-- Procedure: Get user's recent activity summary
CREATE PROCEDURE sp_user_activity_summary(
    IN p_user_id INT
)
BEGIN
    SELECT 
        (SELECT COUNT(*) FROM file_documents WHERE user_id = p_user_id) AS total_documents,
        (SELECT COUNT(*) FROM file_documents WHERE user_id = p_user_id AND parsing_status = 'completed') AS parsed_documents,
        (SELECT COUNT(*) FROM chat_sessions WHERE user_id = p_user_id) AS total_sessions,
        (SELECT COUNT(*) FROM chat_messages cm 
         INNER JOIN chat_sessions cs ON cm.session_id = cs.id 
         WHERE cs.user_id = p_user_id) AS total_messages,
        (SELECT COUNT(*) FROM api_keys WHERE user_id = p_user_id AND is_active = TRUE) AS active_api_keys;
END //

DELIMITER ;

-- ============================================================================
-- Sample Data (for development/testing only)
-- ============================================================================

-- Uncomment the following lines to insert sample data

/*
-- Sample user (password: 'password123')
INSERT INTO users (username, password_hash) VALUES 
('testuser', 'pbkdf2:sha256:260000$salt$hash');

-- Sample API keys
INSERT INTO api_keys (user_id, provider, api_key, is_active) VALUES 
(1, 'qwen', 'sk-test-qwen-api-key-123', TRUE),
(1, 'deepseek', 'sk-test-deepseek-api-key-456', TRUE);

-- Sample document
INSERT INTO file_documents (user_id, filename, filepath, file_type, file_size, parsing_status) VALUES 
(1, 'sample_paper.pdf', '/uploads/1/sample_paper.pdf', 'pdf', 1024000, 'completed');

-- Sample chat session with messages
INSERT INTO chat_sessions (user_id, title) VALUES 
(1, 'Research Discussion');

INSERT INTO chat_messages (session_id, role, content) VALUES 
(1, 'user', 'What is federated learning?'),
(1, 'ai', 'Federated learning is a machine learning approach that trains algorithms across decentralized devices...');
*/

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Show all tables
SHOW TABLES;

-- Describe table structures
DESCRIBE users;
DESCRIBE api_keys;
DESCRIBE file_documents;
DESCRIBE chat_sessions;
DESCRIBE chat_messages;
