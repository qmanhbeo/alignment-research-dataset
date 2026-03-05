# Prerequisite
Windows 11 (is what I used)

Anaconda

Docker Desktop for Windows

Git


# Steps done

Forked a repo from https://github.com/moirage/alignment-research-dataset into https://github.com/qmanhbeo/alignment-research-dataset


```bash
# In an Anaconda-enabled Terminal
conda create -n alignment-dataset python=3.9
conda activate alignment-dataset

git config --global core.longpaths true
git clone https://github.com/qmanhbeo/alignment-research-dataset.git
cd alignment-research-dataset
pip install -r requirements.txt

conda install openjdk=17
conda install maven
```

```bash
# In another terminal on same machine
docker run -p 8070:8070 lfoppiano/grobid:0.8.0
# On a browser, go to http://localhost:8070 and see if Grobid is active
```

Then I modified align_data/arxiv_papers/arxiv_papers.py as follows:
- arxiv-vanity no longer reliably returns markdown for many papers, causing the original pipeline to fail. Therefore the pipeline was modified to download PDFs directly from arxiv.org and extract text via GROBID. Change history is versioned on GitHub.

I also modified align_data/common/utils.py as follows:
- added UTF-8 encoding. This prevents crashes when papers contain: math symbols, unicode punctuation, author names

Then I begin fetching arXiv papers.

```bash
# Back to the Anaconda-enabled Terminal & project directory
# Currently terminal should look something like:
# (alignment-dataset) [some-directories]\alignment-research-dataset\>
python main.py fetch --dataset_name arxiv_papers
```

And it will begin fetching related arXiv papers. As time of writing this (2026-03-05 21:58), there are 739 identified papers, which takes around 70 minutes in total to fetch.

At paper 680, I got an error that said "rate exceeded". Makes sense. I'll go take a shower and return later 

```bash
92%|███████████████████████████████████████████████████████████████████████▊      | 680/739 [1:00:09<05:13,  5.31s/it]
# ... Some traceback call ...
raise HTTPError(url, try_index, resp.status_code)
arxiv.HTTPError: Page request resulted in HTTP 429 (https://export.arxiv.org/api/query?search_query=&id_list=1705.04226&sortBy=relevance&sortOrder=descending&start=0&max_results=100)
```