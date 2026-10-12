IF OBJECT_ID('dbo.health_events', 'U') IS NULL
CREATE TABLE dbo.health_events (
  row_id BIGINT NOT NULL PRIMARY KEY,
  event_id VARCHAR(32) NOT NULL,
  revision INT NOT NULL,
  facility_id VARCHAR(16) NOT NULL,
  service_date VARCHAR(32) NOT NULL,
  service_type VARCHAR(32) NOT NULL,
  visits VARCHAR(16) NOT NULL,
  is_deleted CHAR(1) NOT NULL,
  updated_at VARCHAR(32) NOT NULL
);
GO
IF SCHEMA_ID('ggschema') IS NULL EXEC('CREATE SCHEMA ggschema');
GO
IF (SELECT is_cdc_enabled FROM sys.databases WHERE name = DB_NAME()) = 0
EXEC sys.sp_cdc_enable_db;
GO
-- Table-level CDC must be enabled by GoldenGate ADD TRANDATA, after GGSCHEMA.
-- Generic sp_cdc_enable_table alone does not create GoldenGate tracking objects.
