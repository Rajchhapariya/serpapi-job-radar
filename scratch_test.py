from app.database import db_manager

try:
    p1 = "SELECT COALESCE(via_platform, 'Direct / Portal') AS platform, COUNT(*) AS openings, ROUND(AVG(CASE WHEN salary_raw IS NOT NULL THEN 100.0 ELSE 0.0 END), 1) AS salary_disclosure_pct FROM jobs GROUP BY platform ORDER BY openings DESC LIMIT 10"
    res = db_manager.execute_readonly_query(p1)
    print("SUCCESS:", res)
except Exception as e:
    print("ERROR:", type(e), e)
