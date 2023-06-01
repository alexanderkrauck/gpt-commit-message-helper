#%%
import os
os.chdir("..")

import gpt_commit_message

#%%
commit_message,promt = gpt_commit_message.generate_commit_message(".", return_prompt=True)
print(promt)
print(commit_message)
# %%
from git import Repo
# %%
repo = Repo(".")
[item.a_path for item in repo.index.diff('HEAD')]
# %%
