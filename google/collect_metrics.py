import csv

import requests

INPUT_FILE = "./csv/google_dataset_filtered.csv"
OUTPUT_FILE = "./csv/google_dataset_metrics.csv"

headers = {'Authorization': 'token %s' % "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"}

with open(INPUT_FILE, 'r') as f:
    repo_name_list = f.readlines()

for repo_name in repo_name_list:
    repo_name = repo_name.strip("\n")
    with requests.get(url="https://api.github.com/repos/" + repo_name, headers=headers) as r_repo:
        try:
            r_repo = r_repo.json()
        except:
            print("Error on repo {}".format(repo_name))
            continue
    repo_stars = r_repo.get("stargazers_count", 0)
    repo_forks = r_repo.get("forks_count", 0)
    with requests.get(url="https://api.github.com/repos/{}/contributors".format(repo_name), headers=headers) as contrib:
        try:
            r_contrib = contrib.json()
        except:
            print("Error on repo {}".format(repo_name))
            continue
    repo_contributors = len(r_contrib)

    with open(OUTPUT_FILE, 'a') as outfile:
        write_to_csv = csv.writer(outfile, delimiter=',')

        write_to_csv.writerow(
            [repo_name, repo_stars, repo_forks, repo_contributors])
