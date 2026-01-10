-- Initialize manager user for MySQL views
-- Views (lastmonthtraffic, monthtraffic) use DEFINER=manager@%
-- This user must exist for the views to work properly

CREATE USER IF NOT EXISTS 'manager'@'%' IDENTIFIED BY 'manager';
GRANT ALL PRIVILEGES ON radius.* TO 'manager'@'%';
FLUSH PRIVILEGES;
