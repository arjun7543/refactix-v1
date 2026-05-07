from flask import Flask, request, jsonify
from flask_cors import CORS
import requests, os, json, re

app = Flask(__name__)
CORS(app)

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"

LANGS = {
    "python":"Python","javascript":"JavaScript","typescript":"TypeScript",
    "go":"Go","rust":"Rust","java":"Java","cpp":"C++","php":"PHP",
    "sql":"SQL","swift":"Swift","kotlin":"Kotlin","ruby":"Ruby","csharp":"C#",
    "bash":"Bash","r":"R","scala":"Scala"
}

# Judge0 language IDs for code execution
JUDGE0_IDS = {
    "python":71,"javascript":63,"typescript":74,"go":60,"rust":73,
    "java":62,"cpp":54,"php":68,"bash":46,"ruby":72,"csharp":51,"kotlin":78
}

def call_groq(prompt, max_tokens=3000):
    if not GROQ_KEY:
        raise Exception("API key not configured on server")
    r = requests.post(GROQ_URL,
        headers={"Content-Type":"application/json","Authorization":f"Bearer {GROQ_KEY}"},
        json={"model":MODEL,"messages":[{"role":"user","content":prompt}],
              "max_tokens":max_tokens,"temperature":0.1},
        timeout=45)
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    clean = re.sub(r"```json|```","",raw).strip()
    return json.loads(clean)

# ── REVIEW ──
@app.route("/api/review", methods=["POST"])
def review():
    try:
        b = request.get_json()
        code, lang = b.get("code","").strip(), b.get("lang","python")
        if len(code) < 20: return jsonify({"error":"Code too short"}), 400

        prompt = f"""Expert code review of this {LANGS.get(lang,lang)} code. ONLY valid JSON, no markdown:

CODE:
{code}

{{
  "score": <0-100>,
  "verdict": "<Excellent|Good|Needs Work|Critical Issues>",
  "summary": "<one sentence overall assessment>",
  "bugs": [{{"line":"<line ref>","issue":"<description>","severity":"high|medium|low"}}],
  "security": [{{"line":"<line ref>","issue":"<description>","severity":"high|medium|low"}}],
  "performance": [{{"line":"<line ref>","issue":"<description>","severity":"high|medium|low"}}],
  "best_practices": [{{"line":"<line ref>","issue":"<description>","severity":"high|medium|low"}}],
  "time_complexity": "<Big O notation>",
  "space_complexity": "<Big O notation>",
  "time_explanation": "<one sentence>",
  "space_explanation": "<one sentence>",
  "complexity_rating": "<Optimal|Good|Acceptable|Poor>",
  "alternatives": [
    {{"title":"<approach name>","description":"<how it improves complexity>","time":"<new Big O>","space":"<new Big O>","improvement":"high|medium|low"}}
  ],
  "fixed_code": "<complete rewritten code with ALL issues fixed>"
}}

Rules: bugs/security/performance/best_practices max 5 items each. alternatives: 2-3 genuine improvements. fixed_code: complete runnable code."""

        result = call_groq(prompt)
        return jsonify({"success":True,"data":result})
    except json.JSONDecodeError:
        return jsonify({"error":"AI returned unexpected format, try again"}), 500
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── CONVERT ──
@app.route("/api/convert", methods=["POST"])
def convert():
    try:
        b = request.get_json()
        code = b.get("code","").strip()
        src, tgt = b.get("src","python"), b.get("tgt","javascript")
        if len(code) < 10: return jsonify({"error":"Code too short"}), 400
        if src == tgt: return jsonify({"error":"Source and target are the same"}), 400

        prompt = f"""Convert this {LANGS.get(src,src)} code to {LANGS.get(tgt,tgt)}. ONLY valid JSON, no markdown:

CODE:
{code}

{{
  "converted_code": "<complete idiomatic {LANGS.get(tgt,tgt)} code>",
  "notes": ["<important conversion note or difference>"],
  "warnings": ["<anything that may not map perfectly>"]
}}

Rules: idiomatic target language patterns (not literal translation), preserve ALL logic, 2-4 notes, warnings only if needed."""

        result = call_groq(prompt)
        return jsonify({"success":True,"data":result})
    except json.JSONDecodeError:
        return jsonify({"error":"AI returned unexpected format, try again"}), 500
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── FIX BUGS ──
@app.route("/api/fix", methods=["POST"])
def fix():
    try:
        b = request.get_json()
        code, lang = b.get("code","").strip(), b.get("lang","python")
        if len(code) < 10: return jsonify({"error":"Code too short"}), 400

        prompt = f"""Find and fix ALL bugs in this {LANGS.get(lang,lang)} code. ONLY valid JSON, no markdown:

CODE:
{code}

{{
  "bugs_found": [
    {{
      "line": "<line reference>",
      "type": "bug|security|performance|style",
      "severity": "critical|high|medium|low",
      "description": "<what the bug is>",
      "suggestion": "<how to fix it without applying>"
    }}
  ],
  "fixed_code": "<complete code with ALL bugs fixed>",
  "changes_made": ["<specific change made>"],
  "summary": "<one sentence about what was wrong>"
}}

Rules: be specific with line references, fixed_code is always the complete file."""

        result = call_groq(prompt)
        return jsonify({"success":True,"data":result})
    except json.JSONDecodeError:
        return jsonify({"error":"AI returned unexpected format, try again"}), 500
    except Exception as e:
        return jsonify({"error":str(e)}), 500

# ── RUN CODE (via Judge0) ──
@app.route("/api/run", methods=["POST"])
def run_code():
    try:
        b = request.get_json()
        code, lang = b.get("code","").strip(), b.get("lang","python")
        stdin = b.get("stdin","")

        lang_id = JUDGE0_IDS.get(lang)
        if not lang_id:
            return jsonify({"error":f"Execution not supported for {lang}"}), 400

        # Submit to Judge0 (free public instance)
        sub = requests.post("https://judge0-ce.p.rapidapi.com/submissions",
            headers={
                "content-type":"application/json",
                "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY",""),
                "X-RapidAPI-Host":"judge0-ce.p.rapidapi.com"
            },
            json={"language_id":lang_id,"source_code":code,"stdin":stdin},
            timeout=15)

        if sub.status_code != 201:
            # Fallback: try free Judge0 instance
            sub = requests.post("https://ce.judge0.com/submissions?base64_encoded=false&wait=true",
                headers={"Content-Type":"application/json"},
                json={"language_id":lang_id,"source_code":code,"stdin":stdin},
                timeout=20)
            result = sub.json()
        else:
            token = sub.json().get("token")
            import time; time.sleep(2)
            res = requests.get(f"https://judge0-ce.p.rapidapi.com/submissions/{token}",
                headers={"X-RapidAPI-Key":os.environ.get("RAPIDAPI_KEY",""),"X-RapidAPI-Host":"judge0-ce.p.rapidapi.com"},
                timeout=15)
            result = res.json()

        return jsonify({
            "success": True,
            "stdout": result.get("stdout",""),
            "stderr": result.get("stderr",""),
            "compile_output": result.get("compile_output",""),
            "status": result.get("status",{}).get("description","Unknown"),
            "time": result.get("time",""),
            "memory": result.get("memory","")
        })
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route("/")
def index():
    return jsonify({"status":"Refactix API v2 running","endpoints":["/api/review","/api/convert","/api/fix","/api/run"]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
