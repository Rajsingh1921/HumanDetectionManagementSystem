from detection.database import save_detection

print("Testing MySQL connection...")

save_detection(2)

print("✅ Database test completed successfully!")