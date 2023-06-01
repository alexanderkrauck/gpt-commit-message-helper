#%%
import os
os.chdir("..")

import gpt_change_message

#%%
commit_message, promts = gpt_change_message.generate_change_message(".", return_prompts=True)
#print(promt)
print(commit_message)

# %%
for promt in promts:
    print(promt)
    print()
# %%
