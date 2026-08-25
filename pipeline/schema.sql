-- schema.sql
-- This file contains the Data Definition Language (DDL) for the dimensional model.
-- Note: In a modern data stack using dbt, these tables are often generated automatically 
-- via `CREATE TABLE AS` or `CREATE VIEW AS` statements. 
-- However, this provides a clear view of the target schema and constraints.

-- 1. Dimension Table: dim_date
-- Stores date-related attributes to allow easy slicing by time periods.
CREATE TABLE dim_date (
    date_key DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

-- 2. Dimension Table: dim_holiday
-- Stores attributes about holidays. We use a surrogate key to handle non-holiday days.
CREATE TABLE dim_holiday (
    holiday_id INT PRIMARY KEY, -- Surrogate key (e.g., 0 for 'No Holiday', 1, 2... for specific holidays)
    holiday_name VARCHAR(255) NOT NULL,
    local_name VARCHAR(255) NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    is_global BOOLEAN NOT NULL,
    holiday_type VARCHAR(50) NOT NULL
);

-- 3. Dimension Table: dim_location
-- Stores location attributes to support analysis across different cities/countries.
CREATE TABLE dim_location (
    location_id INT PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    country_code VARCHAR(10) NOT NULL
);

-- 4. Fact Table: fact_daily_weather
-- Stores the daily weather metrics and links to the dimensions.
CREATE TABLE fact_daily_weather (
    fact_id BIGINT PRIMARY KEY, -- or auto-increment depending on the RDBMS
    date_key DATE NOT NULL,
    location_id INT NOT NULL,
    holiday_id INT NOT NULL,
    temperature_2m_max DECIMAL(5,2),
    temperature_2m_min DECIMAL(5,2),
    precipitation_sum DECIMAL(8,2),
    
    -- Foreign Key Constraints (Supported by most modern DWHs, sometimes logical rather than enforced)
    CONSTRAINT fk_date FOREIGN KEY (date_key) REFERENCES dim_date(date_key),
    CONSTRAINT fk_location FOREIGN KEY (location_id) REFERENCES dim_location(location_id),
    CONSTRAINT fk_holiday FOREIGN KEY (holiday_id) REFERENCES dim_holiday(holiday_id)
);

-- Indexes for performance (For Traditional RDBMS; Columnar databases like Snowflake/BigQuery handle this differently, e.g., via clustering/partitioning)
CREATE INDEX idx_fact_date ON fact_daily_weather(date_key);
CREATE INDEX idx_fact_location ON fact_daily_weather(location_id);
CREATE INDEX idx_fact_holiday ON fact_daily_weather(holiday_id);
