# refixit-v1

Code Review API + Web UI — powered by Groq (free).

What it does:
Developers paste code or hit the API endpoint 
→ get back instant AI review: bugs found, security issues, performance problems, and a fixed version.
Something devs actually pay for because it saves real time.

What's inside:
-Bug Fixer — finds and fixes bugs, security holes, performance issues, and style problems. Shows a "What Changed" tab with every fix labeled by type (bug / security / perf / style)
-Code Analyzer — gives you time complexity, space complexity, quality score out of 100, readability, maintainability, issues list, and 2–4 alternate approaches with better Big O

What's built:
-Web UI where devs paste code → get a score, bugs, security issues, performance notes, and a fixed rewrite
-API docs section (cURL, Python, JS examples) — shows developers how to call it programmatically
-Powered by Groq + Llama 3.3 70B — completely free, no credit card ever
-Supports 12 languages with auto-detect
-Animated score ring, copy-fixed-code button, scanline aesthetic
