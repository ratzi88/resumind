import pandas as pd #need to do pip install

#import the database
job_df=pd.read_csv('fake_job_postings.csv')
##print(job_df.head(10))

#drop useless columns
job_df=job_df.drop(columns=['telecommuting', 'has_company_logo', 'has_questions', 'fraudulent'])
##print(job_df.head(10))

#make the database smaller
##print(len(job_df))
job_df=job_df.head(200)
##print(len(job_df))

#embendding with BERT
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")

#conversion of the necessary information
texts = (
    job_df["title"].fillna("") + ". " +
    job_df["description"].fillna("") + ". "+
    job_df["requirements"].fillna("")
)
job_embeddings = model.encode(
    texts.tolist(),
    normalize_embeddings=True
)