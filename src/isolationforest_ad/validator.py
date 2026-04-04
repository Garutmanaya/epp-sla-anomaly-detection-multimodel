from isolationforest_ad.inference import run_inference
from xgboost_ad.validator import generate_test_data
from datetime import datetime, timedelta

def main():

    df = generate_test_data(
        
        start_date=datetime(2026,5,1),
        hours=48,
        anomaly_prob=0.2
    )

    results = run_inference(df)

    total = len(results)
    alerts = (results["Status"] != "Normal ✅").sum()

    print(f"Total: {total}")
    print(f"Alerts: {alerts}")
    print(f"Alert Rate: {round(alerts/total*100, 2)}%")

    print(results.head(20))


if __name__ == "__main__":
    main()
