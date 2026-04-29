"""
CodeExec AI - Prompt Configuration
Centralized storage for all LLM system prompts, templates, and instructions.
"""

# --- Example templates for natural language → code mapping ---
EXAMPLE_TEMPLATES = {
    "average": '''import statistics
data = {data}
avg = statistics.mean(data)
print(f"Average: {{avg}}")
print(f"Count: {{len(data)}}")
print(f"Sum: {{sum(data)}}")
print(f"Min: {{min(data)}}, Max: {{max(data)}}")''',

    "chart": '''import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(x, y, color='#e94560', linewidth=2.5, label='sin(x)')
ax.fill_between(x, y, alpha=0.15, color='#e94560')
ax.set_facecolor('#16213e')
ax.set_title('Sine Wave', color='white', fontsize=16, fontweight='bold')
ax.set_xlabel('x', color='#a0a0a0')
ax.set_ylabel('sin(x)', color='#a0a0a0')
ax.tick_params(colors='#a0a0a0')
ax.legend(facecolor='#1a1a2e', edgecolor='#e94560', labelcolor='white')
for spine in ax.spines.values():
    spine.set_color('#333')
plt.tight_layout()
plt.show()''',

    "fibonacci": '''def fibonacci(n):
    """Generate first n Fibonacci numbers"""
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib[:n]

n = 20
result = fibonacci(n)
print(f"First {n} Fibonacci numbers:")
print(result)
print(f"\\nSum: {sum(result)}")
print(f"Golden ratio approx: {result[-1]/result[-2]:.10f}")''',

    "sort": '''import random
import time

data = [random.randint(1, 10000) for _ in range(10000)]
print(f"Sorting {len(data)} random integers...\\n")

# Bubble sort (first 1000 elements)
arr = data[:1000].copy()
start = time.perf_counter()
for i in range(len(arr)):
    for j in range(len(arr) - i - 1):
        if arr[j] > arr[j+1]:
            arr[j], arr[j+1] = arr[j+1], arr[j]
bubble_time = time.perf_counter() - start

# Built-in sort
arr2 = data.copy()
start = time.perf_counter()
arr2.sort()
builtin_time = time.perf_counter() - start

print(f"Bubble Sort (1000 items): {bubble_time*1000:.2f}ms")
print(f"Built-in Sort (10000 items): {builtin_time*1000:.2f}ms")
print(f"\\nBuilt-in is ~{bubble_time/builtin_time:.0f}x faster (even with 10x more data!)")''',

    "dataframe": '''import pandas as pd
import numpy as np

np.random.seed(42)
df = pd.DataFrame({
    "Product": ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Doohickey"],
    "Q1_Sales": np.random.randint(100, 1000, 5),
    "Q2_Sales": np.random.randint(100, 1000, 5),
    "Q3_Sales": np.random.randint(100, 1000, 5),
    "Q4_Sales": np.random.randint(100, 1000, 5),
})
df["Annual"] = df[["Q1_Sales","Q2_Sales","Q3_Sales","Q4_Sales"]].sum(axis=1)
df["Avg_Quarter"] = df["Annual"] / 4

print("📊 Sales Report")
print("=" * 60)
print(df.to_string(index=False))
print("=" * 60)
print(f"\\nTotal Revenue: ${df['Annual'].sum():,}")
print(f"Top Product: {df.loc[df['Annual'].idxmax(), 'Product']} (${df['Annual'].max():,})")
print(f"Average Quarterly: ${df['Avg_Quarter'].mean():,.0f}")''',

    "barchart": '''import matplotlib.pyplot as plt
import numpy as np

categories = ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust', 'Java']
popularity = [30.3, 18.0, 12.5, 9.2, 8.1, 7.8]
colors = ['#e94560', '#ff6b6b', '#ffa502', '#2ed573', '#1e90ff', '#a855f7']

fig, ax = plt.subplots(figsize=(10, 6))
bars = ax.barh(categories, popularity, color=colors, height=0.6, edgecolor='none')
ax.set_facecolor('#16213e')
ax.set_title('Programming Language Popularity 2026', color='white', fontsize=16, fontweight='bold', pad=15)
ax.set_xlabel('Market Share (%)', color='#a0a0a0', fontsize=12)
ax.tick_params(colors='#a0a0a0', labelsize=11)
for spine in ax.spines.values():
    spine.set_visible(False)
for bar, val in zip(bars, popularity):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f'{val}%', va='center', color='white', fontsize=11, fontweight='bold')
ax.invert_yaxis()
plt.tight_layout()
plt.show()''',

    "scatter": '''import matplotlib.pyplot as plt
import numpy as np

np.random.seed(42)
n = 200
x = np.random.randn(n)
y = 0.7 * x + np.random.randn(n) * 0.5
colors = np.sqrt(x**2 + y**2)

fig, ax = plt.subplots(figsize=(9, 7))
scatter = ax.scatter(x, y, c=colors, cmap='magma', s=60, alpha=0.8, edgecolor='white', linewidth=0.3)
ax.set_facecolor('#16213e')
ax.set_title('Correlation Analysis', color='white', fontsize=16, fontweight='bold')
ax.set_xlabel('Variable X', color='#a0a0a0')
ax.set_ylabel('Variable Y', color='#a0a0a0')
ax.tick_params(colors='#a0a0a0')
for spine in ax.spines.values():
    spine.set_color('#333')
cbar = plt.colorbar(scatter)
cbar.set_label('Distance from origin', color='#a0a0a0')
cbar.ax.tick_params(colors='#a0a0a0')

# Add regression line
z = np.polyfit(x, y, 1)
p = np.poly1d(z)
x_line = np.linspace(x.min(), x.max(), 100)
ax.plot(x_line, p(x_line), color='#e94560', linewidth=2, linestyle='--', label=f'y = {z[0]:.2f}x + {z[1]:.2f}')
ax.legend(facecolor='#1a1a2e', edgecolor='#e94560', labelcolor='white')
plt.tight_layout()
plt.show()

correlation = np.corrcoef(x, y)[0, 1]
print(f"Pearson correlation: {correlation:.4f}")
print(f"R-squared: {correlation**2:.4f}")
print(f"Regression: y = {z[0]:.4f}x + {z[1]:.4f}")'''
}

# --- AI System Prompts ---
SYSTEM_PROMPT_QUERY = """You are CodeExec AI, an expert Python data scientist and coder.
Respond ONLY with a valid JSON object containing these EXACT keys:
- "code": string containing the full executable Python script.
- "explanation": string containing a step-by-step explanation. {explain_instruction}
- "suggestions": string containing code optimization suggestions or further steps.
- "visualization": string summarizing what charts will be generated, if any.

CRITICAL RULES FOR CODE GENERATION:
1. DATA HANDLING:
   - NEVER use 'from datasets import load_dataset' or the HuggingFace datasets library.
   - Use pandas for any data manipulation: pd.read_csv(), pd.read_excel(), pd.read_json(), pd.DataFrame(), etc.
   - If the user provides data inline or asks to generate sample data, create it directly in code.

2. NO USER PROMPTS:
   - NEVER use input(), raw_input(), or any interactive prompts.
   - NEVER write code that asks the user for input.
   - All parameters must be hardcoded or derived from the data itself.
   - If a value is needed, pick a reasonable default or compute it.

3. OUTPUT:
   - ALWAYS use print() to display results to stdout.
   - When generating summary or analysis output, print it clearly with labels.
   - If writing to a file, ALSO print the results to stdout.
   - The code runs in a temp directory, so use simple filenames like 'output.csv' (no absolute paths for output files).

4. VISUALIZATION:
   - Use matplotlib for charts. Always call plt.show() at the end.
   - Charts are captured automatically — no need to save to file.

{multistep_instruction}

No markdown outside the JSON, no extra text."""

SYSTEM_PROMPT_FIX = """You are a Python debugging assistant. The user's code produced an error. Return ONLY the corrected Python code, nothing else. No markdown, no explanation, just raw code.

CRITICAL: 
- NEVER add input() or any interactive prompts to the fixed code.
- NEVER use 'from datasets import load_dataset'.
- Use pandas for reading files: pd.read_csv(), pd.read_excel(), pd.read_json()."""

# --- Specific Instructions ---
EXPLAIN_BEGINNER = "Explain every step in simple, everyday language as if the reader has never coded before. Avoid jargon."
EXPLAIN_TECHNICAL = "Provide a precise technical explanation covering performance, reasoning, and edge cases."

MULTISTEP_INSTRUCTION = (
    "If the user request involves multiple tasks (e.g. 'clean data, compute averages, and plot'), "
    "break it into clearly labeled steps in the code using comments like # Step 1, # Step 2, etc. "
    "Execute them sequentially in a single script."
)

# --- Python Execution Preamble ---
PLOT_CAPTURE_PREAMBLE = '''
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64, json, atexit, os

_codeexec_plots = []
_codeexec_plot_dir = os.environ.get("CODEEXEC_PLOT_DIR", ".")

def _codeexec_save_plots():
    figs = [plt.figure(n) for n in plt.get_fignums()]
    for i, fig in enumerate(figs):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=120, bbox_inches='tight',
                    facecolor='#1a1a2e', edgecolor='none')
        buf.seek(0)
        _codeexec_plots.append(base64.b64encode(buf.read()).decode('utf-8'))
        buf.close()
    if _codeexec_plots:
        manifest = os.path.join(_codeexec_plot_dir, "_plots.json")
        with open(manifest, 'w') as f:
            json.dump(_codeexec_plots, f)

atexit.register(_codeexec_save_plots)

# --- Plugin Architecture Stubs ---
def run_sql_query(query: str):
    print(f"[Plugin: SQL] Executing query: {query}")
    return [{"id": 1, "value": "mock_data"}]

def call_api(endpoint: str, payload: dict = None):
    print(f"[Plugin: API] Calling endpoint {endpoint} with payload {payload}")
    return {"status": 200, "data": "mock_response"}

def analyze_text(text: str):
    print(f"[Plugin: Text] Analyzing text: {text[:20]}...")
    return {"sentiment": "positive", "score": 0.95}
'''


