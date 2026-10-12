IF OBJECT_ID('dbo.facilities', 'U') IS NULL
CREATE TABLE dbo.facilities (
  facility_id VARCHAR(16) NOT NULL,
  facility_name VARCHAR(100) NOT NULL,
  ward INT NOT NULL
) WITH (DISTRIBUTION = REPLICATE, HEAP);
GO
