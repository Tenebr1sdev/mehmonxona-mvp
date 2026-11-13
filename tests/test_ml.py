from app import ml

def test_regression_metrics_and_prediction():
    reg,metrics,_,_,_=ml.models()
    assert set(metrics)=={"mae","rmse","r2"}
    result=ml.predict_revenue(420000,2,10,False)
    assert result["predicted_revenue"]>0

def test_classification_threshold_metrics():
    low=ml.classification_metrics(.25)
    high=ml.classification_metrics(.75)
    assert set(low)=={"accuracy","precision","recall","f1","confusion_matrix"}
    assert low["confusion_matrix"]!=high["confusion_matrix"]
