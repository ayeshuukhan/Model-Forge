"""
Trains a tiny house-price regression model on synthetic data.
Features: [sqft, bedrooms, bathrooms, age_years]
This mirrors a simple, realistic tabular ML use case without
needing an external dataset or GPU.
"""
import os
import numpy as np
import joblib
from sklearn.linear_model import LinearRegression

rng = np.random.default_rng(42)
n = 500

sqft = rng.uniform(500, 4000, n)
bedrooms = rng.integers(1, 6, n)
bathrooms = rng.integers(1, 4, n)
age = rng.uniform(0, 50, n)

# synthetic "true" price relationship + noise
price = (
    sqft * 120
    + bedrooms * 8000
    + bathrooms * 5000
    - age * 800
    + rng.normal(0, 15000, n)
    + 20000
)

X = np.column_stack([sqft, bedrooms, bathrooms, age])
y = price

model = LinearRegression()
model.fit(X, y)

out_path = os.path.join(os.path.dirname(__file__), "regression_model.joblib")
joblib.dump(model, out_path)
print(f"Regression model trained and saved to {out_path}")
