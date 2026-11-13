"""O'quv maqsadidagi sintetik datasetda o'qitiladigan ML modellar."""
from functools import lru_cache
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

@lru_cache(maxsize=1)
def models():
    rng = np.random.default_rng(17)
    n = 1400
    price = rng.choice([420_000, 620_000, 950_000], n)
    nights = rng.integers(1, 9, n)
    lead = rng.integers(0, 100, n)
    weekend = rng.integers(0, 2, n)
    # Regression target: booking revenue with realistic noise.
    revenue = price * nights * (1 + 0.06 * weekend) + rng.normal(0, 45000, n)
    xr = np.column_stack([price, nights, lead, weekend])
    xr_train, xr_test, yr_train, yr_test = train_test_split(xr, revenue, test_size=.25, random_state=21)
    reg = RandomForestRegressor(n_estimators=120, max_depth=9, min_samples_leaf=3, random_state=21)
    reg.fit(xr_train, yr_train)
    rp = reg.predict(xr_test)
    reg_metrics = {"mae": round(float(mean_absolute_error(yr_test, rp)), 2), "rmse": round(float(np.sqrt(mean_squared_error(yr_test, rp))), 2), "r2": round(float(r2_score(yr_test, rp)), 4)}

    # Classification labels are sampled from a cancellation probability rule.
    base = 1 / (1 + np.exp(-(-2.0 + .025 * lead + .15 * (nights > 5) + .4 * (1-weekend))))
    cancelled = rng.binomial(1, base)
    xc = np.column_stack([price, nights, lead, weekend])
    xc_train, xc_test, yc_train, yc_test = train_test_split(xc, cancelled, test_size=.25, random_state=21, stratify=cancelled)
    clf = RandomForestClassifier(n_estimators=140, max_depth=8, min_samples_leaf=4, class_weight="balanced", random_state=21)
    clf.fit(xc_train, yc_train)
    probs = clf.predict_proba(xc_test)[:, 1]
    return reg, reg_metrics, clf, yc_test, probs

def classification_metrics(threshold: float):
    _, _, _, actual, probs = models()
    predicted = (probs >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(actual, predicted, labels=[0,1]).ravel()
    return {"accuracy": round(float(accuracy_score(actual,predicted)),4), "precision": round(float(precision_score(actual,predicted,zero_division=0)),4), "recall": round(float(recall_score(actual,predicted,zero_division=0)),4), "f1": round(float(f1_score(actual,predicted,zero_division=0)),4), "confusion_matrix":{"tn":int(tn),"fp":int(fp),"fn":int(fn),"tp":int(tp)}}

def predict_revenue(price: float, nights: int, lead: int, weekend: bool):
    reg, metrics, _, _, _ = models()
    return {"predicted_revenue": round(float(reg.predict([[price,nights,lead,int(weekend)]])[0]),2), "metrics":metrics}

def predict_cancel(price: float, nights: int, lead: int, weekend: bool, threshold: float):
    _, _, clf, _, _ = models()
    probability = float(clf.predict_proba([[price,nights,lead,int(weekend)]])[0,1])
    return {"cancellation_probability":round(probability,4), "threshold":threshold, "class":"bekor qilinishi mumkin" if probability>=threshold else "bekor qilinishi ehtimoli past", "metrics":classification_metrics(threshold)}
