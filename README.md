# ⚡ CodeExec AI — Smart Code Execution Assistant

> Turn questions into code. Turn code into answers. Instantly.

---

## 🚀 What is CodeExec AI?

CodeExec AI is an intelligent system that lets users **upload datasets, ask questions in plain English, and get instant results with explanations**.

It combines:

* 🤖 LLM-powered **code generation**
* ⚙️ Secure **Python execution**
* 📊 Real-time **data analysis**
* 🧠 Clear **human-friendly explanations**

Think of it like your own AI-powered data analyst — similar to a mini Colab, but automated.

---

## ✨ Key Features

### 📁 Smart Dataset Handling

* Upload CSV / Excel files
* Handles large datasets via Supabase
* Reliable storage (no temp file issues)

### 🤖 AI Code Generation

* Uses IBM Granite / Hugging Face models
* Generates clean Python (Pandas + NumPy)
* Understands natural language queries

### ⚙️ Code Execution Engine

* Runs generated code safely
* Captures outputs and errors
* Returns structured results

### 🧠 Intelligent Explanations

* Explains results clearly
* Describes calculations step-by-step
* Handles messy datasets (missing values, etc.)

### 🔗 MCP Tool Integration

* Structured tool calling
* Clean separation of logic
* Scalable architecture

---

## 🧩 How It Works

```text
Upload Dataset
     ↓
Store in Supabase / Temp Storage
     ↓
User Query ("Calculate average sales")
     ↓
LLM Generates Python Code
     ↓
Execution Engine Runs Code
     ↓
Result Captured
     ↓
LLM Explains Output
     ↓
User Sees Answer 🎉
```

---

## 🛠️ Tech Stack

* 🐍 Python
* ⚡ FastAPI
* 📊 Pandas / NumPy
* 🗄️ Supabase (database + storage)
* 🤖 IBM Granite / Hugging Face APIs
* 🔗 MCP (Model Context Protocol)

---

## ⚙️ Installation

### 1️⃣ Clone Repo

```bash
git clone <your-repo-url>
cd codeexec-ai
```

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Setup Environment Variables

Create a `.env` file:

```env
HF_API_KEY=your_huggingface_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### 4️⃣ Run Server

```bash
uvicorn main:app --reload
```

---

## 🧪 Example

### Input:

```
Calculate average sales
```

### Generated Code:

```python
import pandas as pd

df = pd.read_csv("uploads/data.csv")
result = df["sales"].mean()
result
```

### Output:

```
200
```

### Explanation:

> The average sales value is calculated by summing all sales values and dividing by the number of entries.

---

## 🗄️ Supabase Integration

We use Supabase to:

* Persist datasets securely
* Enable fast retrieval
* Handle large-scale data
* Maintain sync (delete → removed from DB)

This ensures your system is **production-ready and scalable**.

---

## 🔐 Security Considerations

* Sandbox execution environment
* Restricted imports
* File validation
* Size limits for uploads

---

## 🔮 Future Enhancements

* 📈 Data visualization (charts/graphs)
* 🔗 Multi-dataset joins
* 🧠 Auto schema detection
* 💬 Conversational memory
* 🔍 SQL query support

---

## 🌟 Why This Project?

Because analyzing data shouldn’t require writing code manually.

With CodeExec AI:

* Ask questions → get answers
* No boilerplate
* No setup pain
* Just results

---

## 📜 License

MIT

---

## 💡 Contribute

PRs are welcome! Let’s build the future of AI-powered data analysis together 🚀
