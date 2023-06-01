import openai
import os
from os.path import join, basename
import sys
import subprocess
from git import Repo
from openai.error import RateLimitError
from typing import List, Optional, Tuple

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Set default values for environment variables
openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
# openai_max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "60"))
openai_temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
# openai_stop = os.getenv("OPENAI_STOP", None)

def get_changed_files(repo_path, before_version, after_version):
    repo = Repo(repo_path)

    if after_version == "STAGED":
        commit2 = repo.index
    else:
        commit2 = repo.commit(after_version)

    commit1 = repo.commit(before_version)

    diffs = commit2.diff(commit1)

    changed_files = [item.a_path for item in diffs]

    return changed_files



def get_current_file_contents(repo_path, file_path):
    try:
        with open(join(repo_path, file_path), "r") as file:
            return file.read()
    except FileNotFoundError:
        return "File does not exist in this version of the repository."


def remove_first_line(s):
    lines = s.split("\n")
    lines.pop(0)
    return "\n".join(lines)


def get_file_contents(repo_path, file_path, version):
    repo = Repo(repo_path)

    if version == "STAGED":
        return get_current_file_contents(repo_path, file_path)

    # Get the blob (file) from the last commit
    try:
        blob = repo.commit(version).tree[file_path]
    except KeyError:
        return "File does not exist in this version of the repository."

    # Get the file contents
    return blob.data_stream.read().decode("utf-8")


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


def generate_change_message(
    repo_path: str,
    return_prompts: Optional[bool] = False,
    version_before: Optional[str] = "HEAD",
    version_after: Optional[str] = "STAGED",
):
    """
    Generate a summary of the changes made between two versions of a repository.

    Parameters
    ----------
    repo_path : str
        Path to the repository.
    return_prompts : bool, optional
        Whether to return the prompts used to generate the commit message.
    version_before : str, optional
        Version to compare to. Defaults to "HEAD". See below for more information.
    version_after : str, optional
        Version to compare from. Defaults to "HEAD". See below for more information.

    Options for version_before and version_after:
    - "HEAD": The current (commited) version of the repository.
    - "STAGED": The staged version of the repository.
    - "HEAD~n": The version of the repository n commits ago.
    - A commit hash: The version of the repository at the given commit hash.
    """

    assert version_before != "STAGED", "version_before cannot be 'STAGED'"
    assert (
        version_before != version_after
    ), "version_before and version_after cannot be the same"

    promts = []
    file_texts = {}

    file_paths = get_changed_files(repo_path, version_before, version_after)
    for file_path in file_paths:
        file_contents_before = get_file_contents(repo_path, file_path, version_before)
        file_contents_after = get_file_contents(repo_path, file_path, version_after)

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

        try:
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
        except RateLimitError:
            print("Rate Limit Exceeded")
            break

        query_refine = (
            "Reformulate the following so that it doesn't seem as if the writer "
            "comments on someone else's work but instead comments on his own work "
            "(and of course knows why he did what he did). For example, 'suggests' "
            "or 'may have been' is a bad formulation for my cause."
            "No need for full sentences and make it so I can copy paste it."
        )
        promt_refine = f"{query_refine}\n\n{response_text_comparison}"
        promts.append(promt_refine)

        try:
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
        except RateLimitError:
            print("Rate Limit Exceeded")
            break
        
        response_text_refined = remove_first_line(response_text_refined)
        file_texts[file_path] = response_text_refined

    if return_prompts:
        return file_texts, promts
    return file_texts


if __name__ == "__main__":
    file_paths = sys.argv[1:]
    commit_message = generate_change_message(file_paths)
    print(commit_message)
