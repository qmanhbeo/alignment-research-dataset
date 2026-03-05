# Prerequisite
Windows 11 (is what I used)

Anaconda

Docker Desktop for Windows


# Steps done

1. Download and extract repo .zip from https://github.com/moirage/alignment-research-dataset/archive/refs/heads/main.zip

```bash
conda create -n alignment-dataset python=3.9
conda activate alignment-dataset

cd alignment-research-dataset-main
pip install -r requirements.txt

conda install openjdk=17
conda install maven
```

```bash
# In another terminal on same machine
docker run -p 8070:8070 lfoppiano/grobid:0.8.0
```

Then I modified some codes to fetch arXiv papers directly from https://arxiv.org/ instead of https://arxiv-vanity.com/