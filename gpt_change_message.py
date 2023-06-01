import openai
import os
from os.path import join, basename
import sys
import subprocess
from git import Repo
from requests.exceptions import RequestException

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Set default values for environment variables
openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
# openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "60"))
openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
# openai_stop = os.getenv("OPENAI_STOP", None)


def get_staged_files(repo_path):
    repo = Repo(repo_path)
    return [item.a_path for item in repo.index.diff("HEAD")]


def get_file_contents_before_staging(repo_path, file_path):
    repo = Repo(repo_path)

    # Get the blob (file) from the last commit
    blob = repo.head.commit.tree[file_path]

    # Get the file contents
    return blob.data_stream.read().decode("utf-8")


def get_current_file_contents(repo_path, file_path):
    with open(join(repo_path, file_path), "r") as file:
        return file.read()


def remove_first_line(s):
    lines = s.split("\n")
    lines.pop(0)
    return "\n".join(lines)


def generate_summary(file_path):
    # Get git diff of the file
    output = subprocess.run(
        ["git", "diff", "--cached", file_path], capture_output=True, text=True
    )

    # Extract added/modified/deleted lines from git diff
    added_lines = []
    modified_lines = []
    deleted_lines = []
    for line in output.stdout.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            deleted_lines.append("Removed " + line[1:])
        elif line.startswith(" ") and not line.startswith("@@"):
            modified_lines.append(line[1:])

    # Combine added/modified/deleted lines to form summary
    added_summary = "\n".join(added_lines)
    modified_summary = "\n".join(modified_lines)
    deleted_summary = "\n".join(deleted_lines)
    summary = ""
    if added_summary:
        summary += f"Added:\n{added_summary}\n\n"
    if modified_summary:
        summary += f"Modified:\n{modified_summary}\n\n"
    if deleted_summary:
        summary += f"Deleted:\n{deleted_summary}\n\n"
    return summary.strip()


def generate_change_message(repo_path, return_prompts=False):

    
    promts = []
    file_texts = {}
    file_paths = get_staged_files(repo_path)
    for file_path in file_paths:
        file_contents_before = get_file_contents_before_staging(repo_path, file_path)
        file_contents_after = get_current_file_contents(repo_path, file_path)

        query_comparison = (
            "Those are the changes of a file "
            f"{basename(file_path)} in my project (before and after). "
            "What could be the reason those changes were made? "
            "Use a single listing with possible reasons in your answer "
            "without any other paragraphs. Focus on the reasons of the changes "
            "and not on the changes themselves. Keep it short."
        )
        promt_comparison = f"{query_comparison}\n\n\nBEFORE CHANGES:\n{file_contents_before}\n\n\nAFTER CHANGES:\n{file_contents_after}"
        promts.append(promt_comparison)

        response_text_comparison = (
            openai.ChatCompletion.create(
                temperature=openai_temperature,
                model=openai_model,
                messages=[
                    {"role": "system", "content": "You are a project manager."},
                    {"role": "user", "content": promt_comparison},
                ],
            )
            .choices[0]["message"]["content"]
            .strip()
        )

        query_refine = (
            "Reformulate the following so that it doesn't seem as if the writer "
            "comments on someone else's work but instead comments on his own work "
            "(and of course knows why he did what he did). For example, 'suggests' "
            "or 'may have been' is a bad formulation for my cause."
            "No need for full sentences and make it so I can copy paste it."
        )
        promt_refine = f"{query_refine}\n\n{response_text_comparison}"
        promts.append(promt_refine)

        response_text_refined = (
            openai.ChatCompletion.create(
                temperature=openai_temperature,
                model=openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an machine learning software engineer.",
                    },
                    {"role": "user", "content": promt_refine},
                ],
            )
            .choices[0]["message"]["content"]
            .strip()
        )

        response_text_refined = remove_first_line(response_text_refined)
        file_texts[file_path] = response_text_refined

    if return_prompts:
        return file_texts, promts
    return file_texts


if __name__ == "__main__":
    file_paths = sys.argv[1:]
    commit_message = generate_change_message(file_paths)
    print(commit_message)
