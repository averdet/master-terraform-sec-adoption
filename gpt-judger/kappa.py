import pandas as pd
from sklearn.metrics import cohen_kappa_score
import numpy as np
import os

def calculate_kappa(csv_file):
    # Read the CSV file
    data = pd.read_csv(csv_file)

    # Ensure the columns exist
    if 'original_category' not in data.columns or 'assigned_category' not in data.columns:
        raise ValueError("CSV must contain 'original_category' and 'assigned_category' columns.")

    # Extract the two columns
    original_category = data['original_category']
    assigned_category = data['assigned_category']

    # Calculate Cohen's Kappa
    kappa = cohen_kappa_score(original_category, assigned_category)

    return kappa


content_root = os.getcwd()

csv_file = os.path.join(content_root, 'gpt-categorization-tfsec.csv')
kappa_score = calculate_kappa(csv_file)
csv_file = os.path.join(content_root, 'gpt-categorization-tfsec1.csv')
kappa_score1 = calculate_kappa(csv_file)
csv_file = os.path.join(content_root, 'gpt-categorization-tfsec2.csv')
kappa_score2 = calculate_kappa(csv_file)
kappa_tfsec = np.mean([kappa_score, kappa_score1, kappa_score2])
print(f"Cohen's Kappa: {kappa_tfsec:.3f}")

csv_file = os.path.join(content_root, 'gpt-categorization-checkov.csv')
kappa_score = calculate_kappa(csv_file)
csv_file = os.path.join(content_root, 'gpt-categorization-checkov1.csv')
kappa_score1 = calculate_kappa(csv_file)
csv_file = os.path.join(content_root, 'gpt-categorization-checkov2.csv')
kappa_score2 = calculate_kappa(csv_file)
kappa_checkov = np.mean([kappa_score, kappa_score1, kappa_score2])
print(f"Cohen's Kappa: {kappa_checkov:.3f}")
