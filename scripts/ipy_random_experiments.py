# %%
import os
os.chdir("..")

from git import Repo
from os.path import join,basename


def get_file_contents_before_staging(repo_path, file_path):
    repo = Repo(repo_path)

    # Get the blob (file) from the last commit
    blob = repo.head.commit.tree[file_path]

    # Get the file contents
    return blob.data_stream.read().decode("utf-8")


def get_current_file_contents(repo_path, file_path):
    with open(join(repo_path, file_path), "r") as file:
        return file.read()


# %%
# Example usage:
repo_path = "../pretrained-graph-transformer/"
file_path = "scripts/ipy_graphormer_model_setup.py"
file_contents_before = get_file_contents_before_staging(repo_path, file_path)
file_contents_after = get_current_file_contents(repo_path, file_path)

query = f"Those are the changes of a file {basename(file_path)} in my project (before and after). What could be the reason those changes were made? Use a single listing with possible reasons in your answer without any other paragraphs. Focus on the reasons of the changes and not on the changes temselves. Keep it short."


promt = f"{query}\n\n\nBEFORE CHANGES:\n{file_contents_before}\n\n\nAFTER CHANGES:\n{file_contents_after}"
print(promt)
# %%
import openai
import os

openai.api_key = os.environ.get("OPENAI_API_KEY")

openai_engine = os.getenv("OPENAI_ENGINE", "gpt-3.5-turbo")
openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.9"))
openai_stop = os.getenv("OPENAI_STOP", None)

response = openai.ChatCompletion.create(
    temperature=0,
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a project manager."},
        {"role": "user", "content": promt},
    ],
)
response_text = response.choices[0]["message"]["content"].strip()
print(response_text)
# %%
query2 = "reformulate the following so that it does not seem as if the writer comments on someone elses work but instead that the writer comments on his own work (and of course know why he did what he did).For example \"suggests\" or \"may have been\" is a bad forumation for my cause. Keep it very short (no need for full sentences) and make it so i can copy paste it."
promt2 = f"{query2}\n\n{response_text}"
print(promt2)
#%%
response2 = openai.ChatCompletion.create(
    temperature=0,
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are an machine learning software engineer."},
        {"role": "user", "content": promt2},
    ],
)

response_text2 = response2.choices[0]["message"]["content"].strip()
print(response_text2)
# %%
os.environ
# %%
