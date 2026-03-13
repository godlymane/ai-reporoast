import os
import sys
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>RepoRoast 🔥 — AI Brutally Reviews Your GitHub Code</title>
  <meta name="description" content="Paste your GitHub repo URL and get an AI-powered brutal honest code review. Free. Shareable. Hilarious and useful."/>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: #0d0d0d; color: #f0f0f0; font-family: 'Segoe UI', sans-serif; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 40px 20px; }
    h1 { font-size: 3rem; font-weight: 900; background: linear-gradient(135deg, #ff4500, #ff8c00); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px; }
    .subtitle { color: #aaa; font-size: 1.2rem; margin-bottom: 40px; text-align: center; }
    .card { background: #1a1a1a; border: 1px solid #333; border-radius: 16px; padding: 40px; width: 100%; max-width: 720px; }
    input { width: 100%; padding: 16px 20px; border-radius: 10px; border: 2px solid #333; background: #111; color: #fff; font-size: 1rem; margin-bottom: 16px; outline: none; transition: border 0.2s; }
    input:focus { border-color: #ff4500; }
    button { width: 100%; padding: 16px; background: linear-gradient(135deg, #ff4500, #ff8c00); color: white; font-size: 1.1rem; font-weight: 700; border: none; border-radius: 10px; cursor: pointer; transition: opacity 0.2s; }
    button:hover { opacity: 0.9; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .result { margin-top: 30px; background: #111; border: 1px solid #444; border-radius: 12px; padding: 24px; white-space: pre-wrap; line-height: 1.7; font-size: 0.95rem; display: none; }
    .share-btn { margin-top: 16px; width: 100%; padding: 12px; background: #1da1f2; color: white; font-weight: 700; border: none; border-radius: 10px; cursor: pointer; font-size: 1rem; }
    .badge { display: inline-block; background: #ff4500; color: white; font-size: 0.75rem; font-weight: 700; padding: 4px 10px; border-radius: 20px; margin-bottom: 20px; }
    .loader { display: none; text-align: center; margin-top: 20px; color: #ff8c00; font-size: 1rem; }
    .upgrade { margin-top: 24px; text-align: center; color: #aaa; font-size: 0.9rem; }
    .upgrade a { color: #ff8c00; text-decoration: none; font-weight: 700; }
    .examples { margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
    .example-tag { background: #222; border: 1px solid #444; color: #ccc; padding: 6px 12px; border-radius: 20px; font-size: 0.8rem; cursor: pointer; transition: background 0.2s; }
    .example-tag:hover { background: #333; }
  </style>
</head>
<body>
  <h1>🔥 RepoRoast</h1>
  <p class="subtitle">Paste a GitHub repo URL. Get brutally honest AI feedback.<br/>Share your roast. Level up your code.</p>
  <div class="card">
    <span class="badge">FREE — No signup required</span>
    <input type="text" id="repoUrl" placeholder="https://github.com/username/repo" />
    <div class="examples">
      <span class="example-tag" onclick="setExample('https://github.com/torvalds/linux')">linux</span>
      <span class="example-tag" onclick="setExample('https://github.com/facebook/react')">react</span>
      <span class="example-tag" onclick="setExample('https://github.com/django/django')">django</span>
    </div>
    <br/>
    <button id="roastBtn" onclick="roast()">🔥 Roast My Repo</button>
    <div class="loader" id="loader">⚡ AI is reading your repo... this takes ~15 seconds</div>
    <div class="result" id="result"></div>
    <button class="share-btn" id="shareBtn" style="display:none" onclick="shareOnTwitter()">🐦 Share My Roast on Twitter</button>
    <div class="upgrade">
      Want unlimited roasts + team reports? <a href="https://godlymane.gumroad.com" target="_blank">Upgrade to Pro →</a>
    </div>
  </div>
  <script>
    function setExample(url) { document.getElementById('repoUrl').value = url; }
    async function roast() {
      const url = document.getElementById('repoUrl').value.trim();
      if (!url) { alert('Please enter a GitHub repo URL'); return; }
      const btn = document.getElementById('roastBtn');
      const loader = document.getElementById('loader');
      const result = document.getElementById('result');
      const shareBtn = document.getElementById('shareBtn');
      btn.disabled = true;
      loader.style.display = 'block';
      result.style.display = 'none';
      shareBtn.style.display = 'none';
      try {
        const resp = await fetch('/roast', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ url }) });
        const data = await resp.json();
        if (data.error) { result.textContent = '❌ ' + data.error; } 
        else { result.textContent = data.roast; shareBtn.style.display = 'block'; }
        result.style.display = 'block';
      } catch(e) { result.textContent = '❌ Something went wrong. Try again.'; result.style.display = 'block'; }
      btn.disabled = false;
      loader.style.display = 'none';
    }
    function shareOnTwitter() {
      const roastText = document.getElementById('result').textContent.substring(0, 200);
      const tweet = encodeURIComponent('🔥 AI just roasted my GitHub repo:\\n\\n"' + roastText + '..."\\n\\nGet your repo roasted free: https://reporoast.app #coding #github #programming');
      window.open('https://twitter.com/intent/tweet?text=' + tweet, '_blank');
    }
  </script>
</body>
</html>
"""

def fetch_repo_info(repo_url: str) -> dict:
    """Fetch basic repo info and file tree from GitHub API."""
    # Extract owner/repo from URL
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub URL")
    owner, repo = parts[-2], parts[-1]
    
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    # Get repo metadata
    meta_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=10)
    meta = meta_resp.json() if meta_resp.status_code == 200 else {}
    
    # Get file tree (top level)
    tree_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1", headers=headers, timeout=10)
    tree = tree_resp.json() if tree_resp.status_code == 200 else {}
    
    # Get README
    readme_resp = requests.get(f"https://api.github.com/repos/{owner}/{repo}/readme", headers=headers, timeout=10)
    readme_data = readme_resp.json() if readme_resp.status_code == 200 else {}
    readme_content = ""
    if "content" in readme_data:
        import base64
        try:
            readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")[:2000]
        except Exception:
            readme_content = ""
    
    files = [f["path"] for f in tree.get("tree", []) if f.get("type") == "blob"][:100]
    
    return {
        "name": meta.get("name", repo),
        "description": meta.get("description", "No description"),
        "language": meta.get("language", "Unknown"),
        "stars": meta.get("stargazers_count", 0),
        "forks": meta.get("forks_count", 0),
        "open_issues": meta.get("open_issues_count", 0),
        "size_kb": meta.get("size", 0),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "files": files,
        "readme": readme_content,
        "owner": owner,
        "repo": repo,
    }


def generate_roast(repo_info: dict) -> str:
    """Generate AI roast using OpenAI."""
    file_list = "\n".join(repo_info["files"][:60]) if repo_info["files"] else "No files found"
    
    prompt = f"""You are a brutally honest but hilarious senior software engineer doing a code review. 
Roast this GitHub repository hard but make it genuinely useful. Be specific, be funny, be harsh but fair.
Structure your roast as:

🔥 OVERALL VERDICT: [One savage sentence summary]

💀 WHAT'S WRONG (Top 5 Issues):
[List the 5 biggest technical/structural problems you can infer from the file structure, README, and metadata]

😬 THE HALL OF SHAME:
[2-3 specific funny observations about naming, structure, or red flags you see]

✅ WHAT'S ACTUALLY GOOD:
[1-2 genuine compliments if deserved]

🚀 ROADMAP TO NOT SUCK:
[5 concrete, actionable improvement steps]

REPO DATA:
Name: {repo_info['name']}
Description: {repo_info['description']}
Primary Language: {repo_info['language']}
Stars: {repo_info['stars']} | Forks: {repo_info['forks']} | Open Issues: {repo_info['open_issues']}
Size: {repo_info['size_kb']} KB
Files ({len(repo_info['files'])} total):
{file_list}

README Preview:
{repo_info['readme'][:1000] if repo_info['readme'] else 'No README (already bad sign)'}

Be specific to THIS repo. Don't be generic. Make the developer laugh and learn at the same time."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.8,
    )
    return response.choices[0].message.content


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


@app.route("/roast", methods=["POST"])
def roast_endpoint():
    data = request.get_json()
    repo_url = data.get("url", "").strip()
    
    if not repo_url:
        return jsonify({"error": "Please provide a GitHub repo URL"}), 400
    
    if "github.com" not in repo_url:
        return jsonify({"error": "Please provide a valid GitHub URL (e.g. https://github.com/user/repo)"}), 400
    
    try:
        repo_info = fetch_repo_info(repo_url)
        roast = generate_roast(repo_info)
        return jsonify({"roast": roast, "repo": repo_info["name"]})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Could not analyze repo: {str(e)}"}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
