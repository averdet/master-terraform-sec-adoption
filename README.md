# Exploring Security Practices in Infrastructure as Code: An Empirical Study of AWS Terraform Configurations

This Readme file describes the process used to achieve the results of our paper. To support our findings, we provide the source code used to collect the dataset from GitHub, to proceed the Static Code Analysis with Checkov on the repositories and analyze the results in a Jupyter Notebook.  
Except for the dataset collection process which is bonded to the data collection period, one can replicate our findings with the data provided.  
Likewise, the process can easily be ported to other public cloud providers and/or IaC tool while reusing significant part of the source code produced for this paper.  

## Dataset collection from GitHub

The python script [collect_dataset.py](collect_dataset.py) is used to collect the repositories containing an AWS Terraform infrastructure.  
We use the GitHub Code Search API with the snippet `"provider aws" extension:tf` to find the indexed Terraform files introducing an AwS configuration.  
The GitHub Code Search API only allows to retrieve the first 1,000 results. Therefore, we ran this script each day from September 12th to October 5th 2022.  
The script produces a CSV output file to which it appends new corresponding repositories. The results contained in the output are then filtered using a spreadsheet editor (like Google Sheets or Excel) (please refer to the paper for the selection criteria).  
The final dataset of GitHub repositories can be found here: [csv/dataset.csv](csv/dataset.csv). This is the dataset used in our paper to answer our research questions on the adoption of security practices.  

## Security Analysis

We proceed a Static Code Analysis on the Terraform files of our dataset's repositories. As explained in the paper, we use the open-source tool [Checkov](https://github.com/bridgecrewio/checkov) in version  2.2.21.  
The python script [checkov_looper.py](checkov_looper.py) is used to automate the execution of checkov on our dataset's repositories the policies we selected.  
[csv/policies.csv](csv/policies.csv) is a list of the set of policies and their mapped categories used for the analysis process (more details provided in the paper).  
The script downloads the repositories source code in a "tmp" folder . The files are deleted as soon as the SCA is done to avoid using too much disk space.  
The results obtained with this script can be found in [results/results.csv](csv/results.csv). For each repository, it lists all the passed policies and the failed policies. Several occurrences of the same policy means that it has been checked several time (e.g. on different cloud resources).  
The analysis have been produced on October 14th, 2022, with the most recent commit available on each repository.  

## Results Analysis

The Jupyter Notebook [analysis_notebook.ipynb](analysis_notebook.ipynb) presents the code used to analyze the results data and helps answer the research questions of our paper by plotting graphs and generating tables.  

### Others

Python scripts create log files to register all useful information.  

